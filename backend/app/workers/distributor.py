"""
Distributor — Orquestrador central de distribuição de ofertas.

Recebe uma oferta → cria short link → gera conteúdo (IA opcional) → posta nos canais ativos.

Canais suportados (fase 2):
  - Telegram (canal @BestPriceToday) — já funcional
  - Facebook (multi-página: "bestpricetoday" + "Achados Shopee" + outras) — funcional (requer OAuth ativo no banco)
  - TikTok / YouTube Shorts — futuro (precisa OAuth + Content API)

Filtros de qualidade:
  - commission_value >= R$ 8 (estimativa)
  - discount >= 15%
  - price >= R$ 20 (evita frete proporcional alto)
  - não postado nas últimas 24h (dedup)

Cada post = 1 short link /r/{code} único com source = canal.
"""

import asyncio
import hashlib
import httpx
import json
import os
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from app.core.config import settings
from app.core.logging import logger


# ─── Config ───────────────────────────────────────────────────────────────────

BOT_TOKEN = settings.TELEGRAM_BOT_TOKEN
CHANNEL_ID = settings.TELEGRAM_CHANNEL_ID
API_URL = settings.INTERNAL_API_URL
ADMIN_KEY = settings.ADMIN_MANAGER_KEY

# Filtros de qualidade
MIN_PRICE = 20.0          # preço mínimo
MIN_DISCOUNT = 15.0       # desconto mínimo %
DEDUP_TTL_HOURS = 24      # não repete a mesma oferta em 24h

# Dedup file (compartilhado com broadcaster)
DEDUP_FILE = Path("/tmp/broadcaster_dedup.json")

PROVIDER_EMOJI = {
    "aliexpress": "🔴", "shopee": "🟠", "mercadolivre": "🟡",
    "amazon": "📦", "lomadee": "🟣", "kabum": "🟢", "awin": "🔵",
}


def fmt_brl(v: float) -> str:
    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


# ─── Deduplicação ─────────────────────────────────────────────────────────────

def _load_dedup() -> dict:
    try:
        if DEDUP_FILE.exists():
            return json.loads(DEDUP_FILE.read_text())
    except Exception:
        pass
    return {}


def _save_dedup(data: dict):
    try:
        DEDUP_FILE.write_text(json.dumps(data))
    except Exception:
        pass


def _url_hash(url: str) -> str:
    return hashlib.md5(url.encode()).hexdigest()[:12]


def already_posted(url: str) -> bool:
    data = _load_dedup()
    h = _url_hash(url)
    if h not in data:
        return False
    posted_at = datetime.fromisoformat(data[h])
    return datetime.now(timezone.utc) - posted_at < timedelta(hours=DEDUP_TTL_HOURS)


def mark_posted(url: str):
    data = _load_dedup()
    cutoff = datetime.now(timezone.utc) - timedelta(hours=DEDUP_TTL_HOURS)
    data = {h: ts for h, ts in data.items()
            if datetime.fromisoformat(ts) > cutoff}
    data[_url_hash(url)] = datetime.now(timezone.utc).isoformat()
    _save_dedup(data)


# ─── Short link creation ──────────────────────────────────────────────────────

async def create_short_link(offer: dict, source: str, campaign: Optional[str] = None) -> Optional[str]:
    """Cria um short link /r/{code} único para esta oferta + canal."""
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.post(
                f"{API_URL}/api/v1/links/create",
                json={
                    "affiliate_url": offer.get("affiliate_url", ""),
                    "provider": offer.get("provider", ""),
                    "product_title": offer.get("title", "")[:200],
                    "price": offer.get("final_price", 0),
                    "image_url": offer.get("image_url", ""),
                    "original_price": offer.get("original_price", 0),
                    "source": source,
                    "campaign": campaign,
                },
            )
            if r.status_code == 200:
                data = r.json()
                return data.get("short_url") or data.get("url")
    except Exception as e:
        logger.warning(f"Distributor: short link creation failed: {e}")
    return None


# ─── IA: gerador de legenda (OpenRouter) ──────────────────────────────────────

