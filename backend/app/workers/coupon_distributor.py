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
import shutil
from datetime import datetime, timezone, timedelta
from typing import Optional

import httpx
from sqlalchemy import select, text, desc

from app.db.session import AsyncSessionLocal
from app.models.models import (
    Coupon, CouponProduct,
    FacebookAccount, YouTubeAccount,
)
from app.core.config import settings
from app.core.logging import logger
from app.workers.distributor import create_short_link as _create_short_link

# ─── Config ───────────────────────────────────────────────────────────────────

COUPON_POST_SCHEDULE = [(9, 1), (12, 2), (15, 1), (19, 2), (21, 1)]  # (hour, num_offers)
TOLERANCE_HOURS = 2
DEDUP_TTL_HOURS = 24  # não repetir mesmo cupom em 24h

# Telegram
BOT_TOKEN = settings.TELEGRAM_BOT_TOKEN
CHANNEL_ID = settings.TELEGRAM_CHANNEL_ID

# Facebook
FB_API = "https://graph.facebook.com/v21.0"

def fmt_brl(v: float) -> str:
    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _coupon_discount_info(offer: dict) -> tuple[float, float, float]:
    """Calcula (preço final, valor economizado, percentual efetivo) de um cupom.

    Suporta desconto percentual e desconto em valor fixo (R$ X OFF).
    Se ambos existirem, usa o que dá maior economia.
    """
    price = float(offer.get("price", 0) or 0)
    discount_pct = float(offer.get("coupon_discount_percent", 0) or 0)
    discount_value = float(offer.get("coupon_discount_value", 0) or 0)

    final_by_pct = price * (1 - discount_pct / 100) if discount_pct > 0 else price
    final_by_value = price - discount_value if discount_value > 0 else price

    # Usa o desconto que dá o menor preço final (maior economia)
    final_price = min(final_by_pct, final_by_value)
    economy = max(0.0, price - final_price)

    # Recalcula percentual efetivo para exibição
    effective_pct = discount_pct
    if economy > 0 and price > 0:
        effective_pct = max(discount_pct, round((economy / price) * 100, 1))

    return final_price, economy, effective_pct


def _parse_expires(expires) -> Optional[datetime]:
    """Normaliza campo expires para datetime timezone-aware ou None."""
    if not expires:
        return None
    if isinstance(expires, str):
        try:
            expires = datetime.fromisoformat(expires.replace("Z", "+00:00"))
        except Exception:
            return None
    if not isinstance(expires, datetime):
        return None
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    return expires


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


async def find_similar_coupon_products(catalog_title: str, limit: int = 1) -> list[dict]:
    """Acha produtos nos cupons similares ao título do catálogo.
    Otimizado: usa só 2 keywords mais específicas + LIMIT pequeno.
    """
    # Extrai palavras-chave — pega as 2 mais longas (mais específicas)
    stopwords = {"de", "da", "do", "para", "com", "sem", "the", "for", "and", "a", "o", "e", "em", "que", "por"}
    words = re.findall(r'\b[a-zA-ZÀ-ÿ]{4,}\b', catalog_title.lower())
    keywords = [w for w in words if w not in stopwords]
    keywords.sort(key=len, reverse=True)
    keywords = keywords[:2]  # só 2 keywords para query rápida

    if not keywords:
        return []

    async with AsyncSessionLocal() as db:
        from sqlalchemy import or_, func
        conditions = [CouponProduct.title.ilike(f"%{kw}%") for kw in keywords]
        query = (
            select(CouponProduct, Coupon)
            .join(Coupon, CouponProduct.coupon_id == Coupon.id)
            .where(
                Coupon.is_active == True,
                CouponProduct.is_available == True,
                CouponProduct.price.isnot(None),
                CouponProduct.price > 0,
                Coupon.expires_at > datetime.now(timezone.utc),
                or_(*conditions),
            )
            # Ordena por maior desconto efetivo (economia em R$), não por preço
            # coalesce: discount_percent e discount_value são mutuamente exclusivos (um é NULL)
            # NULL * x = NULL → sem coalesce a ordenação quebra para 100% das linhas
            .order_by(
                desc(
                    func.coalesce(Coupon.discount_percent, 0) * CouponProduct.price / 100.0
                    + func.coalesce(Coupon.discount_value, 0)
                )
            )
            .limit(limit)
        )
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
                "coupon_discount_value": float(coupon.discount_value or 0),
                "coupon_expires_at": coupon.expires_at,
                "store_name": coupon.store_name or "",
                "coupon_id": str(coupon.id),
            })
            if len(results) >= limit:
                break
        return results


async def select_coupon_offers(num: int = 2) -> list[dict]:
    """Seleciona ofertas de cupom baseadas nos produtos mais populares do catálogo.

    Estratégia:
    1. Pega top produtos do catálogo por cliques (rápido — tabela pequena)
    2. Para cada um, busca cupom similar por keyword (1 query por produto, LIMIT 3)
    3. Se não achar, fallback: cupons vencendo primeiro
    """
    # 1. Pega top produtos (rápido)
    top_products = await get_top_catalog_products(limit=10)

    # 2. Tenta achar similares — mas com timeout e fallback rápido
    all_offers = []
    for prod in top_products[:5]:  # só top 5 para não demorar
        try:
            similar = await find_similar_coupon_products(prod["title"], limit=1)
            for s in similar:
                s["matched_catalog_title"] = prod["title"]
                s["catalog_clicks"] = prod["clicks"]
                all_offers.append(s)
        except Exception as e:
            logger.warning(f"CouponDistributor: similar search failed for '{prod['title'][:30]}': {e}")
            continue
        if len(all_offers) >= num:
            break

    # 3. Fallback: maiores descontos efetivos primeiro (não vencendo primeiro)
    # Ordena por desconto efetivo (maior economia em R$) × preço mais competitivo
    if len(all_offers) < num:
        async with AsyncSessionLocal() as db:
            r = await db.execute(text("""
                SELECT cp.title, cp.price, cp.image_url, cp.product_url, cp.ml_code,
                       c.coupon_code, c.discount_text, c.discount_percent, c.expires_at,
                       c.store_name, c.id::text as coupon_id, c.discount_value
                FROM coupon_products cp
                JOIN coupons c ON cp.coupon_id = c.id
                WHERE c.is_active = true AND cp.is_available = true
                  AND cp.price IS NOT NULL AND cp.price > 0
                  AND c.expires_at > NOW()
                ORDER BY (
                    GREATEST(c.discount_percent, 0) * cp.price / 100.0
                    + COALESCE(c.discount_value, 0)
                ) DESC, cp.price ASC
                LIMIT :limit
            """), {"limit": num * 3})
            seen_codes = {o["coupon_code"] for o in all_offers}
            for row in r.fetchall():
                if row[5] in seen_codes:
                    continue
                seen_codes.add(row[5])
                all_offers.append({
                    "title": row[0], "price": float(row[1]), "image_url": row[2],
                    "product_url": row[3], "ml_code": row[4],
                    "coupon_code": row[5], "coupon_discount": row[6] or "",
                    "coupon_discount_percent": float(row[7] or 0),
                    "coupon_discount_value": float(row[11] or 0),
                    "coupon_expires_at": row[8], "store_name": row[9] or "",
                    "coupon_id": row[10],
                })
                if len(all_offers) >= num:
                    break

    # Dedup + shuffle
    seen = set()
    unique = []
    for o in all_offers:
        if o["coupon_code"] not in seen:
            seen.add(o["coupon_code"])
            unique.append(o)
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
    store = offer.get("store_name", "")
    expires = offer.get("coupon_expires_at")
    now = datetime.now().strftime("%d/%m %H:%M")

    final_price, economy, discount_pct = _coupon_discount_info(offer)

    lines = [f"🏷️ CUPOM DE DESCONTO — {now}\n"]
    lines.append(f"📦 {title}")
    lines.append("")
    lines.append(f"💵 {fmt_brl(price)}")
    if discount_pct > 0 and economy > 0:
        lines.append(f"🏷️ Com cupom: {fmt_brl(final_price)}")
        lines.append(f"   ↳ Economia: {fmt_brl(economy)} ({discount_pct:.0f}% OFF)")
    if discount:
        lines.append(f"   → {discount}")
    lines.append("")
    lines.append(f"🎫 CUPOM: {coupon_code}")
    if store:
        lines.append(f"🏪 Loja: {store}")

    # Expiração
    exp = _parse_expires(expires)
    if exp:
        delta = exp - datetime.now(timezone.utc)
        if delta.days <= 1:
            hours = int(delta.total_seconds() / 3600)
            if hours <= 24:
                lines.append(f"⏰ Vence em {hours}h!")
            else:
                lines.append("⏰ Vence amanhã!")
        elif delta.days <= 3:
            lines.append(f"⏰ Vence em {delta.days} dias")

    lines.append(f"\n🛒 Comprar: {offer.get('short_url') or offer.get('product_url', '')}")
    lines.append("\n🛍️ BestPriceToday — cupons de desconto")

    return "\n".join(lines)


def build_coupon_caption_facebook(offer: dict) -> str:
    """Legenda Facebook/Instagram — SEM link no corpo (anti-banimento)."""
    title = offer["title"][:80]
    price = offer["price"]
    coupon_code = offer["coupon_code"]
    store = offer.get("store_name", "")
    expires = offer.get("coupon_expires_at")
    now = datetime.now().strftime("%d/%m %H:%M")

    final_price, economy, discount_pct = _coupon_discount_info(offer)

    lines = [f"🏷️ CUPOM DE DESCONTO — {now}\n"]
    lines.append(f"📦 {title}")
    lines.append("")
    lines.append(f"💵 {fmt_brl(price)}")
    if discount_pct > 0 and economy > 0:
        lines.append(f"🏷️ Com cupom: {fmt_brl(final_price)}")
        lines.append(f"   ↳ Economia: {fmt_brl(economy)} ({discount_pct:.0f}% OFF)")

    lines.append(f"\n🎫 CUPOM: {coupon_code}")
    if store:
        lines.append(f"🏪 Loja: {store}")

    exp = _parse_expires(expires)
    if exp:
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
    store = offer.get("store_name", "")
    product_url = offer.get("short_url") or offer.get("product_url", "")

    final_price, economy, discount_pct = _coupon_discount_info(offer)

    lines = [f"🏷️ {title}"]
    lines.append(f"💵 {fmt_brl(price)}")
    if discount_pct > 0 and economy > 0:
        lines.append(f"Com cupom: {fmt_brl(final_price)}")
        lines.append(f"Economia: {fmt_brl(economy)} ({discount_pct:.0f}% OFF)")
    lines.append(f"\n🎫 CUPOM: {coupon_code}")
    if store:
        lines.append(f"🏪 Loja: {store}")
    if product_url:
        lines.append(f"\n🛒 Comprar: {product_url}")
    lines.append(f"\nMais cupons: {settings.PUBLIC_SITE_URL}/cupons")
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
                    },
                )
                if r.status_code == 200:
                    mark_coupon_posted(offer["coupon_code"])
                    return {"ok": True, "method": "photo"}
                logger.warning(f"CouponDistributor: Telegram photo failed: {r.status_code} {r.text[:200]}")

            r = await c.post(
                f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                data={
                    "chat_id": CHANNEL_ID,
                    "text": caption,
                },
            )
            if r.status_code == 200:
                mark_coupon_posted(offer["coupon_code"])
                return {"ok": True, "method": "text"}
            logger.error(f"CouponDistributor: Telegram text failed: {r.status_code} {r.text[:200]}")
            return {"ok": False, "error": f"Telegram: {r.status_code} {r.text[:100]}"}
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
    product_url = offer.get("short_url") or offer.get("product_url", "")
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
                                    "message": f"🛒 Comprar com cupom: {product_url}\n\nMais cupons: {settings.PUBLIC_SITE_URL}/cupons",
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


