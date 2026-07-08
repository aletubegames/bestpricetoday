"""
Conversion Tracker — fecha o loop clique → conversão.

Fluxo:
  1. Cron job ou endpoint manual chama poll_all_conversions()
  2. Para cada plataforma, busca orders recentes via API
  3. Tenta vincular order ao click_id via matching por provider/tempo
  4. Salva na tabela conversion_events (evita duplicatas via external_order_id)
  5. Falhas vão para ConversionRetryQueue (até 3 tentativas)
"""
from __future__ import annotations
import hashlib, hmac, time, httpx
from datetime import datetime, timedelta, timezone
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from app.core.config import settings
from app.core.logging import logger
from app.models.models import ConversionEvent, ClickEvent, ConversionRetryQueue


# NOTE: validate_ml_webhook_signature removed (2026-06-26).
# ML affiliate program does not provide webhooks for affiliates.


async def _sign_top(method: str, params: dict, app_key: str, app_secret: str) -> dict:
    """Sign AliExpress Affiliate API request.

    Docs: https://open.alitrip.com/docs/doc.htm?articleId=45802
    Guide: https://vandevliet.me/how-to-make-aliexpress-affiliate-api-call/

    Algoritmo (MD5):
      1. Juntar todos params (exceto sign) ordenados por key: key1value1key2value2...
      2. Envolver com secret: SECRET + sorted_params + SECRET
      3. MD5 → hex → uppercase
    """
    from datetime import timedelta
    import hashlib as _hl
    # AliExpress exige GMT+8 (China time)
    gmt8 = timezone(timedelta(hours=8))
    ts = datetime.now(gmt8).strftime("%Y-%m-%d %H:%M:%S")
    all_params = {
        "app_key": app_key,
        "sign_method": "md5",
        "timestamp": ts,
        "method": method,
        "format": "json",
        "v": "2.0",
        **params,
    }
    # Concatena key+value ordenado
    msg = "".join(f"{k}{v}" for k, v in sorted(all_params.items()))
    # MD5 com secret como "bookends": SECRET + msg + SECRET
    bookend = f"{app_secret}{msg}{app_secret}"
    sig = _hl.md5(bookend.encode()).hexdigest().upper()
    all_params["sign"] = sig
    return all_params


async def _find_matching_click(db: AsyncSession, provider: str, product_title: str = None) -> Optional[str]:
    """
    Vincula uma conversão ao melhor clique correspondente.

    Estratégia em camadas (da mais para a menos precisa):
    1. Clique com affiliate_url contendo short_link_code que já foi redirecionado
       (via ShortLink.source = 'web'/'tiktok_user'/etc)
    2. Clique mais recente do mesmo provider + título similar (fuzzy)
    3. Clique mais recente do mesmo provider nos últimos 30 dias (fallback)
    """
    from app.models.models import ShortLink
    since = datetime.now(timezone.utc) - timedelta(days=30)

    # Camada 1: via ShortLink rastreado — o mais confiável
    # Busca short links do provider com cliques recentes
    if product_title:
        try:
            sl_q = select(ShortLink).where(
                and_(
                    ShortLink.provider == provider,
                    ShortLink.clicks > 0,
                    ShortLink.last_clicked_at >= since,
                )
            ).order_by(ShortLink.last_clicked_at.desc()).limit(5)
            sl_r = await db.execute(sl_q)
            short_links = sl_r.scalars().all()

            # Tentar match por título
            if short_links and product_title:
                title_lower = product_title.lower()
                for sl in short_links:
                    if sl.product_title and any(
                        word in title_lower
                        for word in (sl.product_title.lower().split()[:4])
                        if len(word) > 4
                    ):
                        # Buscar o ClickEvent que usou este short link
                        click_q = select(ClickEvent.id).where(
                            and_(
                                ClickEvent.provider == provider,
                                ClickEvent.clicked_at >= since,
                                ClickEvent.affiliate_url.contains(f"/r/{sl.code}"),
                            )
                        ).order_by(ClickEvent.clicked_at.desc()).limit(1)
                        cr = await db.execute(click_q)
                        click_id = cr.scalar()
                        if click_id:
                            logger.debug(f"Conversion matched via short_link code={sl.code}")
                            return str(click_id)
        except Exception as e:
            logger.warning(f"_find_matching_click layer1 error: {e}")

    # Camada 2: título similar no ClickEvent direto
    if product_title:
        try:
            words = [w for w in product_title.lower().split() if len(w) > 4][:3]
            for word in words:
                q = select(ClickEvent.id).where(
                    and_(
                        ClickEvent.provider == provider,
                        ClickEvent.clicked_at >= since,
                        ClickEvent.product_title.ilike(f"%{word}%"),
                    )
                ).order_by(ClickEvent.clicked_at.desc()).limit(1)
                r = await db.execute(q)
                row = r.scalar()
                if row:
                    logger.debug(f"Conversion matched via title fuzzy word='{word}'")
                    return str(row)
        except Exception as e:
            logger.warning(f"_find_matching_click layer2 error: {e}")

    # Camada 3: fallback — clique mais recente do provider
    q = select(ClickEvent.id).where(
        and_(
            ClickEvent.provider == provider,
            ClickEvent.clicked_at >= since,
        )
    ).order_by(ClickEvent.clicked_at.desc()).limit(1)
    r = await db.execute(q)
    row = r.scalar()
    if row:
        logger.debug(f"Conversion matched via provider fallback provider={provider}")
    return str(row) if row else None