async def generate_caption_ai(offer: dict) -> Optional[str]:
    """Gera legenda persuasiva via OpenRouter (1 chamada, modelo barato)."""
    if not settings.OPENROUTER_API_KEY:
        return None

    title = offer.get("title", "")[:100]
    price = offer.get("final_price", 0)
    original = offer.get("original_price", 0)
    discount = offer.get("discount_percent", 0)
    provider = offer.get("provider", "")
    shipping_free = offer.get("shipping_free", False)
    economy = offer.get("economy", 0)

    prompt = f"""Escreva uma legenda curta e persuasiva (máximo 280 chars) para uma oferta no Telegram.
Produto: {title}
Preço: {fmt_brl(price)} (original: {fmt_brl(original) if original else "n/a"})
Desconto: {discount:.0f}%
Loja: {provider}
Frete grátis: {"sim" if shipping_free else "não"}
Economia: {fmt_brl(economy) if economy > 0 else "n/a"}

Regras:
- Use emojis com moderação (2-3 no máximo)
- Tom entusiasmado mas não exagerado
- Português brasileiro
- NÃO inclua links (serão adicionados separadamente)
- Foque no benefício/economia, não só no produto
- Máximo 2 linhas além do título"""

    try:
        async with httpx.AsyncClient(timeout=30) as c:
            r = await c.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
                    "HTTP-Referer": settings.PUBLIC_SITE_URL,
                    "Content-Type": "application/json",
                },
                json={
                    "model": "openrouter/free",  # router automatico para modelos free disponiveis
                    "messages": [
                        {"role": "system", "content": "Voce e um copywriter de ofertas. Responda APENAS com o caption final, sem explicacao ou opcoes."},
                        {"role": "user", "content": prompt},
                    ],
                    "max_tokens": 150,
                    "temperature": 0.8,
                },
            )
            if r.status_code == 200:
                data = r.json()
                msg = data["choices"][0]["message"]
                # Alguns modelos free retornam content=None e usam reasoning
                caption = msg.get("content")
                if not caption and msg.get("reasoning"):
                    # Extrai ultima linha do reasoning como caption
                    lines = [l.strip() for l in msg["reasoning"].split("\n") if l.strip() and not l.startswith("#")]
                    caption = lines[-1] if lines else None
                if caption:
                    caption = caption.strip()
                    if caption:
                        logger.info(f"Distributor: AI caption generated ({len(caption)} chars) model={data.get('model','?')}")
                        return caption
                logger.warning(f"Distributor: AI caption empty response, model={data.get('model','?')}")
            else:
                logger.warning(f"Distributor: OpenRouter error {r.status_code}: {r.text[:200]}")
    except Exception as e:
        logger.warning(f"Distributor: AI caption failed: {e}")

    return None


def build_caption_fallback(offer: dict, short_url: str) -> str:
    """Legenda padrão (sem IA) — formato do broadcaster atual."""
    title = offer.get("title", "")[:80]
    price = offer.get("final_price", 0)
    original = offer.get("original_price", 0)
    discount = offer.get("discount_percent", 0)
    shipping_free = offer.get("shipping_free", False)
    provider = offer.get("provider", "loja")
    economy = offer.get("economy", 0)
    score = offer.get("score", 0)
    emoji = PROVIDER_EMOJI.get(provider, "🏪")
    now = datetime.now().strftime("%d/%m %H:%M")

    lines = [f"🔥 *OFERTA — {now}*\n"]

    if discount >= 5 and not offer.get("is_fake_discount"):
        lines.append(f"🏷️ *-{discount:.0f}% de desconto!*")

    lines.append(f"📦 {title}")
    lines.append("")

    if original and original > price:
        lines.append(f"~~De {fmt_brl(original)}~~")
    lines.append(f"💵 *{fmt_brl(price)}*")

    if shipping_free:
        lines.append("✅ Frete grátis")
    if economy > 10:
        lines.append(f"💰 Economize {fmt_brl(economy)}")

    lines.append(f"\n{emoji} Via *{provider.upper()}*")
    if score >= 60:
        lines.append(f"⭐ Score: {score:.0f}/100")

    lines.append(f"\n👉 [Ver oferta e comprar]({short_url})")
    lines.append(f"\n🛍️ @BestPriceToday| {settings.PUBLIC_SITE_URL.replace('https://', '')}")

    return "\n".join(lines)


async def build_caption(offer: dict, short_url: str) -> str:
    """Tenta gerar legenda com IA; se falhar, usa fallback."""
    ai_caption = await generate_caption_ai(offer)
    if ai_caption:
        # Adiciona link e rodapé à legenda IA
        emoji = PROVIDER_EMOJI.get(offer.get("provider", ""), "🏪")
        provider = offer.get("provider", "loja")
        now = datetime.now().strftime("%d/%m %H:%M")

        lines = [f"🔥 *OFERTA — {now}*\n"]
        lines.append(ai_caption)
        lines.append(f"\n{emoji} Via *{provider.upper()}*")
        lines.append(f"\n👉 [Ver oferta e comprar]({short_url})")
        lines.append(f"\n🛍️ @BestPriceToday| {settings.PUBLIC_SITE_URL.replace('https://', '')}")
        return "\n".join(lines)

    return build_caption_fallback(offer, short_url)


def build_caption_facebook(offer: dict) -> str:
    """Legenda para Facebook/Instagram — SEM link no corpo do post.

    Estratégia anti-banimento (política Meta 2026):
    - Links no corpo do post = alcance limitado (2/mês para não-verificados)
    - Links de afiliado no corpo = risco de banimento
    - Solução: CTA 'Link nos comentários' + link fixado no 1º comentário

    O short_url é postado separadamente como comentário fixado.
    """
    title = offer.get("title", "")[:80]
    price = offer.get("final_price", 0)
    original = offer.get("original_price", 0)
    discount = offer.get("discount_percent", 0)
    shipping_free = offer.get("shipping_free", False)
    provider = offer.get("provider", "loja")
    economy = offer.get("economy", 0)
    score = offer.get("score", 0)
    emoji = PROVIDER_EMOJI.get(provider, "🏪")
    now = datetime.now().strftime("%d/%m %H:%M")

    lines = [f"🔥 OFERTA — {now}\n"]

    if discount >= 5 and not offer.get("is_fake_discount"):
        lines.append(f"🏷️ -{discount:.0f}% de desconto!")

    lines.append(f"📦 {title}")
    lines.append("")

    if original and original > price:
        lines.append(f"De {fmt_brl(original)}")
    lines.append(f"💵 {fmt_brl(price)}")

    if shipping_free:
        lines.append("✅ Frete grátis")
    if economy > 10:
        lines.append(f"💰 Economize {fmt_brl(economy)}")

    lines.append(f"\n{emoji} Via {provider.upper()}")
    if score >= 60:
        lines.append(f"⭐ Score: {score:.0f}/100")

    # CTA SEM link — direciona para os comentários
    lines.append("\n👇 Link de compra nos comentários (fixado)")
    lines.append(f"\n🛍️ BestPriceToday — Menor Preço do Brasil")

    return "\n".join(lines)


