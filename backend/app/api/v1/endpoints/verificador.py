"""
verificador.py — "Esse desconto é real?" — veredito factual de preço.

Endpoints públicos do verificador (página /black-friday):
  GET /api/v1/verificador?q=...&limit=12  — busca produtos com histórico medido
  GET /api/v1/verificador/destaques       — descontos reais verificados hoje
  GET /api/v1/verificador/produto/{id}    — veredito de um produto específico

Linguagem sempre factual: preço medido + datas. Nunca acusa a loja.
"""
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, Query, Request
from sqlalchemy import func, select

from app.core.logging import logger
from app.services import text_search
from app.services.price_verdict import verdicts_for

router = APIRouter()

VERDICT_LABEL_FALLBACK = "Histórico curto — ainda medindo"


def _provider_of(affiliate_url: str | None) -> str:
    """Mesma regra do offers_today: 'amazon' na URL → amazon, senão mercadolivre."""
    return "amazon" if "amazon" in (affiliate_url or "").lower() else "mercadolivre"


def _payload(p, verdict: dict | None) -> dict:
    v = verdict or {}
    return {
        "id": str(p.id),
        "title": p.title or "",
        "image_url": p.image_url,
        "affiliate_url": p.affiliate_url,
        "provider": _provider_of(p.affiliate_url),
        "verdict": v.get("verdict", "sem_historico"),
        "verdict_label": v.get("verdict_label", VERDICT_LABEL_FALLBACK),
        "current_price": v.get("current_price"),
        "min_price": v.get("min_price"),
        "min_date": v.get("min_date"),
        "max_price": v.get("max_price"),
        "median_30": v.get("median_30"),
        "pct_vs_median": v.get("pct_vs_median"),
        "days_monitored": v.get("days_monitored", 0),
        "first_date": v.get("first_date"),
        "rise_pct_21d": v.get("rise_pct_21d"),
        "sparkline": v.get("sparkline", []),
    }


async def _check_rate(req: Request) -> None:
    from app.core.rate_limit import check_rate_limit, get_client_ip
    ip = get_client_ip(req)
    if not await check_rate_limit(ip, key="verificador", max_calls=30, window_seconds=60):
        raise HTTPException(status_code=429, detail="Rate limit: max 30 req/min por IP.")


@router.get("/verificador")
async def verificador_search(
    req: Request,
    q: str = Query(..., min_length=3, max_length=80),
    limit: int = Query(default=12, ge=1, le=24),
):
    """Busca produtos com histórico de preço e devolve o veredito de cada um."""
    from app.db.session import get_db
    from app.models.models import AffiliateProduct, AffiliatePriceHistory

    await _check_rate(req)

    toks = text_search.tokens(q)
    if not toks:
        return {"query": q, "results": []}

    since = datetime.now(timezone.utc) - timedelta(days=120)
    hist_count = (
        select(
            AffiliatePriceHistory.product_id.label("product_id"),
            func.count().label("snapshots"),
        )
        .where(AffiliatePriceHistory.recorded_at >= since)
        .group_by(AffiliatePriceHistory.product_id)
        .subquery()
    )

    try:
        async for db in get_db():
            pg = text_search.is_pg(db)
            # AND por token sobre bpt_compact(title): "air fryer" casa
            # "Airfryer", "eletrica" casa "Elétrica", "iphone15" casa "iPhone 15"
            conds = [
                AffiliateProduct.is_active == True,
                AffiliateProduct.price > 0,
                AffiliateProduct.title.isnot(None),
                AffiliateProduct.affiliate_url.isnot(None),
                text_search.match_all(AffiliateProduct.title, toks, pg=pg),
            ]
            stmt = (
                select(AffiliateProduct)
                .join(hist_count, hist_count.c.product_id == AffiliateProduct.id)
                .where(*conds)
                .order_by(hist_count.c.snapshots.desc())
                .limit(40)
            )
            result = await db.execute(stmt)
            products = list(result.scalars().all())

            # Fallback fuzzy p/ erro de digitação: <3 matches + query >=4 chars
            if pg and len(q.strip()) >= 4 and len(products) < 3:
                fuzzy_conds = [
                    AffiliateProduct.is_active == True,
                    AffiliateProduct.price > 0,
                    AffiliateProduct.title.isnot(None),
                    AffiliateProduct.affiliate_url.isnot(None),
                    text_search.fuzzy_clause(AffiliateProduct.title, q),
                ]
                fuzzy_stmt = (
                    select(AffiliateProduct)
                    .join(hist_count, hist_count.c.product_id == AffiliateProduct.id)
                    .where(*fuzzy_conds)
                    .order_by(text_search.fuzzy_rank(AffiliateProduct.title, q))
                    .limit(40)
                )
                fuzzy_result = await db.execute(fuzzy_stmt)
                seen = {p.id for p in products}
                for p in fuzzy_result.scalars().all():
                    if p.id not in seen:
                        seen.add(p.id)
                        products.append(p)

            verdicts = await verdicts_for(db, products)

            results = []
            seen = set()
            for p in products:
                key = p.ml_code or str(p.id)
                if key in seen:
                    continue
                seen.add(key)
                results.append(_payload(p, verdicts.get(p.id)))
                if len(results) >= limit:
                    break
            return {"query": q, "results": results}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Verificador search error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Verificador failed: {str(e)}")