# Keep old name as alias for backward compat
_find_click_by_tracking = _find_matching_click


async def _save_conversion_safe(
    db: AsyncSession,
    external_order_id: str,
    provider: str,
    product_title: Optional[str],
    sale_price: float,
    commission_rate: float,
    commission_value: float,
    status: str,
    click_id: Optional[str] = None,
) -> bool:
    """Save conversion. On failure, add to retry queue."""
    try:
        # Check duplicate
        r = await db.execute(select(ConversionEvent).where(
            ConversionEvent.external_order_id == external_order_id
        ))
        if r.scalar():
            return False  # already saved

        conv = ConversionEvent(
            external_order_id=external_order_id,
            click_id=click_id,
            provider=provider,
            product_title=product_title[:200] if product_title else None,
            sale_price=sale_price,
            commission_rate=commission_rate,
            commission_value=commission_value,
            status=status,
        )
        db.add(conv)
        await db.commit()
        logger.info(f"Conversion saved: {provider} order={external_order_id} commission={commission_value:.2f} status={status}")
        return True
    except Exception as e:
        logger.error(f"Failed to save conversion {external_order_id}: {type(e).__name__}")
        # Add to retry queue
        try:
            await db.rollback()
            retry = ConversionRetryQueue(
                provider=provider,
                external_order_id=external_order_id,
                payload={
                    "external_order_id": external_order_id,
                    "provider": provider,
                    "product_title": product_title,
                    "sale_price": sale_price,
                    "commission_rate": commission_rate,
                    "commission_value": commission_value,
                    "status": status,
                    "click_id": click_id,
                },
                error=str(e)[:500],
            )
            db.add(retry)
            await db.commit()
        except Exception as retry_exc:
            logger.debug(f"Failed to enqueue conversion retry: {type(retry_exc).__name__}")
        return False


# Backward-compat alias used by old code paths
async def _save_conversion(
    db: AsyncSession,
    external_order_id: str,
    provider: str,
    product_title: str,
    sale_price: float,
    commission_rate: float,
    commission_value: float,
    status: str,
    click_id: Optional[str] = None,
) -> bool:
    return await _save_conversion_safe(
        db, external_order_id, provider, product_title,
        sale_price, commission_rate, commission_value, status, click_id
    )


async def process_retry_queue(db: AsyncSession) -> int:
    """Process pending items in retry queue. Called hourly."""
    r = await db.execute(
        select(ConversionRetryQueue).where(
            and_(
                ConversionRetryQueue.resolved == False,
                ConversionRetryQueue.attempts < ConversionRetryQueue.max_attempts,
            )
        ).limit(20)
    )
    items = r.scalars().all()
    processed = 0
    for item in items:
        try:
            p = item.payload
            success = await _save_conversion_safe(
                db, p["external_order_id"], p["provider"], p.get("product_title"),
                p.get("sale_price", 0), p.get("commission_rate", 0),
                p.get("commission_value", 0), p.get("status", "pending"),
                p.get("click_id"),
            )
            item.attempts += 1
            item.last_attempt_at = datetime.now(timezone.utc)
            item.resolved = success
            if not success:
                item.error = "retry failed"
            await db.commit()
            if success:
                processed += 1
        except Exception as e:
            item.attempts += 1
            item.error = str(e)[:500]
            await db.commit()
    return processed