def build_youtube_description(offer: dict, affiliate_url: str, short_url: str) -> str:
    """Descrição para YouTube — COM link direto da loja + disclosure (política 2026).

    YouTube permite links de afiliado na descrição (diferente do Facebook).
    Requisitos:
    - Disclosure obrigatório nas primeiras linhas (FTC + YouTube)
    - Link direto da loja (Amazon, Shopee, etc.) — permitido
    - Short link também (para tracking interno)
    - Data da oferta (para vídeos perecíveis não enganarem no futuro)
    """
    title = offer.get("title", "")[:80]
    price = offer.get("final_price", 0)
    original = offer.get("original_price", 0)
    discount = offer.get("discount_percent", 0)
    shipping_free = offer.get("shipping_free", False)
    provider = offer.get("provider", "loja")
    economy = offer.get("economy", 0)
    score = offer.get("score", 0)
    emoji = PROVIDER_EMOJI.get(provider, "🏪")
    now = datetime.now().strftime("%d/%m/%Y")

    lines = []

    # 1. Disclosure obrigatório (FTC + YouTube) — primeiras linhas
    lines.append("Este vídeo contém links de afiliado. Posso ganhar uma comissão se você comprar por eles.")
    lines.append("")

    # 2. Título da oferta
    lines.append(f"🔥 {title}")
    lines.append(f"📅 Oferta do dia: {now}")
    lines.append("")

    # 3. Preço
    if original and original > price:
        lines.append(f"De R$ {original:.2f}")
    lines.append(f"💵 R$ {price:.2f}")
    if discount >= 5:
        lines.append(f"🏷️ -{discount:.0f}% de desconto")
    if shipping_free:
        lines.append("✅ Frete grátis")
    if economy > 10:
        lines.append(f"💰 Economize R$ {economy:.2f}")

    lines.append("")

    # 4. Links — direto da loja + short link para tracking
    lines.append("🛒 Compre aqui (link direto):")
    lines.append(affiliate_url)
    lines.append("")
    lines.append("🔗 Ou pelo BestPriceToday (com tracking de preço):")
    lines.append(short_url)

    lines.append("")

    # 5. Sobre o canal
    lines.append("━━━━━━━━━━━━━━━━━━━━")
    lines.append("BestPriceToday — Menor Preço do Brasil")
    lines.append("Compare preços em Mercado Livre, Amazon, Shopee, KaBuM e mais.")
    lines.append("Cupons automáticos + cashback + histórico de preços.")
    lines.append(f"{settings.PUBLIC_SITE_URL}")
    lines.append("━━━━━━━━━━━━━━━━━━━━")

    # 6. Hashtags SEO
    tags = ["#oferta", "#desconto", f"#{provider}", "#bestpricetoday", "#promoção"]
    if discount >= 30:
        tags.append("#ofertaimperdível")
    lines.append(" ".join(tags))

    return "\n".join(lines)


# ─── Telegram poster ──────────────────────────────────────────────────────────

async def post_to_telegram(offer: dict, caption: str) -> dict:
    """Posta oferta no canal Telegram com foto + caption."""
    if not BOT_TOKEN or not CHANNEL_ID:
        return {"ok": False, "error": "Telegram not configured"}

    image_url = offer.get("image_url", "")
    affiliate_url = offer.get("affiliate_url", "")

    try:
        async with httpx.AsyncClient(timeout=15) as c:
            if image_url and image_url.startswith("http"):
                r = await c.post(
                    f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto",
                    data={
                        "chat_id": CHANNEL_ID,
                        "photo": image_url,
                        "caption": caption,
                        "parse_mode": "Markdown",
                    }
                )
                if r.status_code == 200:
                    mark_posted(affiliate_url)
                    msg_id = r.json().get("result", {}).get("message_id")
                    return {"ok": True, "message_id": msg_id, "method": "photo"}

                # Se foto falhou (URL inválida), tenta texto
                logger.warning(f"Distributor: Telegram photo failed ({r.status_code}), trying text")

            r = await c.post(
                f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                data={
                    "chat_id": CHANNEL_ID,
                    "text": caption,
                    "parse_mode": "Markdown",
                    "disable_web_page_preview": "false",
                }
            )
            if r.status_code == 200:
                mark_posted(affiliate_url)
                msg_id = r.json().get("result", {}).get("message_id")
                return {"ok": True, "message_id": msg_id, "method": "text"}

            return {"ok": False, "error": f"Telegram API error: {r.status_code} {r.text[:200]}"}

    except Exception as e:
        logger.error(f"Distributor: Telegram error: {e}")
        return {"ok": False, "error": str(e)}


# ─── Facebook poster (multi-página: "bestpricetoday" + outras) ────────────────

