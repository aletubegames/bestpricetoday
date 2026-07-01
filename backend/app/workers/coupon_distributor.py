"""Coupon Distributor — posta produtos com cupom ML 2x/dia em todas as mídias.

Sistema SEPARADO do distributor principal (catálogo + link afiliado).
- Pega produtos mais vendidos/cliques do catálogo
- Acha similares nos cupons ML
- Posta imagem + cupom em telegram/facebook/instagram
- YouTube: imagem + voz XTTS clone ElevenLabs (locutor/matheus), sem editar vídeo
- 2x/dia (12h, 19h) — mesmos horários do distributor mas independente
"""
import asyncio
import os
import re
import json
import tempfile
import subprocess
import random
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

import httpx
from sqlalchemy import select, text, desc, asc, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal
from app.models.models import (
    Coupon, CouponProduct, ClickEvent, ConversionEvent,
    ShortLink, FacebookAccount, YouTubeAccount,
)
from app.core.config import settings
from app.core.logging import logger

# ─── Config ───────────────────────────────────────────────────────────────────

COUPON_POST_SCHEDULE = [(12, 2), (19, 2)]  # (hour, num_offers)
TOLERANCE_HOURS = 2
DEDUP_TTL_HOURS = 24  # não repetir mesmo cupom em 24h

# XTTS v2 — clone ElevenLabs
SERIE_DIR = Path("/media/alessandro/34C0E9B1C0E97A0E/Git_Repo/SERIE")
VOICE_SAMPLE = SERIE_DIR / "PRODUCAO" / "VOZES" / "amostras_xtts" / "matheus_clear_calm_and_confident.wav"
TTS_VENV = "/home/alessandro/tts_venv/bin/python3"
COQUI_ENV = {**os.environ, "COQUI_TOS_AGREED": "1"}

# Telegram
BOT_TOKEN = settings.telegram_bot_token if hasattr(settings, 'telegram_bot_token') else os.environ.get("TELEGRAM_BOT_TOKEN", "")
CHANNEL_ID = settings.telegram_channel_id if hasattr(settings, 'telegram_channel_id') else os.environ.get("TELEGRAM_CHANNEL_ID", "")

# Facebook
FB_API = "https://graph.facebook.com/v21.0"

PROVIDER_EMOJI = {"mercadolivre": "🛒", "ml": "🛒", "amazon": "📦", "shopee": "🛍️", "aliexpress": "🛒"}


def fmt_brl(v: float) -> str:
    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


# ─── Seleção de produtos ──────────────────────────────────────────────────────

async def get_top_catalog_products(limit: int = 20) -> list[dict]:
    """Pega produtos mais clicados/convertidos do catálogo (últimos 7 dias)."""
    async with AsyncSessionLocal() as db:
        # Top por cliques
        r = await db.execute(text("""
            SELECT product_title, provider, COUNT(*) as clicks
            FROM click_events
            WHERE clicked_at >= NOW() - INTERVAL '7 days'
            GROUP BY product_title, provider
            ORDER BY clicks DESC
            LIMIT :limit
        """), {"limit": limit})
        top_clicks = [
            {"title": row[0], "provider": row[1], "clicks": row[2]}
            for row in r.fetchall()
        ]

        # Top por short_link clicks
        r = await db.execute(text("""
            SELECT product_title, provider, clicks
            FROM short_links
            WHERE clicks > 0
            ORDER BY clicks DESC
            LIMIT :limit
        """), {"limit": limit})
        top_shortlinks = [
            {"title": row[0], "provider": row[1], "clicks": row[2]}
            for row in r.fetchall()
        ]

    # Combina e dedup por título
    seen = set()
    combined = []
    for p in top_clicks + top_shortlinks:
        key = p["title"].lower()[:50]
        if key not in seen:
            seen.add(key)
            combined.append(p)
    return combined[:limit]


