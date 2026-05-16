"""
Channel Broadcaster — posta ofertas automaticamente no canal Telegram.

Fluxo a cada hora:
  1. Busca ofertas via API com queries rotacionadas aleatoriamente
  2. Deduplica: nunca posta o mesmo affiliate_url nas últimas 24h
  3. Sorteia posição na lista de resultados (não sempre o top-1)
  4. Formata mensagem rica e posta no canal
  5. Registra clique como source="telegram_channel"

Setup:
  - Criar canal @BestPriceTodayBR e adicionar bot como admin
  - TELEGRAM_CHANNEL_ID no .env (ex: @BestPriceTodayBR ou -100123456)
"""

import asyncio
import hashlib
import httpx
import os
import random
import json
from datetime import datetime, timedelta
from pathlib import Path

BOT_TOKEN  = os.getenv("TELEGRAM_BOT_TOKEN", "")
CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID", "")
API_URL    = os.getenv("API_URL", "https://alessandro2090-bestpricetoday-api.hf.space")
ADMIN_KEY  = os.getenv("ADMIN_MANAGER_KEY", "")

# Arquivo local de deduplicação (persiste entre restarts do worker)
DEDUP_FILE = Path("/tmp/broadcaster_dedup.json")
DEDUP_TTL_HOURS = 24  # não repete a mesma oferta em 24h

# Queries por categoria — broadcaster sorteia categorias diferentes a cada rodada
QUERY_CATEGORIES: dict[str, list[str]] = {
    "smartphones": ["smartphone samsung galaxy", "iphone 15", "xiaomi redmi", "motorola edge", "poco x6"],
    "informatica":  ["notebook gamer", "ssd nvme 1tb", "monitor gamer 144hz", "rtx 4070", "processador amd ryzen"],
    "audio":        ["fone bluetooth tws", "headset gamer", "caixa de som bluetooth", "earbuds airpods"],
    "wearables":    ["smartwatch samsung", "xiaomi band 8", "garmin forerunner", "apple watch"],
    "casa":         ["airfryer 5l", "aspirador robo", "cafeteira expresso", "panela eletrica", "ventilador"],
    "tv_video":     ["smart tv 50 4k", "projetor full hd", "chromecast", "fire stick 4k"],
    "games":        ["playstation 5", "nintendo switch", "controle xbox", "headset ps5", "jogo ps5"],
    "tablets":      ["tablet samsung galaxy", "ipad air", "tablet android 10", "kindle paperwhite"],
    "cameras":      ["camera mirrorless", "gopro hero", "drone dji", "camera digital"],
    "periferico":   ["teclado mecanico", "mouse gamer sem fio", "mousepad gamer", "webcam 1080p"],
}

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
    return datetime.utcnow() - posted_at < timedelta(hours=DEDUP_TTL_HOURS)


def mark_posted(url: str):
    data = _load_dedup()
    # Limpa entradas antigas (> 24h)
    cutoff = datetime.utcnow() - timedelta(hours=DEDUP_TTL_HOURS)
    data = {h: ts for h, ts in data.items()
            if datetime.fromisoformat(ts) > cutoff}
    data[_url_hash(url)] = datetime.utcnow().isoformat()
    _save_dedup(data)


# ─── Busca com variação ────────────────────────────────────────────────────────

async def fetch_varied_offer(query: str, skip_top: int = 0) -> dict | None:
    """
    Busca ofertas para a query e retorna uma que:
    - Não foi postada nas últimas 24h
    - Tem preço > R$20 e affiliate_url válido
    - Não é sempre o top-1 (skip_top = quantos pular)
    """
    try:
        async with httpx.AsyncClient(timeout=20) as c:
            r = await c.get(
                f"{API_URL}/api/v1/search",
                params={"q": query, "limit": 10},
            )
            offers = r.json().get("offers", [])
    except Exception:
        return None

    # Filtra inválidas
    valid = [
        o for o in offers
        if o.get("final_price", 0) >= 20
        and o.get("affiliate_url")
        and not already_posted(o["affiliate_url"])
    ]

    if not valid:
        return None

    # Sorteia entre os válidos (não sempre o primeiro)
    # Peso: score mais alto tem maior chance, mas não é determinístico
    scores = [max(1, o.get("score", 50)) for o in valid]
    total = sum(scores)
    rand = random.uniform(0, total)
    acc = 0
    for offer, score in zip(valid, scores):
        acc += score
        if rand <= acc:
            return offer

    return valid[0]