async def _get_facebook_pages() -> list[dict]:
    """Busca TODAS as páginas Facebook ativas do banco (page_id + page_token).
    Retorna [] se não houver página conectada ou todos os tokens expirados.
    Suporta múltiplas páginas (ex: "Achados Shopee" antiga + "bestpricetoday" nova).
    """
    try:
        from app.db.session import AsyncSessionLocal
        from app.models.models import FacebookAccount
        from sqlalchemy import select

        async with AsyncSessionLocal() as db:
            stmt = select(FacebookAccount).where(
                FacebookAccount.is_active == True,
                FacebookAccount.page_id != "user_token",
            ).order_by(FacebookAccount.updated_at.desc())
            result = await db.execute(stmt)
            accounts = result.scalars().all()
            if not accounts:
                return []

            now = datetime.now(timezone.utc)
            valid = []
            for acct in accounts:
                # Verifica expiração
                if acct.token_expires_at:
                    exp = acct.token_expires_at
                    if exp.tzinfo is None:
                        exp = exp.replace(tzinfo=timezone.utc)
                    if exp < now:
                        logger.warning(f"Distributor: Facebook page '{acct.page_name}' token expirado — refazer OAuth")
                        continue
                valid.append({
                    "page_id": acct.page_id,
                    "page_name": acct.page_name,
                    "access_token": acct.access_token,
                })
            return valid
    except Exception as e:
        logger.error(f"Distributor: erro ao buscar páginas Facebook: {e}")
        return []


async def _post_to_single_facebook_page(page: dict, offer: dict, caption: str, short_url: str) -> dict:
    """Posta oferta em UMA página Facebook com estratégia anti-banimento.

    Estratégia (política Meta 2026):
    1. Posta foto + caption SEM link no corpo (evita limite de 2 links/mês + ban)
    2. Posta comentário com o short link
    3. Fixa o comentário no topo

    Retorna dict com resultado.
    """
    page_id = page["page_id"]
    page_token = page["access_token"]
    page_name = page.get("page_name") or page_id
    image_url = offer.get("image_url", "")
    affiliate_url = offer.get("affiliate_url", "")

    try:
        from app.integrations.instagram import ig_fb_client

        # 1. Postar foto + caption (SEM link no corpo)
        if image_url and image_url.startswith("http"):
            data = await ig_fb_client.publish_photo_facebook(
                page_id=page_id,
                page_token=page_token,
                image_url=image_url,
                caption=caption,
            )
            post_id = data.get("post_id") or data.get("id")
            method = "photo"
        else:
            # Sem imagem: posta texto no feed
            async with httpx.AsyncClient(timeout=15) as c:
                r = await c.post(
                    f"https://graph.facebook.com/v25.0/{page_id}/feed",
                    params={"access_token": page_token, "message": caption},
                )
                if r.status_code != 200:
                    return {"ok": False, "error": f"Facebook feed API error: {r.status_code} {r.text[:200]}", "page_name": page_name}
                post_id = r.json().get("id")
                method = "text"

        logger.info(f"Distributor: Facebook {method} posted on '{page_name}' — post_id={post_id}")

        # 2. Postar comentário com o short link
        comment_text = f"🛒 Compre aqui: {short_url}"
        comment_id = None
        try:
            comment_data = await ig_fb_client.post_comment_facebook(
                post_id=post_id,
                page_token=page_token,
                message=comment_text,
            )
            comment_id = comment_data.get("id")
            logger.info(f"Distributor: Comment with link posted on '{page_name}' — comment_id={comment_id}")

            # 3. Fixar o comentário no topo
            if comment_id:
                pinned = await ig_fb_client.pin_comment_facebook(
                    comment_id=comment_id,
                    page_token=page_token,
                )
                if pinned:
                    logger.info(f"Distributor: Comment pinned on '{page_name}'")
                else:
                    logger.warning(f"Distributor: Could not pin comment on '{page_name}' (non-critical)")
        except Exception as comment_err:
            logger.warning(f"Distributor: Failed to post/pin comment on '{page_name}': {comment_err} (post still live)")

        return {
            "ok": True,
            "post_id": post_id,
            "comment_id": comment_id,
            "method": method,
            "page_name": page_name,
            "link_in_comment": comment_id is not None,
        }

    except Exception as e:
        logger.error(f"Distributor: Facebook error on '{page_name}': {e}")
        return {"ok": False, "error": str(e), "page_name": page_name}


async def post_to_facebook(offer: dict, caption: str, short_url: str = "") -> dict:
    """Posta oferta em TODAS as páginas Facebook ativas com estratégia anti-banimento.

    Multi-página: posta na "bestpricetoday" E na antiga "Achados Shopee"
    (ou quaisquer outras páginas ativas no banco). Cada página recebe um post
    independente — se uma falhar, as outras ainda recebem.

    Estratégia anti-banimento (política Meta 2026):
    - Caption NÃO contém link de afiliado (evita banimento + limite de 2 links/mês)
    - Short link é postado como comentário fixado em cada post
    - Usa Graph API: POST /{page_id}/photos + /{post_id}/comments + pin
    """
    pages = await _get_facebook_pages()
    if not pages:
        return {"ok": False, "error": "Nenhuma página Facebook conectada (refazer OAuth em /api/v1/aletube/auth/facebook)"}

    affiliate_url = offer.get("affiliate_url", "")
    results = []
    ok_count = 0

    for page in pages:
        result = await _post_to_single_facebook_page(page, offer, caption, short_url)
        results.append(result)
        if result.get("ok"):
            ok_count += 1
        # Rate limit entre páginas (evita bloqueio da Graph API)
        if len(pages) > 1:
            await asyncio.sleep(3)

    # Marca como postado se pelo menos uma página recebeu
    if ok_count > 0:
        mark_posted(affiliate_url)

    return {
        "ok": ok_count > 0,
        "pages_posted": ok_count,
        "pages_total": len(pages),
        "results": results,
        "page_names": [r.get("page_name") for r in results if r.get("ok")],
    }