async def find_similar_coupon_products(catalog_title: str, limit: int = 3) -> list[dict]:
    """Acha produtos nos cupons similares ao título do catálogo."""
    # Extrai palavras-chave do título (remove stopwords, números de modelo)
    stopwords = {"de", "da", "do", "para", "com", "sem", "the", "for", "and", "a", "o", "e", "em"}
    words = re.findall(r'\b[a-zA-ZÀ-ÿ]{3,}\b', catalog_title.lower())
    keywords = [w for w in words if w not in stopwords][:5]

    if not keywords:
        return []

    async with AsyncSessionLocal() as db:
        # Busca produtos de cupom que contenham as palavras-chave
        conditions = []
        for kw in keywords:
            conditions.append(CouponProduct.title.ilike(f"%{kw}%"))

        query = (
            select(CouponProduct, Coupon)
            .join(Coupon, CouponProduct.coupon_id == Coupon.id)
            .where(
                Coupon.is_active == True,
                CouponProduct.is_available == True,
                CouponProduct.price.isnot(None),
                CouponProduct.price > 0,
                Coupon.expires_at > datetime.now(timezone.utc),
            )
        )
        # Aplica OR das keywords
        from sqlalchemy import or_
        query = query.where(or_(*conditions))
        query = query.order_by(desc(CouponProduct.price)).limit(limit * 3)

        r = await db.execute(query)
        results = []
        seen_coupons = set()
        for cp, coupon in r.fetchall():
            if coupon.coupon_code in seen_coupons:
                continue
            seen_coupons.add(coupon.coupon_code)
            results.append({
                "title": cp.title,
                "price": float(cp.price),
                "image_url": cp.image_url,
                "product_url": cp.product_url,
                "ml_code": cp.ml_code,
                "coupon_code": coupon.coupon_code,
                "coupon_discount": coupon.discount_text or "",
                "coupon_discount_percent": float(coupon.discount_percent or 0),
                "coupon_expires_at": coupon.expires_at,
                "store_name": coupon.store_name or "",
                "coupon_id": str(coupon.id),
            })
            if len(results) >= limit:
                break
        return results


async def select_coupon_offers(num: int = 2) -> list[dict]:
    """Seleciona ofertas de cupom baseadas nos produtos mais populares do catálogo."""
    top_products = await get_top_catalog_products(limit=30)
    if not top_products:
        logger.info("CouponDistributor: sem produtos populares no catálogo, pegando cupons aleatórios")
        # Fallback: pega cupons ativos aleatórios com produtos
        async with AsyncSessionLocal() as db:
            r = await db.execute(text("""
                SELECT cp.title, cp.price, cp.image_url, cp.product_url, cp.ml_code,
                       c.coupon_code, c.discount_text, c.discount_percent, c.expires_at,
                       c.store_name, c.id::text as coupon_id
                FROM coupon_products cp
                JOIN coupons c ON cp.coupon_id = c.id
                WHERE c.is_active = true AND cp.is_available = true
                  AND cp.price IS NOT NULL AND cp.price > 0
                  AND c.expires_at > NOW()
                ORDER BY c.expires_at ASC
                LIMIT :limit
            """), {"limit": num * 5})
            results = []
            seen = set()
            for row in r.fetchall():
                if row[5] in seen:
                    continue
                seen.add(row[5])
                results.append({
                    "title": row[0], "price": float(row[1]), "image_url": row[2],
                    "product_url": row[3], "ml_code": row[4],
                    "coupon_code": row[5], "coupon_discount": row[6] or "",
                    "coupon_discount_percent": float(row[7] or 0),
                    "coupon_expires_at": row[8], "store_name": row[9] or "",
                    "coupon_id": row[10],
                })
                if len(results) >= num:
                    break
            return results

    # Para cada produto popular, acha similares nos cupons
    all_offers = []
    for prod in top_products:
        similar = await find_similar_coupon_products(prod["title"], limit=2)
        for s in similar:
            s["matched_catalog_title"] = prod["title"]
            s["catalog_clicks"] = prod["clicks"]
            all_offers.append(s)

    # Se não achou similares, pega cupons que estão vencendo primeiro
    if not all_offers:
        async with AsyncSessionLocal() as db:
            r = await db.execute(text("""
                SELECT cp.title, cp.price, cp.image_url, cp.product_url, cp.ml_code,
                       c.coupon_code, c.discount_text, c.discount_percent, c.expires_at,
                       c.store_name, c.id::text as coupon_id
                FROM coupon_products cp
                JOIN coupons c ON cp.coupon_id = c.id
                WHERE c.is_active = true AND cp.is_available = true
                  AND cp.price IS NOT NULL AND cp.price > 0
                  AND c.expires_at > NOW()
                ORDER BY c.expires_at ASC
                LIMIT :limit
            """), {"limit": num * 3})
            for row in r.fetchall():
                all_offers.append({
                    "title": row[0], "price": float(row[1]), "image_url": row[2],
                    "product_url": row[3], "ml_code": row[4],
                    "coupon_code": row[5], "coupon_discount": row[6] or "",
                    "coupon_discount_percent": float(row[7] or 0),
                    "coupon_expires_at": row[8], "store_name": row[9] or "",
                    "coupon_id": row[10],
                })

    # Dedup por coupon_code
    seen = set()
    unique = []
    for o in all_offers:
        if o["coupon_code"] not in seen:
            seen.add(o["coupon_code"])
            unique.append(o)

    # Seleciona aleatoriamente entre os únicos
    random.shuffle(unique)
    return unique[:num]