# ─── YouTube com XTTS v2 (clone ElevenLabs) + ffmpeg ──────────────────────────

# XTTS v2 no servidor
TTS_VENV = "/home/alessandro/tts_venv/bin/python3"
VOICE_SAMPLE = "/home/alessandro/voices/matheus_clear_calm_and_confident.wav"
COQUI_ENV = {**os.environ, "COQUI_TOS_AGREED": "1"}


def split_text_for_tts(text):
    """Divide texto em frases limpas para geração separada no XTTS v2.

    Bug conhecido do XTTS v2 (issues #4171, #3445, #567):
    - Pontos finais (.) são falados como "ponto"
    - Reticências (...) são faladas como "ponto ponto ponto"
    - ? e ! causam alucinações em frases curtas

    Solução: dividir em frases, remover pontuação final, gerar cada uma separada,
    concatenar com silêncio entre elas.
    """
    text = re.sub(r'["\u201c\u201d\u2018\u2019\']+', '', text)
    text = re.sub(r'[\(\)\[\]\{\}]', '', text)
    text = re.sub(r'\*+', '', text)
    text = re.sub(r'[/\\]', ' ', text)
    text = re.sub(r';{2,}', ';', text)
    text = re.sub(r':{2,}', ':', text)
    text = re.sub(r'—{2,}', '—', text)
    text = re.sub(r'\.{3,}', ' \x00 ', text)
    text = re.sub(r'(\.\s){2,}\.?', ' \x00 ', text)
    parts = re.split(r'([.!?\x00])', text)
    frases = []
    pausas = []
    current = ''
    for part in parts:
        if part in ('.', '!', '?'):
            cleaned = current.strip(' ,\n\t')
            if cleaned:
                frases.append(cleaned)
                pausas.append(0.5)
            current = ''
        elif part == '\x00':
            cleaned = current.strip(' ,\n\t')
            if cleaned:
                frases.append(cleaned)
                pausas.append(1.0)
            current = ''
        else:
            current += part
    cleaned = current.strip(' ,\n\t')
    if cleaned:
        frases.append(cleaned)
        pausas.append(0.5)
    if pausas:
        pausas[0] = 0.0
    return frases, pausas


def generate_xtts_narration(text: str, output_path: str) -> bool:
    """Gera narração com XTTS v2 — clone de voz ElevenLabs (matheus/locutor).

    Usa split_text_for_tts() para dividir em frases e gerar cada uma separada,
    evitando que o XTTS v2 fale "ponto" literalmente.

    Síncrono — bloqueia a thread. Use generate_xtts_narration_async() do event loop.
    """
    if not os.path.exists(VOICE_SAMPLE):
        logger.error(f"CouponDistributor: voice sample not found: {VOICE_SAMPLE}")
        return False

    frases, pausas = split_text_for_tts(text)
    if not frases:
        logger.error("CouponDistributor: texto vazio após split")
        return False

    # Script que roda no tts_venv — gera cada frase separada e concatena com silêncio
    frases_json = json.dumps(frases)
    pausas_json = json.dumps(pausas)

    script = f'''
import os, json, numpy as np, torch, torchaudio
os.environ["COQUI_TOS_AGREED"] = "1"
from TTS.api import TTS

tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2")

frases = {frases_json}
pausas = {pausas_json}
speaker_wav = "{VOICE_SAMPLE}"
output_wav = "{output_path}"

if len(frases) == 1:
    tts.tts_to_file(text=frases[0], speaker_wav=speaker_wav, language="pt", file_path=output_wav)
    print("OK")
else:
    wavs = []
    for i, frase in enumerate(frases):
        if pausas[i] > 0:
            wavs.append(np.zeros(int(24000 * pausas[i]), dtype=np.float32))
        w = tts.tts(text=frase, speaker_wav=speaker_wav, language="pt")
        wavs.append(np.array(w))
    wavs.append(np.zeros(int(24000 * 0.3), dtype=np.float32))
    full = np.concatenate(wavs)
    torchaudio.save(output_wav, torch.tensor(full).unsqueeze(0), 24000)
    print("OK")
'''

    try:
        result = subprocess.run(
            [TTS_VENV, "-c", script],
            capture_output=True,
            text=True,
            timeout=600,  # CPU é lento — múltiplas frases
            env=COQUI_ENV,
        )
        if result.returncode == 0 and "OK" in result.stdout:
            return True
        logger.error(f"CouponDistributor: XTTS failed: {result.stderr[-500:]}")
        return False
    except subprocess.TimeoutExpired:
        logger.error("CouponDistributor: XTTS timeout (600s)")
        return False
    except Exception as e:
        logger.error(f"CouponDistributor: XTTS error: {e}")
        return False


async def generate_xtts_narration_async(text: str, output_path: str) -> bool:
    """Versão async — roda XTTS numa thread separada para não bloquear o event loop."""
    import asyncio
    return await asyncio.to_thread(generate_xtts_narration, text, output_path)


# 25 variações de abertura — evita cara de IA, parece humano
_OPENING_VARIATIONS = [
    "Olha o que encontrei pra vocês hoje",
    "Pessoal, presta atenção nessa oferta",
    "Vocês não vão acreditar nesse preço",
    "Atenção galera, essa promoção é quente",
    "Para quem gosta de economia, olha isso",
    "Hoje tem oferta boa demais pra vocês",
    "Não deixem essa passar, olha o que achei",
    "Mais uma oferta pra vocês aproveitarem",
    "Essa aqui vale muito a pena, olha só",
    "Pra quem tava esperando uma boa, chegou",
    "Olha que barganha eu trouxe pra vocês",
    "Gente, esse preço tá imbatível hoje",
    "Se liga nessa oferta que encontrei",
    "Trouxe uma oferta e tanto pra vocês",
    "Olha o que apareceu de bom hoje",
    "Essa promoção tá rolando por pouco tempo",
    "Pra quem busca preço justo, olha aqui",
    "Vocês precisam ver essa oferta urgente",
    "Mais um achado pra vocês hoje",
    "Essa aqui tá saindo barato demais",
    "Olha o que o cupom de hoje reserva",
    "Presta atenção nessa oferta relâmpago",
    "Gente, olha o desconto que conseguimos",
    "Pra você que curte economizar, olha isso",
    "Essa oportunidade não dá pra ignorar",
]

# Arquivo para guardar últimas aberturas usadas
_OPENING_HISTORY_FILE = "/home/alessandro/backend/.opening_history.json"


def _get_random_opening() -> str:
    """Pega uma abertura aleatória que não foi usada nas últimas 5 vezes."""
    history = []
    try:
        if os.path.exists(_OPENING_HISTORY_FILE):
            with open(_OPENING_HISTORY_FILE, "r") as f:
                history = json.load(f)
    except Exception:
        history = []

    # Filtra variações que não foram usadas nas últimas 5
    recent = set(history[-5:]) if len(history) >= 5 else set(history)
    available = [v for v in _OPENING_VARIATIONS if v not in recent]

    # Se todas foram usadas recentemente (improvável com 25), usa todas
    if not available:
        available = _OPENING_VARIATIONS

    chosen = random.choice(available)

    # Atualiza histórico (mantém últimos 24)
    history.append(chosen)
    history = history[-24:]
    try:
        with open(_OPENING_HISTORY_FILE, "w") as f:
            json.dump(history, f, ensure_ascii=False)
    except Exception as e:
        logger.warning(f"CouponDistributor: erro salvando histórico de aberturas: {e}")

    return chosen


