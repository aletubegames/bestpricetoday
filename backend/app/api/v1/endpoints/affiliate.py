"""
Affiliate Products — BestPriceToday
CRUD manual de produtos afiliados ML + geradores de conteúdo + short links.
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
    product_id: str

class ShortLinkRequest(BaseModel):
    product_id: str
    source:     str = "manual"
    campaign:   Optional[str] = None


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _calc(p: AffiliateProduct) -> dict:
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
        "estimate_month":   per_sale,
        "category":         p.category,
        "image_url":        p.image_url,
        "notes":            p.notes,
        "is_active":        p.is_active,
        "created_at":       p.created_at.isoformat() if p.created_at else None,
    }

def _gen_code(length: int = 8) -> str:
    return uuid.uuid4().hex[:length].upper()

async def _claude(prompt: str) -> str:
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

def _parse_json(raw: str) -> dict:
    if not raw:
        raise ValueError("empty")
    text = raw
    if "```" in text:
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    return json.loads(text.strip())


# ─── CRUD ─────────────────────────────────────────────────────────────────────

@router.get("/products")
async def list_products(
    _:  str          = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(AffiliateProduct)
        .where(AffiliateProduct.is_active == True)
        .order_by(AffiliateProduct.created_at.desc())
    )
    products = result.scalars().all()
    return {"total": len(products), "products": [_calc(p) for p in products]}


@router.post("/products", status_code=201)
async def add_product(
    data: ProductCreate,
    _:   str          = Depends(require_admin),
    db:  AsyncSession = Depends(get_db),
):
    existing = (await db.execute(
        select(AffiliateProduct).where(AffiliateProduct.affiliate_url == data.affiliate_url)
    )).scalar()
    if existing:
        raise HTTPException(status_code=409, detail="affiliate_url já existe na base")

    p = AffiliateProduct(
        id             = uuid.uuid4(),
        ml_code        = data.ml_code,
        affiliate_url  = data.affiliate_url,
        title          = data.title,
        price          = data.price,
        commission_pct = data.commission_pct,
        category       = data.category,
        image_url      = data.image_url,
        notes          = data.notes,
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
    p.is_active  = False
    p.updated_at = datetime.now(timezone.utc)
    await db.commit()
    return {"status": "deleted", "id": product_id}


@router.post("/products/seed")
async def seed_products(
    data: SeedRequest,
    _:   str          = Depends(require_admin),
    db:  AsyncSession = Depends(get_db),
):
    """Importa lista em lote. Ignora duplicatas por affiliate_url."""
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


# ─── Geradores de conteúdo ────────────────────────────────────────────────────

@router.post("/generate/marketplace")
async def generate_marketplace_ad(
    data: GenerateRequest,
    _:   str          = Depends(require_admin),
    db:  AsyncSession = Depends(get_db),
):
    p = (await db.execute(
        select(AffiliateProduct).where(AffiliateProduct.id == data.product_id)
    )).scalar()
    if not p:
        raise HTTPException(status_code=404, detail="Produto não encontrado")

    title = p.title or "Produto"
    price = p.price or 0
    cat   = p.category or "Eletrônicos"
    url   = p.affiliate_url

    ml_code_str = p.ml_code or "ML"
    sku_str = f"{ml_code_str}-{datetime.now().strftime('%d%m%y')}"
    notes_hint = f"\nDetalhes adicionais: {p.notes}" if p.notes else ""

    prompt = f"""Você é copywriter sênior especializado em Facebook Marketplace com 10 anos de experiência.

Produto: {title}
Preço: R$ {price:.2f}
Categoria: {cat}
Link afiliado: {url}
SKU: {sku_str}{notes_hint}

Crie um anúncio que CONVERTA. Use gatilhos de urgência, prova social, segurança de compra.
O texto_x1 deve ser personalizado para ESTE produto específico, não genérico.
Varie o tom conforme a categoria: eletrônicos = técnico+objetivo, moda = aspiracional, casa = praticidade.