# ─── Click tracking ───────────────────────────────────────────────────────────

async def register_click(offer: dict, source: str):
    """Registra o clique no backend para tracking."""
    if not ADMIN_KEY:
        return
    try:
        async with httpx.AsyncClient(timeout=5) as c:
            await c.post(f"{API_URL}/api/v1/admin/clicks", json={
                "offer_id": offer.get("product_id", ""),
                "provider": offer.get("provider", ""),
                "product_title": offer.get("title", "")[:80],
                "price": offer.get("final_price", 0),
                "affiliate_url": offer.get("affiliate_url", ""),
                "source": source,
            })
    except Exception:
        pass


# ─── Instagram poster ─────────────────────────────────────────────────────────

async def _clean_image_url_for_ig(url: str) -> str:
    """Limpa URL de imagem para o Instagram Graph API.
    Remove parâmetros de query que podem causar 400 (vteximg, etc).
    """
    from urllib.parse import urlparse, urlunparse
    parsed = urlparse(url)
    # Remove query string se a URL for de CDN com parâmetros longos
    if parsed.query and len(parsed.query) > 20:
        return urlunparse(parsed._replace(query=""))
    return url


async def _get_ig_image_url(offer: dict) -> str:
    """Retorna URL de imagem compatível com Instagram Graph API.
    Estratégia:
    1. Amazon/Shopee funcionam diretamente
    2. Outras URLs: baixa a imagem e re-hospeda via endpoint /img/proxy
    """
    import hashlib, base64
    image_url = offer.get("image_url", "")
    if not image_url or not image_url.startswith("http"):
        return ""
    # Amazon/Shopee funcionam diretamente
    if "amazon.com" in image_url or "shopee.com" in image_url or "m.media-amazon" in image_url:
        return image_url
    # Outras URLs (AliExpress, vteximg, etc): usa proxy do backend
    # Codifica a URL original em base64 para passar como parâmetro
    encoded = base64.urlsafe_b64encode(image_url.encode()).decode().rstrip("=")
    # Usa a API_URL (HTTPS) que é acessível publicamente
    proxy_url = f"{API_URL}/api/v1/img/proxy/{encoded}"
    return proxy_url


async def post_to_instagram(offer: dict, caption: str, short_url: str = "") -> dict:
    """Posta oferta no Instagram via Graph API.

    Estratégia anti-banimento (igual Facebook):
    - Caption SEM link no corpo (Instagram = Meta, mesma política)
    - Link vai nos comentários (fixado se possível)

    Usa publish_photo_instagram() do instagram.py.
    Requer conta Instagram Business/Creator vinculada a uma Facebook Page.
    """
    from app.db.session import AsyncSessionLocal
    from app.models.models import InstagramAccount
    from app.integrations.instagram import InstagramFacebookClient
    from sqlalchemy import select

    image_url = await _get_ig_image_url(offer)
    if not image_url:
        return {"ok": False, "error": "Offer has no valid image_url for Instagram"}

    try:
        async with AsyncSessionLocal() as db:
            # Busca conta Instagram ativa
            r = await db.execute(select(InstagramAccount).where(InstagramAccount.is_active == True))
            acct = r.scalar()
            if not acct:
                return {"ok": False, "error": "Nenhuma conta Instagram ativa"}

            client = InstagramFacebookClient()

            # Publica foto no feed
            result = await client.publish_photo_instagram(
                ig_account_id=acct.instagram_id,
                access_token=acct.access_token,
                image_url=image_url,
                caption=caption[:2200],
            )

            media_id = result.get("media_id")
            logger.info(f"Instagram: posted photo {media_id} for offer '{offer.get('title','')[:40]}'")

            # Tenta postar comentário com o link (mesma estratégia anti-banimento do Facebook)
            comment_id = None
            link_in_comment = False
            if short_url and media_id:
                try:
                    comment_id = await client.post_comment_facebook(
                        post_id=media_id,
                        message=f"🛒 Compre aqui: {short_url}",
                        page_token=acct.access_token,
                    )
                    if comment_id:
                        link_in_comment = True
                        # Tenta fixar o comentário
                        try:
                            await client.pin_comment_facebook(
                                comment_id=comment_id,
                                page_token=acct.access_token,
                            )
                        except Exception as pin_err:
                            logger.warning(f"Instagram: could not pin comment: {pin_err}")
                except Exception as cmt_err:
                    logger.warning(f"Instagram: failed to post comment with link: {cmt_err}")

            return {
                "ok": True,
                "media_id": media_id,
                "comment_id": comment_id,
                "link_in_comment": link_in_comment,
            }

    except Exception as e:
        logger.error(f"Instagram: failed to post: {e}")
        return {"ok": False, "error": str(e)}