# Mapeamento amplo de palavras-chave do título -> para que serve o produto
# Ordem importa: regras mais específicas devem vir antes das genéricas.
_USE_CASE_PATTERNS = [
    # --- Tecnologia / Celulares e Acessórios ---
    (r"\b(iphone|galaxy|xiaomi|motorola|lg|sony|asus)\b", "comunicar, tirar fotos e usar seus apps favoritos"),
    (r"\b(capa de chuva|capa de chuva motoqueiro|pilotilha|imperme[áa]vel|capa de chuva masculina|capa de chuva feminina)\b", "se proteger da chuva no dia a dia"),
    (r"\b(capa de volante|capa para volante|capa banco|capa de banco|capa de estepe|capa para carro)\b", "proteger e estilizar o interior do carro"),
    (r"\b(capa|case|capinha|pel[íi]cula|bumper|flip cover)\b", "proteger seu celular ou aparelho"),
    (r"\b(luva de l[áa]tex|luva de limpeza|luva de borracha|luva de cozinha|luva t[ée]rmica)\b", "proteger as mãos durante tarefas"),
    (r"\b(celular|smartphone|aparelho celular|telefone|iphone|galaxy|xiaomi|motorola|lg|sony|asus)\b", "se comunicar, tirar fotos e usar seus apps favoritos"),
    (r"\b(fone de ouvido|fone bluetooth|headphone|earbuds|headset|airpods|fones)\b", "ouvir música, podcasts e fazer chamadas"),
    (r"\b(carregador|cabo usb|cabo tipo c|power bank|bateria port[áa]til|carregador port[áa]til|bateria externa)\b", "carregar seus dispositivos"),
    (r"\b(bateria de carro|bateria moto|bateria automotiva|bateria para carro|bateria estacion[áa]ria)\b", "manter a energia do veículo"),
    (r"\b(pendrive|ssd|hd externo|cart[ãa]o de mem[óo]ria|mem[óo]ria)\b", "armazenar arquivos e fotos"),
    (r"\b(smartwatch|relogio inteligente|rel[óo]gio digital|amazfit|apple watch)\b", "monitorar sua saúde e atividades físicas"),
    (r"\b(tablet|ipad|galaxy tab)\b", "ler, assistir e navegar"),
    (r"\b(notebook|laptop|macbook|ultrabook|computador|pc)\b", "trabalhar, estudar e jogar"),
    (r"\b(monitor|tela|televis[ãa]o|tv|tv smart|smart tv|monitor gamer)\b", "assistir, jogar e trabalhar"),
    (r"\b(mouse|teclado|mousepad|kit teclado|kit gamer|hub usb|webcam)\b", "usar o computador com mais conforto"),
    (r"\b(impressora|multifuncional|scanner|toner)\b", "imprimir documentos e fotos"),
    (r"\b(roteador|wifi|repetidor|extensor|access point|modem)\b", "melhorar a internet da casa"),
    (r"\b(c[âa]mera|go pro|gopro|dslr|mirrorless|camera digital|filmadora)\b", "filmar e fotografar suas aventuras"),
    (r"\b(caixa de som|speaker|bluetooth speaker|som port[áa]til|home theater|soundbar)\b", "ouvir música e assistir filmes com som de qualidade"),
    (r"\b(controle|controle remoto|joystick|volante|controle xbox|controle ps)\b", "jogar e controlar seus aparelhos"),
    (r"\b(cabo hdmi|cabo vga|adaptador|conversor|hub|switch|extensor)\b", "conectar e expandir seus dispositivos"),
    (r"\b(gabinete|fonte|placa m[ãa]e|processador|mem[óo]ria ram|placa de v[íi]deo|cooler|water cooler)\b", "montar ou melhorar seu computador"),

    # --- Eletrodomésticos e Cozinha ---
    (r"\b(air[\s]?fryer|fritadeira el[ée]trica|fritadeira sem [óo]leo)\b", "preparar alimentos de forma prática e saudável"),
    (r"\b(cafeteira|nespresso|dolce gusto|m[áa]quina de caf[ée]|expresso)\b", "preparar café fresco e saboroso"),
    (r"\b(liquidificador|batedeira|mixer|processador|processador de alimentos|espremedor|centrifuga)\b", "preparar sucos, vitaminas e receitas na cozinha"),
    (r"\b(panela de press[ãa]o|panela el[ée]trica|panela|jogo de panelas|frigideira|wok)\b", "cozinhar refeições"),
    (r"\b(micro[-]?ondas|forno el[ée]trico|forno|air fryer forno)\b", "aquecer e preparar alimentos rápidos"),
    (r"\b(geladeira|refrigerador|frigobar|freezer|cooler)\b", "conservar alimentos e bebidas"),
    (r"\b(fog[ãa]o|cooktop|fogareiro|chapa)\b", "cozinhar"),
    (r"\b(m[áa]quina de lavar|lavadora|lava e seca|secadora|tanquinho)\b", "lavar e secar roupas"),
    (r"\b(aspirador|aspiradora|rob[ôo] aspirador|passadeira|vaporizador)\b", "limpar a casa com praticidade"),
    (r"\b(ventilador|climatizador|ar condicionado|ar split|ventilador de teto|cooler)\b", "refrescar o ambiente"),
    (r"\b(ferro de passar|passadeira|steamer)\b", "passar roupas"),
    (r"\b(purificador|filtro de [áa]gua|bebedouro|garraf[ãa]o t[ée]rmico)\b", "ter [áa]gua limpa e fresca"),
    (r"\b(p[ãa]o|torradeira|sanduicheira|grill el[ée]trico|crepeira|waffle)\b", "preparar caf[ée] da manh[ãa] e lanches"),
    (r"\b(chaleira|chaleira el[ée]trica|jarra el[ée]trica)\b", "ferver [áa]gua rapidamente"),
    (r"\b(freezer|frigobar|conservador)\b", "conservar alimentos e bebidas"),

    # --- Casa, Móveis e Decoração ---
    (r"\b(lumin[áa]ria|abajur|lustre|pendente|plafon|luz de emerg[êe]ncia|led|fita led)\b", "iluminar o ambiente"),
    (r"\b(cadeira gamer|cadeira de escrit[óo]rio|cadeira|poltrona|puff)\b", "sentar com conforto por longas horas"),
    (r"\b(mesa|escrivaninha|mesa de jantar|mesa de centro|mesa dobr[áa]vel|aparador|buffet|mesa de cabeceira)\b", "organizar seu espaço e receber pessoas"),
    (r"\b(estante|rack|arm[áa]rio|guarda-roupa|roupeiro|c[ôo]moda|criado-mudo|bancada|prateleira)\b", "organizar seus pertences"),
    (r"\b(sof[áa]|sof[áa] cama|poltrona reclin[áa]vel|chaise)\b", "relaxar e receber visitas"),
    (r"\b(colch[ãa]o|cama box|cama|travesseiro|edredom|len[çc]ol|cobertor|jogo de cama)\b", "dormir com mais conforto"),
    (r"\b(cortina|persiana|tapete|papel de parede|adesivo|quadro|decora[çc][ãa]o|vaso)\b", "deixar o ambiente mais bonito e aconchegante"),
    (r"\b(organizador|caixa organizadora|cesto|cabide|sapateira|porta trecos)\b", "organizar e otimizar espaços"),
    (r"\b(escada|escadinha|andaime|plataforma)\b", "alcançar lugares altos e facilitar serviços"),
    (r"\b(cerca|cercadinho|grade|port[ãa]o|tranca|fechadura)\b", "proteger e limitar acessos"),

    # --- Esportes, Lazer e Fitness ---
    (r"\b(barra|barras|agachamento|muscula[çc][ãa]o|halter|haltere|peso|anilha|colchonete|tapete|protetor de barras)\b", "treinar e cuidar da saúde"),
    (r"\b(luva|joelheira|munhequeira|tornozeleira|faixa|cintur[ãa]o)\b", "proteger durante atividades físicas"),
    (r"\b(bicicleta|bike|patinete|skate|patins|roller)\b", "se locomover e praticar exercícios"),
    (r"\b(chuteira|t[êe]nis|sapato|sand[áa]lia|bota|botinha|chinelo)\b", "usar no dia a dia e em atividades físicas"),
    (r"\b(camiseta|camisa|cal[çc]a|shorts|legging|jaqueta|moletom|vestido|roupa|moda|agasalho|cueca|meia)\b", "vestir no dia a dia"),
    (r"\b(bolsa|bolsa feminina|bolsa de couro|bolsa transversal|mala|necessaire|carteira feminina)\b", "carregar seus pertences com estilo"),
    (r"\b(suplemento|whey|creatina|vitamina|prote[íi]na|pr[ée] treino|termog[êe]nico|col[áa]geno)\b", "cuidar da saúde e performance"),
    (r"\b(bola|bola de futebol|bola de volei|basquete|tabela|rede|raquete|rede de volei)\b", "praticar esportes e se divertir"),
    (r"\b(pote|pote de vidro|pote herm[ée]tico|potinho|recipiente|tupperware|marmita)\b", "organizar alimentos e mantimentos"),
    (r"\b(mochila t[ée]rmica|lancheira|garrafa|squeeze|cantil|cooler)\b", "hidratar-se e levar bebidas"),
    (r"\b(mochila|mochila escolar|mochila de couro|mochila para notebook|mochila infantil)\b", "carregar seus pertences com praticidade"),
    (r"\b(barraca|saco de dormir|colchonete infl[áa]vel|lanterna|kit camping|isopor|cooler)\b", "acampar e aproveitar o ar livre"),
    (r"\b(vara de pesca|isca|molinete|anzol|caixa de pesca)\b", "pescar e relaxar"),
    (r"\b(prancha de surf|boia|nadadeira|m[áa]scara de mergulho|colete)\b", "curtir praia e piscina"),
    (r"\b(redário|rede de descanso|cadeira de praia|guarda-sol|chap[ée]u de praia)\b", "relaxar em dias de sol"),

    # --- Ferramentas, Construção e Jardim ---
    (r"\b(furadeira|parafusadeira|martelete|esmerilhadeira|politriz|serra|plaina)\b", "fazer trabalhos e consertos em casa"),
    (r"\b(chave|chave de fenda|alicate|estilete|jogo de ferramentas|ferramenta|kit ferramenta)\b", "consertar e montar coisas"),
    (r"\b(escada|andaime|plataforma|trena|nivel|n[íi]vel a laser)\b", "facilitar trabalhos em altura e medi[çc][õo]es"),
    (r"\b(mangueira|aspersor|regador|bomba d[´']?[áa]gua|bico|pulverizador|cortador de grama)\b", "cuidar do jardim e quintal"),
    (r"\b(vaso|vaso de planta|substrato|adubo|semente|mudas|jardineira|cachep[ôo])\b", "cuidar de plantas e jardim"),
    (r"\b(pintura|tinta|rolo de pintura|pincel|massa corrida|lixa|seladora)\b", "pintar e renovar ambientes"),
    (r"\b(cimento|tijolo|areia|brita|telha|telhado|concreto|argamassa)\b", "construir e reformar"),
    (r"\b(fechadura|dobradi[çc]a|trinco|ma[çc]aneta|puxador|rodap[ée]|selante)\b", "completar instala[çc][õo]es e acabamentos"),

    # --- Brinquedos, Infantil e Hobbies ---
    (r"\b(brinquedo|carrinho|boneca|urso|pel[úu]cia|lego|playmobil|massinha|bola)\b", "diversão e entretenimento infantil"),
    (r"\b(jogo de tabuleiro|jogo de cartas|baralho|quebra-cabe[çc]a|dama|xadrez)\b", "divertir a fam[íi]lia e amigos"),
    (r"\b(videogame|console|playstation|xbox|nintendo|jogos|game)\b", "jogar e se divertir"),
    (r"\b(livro|ebook|kindle|revista|HQ|mang[áa]|editora|biblioteca)\b", "ler e aprender"),
    (r"\b(papelaria|caderno|caneta|lápis|mochila escolar|estojo|borracha|corretivo)\b", "estudar e organizar materiais"),
    (r"\b(instru[çc][ãa]o musical|viol[ãa]o|guitarra|teclado|bateria|microfone|pedal)\b", "fazer m[úu]sica e se divertir"),
    (r"\b(pintura|desenho|tela|aquarela|canetinha|pintura diamante|artesanato)\b", "criar arte e relaxar"),
    (r"\b(puzzle|quebra-cabe[çc]a|jogo de montar|engenhoca)\b", "desafiar a mente e se divertir"),

    # --- Beleza, Cuidados Pessoais e Saúde ---
    (r"\b(escova de dente|escova dental|fio dental|enxaguante bucal|creme dental|irrigador oral)\b", "cuidar da saúde bucal"),
    (r"\b(escova|secador|chapinha|prancha|modelador|babyliss)\b", "cuidar dos cabelos"),
    (r"\b(aparador|barbeador|depilador|m[áa]quina de barbear|navalha|creme de barbear)\b", "cuidar da barba e pele"),
    (r"\b(perfume|fragr[âa]ncia|desodorante|col[ôo]nia|body splash)\b", "cuidar da higiene e perfumar"),
    (r"\b(creme|hidratante|protetor solar|maquiagem|base|batom|rimel|sabonete|shampoo|condicionador)\b", "cuidar da pele, cabelo e beleza"),
    (r"\b(suplemento|vitamina|termog[êe]nico|col[áa]geno|pr[ée] treino|[ôo]mega 3)\b", "cuidar da saúde e performance"),
    (r"\b(medicamento|rem[ée]dio|gen[ée]rico|analg[ée]sico|antibiótico|vitamina)\b", "cuidar da saúde"),
    (r"\b(aparelho auditivo|bengala|muleta|cadeira de rodas|andador|colar cervical)\b", "auxiliar na mobilidade e saúde"),
    (r"\b(óculos|lente|óculos de sol|óculos de grau|armação)\b", "proteger os olhos e completar o visual"),
    (r"\b(máscara|máscara facial|máscara de cabelo|máscara de dormir)\b", "cuidar da pele e relaxar"),
    (r"\b(delineador|lápis de olho|sombra|iluminador|pó compacto|primer)\b", "cuidar da maquiagem e beleza"),

    # --- Automotivo, Motos e Bicicletas ---
    (r"\b(pneu|roda|calota|parafuso|porca|estepe|macaco|chave de roda)\b", "manter o carro em bom estado"),
    (r"\b(palheta|l[âa]mpada|farol|lanterna|retr[ôo]visor|parachoques|grade)\b", "cuidar da parte el[ée]trica e est[ée]tica do ve[íi]culo"),
    (r"\b(óleo|lubrificante|filtro|filtro de ar|filtro de [óo]leo|vela|pastilha|freio)\b", "fazer manuten[çc][ãa]o do ve[íi]culo"),
    (r"\b(bateria de carro|bateria moto|carregador de bateria|cabos|bornes)\b", "manter a energia do ve[íi]culo"),
    (r"\b(capa de banco|tapete|capa de volante|organizador|extintor|tri[âa]ngulo)\b", "equipar e proteger o interior do ve[íi]culo"),
    (r"\b(capacete|luva|jaqueta|bota|óleo de moto|pastilha de moto|guid[ãa]o)\b", "andar de moto com seguran[çc]a"),
    (r"\b(cadeado|corrente|trava|alarme|bloqueador|trava de disco)\b", "proteger contra furtos"),
    (r"\b(suporte|bagageiro|bau|bagageiro de moto|extensor de guid[ãa]o)\b", "transportar bagagens"),

    # --- Pet ---
    (r"\b(ra[çc][ãa]o|petisco|areia|banheiro|coleira|peitoral|guia|brinquedo pet|cama pet)\b", "cuidar do seu pet"),
    (r"\b(caixa de transporte|bolsa pet|bebbedouro|comedouro|arranhador)\b", "deixar o pet mais conforto e seguro"),

    # --- Papelaria, Escritório e Escola ---
    (r"\b(caderno|agenda|planner|caneta|lápis|borracha|r[éé]gua|compasso|estojo|mochila)\b", "estudar e organizar o dia a dia"),
    (r"\b(etiqueta|etiquetadora|rotulador|organizador|pasta|envelope|clipe|papel)\b", "organizar documentos e objetos"),
    (r"\b(carteira|porta documentos|chaveiro|rel[óo]gio de pulso|óculos)\b", "usar no dia a dia"),

    # --- Alimentos e Bebidas ---
    (r"\b(chocolate|biscoito|bala|chiclete|pipoca|snack|castanha|amendoim|doce|sobremesa)\b", "saciar a vontade de comer algo gostoso"),
    (r"\b(refrigerante|suco|cerveja|vinho|água|energ[ée]tico|caf[ée]|ch[áa]|whisky)\b", "beber e refrescar"),
    (r"\b(arroz|feij[ãa]o|macarr[ãa]o|azeite|leite|ovos|p[ãa]o|manteiga|caf[ée])\b", "preparar refeições do dia a dia"),

    # --- Genéricos e cestas ---
    (r"\b(kit|conjunto|jogo|combo|pack|pack com|caixa com|kit de|combo de|sortido)\b", "ter tudo o que precisa em um só lugar"),
    (r"\b(presente|cesta|cesta b[áa]sica|cesta de natal|lembrancinha|brinde)\b", "presentear algu[ée]m especial"),
    (r"\b(acess[óo]rio|acess[óo]rios|adaptador|suporte|base|suporte de|trip[ée])\b", "complementar e facilitar o uso de outros itens"),
]