Responda SOMENTE JSON válido:
{{
  "titulo": "título até 80 chars — use números/benefícios concretos quando possível",
  "preco": {price:.2f},
  "descricao": "3-5 parágrafos: 1) benefício principal em linguagem do comprador 2) diferenciais e specs relevantes 3) garantia ML + entrega. Use quebras de linha reais.",
  "categoria": "{cat}",
  "condicao": "Novo",
  "tags_busca": ["6 tags de busca reais que um comprador digitaria"],
  "sku": "{sku_str}",
  "texto_x1": "mensagem de 2-3 linhas para responder 'ainda disponível?' — mencione o produto pelo nome, preço exato, mencione proteção ML, CTA com senso de urgência"
}}"""

    try:
        result = _parse_json(await _claude(prompt))
    except Exception:
        result = {
            "titulo":    title[:80],
            "preco":     price,
            "descricao": (
                f"✅ {title} — produto NOVO, pronta entrega pelo Mercado Livre.\n\n"
                f"💳 Parcele em até 12x sem juros.\n"
                f"📦 Entrega rápida para todo o Brasil.\n\n"
                f"🔒 Compra 100% protegida pelo Mercado Livre: se não chegar, você recebe o dinheiro de volta. Sem discussão."
            ),
            "categoria": cat,
            "condicao":  "Novo",
            "tags_busca": [title.split()[0] if title else cat, cat, "novo", "mercado livre", "entrega rápida", "original"],
            "sku":        sku_str,
            "texto_x1":  (
                f"Olá! Sim, o {title} está disponível por R$ {price:.2f} 🔥\n"
                f"Compra pelo link do ML: entrega rápida, parcelas sem juros e proteção total de pagamento.\n"
                f"Posso te enviar o link agora. Tem mais interessados então garante logo! 🛒"
            ),
        }

    result["affiliate_url"] = url
    return result


@router.post("/generate/tiktok")
async def generate_tiktok_script(
    data: GenerateRequest,
    _:   str          = Depends(require_admin),
    db:  AsyncSession = Depends(get_db),
):
    p = (await db.execute(
        select(AffiliateProduct).where(AffiliateProduct.id == data.product_id)
    )).scalar()
    if not p:
        raise HTTPException(status_code=404, detail="Produto não encontrado")

    title = p.title or "Produto"
    price = p.price or 0
    url   = p.affiliate_url

    notes_hint = f"\nDetalhes: {p.notes}" if p.notes else ""
    cat_hint = f" (categoria: {p.category})" if p.category else ""

    prompt = f"""Você é roteirista de TikTok com +50 vídeos virais (>1M views). Especialidade: afiliados brasileiros.

Produto: {title}{cat_hint}
Preço: R$ {price:.2f}
Link: {url}{notes_hint}

REGRAS DE OURO DO TIKTOK VIRAL:
- Gancho: primeiros 2s decidem tudo. Use INTERRUPÇÃO DE PADRÃO (pergunta provocativa, afirmação chocante, ou começa no meio da ação)
- Ritmo: frases curtas. Sem enrolação. Cada segundo tem que valer.
- Prova social > Promessa vaga. Números reais > Adjetivos.
- CTA natural, não robótico. "Tô deixando o link" > "Clique no link"
- Som-off friendly: texto na tela deve fazer sentido sem áudio

Estrutura 20-25s otimizada para retenção.