# ─── YouTube Shorts poster ────────────────────────────────────────────────────

async def generate_offer_video(offer: dict, output_path: str) -> Optional[str]:
    """Gera vídeo Short (9:16) da oferta usando ffmpeg.

    Layout vertical (1080x1920):
    - Foto do produto no topo
    - Título + preço + desconto embaixo
    - CTA "Link na descrição"

    Retorna path do arquivo gerado ou None se falhar.
    """
    import subprocess
    import tempfile
    import os as _os

    image_url = offer.get("image_url", "")
    if not image_url or not image_url.startswith("http"):
        return None

    title = offer.get("title", "")[:60]
    price = offer.get("final_price", 0)
    original = offer.get("original_price", 0)
    discount = offer.get("discount_percent", 0)
    shipping_free = offer.get("shipping_free", False)
    provider = offer.get("provider", "loja")
    emoji = PROVIDER_EMOJI.get(provider, "🏪")
    now = datetime.now().strftime("%d/%m/%Y")

    tmpdir = tempfile.mkdtemp()

    try:
        # Download imagem do produto
        product_path = _os.path.join(tmpdir, "product.jpg")
        async with httpx.AsyncClient(timeout=15) as c:
            r = await c.get(image_url)
            r.raise_for_status()
            with open(product_path, "wb") as f:
                f.write(r.content)

        # Gera frame com PIL
        from PIL import Image, ImageDraw, ImageFont

        # Canvas vertical 1080x1920 (Shorts)
        img = Image.new("RGB", (1080, 1920), (15, 23, 42))
        draw = ImageDraw.Draw(img)

        # Carrega produto e redimensiona
        product = Image.open(product_path).convert("RGBA")
        product.thumbnail((900, 900), Image.LANCZOS)
        pw, ph = product.size
        # Centraliza produto no topo
        img.paste(product, ((1080 - pw) // 2, 150))

        # Fontes
        try:
            font_huge = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 80)
            font_big  = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 56)
            font_med  = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 40)
            font_sm   = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 32)
        except Exception:
            font_huge = font_big = font_med = font_sm = ImageFont.load_default()

        y = 1150
        # Header
        draw.text((540, y), "BESTPRICETODAY", fill=(0, 229, 160), font=font_big, anchor="mm")
        y += 80

        # Título (quebra em 2 linhas)
        if len(title) > 30:
            mid = title[:30].rfind(" ")
            if mid > 0:
                draw.text((540, y), title[:mid], fill="white", font=font_med, anchor="mm")
                y += 50
                draw.text((540, y), title[mid:][:30], fill="white", font=font_med, anchor="mm")
                y += 50
            else:
                draw.text((540, y), title[:30], fill="white", font=font_med, anchor="mm")
                y += 50
        else:
            draw.text((540, y), title, fill="white", font=font_med, anchor="mm")
            y += 50

        # Preço
        if original and original > price:
            draw.text((540, y), f"De R$ {original:.2f}", fill=(150, 150, 150), font=font_med, anchor="mm")
            y += 50
        draw.text((540, y), f"R$ {price:.2f}", fill=(250, 204, 21), font=font_huge, anchor="mm")
        y += 90

        # Desconto
        if discount >= 5:
            draw.text((540, y), f"-{discount:.0f}% OFF", fill=(239, 68, 68), font=font_big, anchor="mm")
            y += 70

        if shipping_free:
            draw.text((540, y), "Frete grátis", fill=(0, 229, 160), font=font_med, anchor="mm")
            y += 50

        # CTA
        draw.text((540, y + 40), "Link na descricao", fill=(167, 139, 250), font=font_med, anchor="mm")
        draw.text((540, y + 90), now, fill=(100, 100, 100), font=font_sm, anchor="mm")

        frame_path = _os.path.join(tmpdir, "frame.png")
        img.save(frame_path, "PNG")

        # Gera vídeo 8s com ffmpeg
        cmd = [
            "ffmpeg", "-y",
            "-loop", "1", "-i", frame_path,
            "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=44100",
            "-c:v", "libx264", "-t", "8", "-pix_fmt", "yuv420p", "-r", "30",
            "-c:a", "aac", "-shortest",
            output_path,
        ]
        proc = subprocess.run(cmd, capture_output=True, timeout=30)
        if proc.returncode != 0:
            logger.error(f"ffmpeg failed: {proc.stderr.decode()[:500]}")
            return None

        return output_path

    except Exception as e:
        logger.error(f"generate_offer_video failed: {e}")
        return None
    finally:
        # Limpa tmpdir
        import shutil
        try:
            shutil.rmtree(tmpdir)
        except Exception:
            pass