# Palavras que ignoramos no fallback de substantivo principal
_USE_FALLBACK_STOPWORDS = {
    "com", "sem", "para", "por", "dos", "das", "nos", "nas", "que", "como", "aos",
    "esse", "essa", "este", "esta", "aquele", "aquela", "novo", "nova", "novos", "novas",
    "original", "originais", "oficial", "oficiais", "universal", "universais",
    "compatível", "compativeis", "compatíveis", "resistente", "resistentes",
    "premium", "profissional", "profissionais", "doméstico", "doméstica", "domésticos",
    "portátil", "portáteis", "portateis", "elétrico", "elétrica", "elétricos", "eletrico",
    "digital", "digitais", "inteligente", "inteligentes", "smart", "plus", "pro", "max",
    "mini", "ultra", "nacional", "importado", "importada", "importados", "frete", "grátis",
    "gratis", "promoção", "promocao", "oferta", "ofertas", "desconto", "descontos", "cupom",
    "lote", "lotes", "kit", "conjunto", "jogo", "combo", "pack", "sortido", "cor", "cores",
    "tamanho", "modelo", "modelos", "marca", "ref", "referencia", "referência", "codigo",
    "código", "mlb", "garantia", "básica", "basica", "básico", "basico", "puro", "pura",
    "natural", "artesanal", "autentico", "autêntico", "autentica", "autêntica", "feminino",
    "feminina", "masculino", "masculina", "infantil", "adulto", "adulta", "adultos", "pequeno",
    "pequena", "medio", "médio", "media", "média", "grande", "grandes", "extra", "super",
    "mega", "hyper", "hiper", "top", "best", "seller", "venda", "vitrine", "lançamento",
    "lancamento", "versão", "versao", "edicão", "edicao", "limitado", "limitada", "especial",
    "exclusivo", "exclusiva", "selecionado", "selecionada", "certificado", "certificada",
    "homologado", "homologada", "compativel", "original", "garantia", "fabrica", "fábrica",
    "fornecedor", "loja", "vendedor", "atacado", "varejo", "unidade", "unidades", "peca",
    "peça", "pecas", "peças", "par", "pares", "jogo", "conjunto", "kit", "caixa", "pacote",
    "pack", "lote", "refil", "refil", "reposição", "reposiçao", "reposicao", "recarga",
    "complemento", "complementar", "extra", "adicional", "adicionais", "opcional", "opcionais",
    "acessorio", "acessório", "acessorios", "acessórios", "adaptador", "adaptadores",
    "conector", "conectores", "extensão", "extensao", "prolongador", "prolongadores",
    "suporte", "suportes", "base", "bases", "tripé", "tripe", "cabide", "cabides", "gancho",
    "ganchos", "presilha", "presilhas", "organizador", "organizadores", "porta", "portas",
    "capa", "capas", "case", "cases", "capinha", "capinhas", "pelicula", "película", "peliculas",
    "películas", "bumper", "flip", "cover", "proteção", "protecao", "proteger", "blindagem",
    "blindagem", "anti", "queda", "impacto", "risco", "arranhão", "arranhao", "choque", "agua",
    "água", "polegadas", "polegada", "pol", "pols", "cm", "mm", "ml", "g", "kg", "litros",
    "litro", "w", "watts", "volts", "hz", "mah", "gb", "tb", "mb", "tb", "promo", "ofertao",
    "imperdivel", "imperdível", "aproveite", "ultimas", "últimas", "unidades", "restantes",
    "disponivel", "disponível", "pronta", "pronto", "entrega", "envio", "rapido", "rápido",
}


def _product_use_phrase(title: str) -> str:
    """Tenta extrair do título para que serve o produto. Fallback genérico."""
    t = title.lower()
    for pattern, phrase in _USE_CASE_PATTERNS:
        if re.search(pattern, t):
            return phrase

    # Fallback: tenta usar o substantivo principal do título (palavra mais longa e específica)
    words = re.findall(r"\b[a-zà-ÿ]{4,}\b", t)
    candidates = [
        w for w in words
        if w not in _USE_FALLBACK_STOPWORDS
        and not w.isdigit()
        and len(w) >= 5
    ]
    if candidates:
        candidates.sort(key=len, reverse=True)
        noun = candidates[0]
        return f"quem precisa de {noun}"

    return "facilitar o seu dia a dia"


def generate_review_script(offer: dict, title: str, price: float, final_price: float, discount_pct: float) -> str:
    """Gera roteiro fixo (template padrão) — sem IA, sem alucinação, sem rate limit.

    Template: introdução, para que serve, preço/desconto, urgência, CTA.
    Preços por extenso (XTTS lê melhor).
    Abertura é aleatória (25 variações) — não repete nas últimas 5.
    """
    economy = max(0.0, price - final_price)

    price_speak = speak_brl(price)
    final_speak = speak_brl(final_price)
    economy_speak = speak_brl(economy)
    # Limpa título para narração (remove códigos, specs, cores)
    title_clean = _clean_title_for_narration(title)
    use_phrase = _product_use_phrase(title)

    opening = _get_random_opening()

    script = (
        f"{opening}, {title_clean}. "
        f"Serve para {use_phrase}. "
        f"O preço original é {price_speak}, mas com o cupom sai por {final_speak}, "
        f"você economiza {economy_speak}, é desconto real. "
        f"O cupom é por tempo determinado, aproveite enquanto não acaba. "
        f"Use o cupom abaixo na hora de pagar, o endereço está na descrição."
    )
    logger.info(f"CouponDistributor: roteiro gerado ({len(script)} chars) abertura='{opening[:30]}...'")
    return script


def num2words_pt(n: int) -> str:
    """Converte número para extenso em português (até milhões)."""
    unidades = ["zero", "um", "dois", "três", "quatro", "cinco", "seis", "sete", "oito", "nove",
                "dez", "onze", "doze", "treze", "quatorze", "quinze", "dezesseis", "dezessete", "dezoito", "dezenove"]
    dezenas = ["", "", "vinte", "trinta", "quarenta", "cinquenta", "sessenta", "setenta", "oitenta", "noventa"]
    centenas = ["", "cento", "duzentos", "trezentos", "quatrocentos", "quinhentos", "seiscentos", "setecentos", "oitocentos", "novecentos"]

    if n == 0:
        return "zero"
    if n == 100:
        return "cem"
    if n < 0:
        return f"menos {num2words_pt(-n)}"

    parts = []
    milhoes = n // 1000000
    n %= 1000000
    milhares = n // 1000
    n %= 1000
    resto = n

    def trio(v):
        """Converte um trio (0-999) para extenso."""
        if v == 0:
            return ""
        if v == 100:
            return "cem"
        parts = []
        c = v // 100
        v %= 100
        if c > 0:
            parts.append(centenas[c])
        if v >= 20:
            d = v // 10
            u = v % 10
            parts.append(dezenas[d])
            if u > 0:
                parts[-1] += f" e {unidades[u]}"
        elif v > 0:
            parts.append(unidades[v])
        return " e ".join(parts) if len(parts) > 1 else parts[0]

    if milhoes > 0:
        t = trio(milhoes) if milhoes >= 100 else (unidades[milhoes] if milhoes < 20 else num2words_pt(milhoes))
        parts.append(f"{t} {'milhão' if milhoes == 1 else 'milhões'}")
    if milhares > 0:
        if milhares == 1:
            parts.append("mil")
        else:
            t = trio(milhares) if milhares >= 100 else (unidades[milhares] if milhares < 20 else num2words_pt(milhares))
            parts.append(f"{t} mil")
    if resto > 0:
        parts.append(trio(resto))

    return " e ".join(parts)