# ─── Dedup ────────────────────────────────────────────────────────────────────

_dedup: dict[str, datetime] = {}

def mark_coupon_posted(code: str):
    _dedup[code] = datetime.now(timezone.utc)

def already_posted_coupon(code: str) -> bool:
    if code in _dedup:
        elapsed = datetime.now(timezone.utc) - _dedup[code]
        return elapsed < timedelta(hours=DEDUP_TTL_HOURS)
    return False


# ─── Legendas ─────────────────────────────────────────────────────────────────

def build_coupon_caption_telegram(offer: dict) -> str:
    """Legenda Telegram — com cupom e link direto."""
    title = offer["title"][:80]
    price = offer["price"]
    coupon_code = offer["coupon_code"]
    discount = offer.get("coupon_discount", "")
    discount_pct = offer.get("coupon_discount_percent", 0)
    store = offer.get("store_name", "")
    expires = offer.get("coupon_expires_at")
    now = datetime.now().strftime("%d/%m %H:%M")

    # Calcula preço com cupom
    final_price = price
    if discount_pct > 0:
        final_price = price * (1 - discount_pct / 100)

    lines = [f"🏷️ CUPOM DE DESCONTO — {now}\n"]
    lines.append(f"📦 {title}")
    lines.append("")
    lines.append(f"💵 {fmt_brl(price)}")
    if discount_pct > 0:
        lines.append(f"🏷️ Com cupom: {fmt_brl(final_price)}")
    if discount:
        lines.append(f"   → {discount}")
    lines.append("")
    lines.append(f"🎫 CUPOM: {coupon_code}")
    if store:
        lines.append(f"🏪 Loja: {store}")

    # Expiração
    if expires:
        exp = expires if expires.tzinfo else expires.replace(tzinfo=timezone.utc)
        delta = exp - datetime.now(timezone.utc)
        if delta.days <= 1:
            hours = int(delta.total_seconds() / 3600)
            if hours <= 24:
                lines.append(f"⏰ Vence em {hours}h!")
            else:
                lines.append("⏰ Vence amanhã!")
        elif delta.days <= 3:
            lines.append(f"⏰ Vence em {delta.days} dias")

    lines.append(f"\n🛒 Comprar: {offer.get('product_url', '')}")
    lines.append("\n🛍️ BestPriceToday — cupons de desconto")

    return "\n".join(lines)