async def poll_aliexpress_orders(db: AsyncSession, since_hours: int = 6) -> list[dict]:
    """Poll AliExpress affiliate orders via aliexpress.affiliate.order.list.

    Docs: https://open.alitrip.com/docs/doc.htm?articleId=45802
    Endpoint: https://api-sg.aliexpress.com/sync
    Method: aliexpress.affiliate.order.list
    Required: start_time, end_time (PST timezone), status
    """
    if not settings.ALIEXPRESS_APP_KEY or not settings.ALIEXPRESS_APP_SECRET:
        return []

    # AliExpress usa PST para start_time/end_time
    from datetime import timedelta
    pst = timezone(timedelta(hours=-8))
    now_pst = datetime.now(pst)
    since_pst = now_pst - timedelta(hours=since_hours)
    fmt = "%Y-%m-%d %H:%M:%S"

    params = {
        "start_time": since_pst.strftime(fmt),
        "end_time": now_pst.strftime(fmt),
        "page_no": "1",
        "page_size": "50",
        "status": "Payment Completed",  # status é obrigatório
    }
    if settings.ALIEXPRESS_TRACKING_ID:
        params["tracking_id"] = settings.ALIEXPRESS_TRACKING_ID

    signed = await _sign_top(
        "aliexpress.affiliate.order.list", params,
        settings.ALIEXPRESS_APP_KEY, settings.ALIEXPRESS_APP_SECRET
    )

    saved = []
    try:
        async with httpx.AsyncClient(timeout=15) as c:
            r = await c.post("https://api-sg.aliexpress.com/sync", data=signed)
            r.raise_for_status()
            data = r.json()

        # Resposta: aliexpress_affiliate_order_list_response
        resp_key = "aliexpress_affiliate_order_list_response"
        resp = data.get(resp_key, {}).get("resp_result", {})
        if resp.get("resp_code") != 200:
            logger.warning(f"AliExpress orders: {resp.get('resp_msg')}")
            return []

        orders = resp.get("result", {}).get("orders", {}).get("order", [])
        for order in orders:
            order_id = str(order.get("order_id", ""))
            status_raw = order.get("order_status", "")
            if "Completed" in status_raw or "Confirmed" in status_raw:
                status = "confirmed"
            elif "refund" in status_raw.lower():
                status = "rejected"
            else:
                status = "pending"

            sale_price = float(order.get("order_amount", 0) or 0)
            commission = float(order.get("estimated_paid_commission", 0) or 0)
            commission_rate_str = str(order.get("commission_rate", "0") or "0").replace("%", "")
            commission_rate = float(commission_rate_str or 0)
            title = (order.get("product_name", "") or "")[:200]

            click_id = await _find_matching_click(db, "aliexpress", title)
            ok = await _save_conversion_safe(
                db, f"ali_{order_id}", "aliexpress", title,
                sale_price, commission_rate, commission, status, click_id
            )
            if ok:
                saved.append({"order_id": order_id, "status": status, "commission": commission})
    except Exception as e:
        logger.error(f"AliExpress order polling failed: {e}")

    return saved


async def poll_lomadee_orders(db: AsyncSession, since_hours: int = 6) -> list[dict]:
    """Poll Lomadee orders via new API (api.lomadee.com.br/affiliate/orders).

    API nova (2025+): autenticação via header x-api-key, não mais token na URL.
    Docs: https://docs.lomadee.com.br/api-reference/affiliate/orders/all
    """
    if not settings.LOMADEE_API_KEY:
        return []

    now = datetime.now(timezone.utc)
    since = now - timedelta(hours=since_hours)

    saved = []
    try:
        url = "https://api.lomadee.com.br/affiliate/orders"
        params = {
            "page": 1,
            "limit": 100,
            "from": since.strftime("%Y-%m-%d"),
            "to": now.strftime("%Y-%m-%d"),
        }
        headers = {"x-api-key": settings.LOMADEE_API_KEY}
        async with httpx.AsyncClient(timeout=15) as c:
            r = await c.get(url, params=params, headers=headers)
            r.raise_for_status()
            data = r.json()

        orders = data.get("data", []) or []
        for item in orders:
            order_data = item.get("data", item)  # compatibilidade
            order_id = str(order_data.get("orderId", order_data.get("id", "")))
            if not order_id:
                continue
            sale_price = float(order_data.get("value", 0) or 0)
            commission_value = float(order_data.get("commission", 0) or 0)
            commission_rate = (commission_value / sale_price * 100) if sale_price else 0
            # Tenta extrair título do primeiro item
            items_list = order_data.get("items", order_data.get("items  ", [])) or []
            title = ""
            if items_list:
                title = (items_list[0].get("name", "") or "")[:200]
            status_raw = str(order_data.get("status", "pending")).lower()
            status = (
                "confirmed" if "approv" in status_raw else
                "rejected" if "reject" in status_raw or "repprov" in status_raw or "cancel" in status_raw else
                "pending"
            )

            click_id = await _find_matching_click(db, "lomadee", title)
            ok = await _save_conversion_safe(
                db, f"lom_{order_id}", "lomadee", title,
                sale_price, commission_rate, commission_value, status, click_id
            )
            if ok:
                saved.append({"order_id": order_id, "status": status, "commission": commission_value})
    except Exception as e:
        logger.error(f"Lomadee commission polling failed: {e}")

    return saved


# NOTE: handle_ml_webhook removed (2026-06-26).
# ML affiliate program does not provide webhooks for affiliates.
# Conversions tracked via scraping (ml_scraper.py) + polling (poll_all_conversions).


