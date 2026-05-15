"""
Channel Broadcaster — posta ofertas automaticamente no canal Telegram.

Fluxo a cada hora:
  1. Busca top 5 ofertas via API (várias queries rotacionadas)
  2. Para cada oferta: formata mensagem rica com preço, desconto, score
  3. Posta no canal com botão "Ver oferta" (link afiliado)
  4. Registra o clique como source="telegram_channel"

Setup necessário:
  - Criar canal @BestPriceTodayBR no Telegram
  - Adicionar o bot como admin do canal
  - Setar TELEGRAM_CHANNEL_ID no .env (ex: @BestPriceTodayBR ou -1001234567890)
"""

import asyncio
import httpx
import os
import random
from datetime import datetime
from pathlib import Path

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID", "")  # @BestPriceTodayBR
API_URL = os.getenv("API_URL", "https://alessandro2090-bestpricetoday-api.hf.space")
ADMIN_KEY = os.getenv("ADMIN_MANAGER_KEY", "")

# Rotaciona queries para variedade de produtos
QUERY_ROTATION = [
    "smartphone samsung", "iphone", "notebook gamer",
    "fone bluetooth", "smartwatch", "tablet android",
    "ar condicionado", "smart tv", "rtx 4070", "ssd nvme",
    "airfryer", "aspirador robo", "playstation 5",
    "kindle", "cafeteira", "monitor gamer",
    "teclado mecanico", "mouse gamer", "headset",
    "camera fotografica", "drone", "impressora",
]

PROVIDER_EMOJI = {
    "aliexpress": "🔴", "shopee": "🟠", "mercadolivre": "🟡",
    "amazon": "📦", "lomadee": "🟣", "kabum": "🟢", "awin": "🔵",
}

def fmt_brl(v: float) -> str:
    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

async def fetch_best_offer(query: str) -> dict | None:
    try:
        async with httpx.AsyncClient(timeout=20) as c:
            r = await c.get(f"{API_URL}/api/v1/search", params={"q": query, "limit": 3})
            offers = r.json().get("offers", [])
            # Prefer offers with discount and image
            for o in offers:
                if o.get("final_price", 0) > 0 and o.get("affiliate_url"):
                    return o
    except Exception:
        pass
    return None

async def post_offer_to_channel(offer: dict, query: str) -> bool:
    """Posts offer to Telegram channel with photo if available."""
    if not BOT_TOKEN or not CHANNEL_ID:
        return False

    title = offer.get("title", "")[:80]
    price = offer.get("final_price", 0)
    original = offer.get("original_price", 0)
    discount = offer.get("discount_percent", 0)
    shipping_free = offer.get("shipping_free", False)
    provider = offer.get("provider", "loja")
    affiliate_url = offer.get("affiliate_url", "")
    image_url = offer.get("image_url", "")
    score = offer.get("score", 0)
    economy = offer.get("economy", 0)
    emoji = PROVIDER_EMOJI.get(provider, "🏪")
    now = datetime.now().strftime("%d/%m %H:%M")

    # Build caption
    lines = [f"🔥 *OFERTA DO DIA — {now}*\n"]

    if discount >= 5 and not offer.get("is_fake_discount"):
        lines.append(f"🏷️ *-{discount:.0f}% de desconto!*")

    lines.append(f"📦 {title}")
    lines.append("")

    if original and original > price:
        lines.append(f"~~De {fmt_brl(original)}~~")
    lines.append(f"💵 *{fmt_brl(price)}*")

    if shipping_free:
        lines.append("✅ Frete grátis")
    if economy > 5:
        lines.append(f"💰 Economize {fmt_brl(economy)}")

    lines.append(f"\n{emoji} Via *{provider.upper()}*")
    lines.append(f"⭐ Score de oferta: {score:.0f}/100")
    lines.append(f"\n👉 [Ver oferta e comprar]({affiliate_url})")
    lines.append(f"\n🛍️ @BestPriceTodayBR | bestpricetoday.vercel.app")

    caption = "\n".join(lines)

    # Track click
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
                # Try sendPhoto first
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
                    return True
            # Fallback to text message
            r = await c.post(
                f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                data={
                    "chat_id": CHANNEL_ID,
                    "text": caption,
                    "parse_mode": "Markdown",
                    "disable_web_page_preview": "false",
                }
            )
            return r.status_code == 200
    except Exception as e:
        print(f"Telegram post error: {e}")
        return False

async def broadcast_top_offers(n_offers: int = 3) -> dict:
    """Fetch and post N top offers to channel."""
    if not CHANNEL_ID:
        return {"ok": False, "error": "TELEGRAM_CHANNEL_ID not configured"}

    queries = random.sample(QUERY_ROTATION, min(n_offers * 3, len(QUERY_ROTATION)))
    posted = 0
    errors = 0

    for query in queries:
        if posted >= n_offers:
            break
        offer = await fetch_best_offer(query)
        if not offer:
            continue
        # Avoid cheap/irrelevant offers
        if offer.get("final_price", 0) < 20:
            continue
        ok = await post_offer_to_channel(offer, query)
        if ok:
            posted += 1
            await asyncio.sleep(3)  # Rate limit: 3s between posts
        else:
            errors += 1

    return {"posted": posted, "errors": errors}

async def run_broadcaster_loop():
    """Runs forever, broadcasting every hour."""
    print(f"[Broadcaster] Starting. Channel: {CHANNEL_ID or 'NOT SET'}")
    while True:
        now = datetime.now()
        # Post 3 offers per hour, more frequently during peak hours (9am-11pm)
        hour = now.hour
        if 9 <= hour <= 23:
            n = 3
        else:
            n = 1  # Still post at night but less

        print(f"[Broadcaster] {now.strftime('%H:%M')} — posting {n} offers...")
        result = await broadcast_top_offers(n_offers=n)
        print(f"[Broadcaster] Done: {result}")

        await asyncio.sleep(3600)  # 1 hour

if __name__ == "__main__":
    asyncio.run(run_broadcaster_loop())