# ─── Formatação e envio ───────────────────────────────────────────────────────

def _build_caption(offer: dict) -> str:
    title        = offer.get("title", "")[:80]
    price        = offer.get("final_price", 0)
    original     = offer.get("original_price", 0)
    discount     = offer.get("discount_percent", 0)
    shipping_free= offer.get("shipping_free", False)
    provider     = offer.get("provider", "loja")
    affiliate_url= offer.get("affiliate_url", "")
    score        = offer.get("score", 0)
    economy      = offer.get("economy", 0)
    emoji        = PROVIDER_EMOJI.get(provider, "🏪")
    now          = datetime.now().strftime("%d/%m %H:%M")

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

    lines.append(f"\n👉 [Ver oferta e comprar]({affiliate_url})")
    lines.append(f"\n🛍️ @BestPriceTodayBR | bestpricetoday.vercel.app")

    return "\n".join(lines)


async def post_offer_to_channel(offer: dict) -> bool:
    if not BOT_TOKEN or not CHANNEL_ID:
        return False

    caption       = _build_caption(offer)
    image_url     = offer.get("image_url", "")
    affiliate_url = offer.get("affiliate_url", "")
    provider      = offer.get("provider", "")
    title         = offer.get("title", "")[:80]
    price         = offer.get("final_price", 0)

    # Registra clique
    if ADMIN_KEY:
        try:
            async with httpx.AsyncClient(timeout=5) as c:
                await c.post(f"{API_URL}/api/v1/admin/clicks", json={
                    "offer_id": offer.get("product_id", ""),
                    "provider": provider,
                    "product_title": title,
                    "price": price,
                    "affiliate_url": affiliate_url,
                    "source": "telegram_channel",
                })
        except Exception:
            pass

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
                    return True

            # Fallback texto
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
                return True
            return False

    except Exception as e:
        print(f"[Broadcaster] Telegram error: {e}")
        return False


# ─── Broadcast principal ─────────────────────────────────────────────────────

async def broadcast_top_offers(n_offers: int = 3) -> dict:
    """
    Busca e posta N ofertas diversificadas no canal.
    - Seleciona N categorias aleatórias diferentes
    - Dentro de cada categoria, sorteia uma query
    - Garante que nenhuma oferta foi postada nas últimas 24h
    """
    if not CHANNEL_ID:
        return {"ok": False, "error": "TELEGRAM_CHANNEL_ID not configured"}

    # Sorteia N categorias diferentes
    categories = random.sample(list(QUERY_CATEGORIES.keys()),
                               min(n_offers, len(QUERY_CATEGORIES)))

    posted = 0
    errors = 0
    posted_titles = []

    for category in categories:
        if posted >= n_offers:
            break

        # Sorteia queries dentro da categoria (tenta até 3 antes de desistir)
        queries = random.sample(QUERY_CATEGORIES[category],
                                min(3, len(QUERY_CATEGORIES[category])))

        offer = None
        for query in queries:
            offer = await fetch_varied_offer(query)
            if offer:
                break

        if not offer:
            errors += 1
            continue

        ok = await post_offer_to_channel(offer)
        if ok:
            posted += 1
            posted_titles.append(offer.get("title", "")[:40])
            await asyncio.sleep(3)  # rate limit
        else:
            errors += 1

    return {
        "posted": posted,
        "errors": errors,
        "titles": posted_titles,
    }


# ─── Loop automático ──────────────────────────────────────────────────────────

async def run_broadcaster_loop():
    """Roda para sempre, postando a cada hora."""
    print(f"[Broadcaster] Starting. Channel: {CHANNEL_ID or 'NOT SET'}")
    while True:
        now = datetime.now()
        hour = now.hour
        n = 3 if 9 <= hour <= 23 else 1

        print(f"[Broadcaster] {now.strftime('%H:%M')} — posting {n} offers...")
        result = await broadcast_top_offers(n_offers=n)
        print(f"[Broadcaster] Done: {result}")

        await asyncio.sleep(3600)


if __name__ == "__main__":
    asyncio.run(run_broadcaster_loop())