@router.get("/verificador/destaques")
async def verificador_destaques(
    req: Request,
    limit: int = Query(default=12, ge=1, le=24),
):
    """Descontos reais verificados hoje — preço abaixo da média/mínimo histórico.

    Mesma base do /offers/today (preço < max30d * 0.95), mas faixa R$20–3000
    e ordenado pelo veredito (menor_preco/abaixo_media com ≥14 dias medidos).
    """
    from app.db.session import get_db
    from app.models.models import AffiliateProduct, AffiliatePriceHistory
    from app.workers.distributor import _has_recognized_brand, _is_accessory

    await _check_rate(req)

    now = datetime.now(timezone.utc)
    cutoff30 = now - timedelta(days=30)

    max30 = (
        select(
            AffiliatePriceHistory.product_id.label("product_id"),
            func.max(AffiliatePriceHistory.price).label("max30"),
        )
        .where(AffiliatePriceHistory.recorded_at >= cutoff30)
        .group_by(AffiliatePriceHistory.product_id)
        .subquery()
    )

    stmt = (
        select(AffiliateProduct)
        .join(max30, max30.c.product_id == AffiliateProduct.id)
        .where(
            AffiliateProduct.is_active == True,
            AffiliateProduct.price.between(20.0, 3000.0),
            AffiliateProduct.image_url.isnot(None),
            AffiliateProduct.title.isnot(None),
            AffiliateProduct.affiliate_url.isnot(None),
            AffiliateProduct.price < max30.c.max30 * 0.95,
        )
        .order_by((1 - AffiliateProduct.price / max30.c.max30).desc())
        .limit(400)
    )

    try:
        async for db in get_db():
            result = await db.execute(stmt)
            products = [
                p for p in result.scalars().all()
                if not _is_accessory(p.title or "") and _has_recognized_brand(p.title or "")
            ]
            verdicts = await verdicts_for(db, products)

            # monitored_products: produtos com snapshot nos últimos 3 dias
            cutoff3 = now - timedelta(days=3)
            monitored = (await db.execute(
                select(func.count(func.distinct(AffiliatePriceHistory.product_id)))
                .where(AffiliatePriceHistory.recorded_at >= cutoff3)
            )).scalar() or 0
            # since: primeiro snapshot registrado (data)
            first_seen = (await db.execute(
                select(func.min(AffiliatePriceHistory.recorded_at))
            )).scalar()
            since_iso = first_seen.date().isoformat() if first_seen else None

            picked = []
            for p in products:
                v = verdicts.get(p.id) or {}
                if v.get("verdict") not in ("menor_preco", "abaixo_media"):
                    continue
                if (v.get("days_monitored") or 0) < 14:
                    continue
                picked.append((p, v))

            picked.sort(
                key=lambda pv: (pv[1].get("pct_vs_median") is not None,
                                pv[1].get("pct_vs_median") or 0),
                reverse=True,
            )

            results = []
            seen = set()
            for p, v in picked:
                key = p.ml_code or str(p.id)
                if key in seen:
                    continue
                seen.add(key)
                results.append(_payload(p, v))
                if len(results) >= limit:
                    break

            return {
                "monitored_products": int(monitored),
                "since": since_iso,
                "results": results,
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Verificador destaques error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Verificador failed: {str(e)}")


@router.get("/verificador/produto/{product_id}")
async def verificador_produto(
    req: Request,
    product_id: uuid.UUID,
):
    """Veredito de um produto específico pelo id (AffiliateProduct)."""
    from app.db.session import get_db
    from app.models.models import AffiliateProduct

    await _check_rate(req)

    try:
        async for db in get_db():
            product = await db.get(AffiliateProduct, product_id)
            if not product:
                raise HTTPException(status_code=404, detail="Produto não encontrado")
            verdicts = await verdicts_for(db, [product])
            return _payload(product, verdicts.get(product.id))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Verificador produto error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Verificador failed: {str(e)}")
