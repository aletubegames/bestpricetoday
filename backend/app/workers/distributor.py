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
  - não postado nas últimas 72h (dedup por produto: ml_code/id/título)

Cada post = 1 short link /r/{code} único com source = canal.
"""

import asyncio
import glob
import httpx
import json
import os
import random
import re
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from app.core.config import settings
from app.core.logging import logger
from app.services.support_block import append_support, fit_limit

# Semaphore para limitar concorrência de XTTS (evita OOM)
# Máximo 1 processo XTTS por vez (cada processo consome ~2GB RAM)
_XTTS_SEMAPHORE = asyncio.Semaphore(1)


# ─── Config ───────────────────────────────────────────────────────────────────

BOT_TOKEN = settings.TELEGRAM_BOT_TOKEN
CHANNEL_ID = settings.TELEGRAM_CHANNEL_ID
API_URL = settings.INTERNAL_API_URL
ADMIN_KEY = settings.ADMIN_MANAGER_KEY

# Filtros de qualidade — relaxados para aumentar conversões
MIN_PRICE = 20.0          # preço mínimo: R$20 (aumentado de R$30)
MAX_PRICE = 500.0         # preço máximo: R$500 (aumentado de R$200)
MIN_DISCOUNT = 10.0       # desconto mínimo: 10% (reduzido de 15%)
DEDUP_TTL_HOURS = 72      # não repete o mesmo produto em 72h (era 24h — repostava demais)

# Demanda mínima — relaxada para mais produtos
MIN_SALES_COUNT = 100     # ≥100 unidades vendidas (reduzido de 500)
MIN_RATING = 4.3          # nota ≥4.3 (reduzido de 4.7)

# Marcas reconhecidas — expandido para incluir mais marcas populares
RECOGNIZED_BRANDS = {
    # Smartphones / eletrônicos
    "samsung", "apple", "iphone", "xiaomi", "redmi", "motorola", "realme", "pocophone", "poco",
    "lg", "htc", "nokia", "alcatel", "zte", "blu", "vivo", "oppo", "oneplus",
    # Áudio
    "jbl", "sony", "bose", "anker", "soundcore", "beats", "airpods", "edifier", "jvc", "philips",
    "sennheiser", "audio-technica", "pioneer", "kenwood", "pyle", "skullcandy", "plantronics",
    # Wearables
    "garmin", "amazfit", "huawei", "fitbit", "withings", "polar", "suunto", "fossil",
    # Casa / cozinha
    "electrolux", "philco", "mondial", "arno", "oster", "black+decker", "black decker",
    "brastemp", "consul", "whirlpool", "panasonic", "mabe", "britania", "cadence", "walita",
    "breville", "kitchenaid", "cuisinart", "ge", "moulinex", "delonghi", "nespresso",
    # Games
    "playstation", "nintendo", "xbox", "razer", "logitech", "hyperx", "steelseries",
    "corsair", "msi", "asus", "gigabyte", "zowie", "benq", "keychron", "durgod",
    # Informática
    "dell", "acer", "asus", "lenovo", "hp", "intel", "amd", "nvidia", "kingston",
    "corsair", "crucial", "g.skill", "samsung", "western digital", "seagate", "toshiba",
    "intelbras", "tp-link", "d-link", "netgear", "linksys", "mikrotik", "ubiquiti",
    # Câmeras
    "canon", "nikon", "gopro", "dji", "sony", "fujifilm", "olympus", "pentax", "leica",
    # TV
    "lg", "tcl", "hisense", "philips", "sharp", "hitachi", "jvc", "panasonic", "samsung",
    # Eletrodomésticos
    "electrolux", "brastemp", "consul", "whirlpool", "samsung", "lg", "panasonic",
    "mabe", "continental", "esmaltec", "inox", "tramontina", "berkel", "britania",
    # Marcas brasileiras populares
    "intelbras", "multilaser", "c3tech", "positivo", "itautec", "gradiente", "philips",
    "bombril", "ype", "qbo", "eins", "kibon", "natura", "oboticario", "havaianas",
    # Outras marcas reconhecidas
    "adidas", "nike", "puma", "reebok", "new balance", "under armour",
    "calvin klein", "tommy hilfiger", "lacoste", "ralph lauren",
    "nivea", "dove", "pantene", "head & shoulders", "gillette",
}

# Categorias de demanda (expandido para mais categorias que convertem)
DEMAND_CATEGORIES = {
    "audio":        ["fone jbl bluetooth", "fone bluetooth tws", "headset gamer", "caixa de som bluetooth", "earbuds airpods", "speaker bluetooth", "microfone", "soundbar"],
    "wearables":    ["smartwatch samsung", "xiaomi band 8", "amazfit", "smartwatch", "relogio smart", "fitness tracker"],
    "games":        ["jogo ps5", "controle xbox", "jogo nintendo switch", "headset ps5", "mouse gamer", "teclado gamer", "monitor gamer"],
    "periferico":   ["mouse gamer sem fio", "teclado mecanico", "webcam 1080p", "mouse logitech", "monitor", "teclado wireless"],
    "gadgets":      ["power bank xiaomi", "carregador turbo samsung", "smart bulb", "pilhas recarregaveis", "carregador wireless", "cabo usb"],
    "casa":         ["ventilador", "ar condicionado", "ferro de passar", "cafeteira", "liquidificador", "batedeira", "processador"],
    "cozinha":      ["panela", "frigideira", "air fryer", "microondas", "fogao", "geladeira", "freezer"],
    "eletro":       ["tv", "smart tv", "home theater", "barulho", "som", "projetor", "televisao"],
    "esportes":     ["bicicleta", "treadmill", "eliptico", "halter", "peso", "academia", "corrida", "natacao"],
    "beleza":       ["secador", "chapinha", "barbeador", "cortador de cabelo", "cuidado pessoal", "maquiagem"],
    "automotivo":   ["gps", "camera de re", "radar", "carregador carro", "bateria carro", "farol", "pneu"],
    "informatica":  ["notebook", "laptop", "desktop", "ssd", "hd", "memoria ram", "placa de video", "processador"],
}

# Dedup file (compartilhado com broadcaster) — no backend, não em /tmp:
# /tmp é limpo em reboot e o histórico de posts se perdia → reposts
BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
DEDUP_FILE = BACKEND_DIR / ".distributor_dedup.json"

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


def _offer_key(offer: dict) -> str:
    """Chave estável de dedup por produto.

    affiliate_url NÃO serve como chave: o portal ML gera um meli.la novo
    a cada scrape, então dedup por URL nunca batia e o mesmo produto era
    repostado todo dia. Prioriza ml_code > id > product_id > título.
    (ofertas da busca live trazem product_id; do DB trazem ml_code/id)
    """
    key = offer.get("ml_code") or offer.get("id") or offer.get("product_id")
    if key:
        return str(key)
    title = (offer.get("title") or "").strip().lower()
    if title:
        return f"t:{title[:80]}"
    return offer.get("affiliate_url") or ""


def already_posted(key: str) -> bool:
    data = _load_dedup()
    if not key or key not in data:
        return False
    posted_at = datetime.fromisoformat(data[key])
    return datetime.now(timezone.utc) - posted_at < timedelta(hours=DEDUP_TTL_HOURS)


def mark_posted(key: str):
    if not key:
        return
    data = _load_dedup()
    cutoff = datetime.now(timezone.utc) - timedelta(hours=DEDUP_TTL_HOURS)
    data = {h: ts for h, ts in data.items()
            if datetime.fromisoformat(ts) > cutoff}
    data[key] = datetime.now(timezone.utc).isoformat()
    _save_dedup(data)


async def _send_telegram_alert(msg: str):
    """Alerta operacional pro dono via Telegram (mesmo padrão do ml_scraper)."""
    try:
        token = settings.TELEGRAM_BOT_TOKEN
        chat_id = str(settings.TELEGRAM_CHANNEL_ID) if settings.TELEGRAM_CHANNEL_ID else "5899118807"
        if not token:
            return
        async with httpx.AsyncClient(timeout=15) as client:
            await client.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                json={"chat_id": chat_id, "text": msg, "parse_mode": "Markdown"},
            )
        logger.info(f"Alerta Telegram enviado: {msg[:80]}")
    except Exception as e:
        logger.warning(f"Erro ao enviar alerta Telegram: {e}")


# ─── Filtros de qualidade (demanda + marca + desconto real) ──────────────────

def _has_recognized_brand(title: str) -> bool:
    """True se o título menciona uma marca reconhecida (word-boundary match)."""
    import re as _re
    t = (title or "").lower()
    for brand in RECOGNIZED_BRANDS:
        # Word-boundary match: evita falso positivo de "lg" em "bulgaria"
        if _re.search(r'\b' + _re.escape(brand) + r'\b', t):
            return True
    return False


# Keywords de acessórios/genéricos que NÃO devem ser postados (reduzido - só lixo)
EXCLUDE_KEYWORDS = {
    "capa", "case", "cover", "filme", "protetor", "pelicula", "película",
    "screen protector", "vidro nano", "pelicula 3d",
    # Mantive apenas proteção de tela e capas - acessórios úteis (carregador, cabo, etc) agora são permitidos
}


def _is_accessory(title: str) -> bool:
    """True se o título indica acessório/genérico (não produto principal)."""
    t = (title or "").lower()
    return any(kw in t for kw in EXCLUDE_KEYWORDS)


def _meets_demand(offer: dict) -> bool:
    """True se o produto tem prova de demanda (vendas/nota).

    Para providers que não retornam sales_count/rating (ML/Amazon do DB sem notes),
    aceita se o score de relevância for alto (≥0.8) — confia no match do título.
    """
    sales = offer.get("sales_count")
    rating = offer.get("rating")
    # Se tem dados de demanda, usa eles
    if sales is not None and sales > 0:
        if sales < MIN_SALES_COUNT:
            return False
    if rating is not None and rating > 0:
        # ML API retorna 0-5, scraper guarda 0-5, AliExpress retorna 0-1 (converte)
        norm_rating = rating * 5 if rating <= 1.0 else rating
        if norm_rating < MIN_RATING:
            return False
    # Se nenhum dado de demanda disponível, aceita (não penaliza ML/Amazon do DB)
    return True


async def _is_real_discount(offer: dict) -> bool:
    """Valida que o desconto é real: preço atual ≤ mínimo dos últimos 30 dias.

    Consulta affiliate_price_history. Se não houver histórico suficiente (produto novo),
    aceita (não bloqueia produtos sem histórico).
    """
    affiliate_url = offer.get("affiliate_url", "")
    if not affiliate_url:
        return True  # sem URL, não dá pra validar — aceita
    final_price = offer.get("final_price", 0)
    if not final_price or final_price <= 0:
        return True
    try:
        from app.db.session import AsyncSessionLocal
        from app.models.models import AffiliateProduct, AffiliatePriceHistory
        from sqlalchemy import select, func
        from datetime import timedelta
        cutoff = datetime.now(timezone.utc) - timedelta(days=30)
        async with AsyncSessionLocal() as db:
            # Acha o produto pelo affiliate_url
            stmt = select(AffiliateProduct.id).where(
                AffiliateProduct.affiliate_url == affiliate_url
            )
            r = await db.execute(stmt)
            product_id = r.scalar_one_or_none()
            if not product_id:
                return True  # produto não está na tabela — sem histórico
            # Preço mínimo dos últimos 30 dias
            stmt = select(func.min(AffiliatePriceHistory.price)).where(
                AffiliatePriceHistory.product_id == product_id,
                AffiliatePriceHistory.recorded_at >= cutoff,
            )
            r = await db.execute(stmt)
            min_price_30d = r.scalar()
            if min_price_30d is None or min_price_30d <= 0:
                return True  # sem histórico suficiente
            # Desconto real = preço atual ≤ mínimo histórico (com 2% de tolerância)
            return final_price <= min_price_30d * 1.02
    except Exception as e:
        logger.warning(f"Distributor: price history check failed: {e}")
        return True  # erro → não bloqueia


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

# Modelos free do OpenRouter variam a cada chamada — alguns despejam a
# "análise" do prompt no content (ex: "1. Analyze the Request: Role:
# Copywriter...") e isso vazava direto pra legenda do Telegram.
_CAPTION_SCAFFOLD_RE = re.compile(
    r"analyz|copywriter|role\s*:|task\s*:|step\s*\d|prompt|instruction|"
    r"produto\s*:|preço\s*:|desconto\s*:|product\s*:|price\s*:|discount\s*:|"
    r"free shipping|savings\s*:|shop\s*:",
    re.IGNORECASE,
)
_CAPTION_MAX_LEN = 340  # pedimos ≤280 — acima disso é scaffold, não legenda


def _is_usable_caption(caption: str) -> bool:
    """True se o content da IA parece uma legenda real (não análise do prompt)."""
    if len(caption) > _CAPTION_MAX_LEN:
        return False
    return not _CAPTION_SCAFFOLD_RE.search(caption)


async def generate_caption_ai(offer: dict) -> Optional[str]:
    """Gera legenda persuasiva via OpenRouter (1 chamada, modelo barato)."""
    if not settings.OPENROUTER_API_KEY:
        return None

    title = offer.get("title", "")[:100]
    price = offer.get("final_price") or 0
    original = offer.get("original_price") or 0
    # Só mostra original se for maior que price (desconto real)
    if original <= price:
        original = 0
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
                # Usa apenas content — NUNCA reasoning (vaza prompt interno)
                caption = msg.get("content")
                if caption:
                    caption = caption.strip()
                    if caption and _is_usable_caption(caption):
                        logger.info(f"Distributor: AI caption generated ({len(caption)} chars) model={data.get('model','?')}")
                        return caption
                    logger.warning(f"Distributor: AI caption rejected (scaffold/leak), model={data.get('model','?')}")
                else:
                    logger.warning(f"Distributor: AI caption empty response, model={data.get('model','?')}")
            else:
                logger.warning(f"Distributor: OpenRouter error {r.status_code}: {r.text[:200]}")
    except Exception as e:
        logger.warning(f"Distributor: AI caption failed: {e}")

    return None


def build_caption_fallback(offer: dict, short_url: str) -> str:
    """Legenda padrão (sem IA) — formato viral para Telegram."""
    title = offer.get("title", "")[:80]
    price = offer.get("final_price") or 0
    original = offer.get("original_price") or 0
    discount = offer.get("discount_percent", 0)
    shipping_free = offer.get("shipping_free", False)
    provider = offer.get("provider", "loja")
    economy = offer.get("economy", 0)
    coupon = offer.get("coupon")

    # Hooks virais baseados na economia em reais (mais concreto que %)
    if economy >= 100:
        hook = f"🚨 *ECONOMIZE {fmt_brl(economy)} AGORA*"
    elif economy >= 50:
        hook = f"⚡ *POUPA {fmt_brl(economy)} — VAI RÁPIDO*"
    elif discount >= 40:
        hook = "🔥 *OFERTA RELÂMPAGO*"
    elif discount >= 20:
        hook = "🏷️ *ACHADINHO DO DIA*"
    else:
        hook = "💰 *PREÇO BOM*"

    lines = [f"{hook}\n"]
    lines.append(f"📦 *{title}*")
    lines.append("")

    if original and original > price:
        lines.append(f"~~De {fmt_brl(original)}~~")
    lines.append(f"💵 *{fmt_brl(price)}*")

    if economy > 10:
        lines.append(f"💰 *Você economiza {fmt_brl(economy)}*")
    elif discount >= 5 and not offer.get("is_fake_discount"):
        lines.append(f"📉 *-{discount:.0f}% OFF*")
    if shipping_free:
        lines.append("✅ *Frete grátis*")

    if coupon and coupon.get("code"):
        lines.append(f"\n🏷️ *CUPOM: {coupon['code']}*")

    lines.append(f"\n🛒 *Clica aqui antes que acabe*")
    lines.append(f"👉 [Ver oferta]({short_url})")
    lines.append(f"\n🛍️ @BestPriceToday")

    # Pedido de apoio (ordem do dono, 2026-10-19)
    return append_support("\n".join(lines))


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
        lines.append(f"\n🛒 *Compre agora antes que acabe!*")
        lines.append(f"👉 [Ver oferta]({short_url})")
        lines.append(f"\n🛍️ @BestPriceToday | [BestPriceToday]({settings.PUBLIC_SITE_URL})")
        return append_support("\n".join(lines))

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
    price = offer.get("final_price") or 0
    original = offer.get("original_price") or 0
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

    # Cupom — destaque se existir
    coupon = offer.get("coupon")
    if coupon and coupon.get("code"):
        lines.append(f"\n🏷️ CUPOM: {coupon['code']}")
        if coupon.get("discount_text"):
            lines.append(f"   → {coupon['discount_text']} extra no checkout!")

    lines.append(f"\n{emoji} Via {provider.upper()}")

    # CTA SEM link — direciona para os comentários
    lines.append("\n👇 Link nos comentários (fixado)")
    lines.append("🛍️ BestPriceToday — fugimos de promoção fake")

    # Pedido de apoio (ordem do dono, 2026-10-19)
    return append_support("\n".join(lines))


def build_youtube_description(offer: dict, affiliate_url: str, short_url: str) -> str:
    """Descrição para YouTube — COM link direto da loja (sem disclosure).

    YouTube permite links de afiliado na descrição (diferente do Facebook).
    No Brasil, disclosure verbose de afiliado não é comum e reduz conversão.
    Layout: oferta + preço + links + canal + hashtags.
    """
    title = offer.get("title", "")[:80]
    price = offer.get("final_price") or 0
    original = offer.get("original_price") or 0
    discount = offer.get("discount_percent", 0)
    shipping_free = offer.get("shipping_free", False)
    provider = offer.get("provider", "loja")
    economy = offer.get("economy", 0)
    score = offer.get("score", 0)
    emoji = PROVIDER_EMOJI.get(provider, "🏪")
    now = datetime.now().strftime("%d/%m/%Y")

    lines = []

    # 1. Título + preço (compacto)
    lines.append(f"🔥 {title}")
    if original and original > price:
        lines.append(f"De R$ {original:.2f} → 💵 R$ {price:.2f}")
    else:
        lines.append(f"💵 R$ {price:.2f}")
    if discount >= 5:
        lines.append(f"🏷️ -{discount:.0f}% {'• frete grátis' if shipping_free else ''}".rstrip())
    elif shipping_free:
        lines.append("✅ Frete grátis")

    # 2. Link — usa short_url (passa pelo site, rastreia clique)
    lines.append("")
    lines.append("🛒 Compre aqui:")
    lines.append(short_url)

    # Cupom — se existir
    coupon = offer.get("coupon")
    if coupon and coupon.get("code"):
        lines.append("")
        lines.append(f"🏷️ CUPOM: {coupon['code']}")
        if coupon.get("discount_text"):
            lines.append(f"   → {coupon['discount_text']} extra no checkout!")

    # 3. Rodapé enxuto
    lines.append("")
    lines.append("━━━━━━━━━━━━━━━━━━━━")
    lines.append("BestPriceToday — fugimos de promoção fake com histórico de preços.")
    lines.append(f"{settings.PUBLIC_SITE_URL}")
    lines.append("━━━━━━━━━━━━━━━━━━━━")

    # 5. Hashtags SEO
    tags = ["#oferta", "#desconto", f"#{provider}", "#bestpricetoday", "#promoção"]
    if discount >= 30:
        tags.append("#ofertaimperdível")
    lines.append(" ".join(tags))

    # 6. Pedido de apoio (ordem do dono, 2026-10-19) — mesmo bloco do CryptoKitchen
    return append_support("\n".join(lines))


def _youtube_title(offer: dict) -> str:
    """Título do Short com hook de descoberta (antes era "Produto — R$X | BestPriceToday").

    Regras: hook primeiro, marca/produto cedo, preço em R$, máx 100 chars
    (limite do YouTube). Variantes por sinal disponível (discount/economy).
    """
    import re as _re
    raw = (offer.get("title") or "Oferta").strip()
    price = offer.get("final_price") or 0
    original = offer.get("original_price") or 0
    discount = offer.get("discount_percent") or 0
    economy = offer.get("economy") or (original - price if original and original > price else 0)
    # Título de e-commerce vem com spec dump — corta na 1ª vírgula/separador
    short = _re.split(r"[,;|]|\s[-–—]\s", raw)[0].strip() or raw
    short = short[:55].rstrip()
    p = fmt_brl(price)

    hooks = []
    if discount >= 25:
        hooks += [
            f"😱 -{discount:.0f}% OFF: {short} por {p}!",
            f"🚨 {discount:.0f}% de desconto: {short} = {p}",
        ]
    if economy >= 40:
        hooks.append(f"💰 ECONOMIZE {fmt_brl(economy)}: {short} por {p}")
    hooks += [
        f"🔥 {short} por {p} — menor preço agora",
        f"⚡ PREÇO BAIXO: {short} só {p}",
    ]
    return random.choice(hooks)[:100]


# ─── Telegram poster ──────────────────────────────────────────────────────────

async def post_to_telegram(offer: dict, caption: str) -> dict:
    """Posta oferta no canal Telegram com foto + caption."""
    if not BOT_TOKEN or not CHANNEL_ID:
        return {"ok": False, "error": "Telegram not configured"}

    image_url = offer.get("image_url", "")
    # Legenda do Telegram tem limite de 1024 chars (foto) — nunca cortar
    # endereço de doação no meio.
    caption = fit_limit(caption, 1024)

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

    return {
        "ok": ok_count > 0,
        "pages_posted": ok_count,
        "pages_total": len(pages),
        "results": results,
        "page_names": [r.get("page_name") for r in results if r.get("ok")],
    }


# ─── Click tracking ───────────────────────────────────────────────────────────

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

            # Publica foto no feed — se o Graph rejeitar a URL da imagem (400),
            # tenta de novo com a imagem servida pelo nosso /img/proxy
            try:
                result = await client.publish_photo_instagram(
                    ig_account_id=acct.instagram_id,
                    access_token=acct.access_token,
                    image_url=image_url,
                    caption=fit_limit(caption, 2200),
                )
            except Exception:
                raw_url = offer.get("image_url", "")
                if "/img/proxy/" not in image_url and raw_url.startswith("http"):
                    import base64 as _b64
                    encoded = _b64.urlsafe_b64encode(raw_url.encode()).decode().rstrip("=")
                    proxied = f"{API_URL}/api/v1/img/proxy/{encoded}"
                    logger.warning(f"Instagram: imagem direta falhou, retry via proxy: {raw_url[:60]}")
                    result = await client.publish_photo_instagram(
                        ig_account_id=acct.instagram_id,
                        access_token=acct.access_token,
                        image_url=proxied,
                        caption=fit_limit(caption, 2200),
                    )
                else:
                    raise

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


# ─── Limpeza de arquivos temporários ─────────────────────────────────────────────────────

def cleanup_temp_files():
    """Remove arquivos temporários antigos do /tmp (vídeos, áudios, imagens).
    
    Executado periodicamente para evitar ocupação de espaço.
    """
    import glob
    import time
    import shutil
    try:
        logger.info("Distributor: iniciando limpeza de arquivos temporários")
        now = time.time()
        cutoff = now - 3600  # remove arquivos com mais de 1 hora
        
        removed_count = 0
        # Remove arquivos temporários antigos
        for pattern in ["/tmp/tmp*", "/tmp/*.mp4", "/tmp/*.wav", "/tmp/*.jpg"]:
            for filepath in glob.glob(pattern):
                try:
                    if os.path.getmtime(filepath) < cutoff:
                        if os.path.isdir(filepath):
                            shutil.rmtree(filepath)
                            logger.info(f"Distributor: removed old temp directory: {filepath}")
                        else:
                            os.remove(filepath)
                            logger.info(f"Distributor: removed old temp file: {filepath}")
                        removed_count += 1
                except Exception as e:
                    logger.warning(f"Distributor: failed to remove {filepath}: {e}")
        logger.info(f"Distributor: limpeza de arquivos temporários concluída ({removed_count} arquivos removidos)")
    except Exception as e:
        logger.warning(f"Distributor: cleanup_temp_files failed: {e}")


# ─── YouTube Shorts poster ────────────────────────────────────────────────────

async def generate_offer_video(offer: dict, output_path: str, custom_narration: Optional[str] = None) -> Optional[str]:
    """Gera vídeo Short (9:16) da oferta: imagem estática + overlay + narração XTTS.

    Usa a mesma lógica do coupon_distributor:
    - Imagem do produto em HD (baixa, escala, pad)
    - Overlay de texto (título com quebra de linha, preço, desconto)
    - Narração XTTS v2 (voz clonada ElevenLabs — matheus/locutor)
    - Roteiro estruturado (sem cupom — catálogo normal)
    - 25 aberturas aleatórias, preços por extenso, expansão de marcas/unidades
    - custom_narration: permite passar roteiro específico (ex: admin manual)
    """
    import subprocess
    import tempfile
    import os as _os

    # Importa funções compartilhadas do coupon_distributor
    from app.workers.coupon_distributor import (
        generate_xtts_narration_async,
        expand_units_for_tts,
        num2words_pt,
        fmt_brl,
        _clean_title_for_narration,
    )

    image_url = offer.get("image_url", "")
    title = offer.get("title", "")[:80]
    # Título limpo para narração (sem códigos, specs, cores, armazenamento)
    title_clean = _clean_title_for_narration(title)
    price = (offer.get("final_price") or 0) or (offer.get("price") or 0)
    original = offer.get("original_price", 0) or 0
    discount = offer.get("discount_percent", 0) or 0
    shipping_free = offer.get("shipping_free", False)
    provider = offer.get("provider", "loja")

    tmpdir = tempfile.mkdtemp()

    try:
        # ── 1. Baixa imagem do produto em HD ──
        img_path = _os.path.join(tmpdir, "product.jpg")
        if image_url and image_url.startswith("http"):
            hd_url = image_url
            if "amazon.com" in image_url:
                hd_url = image_url.replace("_AC_UL320_", "_AC_UL1000_").replace("_AC_UL200_", "_AC_UL1000_")
            elif "mlstatic.com" in image_url:
                hd_url = image_url.replace("D_Q_NP", "D_NQ_NP").replace("_Q_", "_NQ_")
            for url in [hd_url, image_url]:
                try:
                    with httpx.Client(timeout=10) as c:
                        r = c.get(url, headers={"User-Agent": "Mozilla/5.0"}, follow_redirects=True)
                        if r.status_code == 200 and len(r.content) > 2000:
                            with open(img_path, "wb") as f:
                                f.write(r.content)
                            break
                except Exception:
                    continue

        # ── 2. Gera roteiro de catálogo (sem cupom) ──
        def speak_brl(v):
            reais = int(v)
            centavos = int(round((v - reais) * 100))
            real_word = "real" if reais == 1 else "reais"
            centavo_word = "centavo" if centavos == 1 else "centavos"
            if centavos > 0:
                if reais == 0:
                    return f"{num2words_pt(centavos)} {centavo_word}"
                return f"{num2words_pt(reais)} {real_word} e {num2words_pt(centavos)} {centavo_word}"
            return f"{num2words_pt(reais)} {real_word}"

        if custom_narration:
            narration = custom_narration
        else:
            # Variedade de ganchos/aberturas aleatórias
            hooks = [
                f"Olha só essa oferta: {title_clean} por {speak_brl(price)}!",
                f"Não perca: {title_clean} por {speak_brl(price)}!",
                f"Oferta do dia: {title_clean} por {speak_brl(price)}!",
                f"Preço baixo: {title_clean} por {speak_brl(price)}!",
                f"Promoção imperdível: {title_clean} por {speak_brl(price)}!",
                f"Vale a pena: {title_clean} por {speak_brl(price)}!",
                f"Corre que acaba: {title_clean} por {speak_brl(price)}!",
                f"Super oferta: {title_clean} por {speak_brl(price)}!",
            ]
            
            # Variedade de CTAs aleatórios
            ctas = [
                "Link na descrição. Clica agora!",
                "Clica no link da descrição!",
                "Link na descrição do vídeo!",
                "Confira na descrição!",
                "Link tá na descrição!",
                "Aproveita, link na descrição!",
            ]
            
            # Escolhe aleatoriamente
            import random as _rand
            hook = _rand.choice(hooks)
            cta = _rand.choice(ctas)
            
            # Variedade de estruturas de preço/desconto
            if original and original > price and discount > 0:
                economy = original - price
                price_structures = [
                    f"Era {speak_brl(original)}, agora {speak_brl(price)}. Economiza {speak_brl(economy)}.",
                    f"De {speak_brl(original)} para {speak_brl(price)}. Você economiza {speak_brl(economy)}.",
                    f"Preço antigo {speak_brl(original)}, novo preço {speak_brl(price)}. Economia de {speak_brl(economy)}.",
                    f"Desconto de {speak_brl(economy)}. De {speak_brl(original)} por {speak_brl(price)}.",
                ]
                price_info = _rand.choice(price_structures)
                narration = f"{hook} {price_info} "
            else:
                value_props = [
                    "Oferta imperdível pra quem busca qualidade.",
                    "Excelente custo-benefício.",
                    "Produto de qualidade com preço baixo.",
                    "Não perca essa oportunidade.",
                    "Ideal pra quem quer economizar.",
                ]
                value_prop = _rand.choice(value_props)
                narration = f"{hook} {value_prop} "

            if shipping_free:
                shipping_msgs = [
                    "Frete grátis. ",
                    "Com frete grátis. ",
                    "E ainda tem frete grátis. ",
                    "Envio sem custo. ",
                ]
                narration += _rand.choice(shipping_msgs)

            # Adiciona CTA
            narration += cta

            # Expande marcas e unidades para TTS
            narration = expand_units_for_tts(narration)
            narration = narration.replace("R$", "").replace("r$", "").replace("  ", " ").strip()

        audio_path = _os.path.join(tmpdir, "narration.wav")
        logger.info("Distributor: gerando narração XTTS (voz ElevenLabs)...")
        if not await generate_xtts_narration_async(narration, audio_path):
            logger.error("Distributor: XTTS falhou, pulando vídeo")
            return None

        # ── 3. Duração do áudio ──
        duration = 10
        try:
            result = subprocess.run(
                ["ffprobe", "-v", "error", "-show_entries", "format=duration",
                 "-of", "default=noprint_wrappers=1:nokey=1", audio_path],
                capture_output=True, text=True, timeout=10
            )
            duration = float(result.stdout.strip()) + 2
        except Exception:
            pass

        # ── 4. Texto para overlay (escapado para ffmpeg) ──
        # % precisa virar \\% na string do filtro (parser de opções come uma
        # barra; drawtext precisa receber \% p/ literal) — sem isso a linha
        # inteira renderiza vazia ("Stray %").
        def esc(t):
            return (t.replace("'", "\\'").replace(":", "\\:")
                     .replace(",", "\\,").replace("%", "\\\\%"))

        # Variedade visual aleatória
        import random as _rand
        
        # Quebra título em linhas dinamicamente (max ~30 chars cada)
        title_full = offer.get("title", "")[:90]
        words = title_full.split()
        title_lines = []
        current = ""
        for w in words:
            if len(current) + len(w) + 1 <= 30:
                current = (current + " " + w).strip()
            else:
                if current:
                    title_lines.append(current)
                current = w
        if current:
            title_lines.append(current)
        # Limita a 4 linhas
        title_lines = title_lines[:4]

        # Escreve título num arquivo .txt (ffmpeg textfile permite \n real)
        # \% no arquivo = % literal no drawtext
        title_file = _os.path.join(tmpdir, "title.txt")
        with open(title_file, "w") as f:
            f.write("\n".join(title_lines).replace("%", "\\%"))

        price_text = esc(fmt_brl(price))
        discount_text = esc(f"-{discount:.0f}% OFF") if discount > 0 else ""
        orig_text = esc(fmt_brl(original)) if original and original > price else ""
        economy_val = offer.get("economy", 0) or (original - price if original and original > price else 0)
        economy_text = esc(f"ECONOMIZE {fmt_brl(economy_val)}") if economy_val > 10 else ""

        # Fontes pesadas (servidor: urw-base35) — condensada bold p/ linhas de
        # impacto, sans bold p/ título/labels. Fallback: fonte default do ffmpeg.
        def _pick_font(*paths):
            for p in paths:
                if _os.path.exists(p):
                    return f"fontfile={p}:"
            return ""

        F_BOLD = _pick_font(
            "/usr/share/fonts/opentype/urw-base35/NimbusSans-Bold.otf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        )
        F_COND = _pick_font(
            "/usr/share/fonts/opentype/urw-base35/NimbusSansNarrow-Bold.otf",
            "/usr/share/fonts/truetype/liberation/LiberationSansNarrow-Bold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        )

        # Variedade de cores e posições
        color_schemes = [
            {"price": "0xffd700", "discount": "0xe02020", "economy": "0xffb340"},  # ouro/vermelho/laranja
            {"price": "0x2ee66b", "discount": "0xe02020", "economy": "0xffd60a"},  # verde/vermelho/amarelo
            {"price": "0x40c8ff", "discount": "0xff6432", "economy": "0xffd60a"},  # azul/laranja/amarelo
        ]
        colors = _rand.choice(color_schemes)

        # ── 5. Monta vídeo com ffmpeg ──
        if _os.path.exists(img_path):
            # Gradiente de fundo (melhor que cor sólida)
            vf_parts = [
                "scale=1080:1920:force_original_aspect_ratio=decrease",
                "pad=1080:1920:(ow-iw)/2:(oh-ih)/2:color=0x0a0a1a@0.95",  # cor de fundo com transparência
                "format=yuv420p",
                # Título via textfile (permite quebra de linha real com \n)
                f"drawtext={F_BOLD}textfile={title_file}:fontcolor=white:fontsize=40:"
                f"x=(w-text_w)/2:y=50:line_spacing=10:box=1:boxcolor=0x000000@0.75:boxborderw=16:"
                f"shadowx=0:shadowy=2:shadowcolor=0x000000@0.8",
            ]
            if orig_text:
                vf_parts.append(
                    f"drawtext={F_BOLD}text='DE {orig_text}':fontcolor=0xcccccc:fontsize=42:"
                    f"x=(w-text_w)/2:y=1450:box=1:boxcolor=0x000000@0.65:boxborderw=10"
                )
                vf_parts.append(
                    f"drawtext={F_COND}text='POR {price_text}':fontcolor={colors['price']}:fontsize=72:"
                    f"borderw=5:bordercolor=0x000000:"
                    f"x=(w-text_w)/2:y=1520:box=1:boxcolor=0x000000@0.6:boxborderw=18:"
                    f"shadowx=0:shadowy=3:shadowcolor=0x000000@0.8"
                )
                if discount_text:
                    vf_parts.append(
                        f"drawtext={F_COND}text='{discount_text}':fontcolor=white:fontsize=46:"
                        f"x=(w-text_w)/2:y=1628:box=1:boxcolor={colors['discount']}@0.92:boxborderw=14:"
                        f"shadowx=0:shadowy=2:shadowcolor=0x000000@0.8"
                    )
                if economy_text:
                    vf_parts.append(
                        f"drawtext={F_COND}text='{economy_text}':fontcolor={colors['economy']}:fontsize=44:"
                        f"borderw=3:bordercolor=0x000000:"
                        f"x=(w-text_w)/2:y=1702:box=1:boxcolor=0x000000@0.6:boxborderw=10"
                    )
            else:
                vf_parts.append(
                    f"drawtext={F_COND}text='{price_text}':fontcolor={colors['price']}:fontsize=72:"
                    f"borderw=5:bordercolor=0x000000:"
                    f"x=(w-text_w)/2:y=1520:box=1:boxcolor=0x000000@0.6:boxborderw=18:"
                    f"shadowx=0:shadowy=3:shadowcolor=0x000000@0.8"
                )

            if shipping_free:
                shipping_colors = ["0x2ee66b", "0x40c8ff", "0xffd700"]
                shipping_color = _rand.choice(shipping_colors)
                vf_parts.append(
                    f"drawtext={F_COND}text='FRETE GRATIS':fontcolor={shipping_color}:fontsize=46:"
                    "borderw=3:bordercolor=0x000000:"
                    "x=(w-text_w)/2:y=1768:box=1:boxcolor=0x000000@0.6:boxborderw=12"
                )
            else:
                vf_parts.append(
                    f"drawtext={F_BOLD}text='{provider.upper()}':fontcolor=0xaaaaaa:fontsize=34:"
                    f"x=(w-text_w)/2:y=1768"
                )

            # Variedade de textos de CTA
            cta_texts = [
                "LINK NA DESCRIÇÃO",
                "LINK NA DESCRIÇÃO DO VÍDEO",
                "CLICA NA DESCRIÇÃO",
                "CONFIRA NA DESCRIÇÃO",
            ]
            cta_text = _rand.choice(cta_texts)
            vf_parts.append(
                f"drawtext={F_COND}text='{cta_text}':fontcolor=white:fontsize=34:"
                "borderw=3:bordercolor=0x000000:"
                "x=(w-text_w)/2:y=1848:box=1:boxcolor=0x000000@0.75:boxborderw=10"
            )
            vf_parts.append(
                f"drawtext={F_BOLD}text='BestPriceToday':fontcolor=0x777777:fontsize=26:"
                "x=(w-text_w)/2:y=1890"
            )

            cmd = [
                "ffmpeg", "-y",
                "-loop", "1", "-i", img_path,
                "-i", audio_path,
                # Otimizações para CPU Intel com pouca RAM
                "-c:v", "libx264", "-preset", "veryfast", "-tune", "stillimage",
                "-vf", ",".join(vf_parts),
                "-c:a", "aac", "-b:a", "64k",  # reduzido de 128k para 64k
                "-t", str(duration),
                "-pix_fmt", "yuv420p",
                "-r", "15",  # reduzido de 30fps para 15fps (vídeo estático)
                "-crf", "23",  # aumentado de 20 para 23 (menor arquivo, mais rápido)
                "-threads", "4",  # limita threads para não estourar RAM
                output_path
            ]
        else:
            # Sem imagem: fundo escuro + texto
            vf_parts = [
                f"drawtext={F_BOLD}textfile={title_file}:fontcolor=white:fontsize=44:"
                f"x=(w-text_w)/2:y=700:line_spacing=10:box=1:boxcolor=0x000000@0.5:boxborderw=20:"
                f"shadowx=0:shadowy=2:shadowcolor=0x000000@0.8",
                f"drawtext={F_COND}text='{price_text}':fontcolor={colors['price']}:fontsize=72:"
                f"borderw=5:bordercolor=0x000000:"
                f"x=(w-text_w)/2:y=1100:box=1:boxcolor=0x000000@0.6:boxborderw=18:"
                f"shadowx=0:shadowy=3:shadowcolor=0x000000@0.8",
            ]
            if discount_text:
                vf_parts.append(
                    f"drawtext={F_COND}text='{discount_text}':fontcolor=white:fontsize=46:"
                    f"x=(w-text_w)/2:y=1205:box=1:boxcolor={colors['discount']}@0.92:boxborderw=14:"
                    f"shadowx=0:shadowy=2:shadowcolor=0x000000@0.8"
                )

            cmd = [
                "ffmpeg", "-y",
                "-f", "lavfi", "-i", f"color=c=0x0a0a1a:s=1080x1920:d={duration}",
                "-i", audio_path,
                "-vf", ",".join(vf_parts),
                "-c:v", "libx264", "-preset", "veryfast",  # adicionado preset
                "-c:a", "aac", "-b:a", "64k",  # reduzido de 128k
                "-t", str(duration),
                "-pix_fmt", "yuv420p", "-r", "15", "-crf", "23",  # otimizações
                "-threads", "4",  # limita threads
                output_path
            ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if _os.path.exists(output_path) and _os.path.getsize(output_path) > 5000:
            logger.info(f"Distributor: vídeo gerado ({_os.path.getsize(output_path)} bytes)")
            return output_path
        logger.error(f"Distributor: ffmpeg failed: {result.stderr[-400:]}")
        return None

    except Exception as e:
        logger.error(f"Distributor: generate_offer_video failed: {e}")
        return None
    finally:
        import shutil
        try:
            shutil.rmtree(tmpdir)
        except Exception:
            pass


async def post_to_youtube(offer: dict, description: str, short_url: str = "", video_path: str = "") -> dict:
    """Gera vídeo Short da oferta e publica no YouTube.

    Se `video_path` for fornecido, usa o arquivo existente em vez de gerar um novo.

    YouTube permite link de afiliado na descrição (diferente Facebook/IG).
    Descrição com link direto da loja (sem disclosure — mais natural no BR).
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

            # Usa vídeo fornecido ou gera um novo
            use_provided_video = bool(video_path and _os.path.exists(video_path))
            if not use_provided_video:
                tmp_video = tempfile.mktemp(suffix=".mp4")
                video_path = await generate_offer_video(offer, tmp_video)
            if not video_path or not _os.path.exists(video_path):
                return {"ok": False, "error": "Failed to generate offer video"}

            # Constrói descrição se não fornecida
            if not description:
                description = build_youtube_description(offer, affiliate_url, short_url)

            # Título com hook — descoberta do Shorts é 80% título
            title = _youtube_title(offer)

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

            # Limpa arquivo temporário (sempre, mesmo em caso de erro)
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
        # Limpa arquivo temporário em caso de erro
        if video_path and _os.path.exists(video_path):
            try:
                _os.remove(video_path)
            except Exception:
                pass
        return {"ok": False, "error": str(e)}