async def poll_all_conversions(db: AsyncSession) -> dict:
    """Run all polling with detailed logging."""
    start = datetime.now(timezone.utc)
    results = {}

    logger.info(f"[ConversionPoll] Starting at {start.strftime('%H:%M:%S')}")

    for name, coro_fn in [("aliexpress", poll_aliexpress_orders), ("lomadee", poll_lomadee_orders), ("shopee", poll_shopee_conversions)]:
        try:
            saved = await coro_fn(db)
            results[name] = {"saved": len(saved), "items": saved}
            logger.info(f"[ConversionPoll] {name}: {len(saved)} new conversions")
        except Exception as e:
            results[name] = {"saved": 0, "error": str(e)}
            logger.error(f"[ConversionPoll] {name} failed: {e}")

    # Process retry queue
    retried = await process_retry_queue(db)
    results["retried"] = retried

    elapsed = (datetime.now(timezone.utc) - start).total_seconds()
    logger.info(f"[ConversionPoll] Done in {elapsed:.1f}s — {sum(r.get('saved', 0) if isinstance(r, dict) else 0 for r in results.values())} total new")

    return {k: (v.get("saved", v) if isinstance(v, dict) else v) for k, v in results.items()}


# ─── Shopee conversion polling ────────────────────────────────────────────────

async def poll_shopee_conversions(db: AsyncSession, since_hours: int = 6) -> list[dict]:
    """
    Busca conversões da Shopee via GraphQL Affiliate API.
    Retorna lista de conversões novas salvas.
    """
    import hashlib, time, httpx, json

    app_id = settings.SHOPEE_APP_ID
    secret = settings.SHOPEE_SECRET
    if not app_id or not secret:
        return []

    now = datetime.now(timezone.utc)
    since = now - timedelta(hours=since_hours)

    query = """
    {
      conversionReport(
        purchaseTimeStart: %d
        purchaseTimeEnd: %d
        conversionStatus: ALL
        limit: 50
      ) {
        nodes {
          clickTime
          purchaseTime
          conversionStatus
          estimatedTotalCommission
          orders {
            orderId
            orderStatus
            items {
              itemId
              itemName
              actualAmount
              itemTotalCommission
              itemSellerCommissionRate
              fraudStatus
            }
          }
        }
        pageInfo { hasNextPage }
      }
    }
    """ % (int(since.timestamp()), int(now.timestamp()))

    body = json.dumps({"query": query}, separators=(",", ":"), ensure_ascii=False)
    ts = int(time.time())
    sig = hashlib.sha256(f"{app_id}{ts}{body}{secret}".encode()).hexdigest()
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"SHA256 Credential={app_id},Timestamp={ts},Signature={sig}",
    }

    saved = []
    try:
        async with httpx.AsyncClient(timeout=15) as c:
            r = await c.post(
                "https://open-api.affiliate.shopee.com.br/graphql",
                content=body, headers=headers
            )
        r.raise_for_status()
        d = r.json()
        errors = d.get("errors", [])
        if errors:
            logger.warning(f"Shopee conversion API: {errors[0].get('message','')}")
            return []

        nodes = d.get("data", {}).get("conversionReport", {}).get("nodes", []) or []
        for node in nodes:
            status_raw = node.get("conversionStatus", "")
            status = "confirmed" if "COMPLETED" in status_raw else \
                     "rejected"  if "CANCELLED" in status_raw else "pending"

            commission_total = float(node.get("estimatedTotalCommission", 0) or 0)
            orders = node.get("orders", []) or []

            for order in orders:
                order_id = str(order.get("orderId", ""))
                if not order_id:
                    continue

                items = order.get("items", []) or []
                for item in items:
                    if item.get("fraudStatus") == "FRAUDULENT":
                        continue

                    external_id = f"shopee_{order_id}_{item.get('itemId','')}"
                    sale_price = float(item.get("actualAmount", 0) or 0)
                    commission_value = float(item.get("itemTotalCommission", 0) or 0)
                    commission_rate = float(item.get("itemSellerCommissionRate", 0) or 0)
                    title = str(item.get("itemName", ""))[:200]

                    click_id = await _find_matching_click(db, "shopee", title)
                    ok = await _save_conversion_safe(
                        db, external_id, "shopee", title,
                        sale_price, commission_rate, commission_value, status, click_id
                    )
                    if ok:
                        saved.append({"order_id": order_id, "status": status,
                                      "commission": commission_value})
                        logger.info(f"Shopee: salvo order={order_id} item={title[:40]} "
                                    f"comissão=R${commission_value:.2f}")
    except Exception as e:
        logger.error(f"Shopee conversion polling failed: {type(e).__name__}")

    return saved