async def post_to_youtube(offer: dict, description: str, short_url: str = "") -> dict:
    """Gera vídeo Short da oferta e publica no YouTube.

    YouTube permite link de afiliado na descrição (diferente Facebook/IG).
    Descrição já vem com disclosure FTC + link direto da loja + short link.
    """
    from app.db.session import AsyncSessionLocal
    from app.models.models import YouTubeAccount
    from app.integrations.youtube import youtube_client
    from sqlalchemy import select
    import tempfile
    import os as _os

    affiliate_url = offer.get("affiliate_url", "")
    if not affiliate_url:
        return {"ok": False, "error": "Offer has no affiliate_url"}

    try:
        async with AsyncSessionLocal() as db:
            # Busca conta YouTube ativa
            r = await db.execute(select(YouTubeAccount).where(YouTubeAccount.is_active == True))
            acct = r.scalar()
            if not acct:
                return {"ok": False, "error": "Nenhuma conta YouTube ativa"}

            # Refresh token se expirado
            from datetime import datetime as _dt, timezone as _tz, timedelta as _td
            if acct.token_expires_at and acct.token_expires_at < _dt.now(_tz.utc):
                refreshed = await youtube_client.refresh_token(acct.refresh_token)
                acct.access_token = refreshed["access_token"]
                acct.token_expires_at = _dt.now(_tz.utc) + _td(seconds=refreshed.get("expires_in", 3600))
                await db.commit()

            # Gera vídeo da oferta
            tmp_video = tempfile.mktemp(suffix=".mp4")
            video_path = await generate_offer_video(offer, tmp_video)
            if not video_path or not _os.path.exists(video_path):
                return {"ok": False, "error": "Failed to generate offer video"}

            # Constrói descrição se não fornecida
            if not description:
                description = build_youtube_description(offer, affiliate_url, short_url)

            # Título
            title = f"{offer.get('title', '')[:50]} — R$ {offer.get('final_price', 0):.2f} | BestPriceToday"

            # Tags SEO
            tags = ["oferta", "desconto", offer.get("provider", "loja"), "bestpricetoday", "promoção"]
            if offer.get("discount_percent", 0) >= 30:
                tags.append("ofertaimperdível")

            # Upload
            result = await youtube_client.upload_video(
                access_token=acct.access_token,
                file_path=video_path,
                title=title[:100],
                description=description[:5000],
                tags=tags[:15],
                category_id="22",  # People & Blogs
                privacy="public",
            )

            video_id = result.get("video_id")
            logger.info(f"YouTube: posted Short {video_id} for offer '{offer.get('title','')[:40]}'")

            # Limpa arquivo temporário
            try:
                _os.remove(video_path)
            except Exception:
                pass

            return {
                "ok": True,
                "video_id": video_id,
                "video_url": result.get("video_url"),
            }

    except Exception as e:
        logger.error(f"YouTube: failed to post: {e}")
        return {"ok": False, "error": str(e)}


# ─── Orquestrador principal ───────────────────────────────────────────────────

async def distribute_offer(
    offer: dict,
    channels: list[str] = None,
    campaign: Optional[str] = None,
    use_ai: bool = True,
) -> dict:
    """
    Distribui uma oferta para os canais ativos.

    Args:
        offer: dict com a oferta (provider, title, final_price, affiliate_url, etc.)
        channels: lista de canais (default: ["telegram"])
        campaign: nome da campanha (opcional)
        use_ai: usar IA para gerar legenda (default: True)

    Returns:
        dict com resultado por canal: {telegram: {ok, message_id, short_url}, ...}
    """
    if channels is None:
        channels = ["telegram"]

    affiliate_url = offer.get("affiliate_url", "")
    if not affiliate_url:
        return {"ok": False, "error": "Offer has no affiliate_url"}

    # Dedup
    if already_posted(affiliate_url):
        return {"ok": False, "error": "Offer already posted in last 24h"}

    results = {}

    for channel in channels:
        source = f"distributor_{channel}"
        if campaign:
            source = f"{source}_{campaign}"

        # 1. Criar short link único para este canal
        short_url = await create_short_link(offer, source=source, campaign=campaign)
        if not short_url:
            # Fallback: usa affiliate_url direto
            short_url = affiliate_url

        # 2. Gerar legenda (Facebook/Instagram usam caption SEM link — anti-banimento)
        if channel == "facebook":
            # Facebook: caption sem link no corpo (link vai nos comentários fixados)
            caption = build_caption_facebook(offer)
        elif channel == "instagram":
            # Instagram: caption sem link (CTA "Link na bio" — IG não permite comentários via API sem instagram_manage_comments)
            caption = build_caption_facebook(offer).replace(
                "👇 Link de compra nos comentários (fixado)",
                "👇 Link de compra na BIO"
            )
        elif channel == "youtube":
            # YouTube: descrição COM link direto + disclosure FTC (permitido)
            caption = build_youtube_description(offer, affiliate_url, short_url)
        elif use_ai:
            caption = await build_caption(offer, short_url)
        else:
            caption = build_caption_fallback(offer, short_url)

        # 3. Postar no canal
        if channel == "telegram":
            result = await post_to_telegram(offer, caption)
        elif channel == "facebook":
            result = await post_to_facebook(offer, caption, short_url=short_url)
        elif channel == "instagram":
            result = await post_to_instagram(offer, caption, short_url=short_url)
        elif channel == "youtube":
            result = await post_to_youtube(offer, caption, short_url=short_url)
        else:
            result = {"ok": False, "error": f"Channel '{channel}' not implemented yet"}

        # 4. Registrar click para tracking
        if result.get("ok"):
            await register_click(offer, source)

        result["short_url"] = short_url
        result["source"] = source
        results[channel] = result

        # Rate limit entre canais
        if len(channels) > 1:
            await asyncio.sleep(2)

    return {
        "ok": any(r.get("ok") for r in results.values()),
        "channels": results,
        "offer_title": offer.get("title", "")[:60],
    }