def speak_brl(v: float) -> str:
    """Converte valor monetário para extenso em português (para TTS/YouTube).

    Trata singular/plural de "real" e "centavo", e omite a parte zerada.

    Exemplos:
        >>> speak_brl(0.01)
        'um centavo'
        >>> speak_brl(0.50)
        'cinquenta centavos'
        >>> speak_brl(1.00)
        'um real'
        >>> speak_brl(1.52)
        'um real e cinquenta e dois centavos'
        >>> speak_brl(14.90)
        'quatorze reais e noventa centavos'
        >>> speak_brl(33.24)
        'trinta e três reais e vinte e quatro centavos'
        >>> speak_brl(100.00)
        'cem reais'
        >>> speak_brl(1155.00)
        'mil e cento e cinquenta e cinco reais'
        >>> speak_brl(1097.25)
        'mil e noventa e sete reais e vinte e cinco centavos'
    """
    reais = int(v)
    centavos = int(round((v - reais) * 100))
    # Singular/plural correto: 1 real (não 1 reais), 1 centavo (não 1 centavos)
    real_word = "real" if reais == 1 else "reais"
    centavo_word = "centavo" if centavos == 1 else "centavos"
    if centavos > 0:
        if reais == 0:
            return f"{num2words_pt(centavos)} {centavo_word}"
        return f"{num2words_pt(reais)} {real_word} e {num2words_pt(centavos)} {centavo_word}"
    return f"{num2words_pt(reais)} {real_word}"


# Dicionário de marcas → como devem ser faladas (fonético para TTS)
# Apenas marcas com pronúncia especial/diferente da escrita
_BRAND_NAMES = {
    # Marcas com & ou caracteres especiais
    "m&ms": "eme eme es", "m&m's": "eme eme es", "m&m": "eme eme es",
    "black+decker": "blék dequer", "black & decker": "blék dequer",
    "coca-cola": "coca cola", "coca cola": "coca cola",
    "red bull": "red búll", "go pro": "gou pro", "gopro": "gou pro",
    "new balance": "niu balenssi", "under armour": "ander armor",
    "ferrero rocher": "ferrero rocher",
    # Marcas com pronúncia diferente da escrita
    "samsung": "sansunki", "apple": "epou", "iphone": "aifone", "ipad": "aipad",
    "philips": "filips", "philco": "filco", "brastemp": "brástemp",
    "electrolux": "eletrólux", "cadence": "cadenssi", "britania": "britânia",
    "makita": "makíta", "dewalt": "diuólt", "stihl": "chitil",
    "yamaha": "iamaá", "honda": "ronda",
    "nike": "naíki", "adidas": "adídas", "puma": "púma", "asics": "ásics",
    "xbox": "éksbox", "playstation": "pleisteichon",
    "canon": "cânon", "nikon": "naíkon", "sony": "soni",
    "bose": "bouss", "beats": "bíts", "acer": "ésser",
    "ryzen": "raízen", "dyson": "daison", "nespresso": "nespreso",
    "hamilton": "rémiton", "cuisinart": "cuízinart", "kitchenaid": "quícheneid",
    "toddy": "todi", "milka": "mílka", "haribo": "haríbo",
    "halls": "róls", "schweppes": "chvépes", "heineken": "reineken",
    "budweiser": "baduáizer", "stella": "stéla", "brahma": "bráma",
    "antarctica": "antártica", "bluetooth": "blutúfi",
    "wi-fi": "uái fi", "wifi": "uái fi",
    # Siglas técnicas com pronúncia especial
    "usb": "usbe", "hdmi": "age de emi", "led": "léd",
    "lcd": "ele ce de", "oled": "óled", "qled": "quiled",
    "ssd": "esse esse de", "hd": "age de",
    "gtx": "ge te xis", "rtx": "erre te xis",
    "core i5": "cor i cinco", "core i7": "cor i sete", "core i9": "cor i nove",
    "rgb": "erre ge be", "dvi": "de ve i", "vga": "ve ge a",
    "nfc": "ene efe ce", "gps": "ge pe esse",
    "dslr": "de esse ele erre", "hdr": "age de erre",
    "4k": "quatro kai", "8k": "oito kai", "2k": "dois kai",
    "5g": "cinco ge", "4g": "quatro ge", "3g": "três ge",
    "lte": "ele te e", "cdma": "ce de eme a",
    # ── Smartphones / Android ──
    "galaxy": "galaksi", "redmi": "rédmi", "realme": "ríolmi",
    "xiaomi": "chiaomi", "huawei": "uáuei", "oneplus": "uán plus",
    "motorola": "motorola", "nokia": "nokia", "asus": "assus",
    "tcl": "te ce ele", "zte": "ze te e", "meizu": "meizu",
    "oppo": "ópo", "vivo": "vivo", "honor": "anor",
    "poco": "póco", "infinix": "infinix", "itel": "aitel",
    # Linhas Galaxy
    "galaxy a": "galaksi a", "galaxy s": "galaksi esse",
    "galaxy m": "galaksi eme", "galaxy z": "galaksi ze",
    "galaxy note": "galaksi nóti",
    # ── Apple ──
    "macbook": "macbouque", "airpods": "er pods", "airpod": "er pod",
    "imac": "aimac", "mac mini": "mac mini", "mac": "mac",
    "watch": "uótchi", "ipod": "aipod", "homepod": "roumpod",
    "magSafe": "megue seife",
    # ── Áudio ──
    "jbl": "jótabêéli", "akg": "a ke ge", "marshall": "marchal",
    "sennheiser": "zenaizer", "beyerdynamic": "baierdinamic",
    "audio-technica": "audio tecnica", "technics": "téknics",
    "bang & olufsen": "bang olufsen", "b&o": "bang olufsen",
    "tcl": "te ce ele", "polk": "polk", "klipsch": "clipsch",
    "edifier": "edifaier", "creative": "crieitiv",
    "harman kardon": "árman kárdon", "harman": "árman",
    "kardon": "kárdon", "dolby": "dólbi", "atmos": "átmos",
    "dts": "de te esse", "thx": "te age xis",
    "tws": "te dabliu esse", "ticking": "ticking",
    "jvc": "jota ve ce", "kenwood": "kenuód",
    "pioneer": "pionír", "onkyo": "onkio", "denon": "dínon",
    "yamaha": "iamaá",
    # ── Áudio — correções adicionais ──
    "sony wh": "soni dabliu age", "wh-1000": "dabliu age mil",
    "tune": "tiun", "charge": "tchárge", "flip": "flip",
    "pulse": "polsi", "wonderboom": "uonderbum",
    "boom": "bum", "megaboom": "megabum",
    "soundlink": "sound linc", "quietcomfort": "quaiet confort",
    "qc35": "qu si trinta e cinco", "qc45": "qu si quarenta e cinco",
    "airpods pro": "er pods pro", "airpods max": "er pods max",
    "galaxy buds": "galaksi bóds", "buds": "bóds",
    "echo dot": "eco dot", "alexa": "alexa",
    "homepod": "roumpod", "home pod": "roumpod",
    "soundcore": "sound cor", "anker": "anker",
    "tribit": "tribit", "jabra": "jábra",
    "plantronics": "plántronics", "bluedio": "blúdio",
    "kz": "ke ze", "koss": "cós", "fostex": "fóstecks",
    "shure": "chur", "audio-technica": "audio tecnica",
    "westone": "uéston", "campfire": "cámpfair",
    "moondrop": "mundrop", "fiio": "fíio",
    "ibasso": "ibasso", "hidizs": "ridizs",
    "qkz": "qu ke ze", "ccz": "ce ce ze",
    "kbeast": "ke bist", "kz": "ke ze",
    "simgot": "símgot", "letshuoer": "léts chuoer",
    "tanchjim": "tanchím", "aful": "afúll",
    "7hz": "sete age ze", "kinera": "kinera",
    "dunu": "dúnu", "tip": "tip",
    "earbuds": "ir bóds", "earphone": "ir fone",
    "earphones": "ir fones", "headphone": "ed fone",
    "headphones": "ed fones", "in-ear": "in ir",
    "over-ear": "over ir", "on-ear": "on ir",
    "noise cancelling": "noiz cánceling",
    "anc": "a ene ce", "tws": "te dabliu esse",
    # ── Gaming ──
    "nintendo": "nintento", "switch": "suítchi",
    "wii": "uí", "gameboy": "geimei boi",
    "razer": "reizer", "logitech": "loguitech",
    "corsair": "corsér", "steelseries": "stil séris",
    "hyperx": "haiper xis", "roccat": "rócat",
    "turtle beach": "turtol bítchi",
    "nacon": "nácón", "thrustmaster": "thrustmaster",
    # ── Hardware/PC ──
    "intel": "intel", "core": "cor",
    "pentium": "pentium", "celeron": "celeron",
    "xeon": "xion", "arc": "arc",
    "amd": "a eme de", "radeon": "rádeon",
    "epyc": "epic", "threadripper": "threadripper",
    "nvidia": "envídia", "geforce": "guiforce",
    "quadro": "quádro", "tesla": "tesla",
    "msi": "eme esse i", "gigabyte": "gigabaite",
    "asrock": "asrock", "biostar": "baistar",
    "crucial": "crúcial", "kingston": "kingston",
    "corsair": "corsér", "g.skill": "gi skil",
    "western digital": "uésten digital", "wd": "dabliu de",
    "seagate": "seigueite", "toshiba": "toshíba",
    "nvme": "envi eme e", "sata": "sata",
    "ddr3": "de de erre três", "ddr4": "de de erre quatro",
    "ddr5": "de de erre cinco", "ddr2": "de de erre dois",
    # ── Eletrodomésticos ──
    "consul": "cónsul", "midea": "midea", "mondial": "mondial",
    "arno": "árno", "luminair": "luminair",
    "black decker": "blék dequer",
    "walmart": "uólmart",
    # ── Telecom/Redes ──
    "qualcomm": "quálcom", "snapdragon": "snapdragon",
    "mediatek": "media tek", "helio": "helio",
    "exynos": "exinos", "bionic": "bionic",
    "broadcom": "brodcom", "realtek": "realtek",
    # ── Display/Camera ──
    "amoled": "amoled", "super amoled": "super amoled",
    "retina": "retina", "oled": "óled",
    "uhd": "u age de", "fhd": "efe age de",
    "qhd": "qu age de", "wqhd": "dabliu qu age de",
    "hdr10": "age de erre dez", "dolby vision": "dólbi vision",
    "leica": "laica", "zeiss": "tsais",
    "tamron": "tâmnron", "sigma": "sigma",
    "gopro": "gou pro", "insta360": "insta trezentos e sessenta",
    "dji": "de jota i", "phantom": "phantom",
    # ── Wearables ──
    "garmin": "garmin", "fitbit": "fitbit",
    "suunto": "suunto", "polar": "polar",
    "amazfit": "amazfit", "mobvoi": "mobvoi",
    "withings": "uithings", "fossil": "fossil",
    "skagen": "skágen", "michael kors": "maicol cors",
    # ── Diversos ──
    "lego": "lego", "playmobil": "pleimobil",
    "nerf": "nerf", "hot wheels": "rot uíls",
    "barbie": "barbie", "fisher-price": "fisher price",
    "little tikes": "litol taiks",
    # ── Beleza/Perfumaria ──
    "l'oreal": "loréal", "loreal": "loréal",
    "nivea": "nivéa", "garnier": "garniér",
    "avon": "avon", "natura": "natura",
    "chanel": "chanel", "dior": "dior",
    "calvin klein": "calvin clain",
    "tommy hilfiger": "tomi hilfiger",
    "ralph lauren": "ralf loren",
    # ── Moda/Têxtil ──
    "levi's": "levais", "levis": "levais",
    "wrangler": "urángler", "lee": "li",
    "gap": "gep", "zara": "zara",
    "h&m": "age e eme", "forever 21": "forever tuenti uán",
    # ── Alimentos/Bebidas ──
    "nestle": "nestlé", "kraft": "kraft",
    "heinz": "heinz", "unilever": "unilever",
    "pepsi": "pépsi", "dr pepper": "di pepper",
    "sprite": "spraite", "fanta": "fanta",
    "guarana": "guaraná", "antarctica": "antártica",
    # ── RAM/ROM (pronúncia especial) ──
    "ram": "rã", "rom": "róm",
    "ddr": "de de erre",
    # ── Conectores ──
    "usb-c": "usbe ce", "type-c": "taipi ce", "usb type-c": "usbe taipi ce",
    "thunderbolt": "thunderbolt", "lightning": "laitning",
    "pd": "pe de", "qc": "qu ce",
    "quick charge": "quick charge", "fast charge": "fast charge",
    # ── Certificações ──
    "ip67": "i pe sessenta e sete", "ip68": "i pe sessenta e oito",
    "ipx7": "i pe xis sete", "ipx8": "i pe xis oito",
    "ip44": "i pe quarenta e quatro",
    # ── Realidade virtual ──
    "vr": "ve erre", "ar": "a erre",
    "oculus": "óculus", "quest": "quest",
    "hololens": "ololens",
    # ── Diversos tech ──
    "ai": "a i", "iot": "i o te",
    "qi": "tchi", "pogopin": "pogopin",
    "nfc": "ene efe ce",
    " esim": "e sim", "esim": "e sim",
    # ── Marcas BR ──
    "positivo": "positivo", "cce": "ce ce e",
    "megaware": "megauare", "neologic": "neologic",
    "winca": "uínca", "h-buster": "age buster",
    "multilaser": "multilaser", "dl": "de ele",
    "lenovo": "lenovo", "hp": "age pe",
    "dell": "dél", "alienware": "alienuear",
    "trendnet": "trendnet", "tp-link": "te pi link",
    "netgear": "netguir", "d-link": "de link",
    # ── E-commerce/Lojas ──
    "mercadolivre": "mercado livre", "mercadolivre.com": "mercado livre",
    "shopee": "chopi", "aliexpress": "aliexpress",
    "amazon": "amazon", "magalu": "magalu",
    "magazine luiza": "magazine luiza",
    # ── Automotivo ──
    "pioneer": "pionír", "pioneer": "pionír",
    "volvo": "volvo", "honda": "ronda",
    "toyota": "toióta", "nissan": "nissan",
    "hyundai": "iúndai", "kia": "kia",
    "volkswagen": "volkswagen", "vw": "ve dabliu",
    "audi": "audi", "bmw": "be eme dabliu",
    "mercedes": "mercedes", "mercedes-benz": "mercedes benz",
    "ferrari": "ferrari", "lamborghini": "lamborguini",
    "porsche": "porche", "mclaren": "mac laren",
    "bugatti": "bugatti", "maserati": "maserati",
    "bentley": "bentley", "rolls-royce": "rols roice",
    # ── Tipos de produto (XTTS lê errado em PT-BR) ──
    "smartwatch": "smartuótchi", "smartwatch": "smartuótchi",
    "powerbank": "pouer banque", "power bank": "pouer banque",
    "powerbank": "pouer banque",
    "webcam": "uebecam", "earbuds": "ir bóds",
    "notebook": "notebuque", "mousepad": "mause pad",
    "smartphone": "smartufone", "smartband": "smart band",
    "smarttv": "smart te ve", "smart tv": "smart te ve",
    "streamdeck": "strim dec", "joystick": "joístique",
    "gamepad": "geime pad", "headset": "edseti",
    "headphone": "ed fone", "earphone": "ir fone",
    "keyboard": "quibórd", "speaker": "espíquer",
    "laptop": "laptop", "display": "displêi",
    "charger": "tchárger", "cable": "keibou",
    "microphone": "maicrofone", "microfone": "maicrofone",
    "webcam hd": "uebecam age de",
    # ── Gaming marcas ──
    "redragon": "redragon", "cougar": "cúgar",
    "genesis": "guênesis", "deathadder": "deft ader",
    "arctis": "ártics", "cloud": "cláud",
    # ── Smartphones linhas ──
    "moto g": "moto ge", "moto edge": "moto edge",
    "pixel": "pixou", "nord": "nórd",
    "magic": "magic",
    # ── Eletro domésticos ──
    "lg": "ele ge", "panasonic": "panasonic",
    "bosch": "bósh", "siemens": "símens",
    "miele": "míle", "smeg": "smég",
    # ── Automotivo áudio ──
    "alpine": "álpain", "blaupunkt": "bláupunt",
    "clarion": "clárian",
    # ── Beleza/perfumaria ──
    "victoria's secret": "victória secret",
    "maybelline": "meibelin", "boticário": "boticário",
    "eudora": "eudora", "jequiti": "jequiti",
    # ── Calçados ──
    "reebok": "ríboc", "vans": "vans",
    "converse": "converse", "all star": "ol star",
    "olympikus": "olimpikus", "mizuno": "mizuno",
    "fila": "fila", "skechers": "skéchers",
    "crocs": "crócs", "havaianas": "avaiânas",
    "rider": "raider", "melissa": "melissa",
    # ── Moda/luxo ──
    "gucci": "gúci", "louis vuitton": "luí vuitôn",
    "prada": "prada", "burberry": "búrberri",
    "coach": "couch", "kate spade": "keit speid",
    "tory burch": "tori burch", "lacoste": "lacóst",
    "hugo boss": "iugo boss", "versace": "versáchi",
    "armani": "armáni", "diesel": "dizel",
    "oakley": "óukli", "ray-ban": "rei ban",
    # ── Alimentos ──
    "lacta": "lacta", "garoto": "garoto",
    "danone": "danone", "yoplait": "ioplê",
    "activia": "activia", "nestea": "nestea",
    "tang": "tang", "mucilon": "mucilon",
    "nescau": "nescau", "nesquik": "nesquic",
    # ── Tech geral ──
    "google": "gugle", "microsoft": "maicrossóft",
    "windows": "uindous", "android": "andróid",
    "chromebook": "croumboque", "firefox": "fáierfócs",
    "tiktok": "tictoc", "instagram": "instagran",
    "whatsapp": "uátsap", "telegram": "telegram",
    "spotify": "spotifaí", "netflix": "netflix",
    "youtube": "ioutube", "twitch": "tuítchi",
    "discord": "discórd", "reddit": "réddit",
}

