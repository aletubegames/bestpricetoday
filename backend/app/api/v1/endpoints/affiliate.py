"""
Affiliate Products — BestPriceToday
CRUD de produtos afiliados ML (links manuais do admin) + geração de conteúdo via Claude.

Endpoints:
  GET    /affiliate/products              → lista todos com cálculo de comissão
  POST   /affiliate/products              → adiciona produto (bloqueia duplicata de affiliate_url)
  PATCH  /affiliate/products/{id}         → edita título/preço/comissão/etc
  DELETE /affiliate/products/{id}         → remove (soft delete: is_active=False)
  POST   /affiliate/products/seed         → importa lista em lote (ignora duplicatas)
  POST   /affiliate/generate/marketplace  → gera anúncio Facebook Marketplace via Claude
  POST   /affiliate/generate/tiktok       → gera script TikTok via Claude
  POST   /affiliate/generate/youtube      → gera roteiro YouTube via Claude
  POST   /affiliate/shortlink             → cria short link rastreado para produto
"""

import uuid
import json
import httpx
from typing import Optional, List
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.db.session import get_db
from app.models.models import AffiliateProduct, ShortLink
from app.core.config import settings
from app.api.v1.endpoints.admin import require_admin

router = APIRouter(prefix="/affiliate", tags=["affiliate"])


# ─── Schemas ─────────────────────────────────────────────────────────────────

class ProductCreate(BaseModel):
    ml_code:        Optional[str]   = None
    affiliate_url:  str
    title:          Optional[str]   = None
    price:          Optional[float] = None
    commission_pct: Optional[float] = None
    category:       Optional[str]   = None
    image_url:      Optional[str]   = None
    notes:          Optional[str]   = None

class ProductUpdate(BaseModel):
    title:          Optional[str]   = None
    price:          Optional[float] = None
    commission_pct: Optional[float] = None
    category:       Optional[str]   = None
    image_url:      Optional[str]   = None
    notes:          Optional[str]   = None
    is_active:      Optional[bool]  = None

class SeedItem(BaseModel):
    ml_code:       str
    affiliate_url: str

class SeedRequest(BaseModel):
    items: List[SeedItem]

class GenerateRequest(BaseModel):
    product_id: str  # UUID do AffiliateProduct

class ShortLinkRequest(BaseModel):
    product_id: str
    source:     str = "manual"
    campaign:   Optional[str] = None


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _calc(p: AffiliateProduct) -> dict:
    """Calcula comissão e estimativas."""
    price    = p.price or 0.0
    pct      = p.commission_pct or 0.0
    per_sale = round(price * pct / 100, 2)
    return {
        "id":               str(p.id),
        "ml_code":          p.ml_code,
        "affiliate_url":    p.affiliate_url,
        "title":            p.title,
        "price":            price,
        "commission_pct":   pct,
        "commission_value": per_sale,
        "estimate_10d":     round(per_sale * 10, 2),
        "estimate_month":   round(per_sale * 10 * 30, 2),
        "category":         p.category,
        "image_url":        p.image_url,
        "notes":            p.notes,
        "is_active":        p.is_active,
        "created_at":       p.created_at.isoformat() if p.created_at else None,
    }

def _gen_code(length: int = 8) -> str:
    return uuid.uuid4().hex[:length].upper()

async def _claude(prompt: str) -> str:
    """Chama Claude Haiku e retorna texto. Fallback vazio se sem API key."""
    if not settings.ANTHROPIC_API_KEY:
        return ""
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key":         settings.ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type":      "application/json",
            },
            json={
                "model":      "claude-3-haiku-20240307",
                "max_tokens": 2000,
                "messages":   [{"role": "user", "content": prompt}],
            },
        )
        r.raise_for_status()
        return r.json()["content"][0]["text"].strip()


# ─── CRUD ─────────────────────────────────────────────────────────────────────

@router.get("/products")
async def list_products(
    _:  str          = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(AffiliateProduct).order_by(AffiliateProduct.created_at.desc())
    )
    products = result.scalars().all()
    return {"total": len(products), "products": [_calc(p) for p in products]}