def build_coupon_caption_facebook(offer: dict) -> str:
    """Legenda Facebook/Instagram — SEM link no corpo (anti-banimento)."""
    title = offer["title"][:80]
    price = offer["price"]
    coupon_code = offer["coupon_code"]
    discount_pct = offer.get("coupon_discount_percent", 0)
    store = offer.get("store_name", "")
    expires = offer.get("coupon_expires_at")
    now = datetime.now().strftime("%d/%m %H:%M")

    final_price = price
    if discount_pct > 0:
        final_price = price * (1 - discount_pct / 100)

    lines = [f"🏷️ CUPOM DE DESCONTO — {now}\n"]
    lines.append(f"📦 {title}")
    lines.append("")
    lines.append(f"💵 {fmt_brl(price)}")
    if discount_pct > 0:
        lines.append(f"🏷️ Com cupom: {fmt_brl(final_price)}")

    lines.append(f"\n🎫 CUPOM: {coupon_code}")
    if store:
        lines.append(f"🏪 Loja: {store}")

    if expires:
        exp = expires if expires.tzinfo else expires.replace(tzinfo=timezone.utc)
        delta = exp - datetime.now(timezone.utc)
        if delta.days <= 1:
            lines.append("⏰ Vence hoje/amanhã!")
        elif delta.days <= 3:
            lines.append(f"⏰ Vence em {delta.days} dias")

    lines.append("\n👇 Link nos comentários (fixado)")
    lines.append("🛍️ BestPriceToday — cupons de desconto")

    return "\n".join(lines)


def build_coupon_youtube_description(offer: dict) -> str:
    """Descrição YouTube — com cupom + link direto da loja."""
    title = offer["title"][:80]
    price = offer["price"]
    coupon_code = offer["coupon_code"]
    discount_pct = offer.get("coupon_discount_percent", 0)
    store = offer.get("store_name", "")
    product_url = offer.get("product_url", "")

    final_price = price
    if discount_pct > 0:
        final_price = price * (1 - discount_pct / 100)

    lines = [f"🏷️ {title}"]
    lines.append(f"💵 {fmt_brl(price)}")
    if discount_pct > 0:
        lines.append(f"Com cupom: {fmt_brl(final_price)}")
    lines.append(f"\n🎫 CUPOM: {coupon_code}")
    if store:
        lines.append(f"🏪 Loja: {store}")
    if product_url:
        lines.append(f"\n🛒 Comprar: {product_url}")
    lines.append(f"\nMais cupons: https://bestpricetoday.alaserver.com.br/cupons")
    lines.append("\n#cupom #desconto #mercadolivre #oferta #bestpricetoday #promoção")

    return "\n".join(lines)


# ─── Postagem Telegram ────────────────────────────────────────────────────────

async def post_coupon_telegram(offer: dict) -> dict:
    if not BOT_TOKEN or not CHANNEL_ID:
        return {"ok": False, "error": "Telegram not configured"}

    caption = build_coupon_caption_telegram(offer)
    image_url = offer.get("image_url", "")

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
                    },
                )
                if r.status_code == 200:
                    mark_coupon_posted(offer["coupon_code"])
                    return {"ok": True, "method": "photo"}

            r = await c.post(
                f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                data={
                    "chat_id": CHANNEL_ID,
                    "text": caption,
                    "parse_mode": "Markdown",
                },
            )
            if r.status_code == 200:
                mark_coupon_posted(offer["coupon_code"])
                return {"ok": True, "method": "text"}
            return {"ok": False, "error": f"Telegram: {r.status_code}"}
    except Exception as e:
        logger.error(f"CouponDistributor: Telegram error: {e}")
        return {"ok": False, "error": str(e)}


# ─── Postagem Facebook/Instagram ──────────────────────────────────────────────

async def _get_facebook_pages() -> list[dict]:
    try:
        async with AsyncSessionLocal() as db:
            r = await db.execute(
                select(FacebookAccount).where(
                    FacebookAccount.is_active == True,
                    FacebookAccount.page_id != "user_token",
                ).order_by(FacebookAccount.updated_at.desc())
            )
            accounts = r.scalars().all()
            now = datetime.now(timezone.utc)
            valid = []
            for acct in accounts:
                if acct.token_expires_at:
                    exp = acct.token_expires_at
                    if exp.tzinfo is None:
                        exp = exp.replace(tzinfo=timezone.utc)
                    if exp < now:
                        continue
                valid.append({
                    "page_id": acct.page_id,
                    "page_name": acct.page_name,
                    "access_token": acct.access_token,
                })
            return valid
    except Exception as e:
        logger.error(f"CouponDistributor: FB pages error: {e}")
        return []