Responda SOMENTE JSON válido:
{{
  "segments": {{
    "gancho": "abertura 0-3s: interrompe o scroll. Pode ser pergunta, stat chocante ou situação real. Max 15 palavras.",
    "problema": "3-8s: dor real que o espectador sente. Específico, não genérico. Max 20 palavras.",
    "solucao": "8-15s: apresenta o produto como solução natural — com o preço. Direto. Max 25 palavras.",
    "prova": "15-20s: prova concreta: avaliação real, número de vendidos, benefício específico e mensurável. Max 20 palavras.",
    "cta": "20-25s: CTA conversacional, não robótico. Mencione urgência real se houver. Max 12 palavras."
  }},
  "legenda": "legenda com gancho emocional nos primeiros 100 chars (aparece antes do 'ver mais'), emojis estratégicos, 180-220 chars total",
  "hashtags": ["8 hashtags: mix de nicho+trending+produto+comportamento"],
  "musica_sugerida": "nome de trilha ou estilo específico que combina com o tom do vídeo (ex: drill brasileiro para urgência, lofi para produto premium, trend atual)",
  "dica_visual": "storyboard rápido: o que aparece na tela em cada segmento — close, texto overlay, transição sugerida",
  "variacao_b": "gancho alternativo completamente diferente para testar (A/B) — formato diferente do principal"
}}"""

    try:
        raw = await _claude(prompt)
        result = _parse_json(raw)
    except Exception:
        result = {
            "segments": {
                "gancho":   f"Esse produto mudou minha rotina e custa menos de R$ {price:.0f}.",
                "problema": "Você provavelmente já procurou algo assim e desistiu por achar caro ou complicado.",
                "solucao":  f"{title} resolve isso por R$ {price:.2f} com entrega pelo Mercado Livre.",
                "prova":    "Mais de 100 avaliações positivas. Chegou em 2 dias, funcionou de primeira.",
                "cta":      "Tô deixando o link na bio pra você ver. Corre que esgota.",
            },
            "legenda":        f"Encontrei {title} por R$ {price:.2f} e valeu cada centavo 🔥 Link na bio 👆",
            "hashtags":       ["mercadolivre", "achadodomercadolivre", "ofertaml", "tiktokbrasil", "fyp", "indicação", "produtobom", "compraonline"],
            "musica_sugerida": "trending upbeat brasileiro — busque 'viral brazil 2024' no TikTok",
            "dica_visual":    "0-3s: texto grande na tela com o gancho | 3-15s: produto em uso real, close | 15-20s: tela do ML com preço | 20-25s: flecha animada apontando para bio",
            "variacao_b":     f"POV: você comprou {title} sem esperar muito e ficou impressionado — mostre o unboxing reação real.",
        }

    result["affiliate_url"] = url
    return result


@router.post("/generate/youtube")
async def generate_youtube_script(
    data: GenerateRequest,
    _:   str          = Depends(require_admin),
    db:  AsyncSession = Depends(get_db),
):
    p = (await db.execute(
        select(AffiliateProduct).where(AffiliateProduct.id == data.product_id)
    )).scalar()
    if not p:
        raise HTTPException(status_code=404, detail="Produto não encontrado")

    title = p.title or "Produto"
    price = p.price or 0
    url   = p.affiliate_url

    notes_hint = f"\nDetalhes: {p.notes}" if p.notes else ""
    year = datetime.now().year

    prompt = f"""Você é estrategista de YouTube com foco em afiliados brasileiros. Canal de review + indicação.

Produto: {title}
Preço: R$ {price:.2f}
Link afiliado: {url}{notes_hint}

Objetivo: vídeo de 4-6 minutos que ranqueia no YouTube E converte em clique de afiliado.

ESTRATÉGIA YOUTUBE QUE FUNCIONA:
- Título: keyword principal no início, número ou promessa específica, gera curiosidade (não clickbait)
- Roteiro: começa com a conclusão ("Esse produto vale ou não vale?"), depois justifica — mantém engajamento
- Descrição: primeiras 2 linhas são o que aparece antes do 'ver mais' — coloque o link lá
- Thumbnail texto: max 4 palavras, legível em miniatura, instiga clique
- Tags: mix de long-tail + produto + comparativos