# Siglas de 2-5 letras maiúsculas que devem ser soletradas automaticamente
# (não estão no _BRAND_NAMES, não são palavras comuns)
_AUTO_SPELL_EXCEPTIONS = {
    # Palavras que parecem siglas mas são palavras normais — NÃO soletrar
    "DE", "DA", "DO", "DAS", "DOS", "AO", "AOS", "EM", "NO", "NA", "NOS", "NAS",
    "POR", "PARA", "COM", "SEM", "SOB", "SOBRE", "ANTE", "ENTRE", "APOS",
    "E", "OU", "MAS", "SE", "QUE", "COMO", "ONDE", "QUANDO",
    "HD", "TV", "PC", "DVD", "CD", "MP3", "OK",
}

# Nomes das letras em português (para soletrar siglas)
_LETTER_NAMES = {
    'A': 'a', 'B': 'be', 'C': 'ce', 'D': 'de', 'E': 'e', 'F': 'efe',
    'G': 'ge', 'H': 'age', 'I': 'i', 'J': 'jota', 'K': 'ka', 'L': 'ele',
    'M': 'eme', 'N': 'ene', 'O': 'o', 'P': 'pe', 'Q': 'quê', 'R': 'erre',
    'S': 'esse', 'T': 'te', 'U': 'u', 'V': 've', 'W': 'dabliu', 'X': 'xis',
    'Y': 'ipsilon', 'Z': 'ze',
}