async def post_coupon_facebook(offer: dict) -> dict:
    pages = await _get_facebook_pages()
    if not pages:
        return {"ok": False, "error": "No Facebook pages"}

    caption = build_coupon_caption_facebook(offer)
    image_url = offer.get("image_url", "")
    product_url = offer.get("product_url", "")
    posted = 0

    async with httpx.AsyncClient(timeout=30) as c:
        for page in pages:
            try:
                # Posta foto
                if image_url and image_url.startswith("http"):
                    r = await c.post(
                        f"{FB_API}/{page['page_id']}/photos",
                        data={
                            "url": image_url,
                            "caption": caption,
                            "access_token": page["access_token"],
                        },
                    )
                    if r.status_code == 200:
                        post_id = r.json().get("id")
                        # Comenta com o link (fixado)
                        if post_id and product_url:
                            cr = await c.post(
                                f"{FB_API}/{post_id}/comments",
                                data={
                                    "message": f"🛒 Comprar com cupom: {product_url}\n\nMais cupons: https://bestpricetoday.alaserver.com.br/cupons",
                                    "access_token": page["access_token"],
                                },
                            )
                            # Fixa o comentário
                            comment_id = cr.json().get("id")
                            if comment_id:
                                await c.post(
                                    f"{FB_API}/{comment_id}?is_pinned=true",
                                    data={"access_token": page["access_token"]},
                                )
                        posted += 1
                        continue

                # Fallback: post de texto
                r = await c.post(
                    f"{FB_API}/{page['page_id']}/feed",
                    data={
                        "message": caption,
                        "access_token": page["access_token"],
                    },
                )
                if r.status_code == 200:
                    post_id = r.json().get("id")
                    if post_id and product_url:
                        await c.post(
                            f"{FB_API}/{post_id}/comments",
                            data={
                                "message": f"🛒 Comprar com cupom: {product_url}",
                                "access_token": page["access_token"],
                            },
                        )
                    posted += 1
            except Exception as e:
                logger.error(f"CouponDistributor: FB post error for {page['page_name']}: {e}")

    if posted > 0:
        mark_coupon_posted(offer["coupon_code"])
        return {"ok": True, "posted": posted}
    return {"ok": False, "error": "All FB posts failed"}


# ─── YouTube com XTTS v2 ──────────────────────────────────────────────────────

def generate_xtts_narration(text: str, output_path: str) -> bool:
    """Gera narração com XTTS v2 usando clone de voz ElevenLabs (matheus/locutor).

    Usa o tts_venv separado com Coqui TTS instalado.
    """
    if not VOICE_SAMPLE.exists():
        logger.error(f"CouponDistributor: voice sample not found: {VOICE_SAMPLE}")
        return False

    # Script Python que roda no tts_venv
    script = f'''
import sys
sys.path.insert(0, "/home/alessandro/tts_venv/lib/python3.12/site-packages")
import os
os.environ["COQUI_TOS_AGREED"] = "1"
from TTS.api import TTS

tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2")
tts.tts_to_file(
    text={repr(text)},
    speaker_wav="{VOICE_SAMPLE}",
    language="pt",
    file_path="{output_path}",
)
print("OK")
'''

    try:
        result = subprocess.run(
            [TTS_VENV, "-c", script],
            capture_output=True,
            text=True,
            timeout=60,
            env=COQUI_ENV,
        )
        if result.returncode == 0 and "OK" in result.stdout:
            return True
        logger.error(f"CouponDistributor: XTTS failed: {result.stderr[-500:]}")
        return False
    except Exception as e:
        logger.error(f"CouponDistributor: XTTS error: {e}")
        return False