@router.post("/products", status_code=201)
async def add_product(
    data: ProductCreate,
    _:   str          = Depends(require_admin),
    db:  AsyncSession = Depends(get_db),
):
    # Bloqueia duplicata
    existing = (await db.execute(
        select(AffiliateProduct).where(AffiliateProduct.affiliate_url == data.affiliate_url)
    )).scalar()
    if existing:
        raise HTTPException(status_code=409, detail="affiliate_url já existe na base")

    p = AffiliateProduct(
        id            = uuid.uuid4(),
        ml_code       = data.ml_code,
        affiliate_url = data.affiliate_url,
        title         = data.title,
        price         = data.price,
        commission_pct= data.commission_pct,
        category      = data.category,
        image_url     = data.image_url,
        notes         = data.notes,
    )
    db.add(p)
    await db.commit()
    await db.refresh(p)
    return _calc(p)


@router.patch("/products/{product_id}")
async def update_product(
    product_id: str,
    data: ProductUpdate,
    _:   str          = Depends(require_admin),
    db:  AsyncSession = Depends(get_db),
):
    p = (await db.execute(
        select(AffiliateProduct).where(AffiliateProduct.id == product_id)
    )).scalar()
    if not p:
        raise HTTPException(status_code=404, detail="Produto não encontrado")

    for field, value in data.model_dump(exclude_none=True).items():
        setattr(p, field, value)
    p.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(p)
    return _calc(p)


@router.delete("/products/{product_id}")
async def delete_product(
    product_id: str,
    _:   str          = Depends(require_admin),
    db:  AsyncSession = Depends(get_db),
):
    p = (await db.execute(
        select(AffiliateProduct).where(AffiliateProduct.id == product_id)
    )).scalar()
    if not p:
        raise HTTPException(status_code=404, detail="Produto não encontrado")
    p.is_active = False
    p.updated_at = datetime.now(timezone.utc)
    await db.commit()
    return {"status": "deleted", "id": product_id}


@router.post("/products/seed")
async def seed_products(
    data: SeedRequest,
    _:   str          = Depends(require_admin),
    db:  AsyncSession = Depends(get_db),
):
    """Importa lista em lote. Ignora duplicatas silenciosamente."""
    added = 0
    skipped = 0
    for item in data.items:
        existing = (await db.execute(
            select(AffiliateProduct).where(AffiliateProduct.affiliate_url == item.affiliate_url)
        )).scalar()
        if existing:
            skipped += 1
            continue
        db.add(AffiliateProduct(
            id            = uuid.uuid4(),
            ml_code       = item.ml_code,
            affiliate_url = item.affiliate_url,
        ))
        added += 1
    await db.commit()
    return {"added": added, "skipped": skipped}