async def distribute_auto(
    n_offers: int = 3,
    channels: list[str] = None,
    campaign: Optional[str] = None,
    use_ai: bool = True,
) -> dict:
    """
    Busca e distribui N ofertas automaticamente.
    Seleciona ofertas de alta qualidade (desconto, score, preço) que não foram postadas.
    """
    if channels is None:
        channels = ["telegram", "facebook"]

    # Queries por categoria (reaproveita do broadcaster)
    from app.workers.channel_broadcaster import QUERY_CATEGORIES

    categories = random.sample(
        list(QUERY_CATEGORIES.keys()),
        min(n_offers, len(QUERY_CATEGORIES))
    )

    posted = 0
    errors = 0
    details = []

    for category in categories:
        if posted >= n_offers:
            break

        queries = random.sample(
            QUERY_CATEGORIES[category],
            min(3, len(QUERY_CATEGORIES[category]))
        )

        offer = None
        for query in queries:
            try:
                async with httpx.AsyncClient(timeout=20) as c:
                    r = await c.get(
                        f"{API_URL}/api/v1/search",
                        params={"q": query, "limit": 10},
                    )
                    offers = r.json().get("offers", [])
            except Exception:
                continue

            # Filtra por qualidade + dedup
            valid = [
                o for o in offers
                if o.get("final_price", 0) >= MIN_PRICE
                and o.get("discount_percent", 0) >= MIN_DISCOUNT
                and o.get("affiliate_url")
                and not already_posted(o["affiliate_url"])
            ]

            if valid:
                # Seleciona por score (peso) com aleatoriedade
                scores = [max(1, o.get("score", 50)) for o in valid]
                total = sum(scores)
                rand = random.uniform(0, total)
                acc = 0
                for o, s in zip(valid, scores):
                    acc += s
                    if rand <= acc:
                        offer = o
                        break
                if not offer:
                    offer = valid[0]
                break

        if not offer:
            errors += 1
            continue

        result = await distribute_offer(offer, channels=channels, campaign=campaign, use_ai=use_ai)
        details.append({
            "category": category,
            "title": offer.get("title", "")[:50],
            "price": offer.get("final_price", 0),
            "discount": offer.get("discount_percent", 0),
            **result,
        })

        if result.get("ok"):
            posted += 1
        else:
            errors += 1

        await asyncio.sleep(3)  # rate limit

    return {
        "ok": posted > 0,
        "posted": posted,
        "errors": errors,
        "details": details,
    }


# ─── Loop automático ──────────────────────────────────────────────────────────

# Horários de postagem (hora local BR, UTC-3)
# 2x/dia nos picos de engajamento simultâneo de todas as plataformas
# Facebook: 12h-14h, 20h-22h | Instagram: 11h-13h, 19h-21h | YouTube: 10h-12h, 18h-20h
# Janelas que coincidem: 12h e 19h
POST_SCHEDULE = [
    (12, 2),  # 12h — 2 ofertas (pico almoço: FB + IG + YT + TG)
    (19, 2),  # 19h — 2 ofertas (pico noite: FB + IG + YT + TG)
]
NIGHT_OFFERS = 0  # sem madrugada (baixo engajamento em todas)
INTERVAL_SECONDS = 1800  # checa a cada 30 min se é hora de postar
ALL_CHANNELS = ["telegram", "facebook", "instagram", "youtube"]


async def run_distributor_loop():
    """Loop automático do distributor.

    Roda para sempre, postando ofertas em horários estratégicos:
    - 12h: 2 ofertas (pico almoço — FB + IG + YT + TG)
    - 19h: 2 ofertas (pico noite — FB + IG + YT + TG)
    - 4 ofertas/dia em 4 canais simultaneamente
    - Usa IA se disponível, fallback para legenda padrão
    """
    logger.info(f"Distributor loop started. Channels: {ALL_CHANNELS}")

    # Track se já postou em cada horário hoje
    posted_today = {}  # {hour: True}

    while True:
        now = datetime.now()
        hour = now.hour
        today_key = now.strftime("%Y-%m-%d")

        # Reset diario
        if not posted_today or list(posted_today.keys())[0].startswith(today_key) is False:
            if any(not k.startswith(today_key) for k in posted_today):
                posted_today = {}

        # Determina quantas ofertas postar agora
        n_offers = 0
        schedule_hour = None

        for sched_hour, sched_n in POST_SCHEDULE:
            if hour == sched_hour and not posted_today.get(f"{today_key}_{sched_hour}"):
                n_offers = sched_n
                schedule_hour = sched_hour
                break

        if n_offers > 0 and CHANNEL_ID:
            logger.info(f"Distributor: posting {n_offers} offers (hour={hour})...")
            try:
                result = await distribute_auto(
                    n_offers=n_offers,
                    channels=ALL_CHANNELS,
                    use_ai=True,
                )
                logger.info(f"Distributor: done — posted={result.get('posted', 0)}, errors={result.get('errors', 0)}")
                if result.get("ok"):
                    posted_today[f"{today_key}_{schedule_hour}"] = True
            except Exception as e:
                logger.error(f"Distributor loop error: {e}", exc_info=True)

        await asyncio.sleep(INTERVAL_SECONDS)