def generate_coupon_video(offer: dict, output_path: str) -> Optional[str]:
    """Gera vídeo do cupom: imagem do produto + narração XTTS.
    Sem animação complexa — só imagem + áudio, como nas outras mídias.
    """
    import tempfile
    tmpdir = tempfile.mkdtemp()

    try:
        # 1. Baixa imagem do produto
        img_path = os.path.join(tmpdir, "product.jpg")
        img_url = offer.get("image_url", "")
        if img_url and img_url.startswith("http"):
            try:
                with httpx.Client(timeout=10) as c:
                    r = c.get(img_url)
                    if r.status_code == 200:
                        with open(img_path, "wb") as f:
                            f.write(r.content)
            except Exception:
                pass

        # 2. Gera narração XTTS
        title = offer["title"][:60]
        price = offer["price"]
        coupon_code = offer["coupon_code"]
        discount_pct = offer.get("coupon_discount_percent", 0)
        final_price = price * (1 - discount_pct / 100) if discount_pct > 0 else price

        narration = f"{title}. De {fmt_brl_speak(price)} por {fmt_brl_speak(final_price)} com o cupom. Use o cupom {coupon_code} no checkout. Link na descrição."

        audio_path = os.path.join(tmpdir, "narration.wav")
        if not generate_xtts_narration(narration, audio_path):
            # Fallback: gera vídeo sem áudio (10s)
            cmd = [
                "ffmpeg", "-y", "-f", "lavfi", "-i", "color=c=black:s=1080x1920:d=10",
                "-c:v", "libx264", "-pix_fmt", "yuv420p", output_path
            ]
            subprocess.run(cmd, capture_output=True, timeout=30)
            return output_path if os.path.exists(output_path) else None

        # 3. Medge duração do áudio
        duration = 10  # fallback
        try:
            result = subprocess.run(
                ["ffprobe", "-v", "error", "-show_entries", "format=duration",
                 "-of", "default=noprint_wrappers=1:nokey=1", audio_path],
                capture_output=True, text=True, timeout=10
            )
            duration = float(result.stdout.strip()) + 2  # +2s margem
        except Exception:
            pass

        # 4. Monta vídeo: imagem + áudio (1080x1920 vertical para Shorts)
        if os.path.exists(img_path):
            # Imagem com zoom lento (Ken Burns) + áudio
            cmd = [
                "ffmpeg", "-y",
                "-loop", "1", "-i", img_path,
                "-i", audio_path,
                "-c:v", "libx264", "-tune", "stillimage",
                "-vf", "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2:color=black,format=yuv420p",
                "-c:a", "aac", "-b:a", "128k",
                "-t", str(duration),
                "-pix_fmt", "yuv420p",
                "-r", "30",
                output_path
            ]
        else:
            # Sem imagem: fundo preto + texto + áudio
            title_escaped = title.replace("'", "\\'")
            cmd = [
                "ffmpeg", "-y",
                "-f", "lavfi", "-i", f"color=c=0x1a1a2e:s=1080x1920:d={duration}",
                "-i", audio_path,
                "-vf", f"drawtext=text='{title_escaped}':fontcolor=white:fontsize=48:x=(w-text_w)/2:y=(h-text_h)/2",
                "-c:v", "libx264", "-c:a", "aac", "-b:a", "128k",
                "-t", str(duration),
                "-pix_fmt", "yuv420p", "-r", "30",
                output_path
            ]

        result = subprocess.run(cmd, capture_output=True, timeout=60)
        if os.path.exists(output_path):
            return output_path
        logger.error(f"CouponDistributor: ffmpeg failed: {result.stderr[-300:]}")
        return None

    except Exception as e:
        logger.error(f"CouponDistributor: video gen error: {e}")
        return None


def fmt_brl_speak(v: float) -> str:
    """Formata preço para fala (XTTS lê melhor por extenso)."""
    reais = int(v)
    centavos = int((v - reais) * 100)
    if centavos > 0:
        return f"{reais} reais e {centavos} centavos"
    return f"{reais} reais"