@router.post("/products/enrich")
async def enrich_products(
    _:  str          = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Para cada produto sem título, busca na API oficial do ML usando o
    ml_code como query. Usa o OAuth token armazenado no banco.
    100% dentro dos Termos de Uso do programa de afiliados ML.
    """
    from app.services.ml_token_service import get_token as get_ml_token

    token = await get_ml_token(db)
    if not token:
        raise HTTPException(
            status_code=400,
            detail="Token ML não configurado. Faça OAuth em /auth/ml/authorize primeiro."
        )

    result_q = await db.execute(
        select(AffiliateProduct).where(
            AffiliateProduct.title == None,
            AffiliateProduct.is_active == True,
        )
    )
    products = result_q.scalars().all()

    enriched = 0
    failed   = 0
    skipped  = 0

    async with httpx.AsyncClient(timeout=10) as client:
        for p in products:
            if not p.ml_code:
                skipped += 1
                continue
            try:
                r = await client.get(
                    "https://api.mercadolibre.com/products/search",
                    params={"site_id": "MLB", "q": p.ml_code, "limit": 1},
                    headers={"Authorization": f"Bearer {token}"},
                )
                if r.status_code != 200:
                    failed += 1
                    continue

                results = r.json().get("results", [])
                if not results:
                    failed += 1
                    continue

                item = results[0]
                pid  = item.get("id") or item.get("catalog_product_id")

                # Buscar detalhes completos (preço + imagem)
                if pid:
                    r2 = await client.get(
                        f"https://api.mercadolibre.com/products/{pid}",
                        params={"includes": "buy_box_winner"},
                        headers={"Authorization": f"Bearer {token}"},
                    )
                    if r2.status_code == 200:
                        detail   = r2.json()
                        bb       = detail.get("buy_box_winner") or {}
                        price    = float(bb.get("price") or 0) or None
                        pictures = detail.get("pictures") or item.get("pictures") or []
                        image    = pictures[0].get("url", "").replace("-F.jpg", "-O.jpg") if pictures else None
                        name     = detail.get("name") or item.get("name") or ""
                    else:
                        name  = item.get("name") or ""
                        price = None
                        image = None
                else:
                    name  = item.get("name") or ""
                    price = None
                    image = None

                if name:
                    p.title     = name
                    p.price     = price or p.price
                    p.image_url = image or p.image_url
                    enriched += 1
                else:
                    failed += 1

            except Exception:
                failed += 1

    await db.commit()
    return {"enriched": enriched, "failed": failed, "skipped": skipped, "total": len(products)}


class EnrichByUrlRequest(BaseModel):
    product_id: str
    ml_url: str  # URL completa: https://www.mercadolivre.com.br/MLB-XXXXXXX-...


class EnrichBatchRequest(BaseModel):
    items: dict[str, str]  # {ml_code: url_produto_ml}


async def _fetch_ml_item(ml_url: str, token: str) -> dict:
    """
    Extrai dados do produto ML a partir da URL.
    Tenta 3 abordagens em sequência:
    1. /products/{catalog_id} — para URLs /p/MLB...
    2. /products/search com o slug da URL como query
    3. /items/{item_id} — para URLs de item direto
    """
    import re

    # Extrair catalog product id (/p/MLB...) ou item id
    catalog_match = re.search(r'/p/(MLB\d+)', ml_url)
    item_match    = re.search(r'MLB-?(\d+)', ml_url)

    async with httpx.AsyncClient(timeout=10) as client:
        headers = {"Authorization": f"Bearer {token}"}

        # 1. Catalog product endpoint
        if catalog_match:
            pid = catalog_match.group(1)
            r = await client.get(
                f"https://api.mercadolibre.com/products/{pid}",
                params={"includes": "buy_box_winner"},
                headers=headers,
            )
            if r.status_code == 200:
                d = r.json()
                bb = d.get("buy_box_winner") or {}
                pictures = d.get("pictures") or []
                image = pictures[0].get("url", "").replace("-F.jpg", "-O.jpg") if pictures else None
                return {"title": d.get("name") or d.get("title"), "price": bb.get("price"), "image_url": image, "mlb_id": pid}

        # 2. /products/search com slug da URL como query
        slug_match = re.search(r'com\.br/([^/?#]+)', ml_url)
        if slug_match:
            slug  = slug_match.group(1).replace("-", " ")
            # Remover o MLB id do slug para não confundir a busca
            query = re.sub(r'MLB\d+', '', slug).strip()
            if len(query) > 5:
                r2 = await client.get(
                    "https://api.mercadolibre.com/products/search",
                    params={"site_id": "MLB", "q": query, "limit": 1},
                    headers=headers,
                )
                if r2.status_code == 200:
                    results = r2.json().get("results", [])
                    if results:
                        item = results[0]
                        pid2 = item.get("id") or item.get("catalog_product_id")
                        pictures = item.get("pictures") or []
                        image = pictures[0].get("url", "").replace("-F.jpg", "-O.jpg") if pictures else None
                        # Tentar buscar buy_box_winner
                        price = None
                        if pid2:
                            r3 = await client.get(
                                f"https://api.mercadolibre.com/products/{pid2}",
                                params={"includes": "buy_box_winner"},
                                headers=headers,
                            )
                            if r3.status_code == 200:
                                d3  = r3.json()
                                bb3 = d3.get("buy_box_winner") or {}
                                price = bb3.get("price")
                                pics3 = d3.get("pictures") or []
                                image = pics3[0].get("url", "").replace("-F.jpg", "-O.jpg") if pics3 else image
                        return {"title": item.get("name") or item.get("title"), "price": price, "image_url": image, "mlb_id": pid2}

        # 3. Item direto
        if item_match:
            mlb_id = f"MLB{item_match.group(1)}"
            r4 = await client.get(
                f"https://api.mercadolibre.com/items/{mlb_id}",
                headers=headers,
            )
            if r4.status_code == 200:
                d4 = r4.json()
                pictures = d4.get("pictures") or []
                image = pictures[0].get("url", "").replace("-F.jpg", "-O.jpg") if pictures else None
                return {"title": d4.get("title"), "price": d4.get("price"), "image_url": image, "mlb_id": mlb_id}

    return {}


@router.post("/products/enrich-url")
async def enrich_by_url(
    data: EnrichByUrlRequest,
    _:   str          = Depends(require_admin),
    db:  AsyncSession = Depends(get_db),
):
    """Preenche 1 produto com título/preço/imagem a partir da URL do produto ML."""
    from app.services.ml_token_service import get_token as get_ml_token
    token = await get_ml_token(db)
    if not token:
        raise HTTPException(status_code=400, detail="Token ML não configurado.")
    p = (await db.execute(select(AffiliateProduct).where(AffiliateProduct.id == data.product_id))).scalar()
    if not p:
        raise HTTPException(status_code=404, detail="Produto não encontrado")
    info = await _fetch_ml_item(data.ml_url, token)
    if not info.get("title"):
        raise HTTPException(status_code=400, detail=f"Não foi possível extrair dados de: {data.ml_url}")
    p.title     = info["title"]
    p.price     = info.get("price") or p.price
    p.image_url = info.get("image_url") or p.image_url
    await db.commit()
    await db.refresh(p)
    return _calc(p)


@router.post("/products/enrich-batch")
async def enrich_batch(
    data: EnrichBatchRequest,
    _:   str          = Depends(require_admin),
    db:  AsyncSession = Depends(get_db),
):
    """
    Preenche vários produtos de uma vez.
    Body: {"items": {"S5L99N-Y7WN": "https://www.mercadolivre.com.br/MLB-XXXXXXX-..."}}
    """
    from app.services.ml_token_service import get_token as get_ml_token
    import asyncio
    token = await get_ml_token(db)
    if not token:
        raise HTTPException(status_code=400, detail="Token ML não configurado.")
    result_q = await db.execute(select(AffiliateProduct).where(AffiliateProduct.is_active == True))
    products  = {p.ml_code: p for p in result_q.scalars().all() if p.ml_code}

    async def _enrich_one(ml_code: str, ml_url: str):
        p = products.get(ml_code)
        if not p:
            return False
        try:
            info = await _fetch_ml_item(ml_url, token)
            if info.get("title"):
                p.title     = info["title"]
                p.price     = info.get("price") or p.price
                p.image_url = info.get("image_url") or p.image_url
                return True
        except Exception:
            pass
        return False

    results  = await asyncio.gather(*[_enrich_one(c, u) for c, u in data.items.items()])
    enriched = sum(1 for r in results if r)
    failed   = [c for c, r in zip(data.items.keys(), results) if not r]
    await db.commit()
    return {"enriched": enriched, "failed": failed, "total": len(data.items)}



@router.post("/generate/marketplace")
async def generate_marketplace_ad(
    data: GenerateRequest,
    _:   str          = Depends(require_admin),
    db:  AsyncSession = Depends(get_db),
):
    """Gera anúncio completo para Facebook Marketplace."""
    p = (await db.execute(
        select(AffiliateProduct).where(AffiliateProduct.id == data.product_id)
    )).scalar()
    if not p:
        raise HTTPException(status_code=404, detail="Produto não encontrado")

    title   = p.title or "Produto"
    price   = p.price or 0
    pct     = p.commission_pct or 0
    cat     = p.category or "Eletrônicos"
    url     = p.affiliate_url

    prompt = f"""Você é um especialista em vendas no Facebook Marketplace.

Produto: {title}
Preço: R$ {price:.2f}
Categoria: {cat}
Link: {url}

Gere um anúncio COMPLETO para Facebook Marketplace. Responda SOMENTE com JSON válido:

{{
  "titulo": "título do anúncio até 80 chars, claro e direto",
  "preco": {price:.2f},
  "descricao": "descrição detalhada do produto, 3-5 parágrafos, benefícios, características, garantia ML",
  "categoria": "{cat}",
  "condicao": "Novo",
  "tags_busca": ["tag1", "tag2", "tag3", "tag4", "tag5 com erro proposital para ser achado"],
  "sku": "{(p.ml_code or 'ML')}-{datetime.now().strftime('%d%m%y')}",
  "texto_x1": "mensagem para enviar ao comprador quando ele entrar em contato, explicando segurança ML, entrega rápida, garantia"
}}"""

    raw = await _claude(prompt)

    # Parse JSON ou fallback
    try:
        if raw:
            text = raw
            if "```" in text:
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            result = json.loads(text)
        else:
            raise ValueError("sem resposta")
    except Exception:
        result = {
            "titulo":     title[:80],
            "preco":      price,
            "descricao":  f"{title}\n\nProduto novo, entrega pelo Mercado Livre. Se não chegar, ML devolve o dinheiro.\n\nLink: {url}",
            "categoria":  cat,
            "condicao":   "Novo",
            "tags_busca": [title, cat, "novo", "entrega rápida", "mercado livre"],
            "sku":        f"{(p.ml_code or 'ML')}-{datetime.now().strftime('%d%m%y')}",
            "texto_x1":   f"Olá! O produto é 100% novo e vendido pelo Mercado Livre. A entrega é garantida — se não chegar, o ML devolve seu dinheiro. Link para compra: {url}",
        }

    result["affiliate_url"] = url
    return result


@router.post("/generate/tiktok")
async def generate_tiktok_script(
    data: GenerateRequest,
    _:   str          = Depends(require_admin),
    db:  AsyncSession = Depends(get_db),
):
    """Gera script TikTok estruturado (Gancho→Problema→Solução→Prova→CTA)."""
    p = (await db.execute(
        select(AffiliateProduct).where(AffiliateProduct.id == data.product_id)
    )).scalar()
    if not p:
        raise HTTPException(status_code=404, detail="Produto não encontrado")

    title = p.title or "Produto"
    price = p.price or 0
    url   = p.affiliate_url

    prompt = f"""Você é um especialista em vídeos virais no TikTok que vende produtos como afiliado.

Produto: {title}
Preço: R$ {price:.2f}
Link afiliado: {url}

Crie um script de vídeo TikTok viral de 15-22 segundos para vender esse produto.
Responda SOMENTE com JSON válido:

{{
  "gancho_0_3s": "frase de abertura impactante que gera medo, curiosidade ou identificação. Max 15 palavras.",
  "problema_3_6s": "mostra a dor/risco do espectador sem o produto. Max 15 palavras.",
  "solucao_6_12s": "apresenta o produto como solução, descreve o visual do vídeo. Max 20 palavras.",
  "prova_12_18s": "benefício concreto + prova social resumida. Max 15 palavras.",
  "cta_18_22s": "call to action. Sempre termina com 'Link na bio'. Max 10 palavras.",
  "legenda": "legenda completa do TikTok até 200 chars com emojis e link na bio",
  "hashtags": ["lista", "de", "5", "hashtags", "relevantes"],
  "musica_sugerida": "estilo/mood de música ideal para esse vídeo",
  "dica_visual": "instrução do que mostrar na tela em cada parte"
}}"""

    raw = await _claude(prompt)

    try:
        if raw:
            text = raw
            if "```" in text:
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            result = json.loads(text)
        else:
            raise ValueError()
    except Exception:
        result = {
            "gancho_0_3s":    f"Você ainda vive sem {title}?",
            "problema_3_6s":  "Eu também achei que não precisava... até que precisei.",
            "solucao_6_12s":  f"Aí descobri o {title} por R$ {price:.2f} no Mercado Livre.",
            "prova_12_18s":   "Chegou em 2 dias, funcionou perfeitamente.",
            "cta_18_22s":     "Link na bio para garantir o seu!",
            "legenda":        f"🔥 {title} por R$ {price:.2f}! Link na bio 👆 #mercadolivre #oferta",
            "hashtags":       ["mercadolivre", "oferta", "desconto", "tiktokbrasil", "fyp"],
            "musica_sugerida": "trending upbeat",
            "dica_visual":    "Mostre o produto sendo usado no dia a dia",
        }

    result["affiliate_url"] = url
    return result


@router.post("/generate/youtube")
async def generate_youtube_script(
    data: GenerateRequest,
    _:   str          = Depends(require_admin),
    db:  AsyncSession = Depends(get_db),
):
    """Gera roteiro YouTube + descrição SEO."""
    p = (await db.execute(
        select(AffiliateProduct).where(AffiliateProduct.id == data.product_id)
    )).scalar()
    if not p:
        raise HTTPException(status_code=404, detail="Produto não encontrado")

    title = p.title or "Produto"
    price = p.price or 0
    url   = p.affiliate_url

    prompt = f"""Você é um especialista em YouTube que faz reviews de produtos afiliados.

Produto: {title}
Preço: R$ {price:.2f}
Link afiliado: {url}

Crie roteiro e metadados para vídeo de review no YouTube.
Responda SOMENTE com JSON válido:

{{
  "titulo_video": "título SEO até 70 chars, keyword no início, sem clickbait excessivo",
  "roteiro": {{
    "intro_0_30s": "script da introdução, apresenta o produto e o que o espectador vai ver",
    "contexto_30_90s": "por que alguém precisa desse produto, casos de uso reais",
    "demonstracao_90_180s": "o que mostrar do produto, características principais, como funciona",
    "prova_social_180_240s": "citar avaliações reais do ML, número de vendas, credibilidade ML",
    "comparativo_240_300s": "comparar com alternativas, por que esse produto se destaca",
    "cta_300s": "call to action com link na descrição, pedir like/inscrição"
  }},
  "descricao_youtube": "descrição SEO completa, até 400 chars, parágrafos, link afiliado incluso, keywords naturais",
  "tags": ["lista", "de", "12", "tags", "youtube", "mix", "broad", "nicho"],
  "timestamps": ["0:00 Introdução", "0:30 Por que usar", "1:30 Demonstração", "3:00 Avaliações", "4:00 Vale a pena?", "5:00 Link e desconto"],
  "thumbnail_texto": "texto para thumbnail (máx 4 palavras em caps)",
  "keyword_principal": "keyword principal do vídeo para SEO"
}}"""

    raw = await _claude(prompt)

    try:
        if raw:
            text = raw
            if "```" in text:
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            result = json.loads(text)
        else:
            raise ValueError()
    except Exception:
        result = {
            "titulo_video":   f"{title} - Vale a Pena? Review Completo {datetime.now().year}",
            "roteiro":        {"intro_0_30s": f"Hoje vou te mostrar tudo sobre o {title}"},
            "descricao_youtube": f"Review completo do {title} por R$ {price:.2f}.\n🛒 Compre aqui: {url}\n\n#review #mercadolivre",
            "tags":           [title, "review", "mercadolivre", "vale a pena", "oferta"],
            "timestamps":     ["0:00 Introdução", "1:00 Review", "3:00 Vale a pena?"],
            "thumbnail_texto": "VALE A PENA?",
            "keyword_principal": title,
        }

    result["affiliate_url"] = url
    return result


# ─── Short Link ───────────────────────────────────────────────────────────────


# ─── Import por categoria ───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────

class ImportCategoryRequest(BaseModel):
    query: str
    limit: int = 10
    category: str = ""
    commission_pct: float = 0.0


@router.post("/products/import-category")
async def import_category(
    data: ImportCategoryRequest,
    _:   str          = Depends(require_admin),
    db:  AsyncSession = Depends(get_db),
):
    """
    Busca produtos no ML por query/categoria usando o token OAuth
    e importa automaticamente com título, preço e imagem.
    Links de afiliado são gerados com o APP_ID configurado.
    Ignora duplicatas.
    """
    from app.services.ml_token_service import get_token as get_ml_token

    token = await get_ml_token(db)
    if not token:
        raise HTTPException(status_code=400, detail="Token ML não configurado.")

    limit = min(data.limit, 20)

    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.get(
            "https://api.mercadolibre.com/products/search",
            params={"site_id": "MLB", "q": data.query, "limit": limit * 2},
            headers={"Authorization": f"Bearer {token}"},
        )
        if r.status_code != 200:
            raise HTTPException(status_code=400, detail=f"ML retornou {r.status_code}")

        results = r.json().get("results", [])
        if not results:
            raise HTTPException(status_code=404, detail="Nenhum produto encontrado")

        added   = 0
        skipped = 0
        imported_products = []

        for item in results[:limit]:
            pid  = item.get("id") or item.get("catalog_product_id")
            name = item.get("name") or item.get("title") or ""
            if not name or not pid:
                skipped += 1
                continue

            affiliate_url = f"https://www.mercadolivre.com.br/p/{pid}?matt_tool={settings.MERCADOLIVRE_APP_ID}"

            existing = (await db.execute(
                select(AffiliateProduct).where(AffiliateProduct.affiliate_url == affiliate_url)
            )).scalar()
            if existing:
                skipped += 1
                continue

            price = None
            image = None
            r2 = await client.get(
                f"https://api.mercadolibre.com/products/{pid}",
                params={"includes": "buy_box_winner"},
                headers={"Authorization": f"Bearer {token}"},
            )
            if r2.status_code == 200:
                d2   = r2.json()
                bb   = d2.get("buy_box_winner") or {}
                price = bb.get("price")
                pics = d2.get("pictures") or item.get("pictures") or []
                image = pics[0].get("url", "").replace("-F.jpg", "-O.jpg") if pics else None

            p = AffiliateProduct(
                id            = uuid.uuid4(),
                ml_code       = pid,
                affiliate_url = affiliate_url,
                title         = name,
                price         = price,
                commission_pct= data.commission_pct or None,
                category      = data.category or None,
                image_url     = image,
            )
            db.add(p)
            added += 1
            imported_products.append({"id": str(p.id), "title": name, "price": price, "mlb_id": pid})

        await db.commit()
        return {"added": added, "skipped": skipped, "products": imported_products}


@router.post("/shortlink")
async def create_shortlink(
    data: ShortLinkRequest,
    _:   str          = Depends(require_admin),
    db:  AsyncSession = Depends(get_db),
):
    """Cria short link rastreado para produto afiliado."""
    p = (await db.execute(
        select(AffiliateProduct).where(AffiliateProduct.id == data.product_id)
    )).scalar()
    if not p:
        raise HTTPException(status_code=404, detail="Produto não encontrado")

    code = None
    for _ in range(10):
        candidate = _gen_code(8)
        existing  = (await db.execute(
            select(ShortLink).where(ShortLink.code == candidate)
        )).scalar()
        if not existing:
            code = candidate
            break
    if not code:
        raise HTTPException(status_code=500, detail="Falha ao gerar código")

    link = ShortLink(
        code          = code,
        affiliate_url = p.affiliate_url,
        provider      = "mercadolivre",
        product_title = (p.title or p.ml_code or "")[:200],
        price         = p.price,
        source        = data.source,
        campaign      = data.campaign or f"affiliate_{p.ml_code or str(p.id)[:8]}",
    )
    db.add(link)
    await db.commit()

    return {
        "code":      code,
        "short_url": f"https://bestpricetoday.vercel.app/r/{code}",
        "product":   p.title or p.ml_code,
    }