# Dicionário de abreviações de unidades → extenso (para TTS falar corretamente)
# SÓ serão expandidas quando vierem coladas após um número (ex: 132g, 500ml)
_UNIT_ABBREVS = {
    # Peso
    "g": "gramas", "gr": "gramas", "gramas": "gramas",
    "kg": "quilos", "kgs": "quilos", "quilos": "quilos",
    "mg": "miligramas", "mcg": "microgramas",
    "ton": "toneladas", "t": "toneladas",
    "lb": "libras", "oz": "onças", "cts": "quilates",
    # Volume
    "ml": "mililitros", "l": "litros", "lt": "litros", "lts": "litros",
    "litro": "litro", "litros": "litros",
    "gal": "galões", "cc": "centímetros cúbicos",
    # Comprimento
    "mm": "milímetros", "cm": "centímetros", "m": "metros",
    "km": "quilômetros", "ft": "pés", "in": "polegadas",
    "yd": "jardas", "micron": "micrômetros",
    # Área
    "m2": "metros quadrados", "cm2": "centímetros quadrados",
    "ha": "hectares", "km2": "quilômetros quadrados",
    # Energia/Elétrica
    "w": "watts", "watts": "watts", "kw": "quilowatts", "mw": "megawatts",
    "v": "volts", "volts": "volts", "kv": "quilovolts", "mv": "milivolts",
    "mah": "miliamperes hora", "ah": "amperes hora", "a": "amperes",
    "kwh": "quilowatts hora", "wh": "watts hora",
    "va": "volts amperes", "kva": "quilovolts amperes",
    # Tempo
    "h": "horas", "hrs": "horas", "hr": "horas",
    "min": "minutos", "seg": "segundos", "s": "segundos",
    "ms": "milissegundos",
    # Tela/Resolução
    "polegadas": "polegadas", "pol": "polegadas",
    "px": "pixels", "mp": "megapixels", "dpi": "dpi",
    "fps": "frames por segundo", "hz": "hertz",
    # Dados
    "gb": "gigabytes", "mb": "megabytes", "tb": "terabytes",
    "kb": "quilobytes", "pb": "petabytes",
    "ghz": "giga-hertz", "mhz": "mega-hertz", "khz": "quilo-hertz",
    "ram": "ram", "rom": "rom", "ddr": "de de erre",
    "mhz": "mega-hertz",
    # Temperatura
    "c": "graus celsius", "f": "graus fahrenheit", "k": "kelvin",
    # Pressão
    "psi": "libras por polegada quadrada", "bar": "bar", "pa": "pascals",
    "atm": "atmosferas",
    # Outros
    "rpm": "rotações por minuto",
    "db": "decibéis", "lm": "lúmens", "lux": "lux",
    "cv": "cavalos", "hp": "cavalos",
    "btu": "btus", "btus": "btus", "btuh": "btus por hora",
    "pct": "por cento",
    "un": "unidade", "unid": "unidades",
    "pç": "peça", "pças": "peças", "pecas": "peças",
    "cx": "caixa", "cxs": "caixas", "cx12": "caixa com doze",
    "kit": "kit", "par": "par", "pares": "pares",
    "cal": "calorias", "kcal": "quilocalorias", "kj": "quilojoules",
    "nm": "nanômetros", "ppm": "partes por milhão",
    "lumen": "lúmens", "lumens": "lúmens",
    "mca": "metros de coluna d'água",
    # Embalagens
    "pack": "pacote", "pack6": "pacote com seis",
    "refil": "refil", "ref": "refil",
    "cp": "copos", "sachê": "sachê", "saches": "sachês",
    "dose": "doses", "doses": "doses",
    "caps": "cápsulas", "cap": "cápsula",
    "comp": "comprimidos", "comps": "comprimidos",
    "mls": "mililitros",
}


def _spell_acronym(word: str) -> str:
    """Soletra uma sigla letra por letra em português."""
    return " ".join(_LETTER_NAMES.get(c.upper(), c) for c in word)


# ─── Limpeza de título para narração ──────────────────────────────────────────

# Palavras que NÃO são spec e devem ser mantidas mesmo se pareçam códigos
_NARRATION_KEEP_WORDS = {
    # Palavras de linha de modelo (ficam depois da marca)
    'ultra', 'pro', 'max', 'mini', 'plus', 'lite', 'air', 'note', 'edge',
    'flip', 'fold', 'tab', 'book', 'watch', 'buds', 'fe', 'se', 'neo',
    'sport', 'active', 'classic', 'essential', 'go',
    # Tipos de produto (PT-BR)
    'gamer', 'headset', 'fone', 'mouse', 'teclado', 'monitor', 'notebook',
    'smartphone', 'celular', 'tablet', 'camera', 'caneca', 'garrafa',
    'relogio', 'smartwatch', 'caixa', 'som', 'microfone', 'cadeira',
    'mesa', 'luminaria', 'lampada', 'carregador', 'cabo', 'fones',
    'caixas', 'relogios', 'pelicula', 'capa', 'suporte', 'base',
    'peliculas', 'capas', 'suportes', 'bases', 'controle', 'controles',
    # Tipos de produto (EN)
    'earbuds', 'speaker', 'keyboard', 'laptop', 'phone', 'headphone',
    'earphone', 'webcam', 'microphone', 'chair', 'desk', 'lamp',
    'charger', 'cable', 'dock', 'hub', 'stand', 'case', 'cover',
    'screen', 'display', 'screen', 'protector', 'film', 'glass',
    # Palavras de automotivo
    'car', 'rear', 'view', 'front', 'dash', 'backup', 'camera',
    # Conectores
    'com', 'sem', 'para', 'pra', 'pro', 'com', 'e',
}

# Specs que devem ser removidas do final do título
_NARRATION_SPEC_EXACT = {
    # Cores
    'preto', 'branco', 'azul', 'vermelho', 'verde', 'rosa', 'roxo', 'cinza',
    'grafite', 'prata', 'dourado', 'amarelo', 'laranja', 'marrom', 'bege',
    'violeta', 'turquesa', 'midnight', 'starlight', 'titanium',
    'black', 'white', 'blue', 'red', 'green', 'pink', 'purple', 'gray',
    'grey', 'silver', 'gold', 'yellow', 'orange', 'brown', 'beige',
    'dark', 'light', 'coral', 'indigo',
    # Condição/origem
    'original', 'novo', 'nova', 'usado', 'lacrado', 'recondicionado',
    'factory', 'unlocked', 'nacional', 'importado', 'oficial',
    # Tamanhos
    'm', 'l', 's', 'xl', 'xxl', 'unico', 'único', 'tamanho',
    # Conectividade
    '5g', '4g', '3g', 'lte', 'wifi', 'wi-fi', 'dual', 'sim', 'dual-sim',
    'esim', 'nano-sim', 'gsm',
    # Specs técnicas (quando isoladas no final)
    'rgb', 'hdr', 'oled', 'lcd', 'led', 'qled', 'amoled',
    # Selos/categorias
    'premium', 'special', 'edition', 'limited',
}

# Padrões regex de spec (número + unidade)
_NARRATION_SPEC_PATTERNS = [
    re.compile(r'\d+\s*gb\b', re.IGNORECASE),
    re.compile(r'\d+\s*tb\b', re.IGNORECASE),
    re.compile(r'\d+\s*mp\b', re.IGNORECASE),
    re.compile(r'\d+\s*mah\b', re.IGNORECASE),
    re.compile(r'\d+["p]\b'),  # 6.5" / 6p
    re.compile(r'\d+\s*polegadas?\b', re.IGNORECASE),
    re.compile(r'\d+\s*ghz\b', re.IGNORECASE),
    re.compile(r'\d+\s*mhz\b', re.IGNORECASE),
    re.compile(r'\d+\s*ram\b', re.IGNORECASE),
    re.compile(r'\d+\s*w\b', re.IGNORECASE),
    re.compile(r'\d+\s*v\b', re.IGNORECASE),
    re.compile(r'\d+\s*db\b', re.IGNORECASE),
]


def _clean_title_for_narration(title: str) -> str:
    """Limpa título para narração: remove códigos, specs, cores, armazenamento.

    Exemplos:
      '31445951 Car Rear View Camera For Volvo S90 V90 2017...' → 'Car Rear View Camera'
      'Headset Gamer Neologic Ngx Dark, RGB, Preto, NGXDA' → 'Headset Gamer Neologic'
      'Samsung Galaxy S22 Ultra 5g Preto 256gb Original M' → 'Samsung Galaxy S22 Ultra'
    """
    t = title.strip()

    # 1. Remove códigos numéricos leading (31445951, 12345678)
    t = re.sub(r'^\d{4,}\s+', '', t)

    # 2. Corta em " For " (compatibilidade — tudo depois é spec de carro/modelo)
    t = re.split(r'\s+for\s+', t, flags=re.IGNORECASE)[0]

    # 3. Corta em " Para " (compatibilidade em PT)
    t = re.split(r'\s+para\s+', t, flags=re.IGNORECASE)[0]

    # 4. Corta na primeira vírgula (specs separadas por vírgula)
    t = t.split(',')[0]

    # 5. Corta em " - " (separador de spec com hífen)
    t = t.split(' - ')[0].split(' – ')[0]

    tokens = t.split()

    # 6. Remove tokens de spec do final (cores, armazenamento, condição, etc)
    def _is_spec(tok):
        low = tok.lower().strip('.,;:!')
        if low in _NARRATION_SPEC_EXACT:
            return True
        for pat in _NARRATION_SPEC_PATTERNS:
            if pat.fullmatch(low):
                return True
        return False

    while tokens and _is_spec(tokens[-1]):
        tokens.pop()

    # 7. Remove trailing model codes (tokens curtos não-dicionário após a marca)
    # Ex: "Neologic Ngx" → strip "Ngs" (não é palavra comum)
    # Para: "Galaxy S22 Ultra" → "Ultra" está no keep-words → mantém
    while len(tokens) > 3:
        last = tokens[-1]
        low = last.lower().strip('.,;:!')
        if low in _NARRATION_KEEP_WORDS:
            break
        # Model code: ≤6 chars, mixed case ou all caps, não é palavra comum
        if len(last) <= 6 and last != last.lower() and not low.isdigit():
            tokens.pop()
        else:
            break

    # 8. Limita a 5 tokens no máximo (evita nomes muito longos)
    if len(tokens) > 5:
        tokens = tokens[:5]

    return ' '.join(tokens).strip()