Responda SOMENTE JSON válido:
{{
  "titulo_video": "título YouTube até 70 chars — keyword no início, específico, gera clique",
  "roteiro": "roteiro COMPLETO como texto corrido, com marcações de tempo. Ex:\n[0:00] Frase de abertura com a conclusão antecipada...\n[0:30] Contexto: por que alguém precisa desse produto...\n[1:30] Demonstração detalhada...\n[3:00] Prova social e avaliações...\n[4:30] Comparativo rápido com alternativas...\n[5:30] Veredicto final + CTA com link",
  "descricao": "descrição SEO completa: primeiras 2 linhas com link afiliado e benefício principal. Depois: sobre o produto, timestamps, hashtags. Total 800-1000 chars.",
  "tags": ["15 tags: keyword principal, produto, review, vale a pena, comparativo, alternativas, marca, nicho, afiliado, mercadolivre, + variações long-tail"],
  "timestamps": ["0:00 - label", "0:30 - label", "1:30 - label", "3:00 - label", "4:30 - label", "5:30 - label"],
  "thumbnail_texto": "MAX 4 PALAVRAS CAPS",
  "keyword_principal": "keyword SEO principal que o vídeo rankeia",
  "titulo_alternativo": "segunda opção de título com ângulo diferente para A/B test"
}}"""

    try:
        raw = await _claude(prompt)
        result = _parse_json(raw)
    except Exception:
        result = {
            "titulo_video":     f"{title} - Vale a Pena? Review Honesto {year}",
            "roteiro": (
                f"[0:00] Vou te contar direto: o {title} por R$ {price:.2f} é uma das melhores compras que você pode fazer hoje. Mas tem um porém — fica até o final.\n\n"
                f"[0:30] Quem precisa disso? Se você já procurou uma solução pra [problema do nicho] e não achou nada com bom custo-benefício, esse vídeo é pra você.\n\n"
                f"[1:30] Na prática: [demonstração de uso real, specs principais, o que impressiona].\n\n"
                f"[3:00] O que outras pessoas estão falando: mais de 100 avaliações, nota alta, entrega confirmada.\n\n"
                f"[4:30] Por que esse e não o concorrente? Preço, garantia ML, reputação do vendedor.\n\n"
                f"[5:30] Veredicto: COMPRO SIM. Link na descrição — compra pelo Mercado Livre, proteção total."
            ),
            "descricao": (
                f"🛒 {title} por R$ {price:.2f} — link afiliado: {url}\n"
                f"Review completo e honesto. Compra pelo Mercado Livre com proteção total.\n\n"
                f"TIMESTAMPS:\n"
                f"0:00 Veredicto antecipado\n0:30 Quem precisa\n1:30 Demo\n3:00 Avaliações\n4:30 Comparativo\n5:30 Conclusão\n\n"
                f"#review #mercadolivre #{(title.split()[0] if title else 'produto').lower()} #vaealapena #afiliados"
            ),
            "tags":             [title, f"{title} review", f"{title} vale a pena", "mercadolivre", "review", "vale a pena", "afiliado ml", "compra online", "indicação"],
            "timestamps":       ["0:00 - Veredicto antecipado", "0:30 - Quem precisa", "1:30 - Demonstração", "3:00 - Avaliações", "4:30 - Comparativo", "5:30 - Conclusão"],
            "thumbnail_texto":  "VALE A PENA?",
            "keyword_principal": f"{title} review",
            "titulo_alternativo": f"Comprei o {title} por R$ {price:.2f} — Honestidade Total",
        }

    result["affiliate_url"] = url
    return result


# ─── Short Link ───────────────────────────────────────────────────────────────

@router.post("/shortlink")
async def create_shortlink(
    data: ShortLinkRequest,
    _:   str          = Depends(require_admin),
    db:  AsyncSession = Depends(get_db),
):
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
        "short_url": f"{settings.PUBLIC_SITE_URL}/r/{code}",
        "product":   p.title or p.ml_code,
    }