async def _enrich_offer_with_coupon(offer: dict) -> dict:
    """Busca cupom ativo para o provider da oferta e injeta no offer dict.
    Para ML: só aplica se store_name do cupom bater com seller_name do produto.
    Para Amazon: aplica qualquer cupom (já é detectado na página do produto).
    """
    provider = offer.get("provider", "")
    provider_map = {
        "mercadolivre": "mercadolivre",
        "amazon": "amazon",
    }
    coupon_provider = provider_map.get(provider)
    if not coupon_provider:
        return offer

    try:
        from app.db.session import AsyncSessionLocal
        from app.models.models import Coupon
        from sqlalchemy import select, or_, and_, func

        async with AsyncSessionLocal() as db:
            # Filtro comum: cupom deve ter desconto definido (percent OU valor fixo)
            # Ignora cupons lixo (#ENTREGA, etc.) sem desconto real
            has_discount = or_(
                and_(Coupon.discount_percent.isnot(None), Coupon.discount_percent > 0),
                and_(Coupon.discount_value.isnot(None), Coupon.discount_value > 0),
            )

            # Para ML: tenta casar por store_name (nome da loja)
            # Para Amazon: pega qualquer cupom ativo
            if coupon_provider == "mercadolivre":
                # Pega o seller_name do produto (se tiver)
                seller = offer.get("seller_name", "")

                if seller:
                    # Busca cupom da mesma loja
                    result = await db.execute(
                        select(Coupon)
                        .where(
                            Coupon.provider == coupon_provider,
                            Coupon.is_active == True,
                            has_discount,
                            or_(
                                Coupon.store_name == seller,
                                Coupon.store_name.ilike(f"%{seller}%"),
                                Coupon.store_name.is_(None),  # cupons sem loja específica
                            ),
                        )
                        .order_by(Coupon.expires_at.asc())
                        .limit(1)
                    )
                else:
                    # Sem seller_name no produto — pega qualquer cupom (fallback)
                    result = await db.execute(
                        select(Coupon)
                        .where(
                            Coupon.provider == coupon_provider,
                            Coupon.is_active == True,
                            has_discount,
                        )
                        .order_by(Coupon.expires_at.asc())
                        .limit(1)
                    )
            else:
                # Amazon: qualquer cupom ativo COM desconto definido
                result = await db.execute(
                    select(Coupon)
                    .where(
                        Coupon.provider == coupon_provider,
                        Coupon.is_active == True,
                        has_discount,
                    )
                    .order_by(Coupon.expires_at.asc())
                    .limit(1)
                )

            coupon = result.scalar()
            if coupon:
                offer["coupon"] = {
                    "code": coupon.coupon_code,
                    "discount_text": coupon.discount_text,
                    "expires_at": coupon.expires_at.isoformat() if coupon.expires_at else None,
                    "store_name": coupon.store_name,
                }
                logger.info(f"Cupom aplicado: {coupon.coupon_code} ({coupon.discount_text}) — loja: {coupon.store_name}")
    except Exception as e:
        logger.debug(f"Erro ao buscar cupom: {e}")

    return offer


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

    # Dedup por produto (ml_code/id/título — NÃO affiliate_url: o meli.la
    # muda a cada scrape, então dedup por URL nunca batia e repostava)
    offer_key = _offer_key(offer)
    if already_posted(offer_key):
        return {"ok": False, "error": "Offer already posted recently"}

    # Busca cupom ativo para o provider da oferta
    offer = await _enrich_offer_with_coupon(offer)

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
            # Instagram: caption SEM link no corpo (anti-banimento Meta)
            # Link vai nos comentários (fixado automaticamente)
            caption = build_caption_facebook(offer)
        elif channel == "youtube":
            # YouTube: descrição COM link direto (permitido, sem disclosure)
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

        result["short_url"] = short_url
        result["source"] = source
        results[channel] = result

        # Rate limit entre canais
        if len(channels) > 1:
            await asyncio.sleep(2)

    posted_any = any(r.get("ok") for r in results.values())
    if posted_any:
        # Marca uma vez por produto se QUALQUER canal postou — antes só
        # Telegram/Facebook marcavam, então sucesso só no Instagram/YouTube
        # deixava a oferta elegível de novo na próxima janela
        mark_posted(offer_key)
    return {
        "ok": posted_any,
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

    # Usa categorias de demanda (não aleatório geral — só queries que convertem)
    categories = random.sample(
        list(DEMAND_CATEGORIES.keys()),
        min(n_offers, len(DEMAND_CATEGORIES))
    )

    posted = 0
    errors = 0
    details = []

    for category in categories:
        if posted >= n_offers:
            break

        queries = random.sample(
            DEMAND_CATEGORIES[category],
            min(3, len(DEMAND_CATEGORIES[category]))
        )

        # Busca in-process — antes ia via HTTP na API pública e competia
        # no rate-limit de 30 buscas/min do bucket 127.0.0.1 (compartilhado
        # com o SSR do site) → 429 esvaziava todas as categorias. Também
        # deixa de gravar evento na tabela searches (poluía stats como 'ssr').
        from app.services.search import search_all

        offer = None
        for query in queries:
            try:
                resp = await search_all(query, limit=20, record_event=False)
                offers = [o.model_dump(mode="json") for o in resp.offers]
            except Exception:
                continue

            # Filtra por qualidade + demanda + marca + dedup
            candidates = []
            for o in offers:
                fp = o.get("final_price") or 0
                if not (MIN_PRICE <= fp <= MAX_PRICE):
                    continue
                if not o.get("affiliate_url"):
                    continue
                # Desconto: se tem discount_percent > 0, exige >= 15%
                # Se discount_percent == 0 (ML/Amazon DB sem preço original), aceita
                # — o _is_real_discount valida contra histórico de preço
                dp = o.get("discount_percent", 0)
                if dp > 0 and dp < MIN_DISCOUNT:
                    continue
                if not _has_recognized_brand(o.get("title", "")):
                    continue
                if _is_accessory(o.get("title", "")):
                    continue
                if not _meets_demand(o):
                    continue
                if already_posted(_offer_key(o)):
                    continue
                candidates.append(o)

            # Valida desconto real contra histórico de preço (async)
            valid = []
            for o in candidates:
                if await _is_real_discount(o):
                    valid.append(o)

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
            logger.warning(
                f"Distributor: nenhuma oferta elegível na categoria '{category}' "
                f"(queries={queries}) — filtros de qualidade/marca/dedup rejeitaram tudo"
            )
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
            chans = result.get("channels") or {}
            errs = "; ".join(
                f"{c}: {r.get('error', '?')}" for c, r in chans.items() if not r.get("ok")
            )
            logger.warning(
                f"Distributor: post falhou ('{offer.get('title', '')[:40]}'): {errs or 'sem detalhe'}"
            )

        await asyncio.sleep(3)  # rate limit

    return {
        "ok": posted > 0,
        "posted": posted,
        "errors": errors,
        "details": details,
    }


# ─── Loop automático ──────────────────────────────────────────────────────────

# Horários de postagem (hora local BR, UTC-3)
# Foco em qualidade: 3 posts/dia para Telegram/FB/IG (apenas melhores ofertas)
# Horários de pico: almoço e jantar
POST_SCHEDULE = [
    (12, 1),  # 12h — 1 oferta (pico almoço)
    (19, 2),  # 19h — 2 ofertas (jantar)
]

# YouTube: 2 vídeos/dia (qualidade sobre quantidade)
YOUTUBE_POST_SCHEDULE = [
    (12, 1),
    (19, 1),
]

NIGHT_OFFERS = 0  # sem madrugada (baixo engajamento em todas)
INTERVAL_SECONDS = 1800  # checa a cada 30 min se é hora de postar
ALL_CHANNELS = ["telegram", "facebook", "instagram", "youtube"]


async def run_distributor_loop():
    """Loop automático do distributor.

    Foco em qualidade sobre quantidade:
    - Telegram/FB/IG: 3 posts/dia nos horários de pico (12h, 19h)
    - YouTube: 2 vídeos/dia (12h, 19h)

    Janela de postagem: 2 horas (sched_hour até sched_hour+1:59)
    — garante que mesmo se o loop acordar tarde, ainda posta.
    Canais rápidos (telegram, facebook, instagram) rodam primeiro;
    YouTube roda em background para não travar o loop.
    """
    logger.info(f"Distributor loop started. Channels: {ALL_CHANNELS}")

    # Track se já postou em cada horário hoje
    posted_today = {}      # {"2026-06-28_12": True}
    youtube_posted_today = {}  # mesmo formato, só para YouTube
    yt_fail_streak = 0     # janelas seguidas sem postar → alerta Telegram a cada 3

    while True:
        now = datetime.now()
        hour = now.hour
        today_key = now.strftime("%Y-%m-%d")

        # Reset diario
        stale = [k for k in posted_today if not k.startswith(today_key)]
        for k in stale:
            del posted_today[k]
        stale_yt = [k for k in youtube_posted_today if not k.startswith(today_key)]
        for k in stale_yt:
            del youtube_posted_today[k]

        # Limpeza de arquivos temporários (a cada loop)
        cleanup_temp_files()

        # ── Canais rápidos (Telegram, Facebook, Instagram) ──
        n_offers = 0
        schedule_hour = None
        for sched_hour, sched_n in POST_SCHEDULE:
            in_window = hour == sched_hour or hour == sched_hour + 1
            key = f"{today_key}_{sched_hour}"
            if in_window and not posted_today.get(key):
                n_offers = sched_n
                schedule_hour = sched_hour
                break

        if n_offers > 0 and CHANNEL_ID:
            logger.info(f"Distributor: posting {n_offers} offers (hour={hour}, window={schedule_hour})...")
            try:
                fast_channels = ["telegram", "facebook", "instagram"]
                result = await distribute_auto(
                    n_offers=n_offers,
                    channels=fast_channels,
                    use_ai=True,
                )
                logger.info(f"Distributor: fast channels done — posted={result.get('posted', 0)}, errors={result.get('errors', 0)}")
                if result.get("ok"):
                    posted_today[f"{today_key}_{schedule_hour}"] = True
            except Exception as e:
                logger.error(f"Distributor loop error: {e}", exc_info=True)
                posted_today[f"{today_key}_{schedule_hour}"] = True

        # ── YouTube separado (menos posts) ──
        yt_n_offers = 0
        yt_schedule_hour = None
        for sched_hour, sched_n in YOUTUBE_POST_SCHEDULE:
            in_window = hour == sched_hour or hour == sched_hour + 1
            key = f"{today_key}_{sched_hour}"
            if in_window and not youtube_posted_today.get(key):
                yt_n_offers = sched_n
                yt_schedule_hour = sched_hour
                break

        if yt_n_offers > 0:
            async def _youtube_background(n, sched):
                nonlocal yt_fail_streak
                try:
                    yt_result = await distribute_auto(
                        n_offers=n,
                        channels=["youtube"],
                        use_ai=False,
                    )
                    logger.info(f"Distributor: YouTube done — posted={yt_result.get('posted', 0)}, errors={yt_result.get('errors', 0)}")
                    if yt_result.get("ok"):
                        youtube_posted_today[f"{today_key}_{sched}"] = True
                        yt_fail_streak = 0
                    else:
                        yt_fail_streak += 1
                        if yt_fail_streak >= 3 and yt_fail_streak % 3 == 0:
                            det = yt_result.get("details") or []
                            motivo = det[0] if det else "nenhuma oferta elegível (ver log acima)"
                            await _send_telegram_alert(
                                f"⚠️ *YouTube distributor*: {yt_fail_streak} janelas seguidas sem postar.\n"
                                f"Último motivo: `{str(motivo)[:200]}`"
                            )
                except Exception as e:
                    logger.error(f"Distributor: YouTube background error: {e}")
                    yt_fail_streak += 1
                    if yt_fail_streak >= 3 and yt_fail_streak % 3 == 0:
                        await _send_telegram_alert(
                            f"⚠️ *YouTube distributor*: {yt_fail_streak} janelas seguidas sem postar.\n"
                            f"Último motivo: exceção `{str(e)[:180]}`"
                        )
                    youtube_posted_today[f"{today_key}_{sched}"] = True

            asyncio.create_task(_youtube_background(yt_n_offers, yt_schedule_hour))

        await asyncio.sleep(INTERVAL_SECONDS)