def expand_units_for_tts(text: str) -> str:
    """Expande abreviações de unidades, marcas, siglas e números para extenso (XTTS lê melhor).

    Ordem:
    1. Marcas conhecidas (M&Ms → eme eme es, LG → ele ge, etc) — com word boundary
    2. Siglas maiúsculas 2-5 letras (+ número opcional) → soletrar automaticamente
    3. Unidades coladas em números (132g → 132 gramas, 500ml → 500 mililitros)
    4. Números isolados → extenso (50 → cinquenta, evita pausa do XTTS)
    5. Símbolos especiais (% → por cento, & → e, / → espaço)
    6. Limpeza final
    """

    # 1. Expande marcas conhecidas PRIMEIRO (com word boundary pra não pegar dentro de palavras)
    for brand, spoken in sorted(_BRAND_NAMES.items(), key=lambda x: len(x[0]), reverse=True):
        pattern = r'\b' + re.escape(brand) + r'\b'
        text = re.sub(pattern, spoken, text, flags=re.IGNORECASE)

    # 1b. Model codes: 1 letra maiúscula + número (A12, S22, V90, M11, P40)
    # XTTS lê "A12" como "a doze" errado; forçamos "a doze", "esse vinte e dois", etc
    def _model_code_to_spoken(m):
        letter = m.group(1).upper()
        num = int(m.group(2))
        letter_spoken = _LETTER_NAMES.get(letter, letter)
        num_spoken = num2words_pt(num)
        return f"{letter_spoken} {num_spoken}"

    text = re.sub(r'\b([A-Z])(\d{1,2})\b', _model_code_to_spoken, text)

    # 2. Soletra siglas maiúsculas 2-5 letras, opcionalmente seguidas de número (ABNT2, DDR4)
    def spell_if_acronym(m):
        word = m.group(1)
        suffix = m.group(2) or ""
        if word.upper() in _AUTO_SPELL_EXCEPTIONS:
            return word + suffix
        if len(word) < 2 or len(word) > 5:
            return word + suffix
        spelled = _spell_acronym(word)
        return f"{spelled} {suffix}" if suffix else spelled

    text = re.sub(r'\b([A-Z]{2,5})(\d+)?\b', spell_if_acronym, text)

    # 3. Expande unidades coladas após números (ex: 132g, 500ml, 10W, 220V, 3.4GHz)
    unit_pattern = '|'.join(re.escape(k) for k in sorted(_UNIT_ABBREVS.keys(), key=len, reverse=True))
    pattern = re.compile(r'(\d+(?:[.,]\d+)?)\s*(' + unit_pattern + r')\b', re.IGNORECASE)

    def replace_unit(m):
        num_str = m.group(1)
        unit = m.group(2).lower()
        expanded = _UNIT_ABBREVS.get(unit, unit)
        # Normaliza vírgula para ponto
        num_normalized = num_str.replace(",", ".")
        try:
            num_val = float(num_normalized)
        except Exception:
            return f"{num_str} {expanded}"

        # Caso especial: X.5 → "X e meio"
        if num_val == int(num_val) + 0.5:
            int_part = int(num_val)
            # Singular/plural: "um litro e meio", "dois litros e meio"
            if expanded.endswith("s"):
                singular = expanded[:-1]
            else:
                singular = expanded
            if int_part == 0:
                return f"meio {singular}"
            if int_part == 1:
                return f"um {singular} e meio"
            int_ext = num2words_pt(int_part)
            return f"{int_ext} {expanded} e meio"

        # Inteiro → extenso
        if num_val == int(num_val):
            num_ext = num2words_pt(int(num_val))
            return f"{num_ext} {expanded}"

        # Decimal genérico → parte inteira + "vírgula" + decimal como número
        int_part = int(num_val)
        decimal_part = num_normalized.split(".")[1]
        # Remove zeros à esquerda desnecessários e converte o decimal como número inteiro
        decimal_num = int(decimal_part)
        decimal_ext = num2words_pt(decimal_num)
        int_ext = num2words_pt(int_part)
        return f"{int_ext} vírgula {decimal_ext} {expanded}"

    text = pattern.sub(replace_unit, text)

    # 4. Converte números isolados (inteiros, sem decimal) para extenso
    # Evita pausa do XTTS ao ler números. NÃO converte decimais (1.5, 3.4)
    def num_to_ext(m):
        n = m.group(0)
        try:
            return num2words_pt(int(n))
        except Exception:
            return n

    # Só converte números inteiros isolados (não decimais, não seguidos de unidade)
    text = re.sub(r'\b(?<![\d.,])(\d{1,4})(?![\d.,])\b', num_to_ext, text)

    # 5. Símbolos especiais
    text = text.replace("%", " por cento")
    text = text.replace("&", " e ")
    text = text.replace("/", " ")
    text = text.replace("+", " mais ")
    text = re.sub(r'(\d+)\s*x\b', r'\1 por', text, flags=re.IGNORECASE)
    text = re.sub(r'\s+', ' ', text).strip()

    return text


async def generate_coupon_video(offer: dict, output_path: str) -> Optional[str]:
    """Gera vídeo do cupom: imagem HD do produto + texto + narração XTTS (voz ElevenLabs).

    Estrutura: imagem em alta resolução + overlay de texto (preço/cupom/desconto)
    + narração em português com voz clonada. Tudo via ffmpeg, roda no servidor.
    """
    tmpdir = tempfile.mkdtemp()

    try:
        title = offer["title"][:60]
        price = offer["price"]
        coupon_code = offer["coupon_code"]
        store = offer.get("store_name", "")
        final_price, economy, discount_pct = _coupon_discount_info(offer)

        # 1. Baixa imagem em alta resolução (troca _Q por _NQ para versão maior)
        img_path = os.path.join(tmpdir, "product.jpg")
        img_url = offer.get("image_url", "")
        if img_url and img_url.startswith("http"):
            # ML: D_Q_NP = thumbnail, D_NQ_NP = maior qualidade
            hd_url = img_url.replace("D_Q_NP", "D_NQ_NP").replace("_Q_", "_NQ_")
            for url in [hd_url, img_url]:
                try:
                    async with httpx.AsyncClient(timeout=10) as c:
                        r = await c.get(url, headers={"User-Agent": "Mozilla/5.0"}, follow_redirects=True)
                        if r.status_code == 200 and len(r.content) > 2000:
                            with open(img_path, "wb") as f:
                                f.write(r.content)
                            break
                except Exception:
                    continue

        # 2. Gera roteiro (template fixo — sem IA, sem alucinação)
        narration = generate_review_script(offer, title, price, final_price, discount_pct)
        # Expande marcas e unidades para TTS (M&Ms→eme eme es, 132g→132 gramas, etc)
        narration = expand_units_for_tts(narration)
        # Limpa símbolos que o XTTS lê errado
        narration = narration.replace("R$", "").replace("r$", "").replace("  ", " ").strip()

        audio_path = os.path.join(tmpdir, "narration.wav")
        logger.info("CouponDistributor: gerando narração XTTS (voz ElevenLabs)...")
        if not await generate_xtts_narration_async(narration, audio_path):
            logger.error("CouponDistributor: XTTS falhou, pulando vídeo")
            return None

        # 3. Duração do áudio
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

        # 4. Texto para overlay (escapado para ffmpeg)
        def esc(t):
            return t.replace("'", "\\'").replace(":", "\\:").replace(",", "\\,")

        # Quebra título em linhas dinamicamente (max ~30 chars cada)
        title_full = offer["title"][:90]
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
        title_lines = title_lines[:4]

        # Escreve título num arquivo .txt (ffmpeg textfile permite \n real)
        title_file = os.path.join(tmpdir, "title.txt")
        with open(title_file, "w") as f:
            f.write("\n".join(title_lines))

        price_text = esc(fmt_brl(price))
        final_text = esc(fmt_brl(final_price))
        coupon_text = esc(f"CUPOM: {coupon_code}")
        discount_text = esc(f"-{discount_pct:.0f}% OFF") if discount_pct > 0 else ""

        # 5. Monta vídeo com ffmpeg
        if os.path.exists(img_path):
            # Imagem HD + overlay de texto + áudio
            vf_parts = [
                "scale=1080:1920:force_original_aspect_ratio=decrease",
                "pad=1080:1920:(ow-iw)/2:(oh-ih)/2:color=0x0a0a0a",
                "format=yuv420p",
                # Título via textfile (permite quebra de linha real com \n)
                f"drawtext=textfile={title_file}:fontcolor=white:fontsize=32:"
                f"x=(w-text_w)/2:y=60:line_spacing=8:box=1:boxcolor=0x000000@0.7:boxborderw=12",
                # Preço original (riscado visualmente com cor cinza)
                f"drawtext=text='DE {price_text}':fontcolor=0x999999:fontsize=38:"
                f"x=(w-text_w)/2:y=1480:box=1:boxcolor=0x000000@0.6:boxborderw=8",
            ]
            if discount_pct > 0:
                vf_parts.append(
                    f"drawtext=text='POR {final_text}':fontcolor=0x00ff88:fontsize=52:"
                    f"x=(w-text_w)/2:y=1550:box=1:boxcolor=0x000000@0.8:boxborderw=14"
                )
                vf_parts.append(
                    f"drawtext=text='{discount_text}':fontcolor=0xff4444:fontsize=42:"
                    f"x=(w-text_w)/2:y=1640:box=1:boxcolor=0x000000@0.6:boxborderw=10"
                )
            vf_parts.append(
                f"drawtext=text='{coupon_text}':fontcolor=0xffcc00:fontsize=44:"
                f"x=(w-text_w)/2:y=1730:box=1:boxcolor=0x000000@0.85:boxborderw=18"
            )
            vf_parts.append(
                "drawtext=text='BestPriceToday':fontcolor=0x888888:fontsize=22:"
                "x=(w-text_w)/2:y=1860"
            )

            cmd = [
                "ffmpeg", "-y",
                "-loop", "1", "-i", img_path,
                "-i", audio_path,
                "-c:v", "libx264", "-tune", "stillimage",
                "-vf", ",".join(vf_parts),
                "-c:a", "aac", "-b:a", "128k",
                "-t", str(duration),
                "-pix_fmt", "yuv420p",
                "-r", "30",
                "-crf", "20",
                output_path
            ]
        else:
            # Sem imagem: fundo + texto
            noimg_vf = [
                f"drawtext=textfile={title_file}:fontcolor=white:fontsize=42:"
                f"x=(w-text_w)/2:y=800:line_spacing=10:box=1:boxcolor=0x000000@0.5:boxborderw=20",
                f"drawtext=text='DE {price_text}':fontcolor=0x999999:fontsize=48:"
                f"x=(w-text_w)/2:y=1000",
                f"drawtext=text='POR {final_text}':fontcolor=0x00ff88:fontsize=56:"
                f"x=(w-text_w)/2:y=1080",
                f"drawtext=text='{coupon_text}':fontcolor=0xffcc00:fontsize=52:"
                f"x=(w-text_w)/2:y=1200:box=1:boxcolor=0x000000@0.7:boxborderw=15",
            ]
            cmd = [
                "ffmpeg", "-y",
                "-f", "lavfi", "-i", f"color=c=0x0a0a1a:s=1080x1920:d={duration}",
                "-i", audio_path,
                "-vf", ",".join(noimg_vf),
                "-c:v", "libx264", "-c:a", "aac", "-b:a", "128k",
                "-t", str(duration),
                "-pix_fmt", "yuv420p", "-r", "30", "-crf", "20",
                output_path
            ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if os.path.exists(output_path) and os.path.getsize(output_path) > 5000:
            logger.info(f"CouponDistributor: vídeo gerado ({os.path.getsize(output_path)} bytes)")
            return output_path
        logger.error(f"CouponDistributor: ffmpeg failed: {result.stderr[-400:]}")
        return None

    except Exception as e:
        logger.error(f"CouponDistributor: video gen error: {e}")
        return None
    finally:
        if tmpdir:
            shutil.rmtree(tmpdir, ignore_errors=True)


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
            video_path = await generate_coupon_video(offer, tmp_video)
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
    now = datetime.now(timezone.utc)
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

        # Cria short link para o product_url (rastreia clique + passa pelo site)
        product_url = offer.get("product_url", "")
        short_url = None
        if product_url:
            short_link_offer = {
                "affiliate_url": product_url,
                "provider": "mercadolivre",
                "title": offer.get("title", ""),
                "final_price": offer.get("price", 0),
                "image_url": offer.get("image_url", ""),
            }
            short_url = await _create_short_link(short_link_offer, source="coupon", campaign=offer.get("coupon_code"))
        offer["short_url"] = short_url or product_url  # fallback: product_url direto

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