async def post_coupon_youtube(offer: dict) -> dict:
    """Posta vídeo no YouTube com imagem + narração XTTS."""
    from app.integrations.youtube import youtube_client

    try:
        async with AsyncSessionLocal() as db:
            r = await db.execute(select(YouTubeAccount).where(YouTubeAccount.is_active == True))
            acct = r.scalar()
            if not acct:
                return {"ok": False, "error": "Nenhuma conta YouTube ativa"}

            # Refresh token se expirado
            if acct.token_expires_at and acct.token_expires_at < datetime.now(timezone.utc):
                refreshed = await youtube_client.refresh_token(acct.refresh_token)
                acct.access_token = refreshed["access_token"]
                acct.token_expires_at = datetime.now(timezone.utc) + timedelta(seconds=refreshed.get("expires_in", 3600))
                await db.commit()

            # Gera vídeo
            tmp_video = tempfile.mktemp(suffix=".mp4")
            video_path = generate_coupon_video(offer, tmp_video)
            if not video_path or not os.path.exists(video_path):
                return {"ok": False, "error": "Failed to generate coupon video"}

            # Descrição
            description = build_coupon_youtube_description(offer)
            title = f"🏷️ CUPOM: {offer['title'][:50]} — {offer['coupon_code']} | BestPriceToday"

            tags = ["cupom", "desconto", "mercadolivre", "oferta", "bestpricetoday", "promoção", "cupom de desconto"]

            # Upload
            result = await youtube_client.upload_video(
                access_token=acct.access_token,
                file_path=video_path,
                title=title[:100],
                description=description[:5000],
                tags=tags[:15],
                category_id="22",
                privacy="public",
            )

            video_id = result.get("video_id")
            logger.info(f"CouponDistributor: YouTube posted {video_id} for coupon {offer['coupon_code']}")

            try:
                os.remove(video_path)
            except Exception:
                pass

            mark_coupon_posted(offer["coupon_code"])
            return {"ok": True, "video_id": video_id, "video_url": result.get("video_url")}

    except Exception as e:
        logger.error(f"CouponDistributor: YouTube error: {e}")
        return {"ok": False, "error": str(e)}


# ─── Loop principal ───────────────────────────────────────────────────────────

async def distribute_coupons():
    """Posta cupons 2x/dia em todas as mídias."""
    now = datetime.now()
    hour = now.hour

    # Verifica se está numa janela de postagem
    should_post = False
    for sched_hour, num in COUPON_POST_SCHEDULE:
        if abs(hour - sched_hour) <= TOLERANCE_HOURS:
            # Verifica se já postou nesta janela hoje
            today_key = f"coupon_{now.strftime('%Y%m%d')}_{sched_hour}"
            if today_key in _dedup:
                continue
            should_post = True
            _dedup[today_key] = now  # marca que tentou
            break

    if not should_post:
        return

    logger.info("CouponDistributor: iniciando postagem de cupons...")

    # Seleciona ofertas
    offers = await select_coupon_offers(num=2)
    if not offers:
        logger.info("CouponDistributor: nenhuma oferta de cupom disponível")
        return

    # Filtra já postados
    offers = [o for o in offers if not already_posted_coupon(o["coupon_code"])]
    if not offers:
        logger.info("CouponDistributor: todas as ofertas já foram postadas recentemente")
        return

    for offer in offers:
        logger.info(f"CouponDistributor: postando cupom {offer['coupon_code']} — {offer['title'][:40]}")

        # Telegram + Facebook (síncrono)
        tg = await post_coupon_telegram(offer)
        logger.info(f"  Telegram: {tg.get('ok')}")

        fb = await post_coupon_facebook(offer)
        logger.info(f"  Facebook: {fb.get('ok')}")

        # YouTube em background (não bloqueia)
        asyncio.create_task(post_coupon_youtube(offer))

        await asyncio.sleep(2)

    logger.info(f"CouponDistributor: concluído — {len(offers)} cupons postados")


async def coupon_distributor_loop():
    """Loop principal — roda a cada 30min verificando horários."""
    logger.info("CouponDistributor: loop iniciado")
    while True:
        try:
            await distribute_coupons()
        except Exception as e:
            logger.error(f"CouponDistributor: loop error: {e}")
        await asyncio.sleep(1800)  # 30 min


if __name__ == "__main__":
    asyncio.run(distribute_coupons())
