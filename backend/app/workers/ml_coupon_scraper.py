"""
ml_coupon_scraper.py — Scraper de cupons do Mercado Livre (modelo consumidor).

Fonte: https://www.mercadolivre.com.br/cupons (página de cupons do usuário logado).

O modelo antigo de afiliados (gerar código ALETUBE*) foi descontinuado pelo ML
em set/2026 — /afiliados/coupons redireciona pro hub. O novo modelo expõe
~2200 cupons reais em /cupons/filter?all=true&page=N (30/página), com todos os
dados estruturados no JSON de hydration <script id="__NORDIC_RENDERING_CTX__">
(_n.ctx.r={...}) — scrape é HTTP puro com os cookies da sessão, SEM browser.

Dados por cupom (filteredCouponsData.coupons + tracking...coupons_list):
- campaignId → coupon_code sintético "MLC-{id}" (não há código digitável)
- title.text → "10% OFF" / discount_type + discount_value (PERCENT/NOMINAL)
- initialSubtitle.text → loja ("Em produtos de X")
- amount.minAmount/capAmount → condições (compra mínima / limite)
- tracking.expiration_date → expires_at (ISO real)
- status.id → ACTIVE (já ativado na nossa conta — tem link) / INACTIVE
- action.value (ACTIVE) → lista.mercadolivre.com.br/_CustId_{collector}?coupon_campaign_id={id}
- tracking.item_ids + items[] → produtos amostra (CouponProduct)

Para INACTIVE o link é reconstruído: _CustId_{collectors[0]}?coupon_campaign_id=.
CTA do site: "Ver produtos" (o "Aplicar" ativa na conta de quem clica — nunca
é acionado pelo scraper).

Uso:
  cd backend && venv/bin/python -m app.workers.ml_coupon_scraper
  cd backend && venv/bin/python -m app.workers.ml_coupon_scraper --max-pages 5
  cd backend && venv/bin/python -m app.workers.ml_coupon_scraper --cleanup-only
"""
import asyncio
import fcntl
import json
import logging
import os
import random
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Optional, Tuple

import httpx

logger = logging.getLogger("ml_coupon_scraper")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR.parent.parent
ENV_FILE = BACKEND_DIR / ".env"
COOKIES_FILE = BACKEND_DIR / ".ml_cookies.json"
LOCK_FILE = BACKEND_DIR / ".ml_coupon_scraper.lock"

# Flag de sessão expirada compartilhado com ml_session_keeper (dedup de ruído)
EXPIRED_FILE = BACKEND_DIR / ".ml_session_expired"
EXPIRED_RECENT_HOURS = 12

COUPONS_FILTER_URL = "https://www.mercadolivre.com.br/cupons/filter?all=true"
COUPONS_HOME_URL = "https://www.mercadolivre.com.br/cupons"
PAGE_SIZE = 30  # cupons por página na listagem "Todos os cupons"
PAGE_DELAY_RANGE = (2.0, 4.0)  # segundos entre páginas — polidez, evita captcha
MAX_PAGES_HARD_LIMIT = 120  # segurança: nunca passa de N páginas por rodada

# Pool de UAs (mesmo estilo do ml_session_keeper — UA fixo era detectável)
USER_AGENTS = [
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.7922.108 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.7078.130 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.7922.75 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.7078.177 Safari/537.36",
]

# Categorias de demanda — só salva cupons cujos produtos match essas keywords
# (evita lixo como "Bolsa Airbag Ford Ranger 2015", "Capa Máquina de Lavar")
DEMAND_KEYWORDS = {
    # Smartphones / celulares
    "celular", "smartphone", "iphone", "samsung galaxy", "xiaomi", "redmi", "motorola",
    "poco", "realme", "phone", "telefon",
    # Áudio
    "fone", "headset", "earbuds", "airpods", "caixa de som", "bluetooth", "tws",
    "jbl", "soundcore", "speaker",
    # Wearables
    "smartwatch", "smart watch", "relógio inteligente", "xiaomi band", "mi band",
    "amazfit", "garmin", "apple watch", "fitbit",
    # Casa / cozinha (demanda alta)
    "airfryer", "air fryer", "fritadeira", "aspirador", "cafeteira", "liquidificador",
    "panela eletrica", "ventilador", "ar condicionado",
    # Games
    "playstation", "nintendo", "xbox", "controle", "ps5", "ps4", "switch",
    # Informática
    "notebook", "laptop", "monitor", "teclado", "mouse", "webcam", "ssd", "pendrive",
    "tablet", "kindle",
    # Câmeras
    "camera", "câmera", "gopro", "drone",
    # TV
    "smart tv", "tv 4k", "tv led",
}

# Keywords de produtos que NÃO devem ser salvos (acessórios/genéricos)
EXCLUDE_KEYWORDS = {
    "capa", "case", "cover", "filme", "protetor", "pelicula", "película",
    "carregador", "cabo", "fonte", "adaptador", "suporte", "base",
    "pneu", "aro", "roda", "para-choque", "parachoque", "retrovisor",
    "bolsa airbag", "tapete", "capa máquina", "capo", "capó",
}


def _is_demand_coupon(coupon: dict) -> bool:
    """False só se o cupom é claramente lixo (todas as amostras são acessórios).

    Modelo novo (set/2026): items[] são só ~4 produtos amostra por cupom —
    cupom amplo ("Em produtos selecionados") era rejeitado por amostra
    aleatória quando se exigia match de DEMAND_KEYWORDS (rejeitava ~78% de
    um inventário já curado pelo ML). Mantido como filtro de exclusão:
    rejeita quando TODOS os produtos amostra batem em EXCLUDE_KEYWORDS.
    """
    store = (coupon.get("store_name") or "").lower()
    products = coupon.get("products", [])
    if not products:
        return True
    if any(kw in store for kw in DEMAND_KEYWORDS):
        return True
    if all(any(ex in (p.get("title") or "").lower() for ex in EXCLUDE_KEYWORDS)
           for p in products):
        return False
    return True


def _check_cookies_valid() -> bool:
    """Verifica se existem cookies e se parecem ser de sessão do ML."""
    if not COOKIES_FILE.exists():
        logger.error("Arquivo de cookies .ml_cookies.json não encontrado")
        return False
    try:
        cookies = json.loads(COOKIES_FILE.read_text())
        if not cookies:
            logger.error("Arquivo de cookies vazio")
            return False
        session_names = {"org_id", "site_id", "_csrf", "sid", "ui", "mp-session"}
        ml_names = {c.get("name", "") for c in cookies}
        if not session_names.intersection(ml_names):
            logger.error("Cookies não parecem ser de sessão do Mercado Livre")
            return False
        logger.info(f"Cookies presentes: {len(cookies)} cookies")
        return True
    except Exception as e:
        logger.error(f"Erro ao ler cookies: {e}")
        return False


def _load_cookie_dict() -> dict:
    """Carrega cookies do arquivo JSON em formato {name: value}."""
    try:
        cookies = json.loads(COOKIES_FILE.read_text())
        return {c["name"]: c["value"] for c in cookies if "name" in c and "value" in c}
    except Exception:
        return {}


class LockFile:
    """Lock simples baseado em arquivo para evitar execuções simultâneas."""

    def __init__(self, path: Path):
        self.path = path
        self.fd = None

    def acquire(self) -> bool:
        try:
            self.fd = open(self.path, "w")
            fcntl.flock(self.fd.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            self.fd.write(str(os.getpid()))
            self.fd.flush()
            return True
        except (IOError, OSError):
            if self.fd:
                self.fd.close()
                self.fd = None
            return False

    def release(self):
        if self.fd:
            try:
                fcntl.flock(self.fd.fileno(), fcntl.LOCK_UN)
            except Exception:
                pass
            try:
                self.fd.close()
            except Exception:
                pass
            try:
                self.path.unlink(missing_ok=True)
            except Exception:
                pass
            self.fd = None


# ── env ────────────────────────────────────────────────────────────────────────
def load_env() -> dict:
    env = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip().strip('"').strip("'")
    return env


# ── DB ──────────────────────────────────────────────────────────────────────────
async def save_coupons(coupons: List[dict]):
    """Salva cupons e seus produtos no banco (upsert por coupon_code)."""
    from app.db.session import AsyncSessionLocal
    from app.models.models import Coupon, CouponProduct
    from app.services.affiliate_tracking import add_ml_affiliate_tracking
    from sqlalchemy import select, delete

    saved = 0
    total_products = 0
    skipped_low_demand = 0
    async with AsyncSessionLocal() as db:
        for c in coupons:
            # Filtro: só salva cupons com produtos em categorias de demanda
            if not _is_demand_coupon(c):
                skipped_low_demand += 1
                continue
            existing = await db.execute(
                select(Coupon)
                .where(
                    Coupon.provider == "mercadolivre",
                    Coupon.coupon_code == c["coupon_code"],
                )
                .order_by(Coupon.updated_at.desc())
            )
            existing_rows = existing.scalars().all()
            if existing_rows:
                # Purga duplicatas históricas do mesmo provider+code (o upsert
                # antigo sem provider podia deixar linhas gêmeas no banco)
                if len(existing_rows) > 1:
                    dup_ids = [r.id for r in existing_rows[1:]]
                    await db.execute(
                        delete(CouponProduct).where(CouponProduct.coupon_id.in_(dup_ids))
                    )
                    await db.execute(delete(Coupon).where(Coupon.id.in_(dup_ids)))
                    logger.info(f"Removidas {len(dup_ids)} duplicatas de {c['coupon_code']}")
                existing = existing_rows[0]
                # Atualiza
                existing.discount_text = c.get("discount_text")
                existing.discount_percent = c.get("discount_percent")
                existing.discount_value = c.get("discount_value")
                existing.expires_at = c.get("expires_at")
                existing.budget_remaining = c.get("budget_remaining")
                existing.conditions = c.get("conditions")
                existing.store_name = c.get("store_name")
                existing.product_url = add_ml_affiliate_tracking(c.get("product_url"))
                existing.is_active = True
                existing.updated_at = datetime.now(timezone.utc)
                coupon_obj = existing
            else:
                coupon_obj = Coupon(
                    provider="mercadolivre",
                    store_name=c.get("store_name"),
                    coupon_code=c["coupon_code"],
                    discount_text=c.get("discount_text"),
                    discount_percent=c.get("discount_percent"),
                    discount_value=c.get("discount_value"),
                    expires_at=c.get("expires_at"),
                    budget_remaining=c.get("budget_remaining"),
                    conditions=c.get("conditions"),
                    product_url=add_ml_affiliate_tracking(c.get("product_url")),
                    is_active=True,
                )
                db.add(coupon_obj)
                await db.flush()  # precisa do ID

            # Salva produtos do cupom (deleta os antigos e insere os novos)
            products = c.get("products", [])
            if products:
                # Deleta produtos antigos deste cupom
                await db.execute(
                    delete(CouponProduct).where(CouponProduct.coupon_id == coupon_obj.id)
                )
                # Dedup por ml_code ou product_url
                seen_prods = set()
                for p in products:
                    key = p.get("ml_code") or p.get("product_url")
                    if key in seen_prods:
                        continue
                    seen_prods.add(key)
                    # Sanity check no preço
                    price = p.get("price")
                    if price and (price > 10000000 or price < 0.01):
                        price = None
                    db.add(CouponProduct(
                        coupon_id=coupon_obj.id,
                        title=p["title"],
                        product_url=add_ml_affiliate_tracking(p["product_url"]),
                        image_url=p.get("image_url"),
                        price=price,
                        ml_code=p.get("ml_code"),
                        is_available=p.get("available", True),
                    ))
                    total_products += 1

            saved += 1
        await db.commit()
    if skipped_low_demand:
        logger.info(f"Pulados {skipped_low_demand} cupons fora de categorias de demanda")
    logger.info(f"Salvos {saved} cupons e {total_products} produtos no banco")
    return saved


async def deactivate_expired_coupons():
    """Deleta cupons vencidos do banco (data de vencimento já passou)."""
    from app.db.session import AsyncSessionLocal
    from app.models.models import Coupon, CouponProduct
    from sqlalchemy import select, delete

    now = datetime.now(timezone.utc)
    async with AsyncSessionLocal() as db:
        # Seleciona IDs dos cupons vencidos
        expired = await db.execute(
            select(Coupon.id).where(Coupon.expires_at < now)
        )
        expired_ids = [row[0] for row in expired.all()]

        if expired_ids:
            # Deleta produtos associados primeiro para não violar FK
            await db.execute(
                delete(CouponProduct).where(CouponProduct.coupon_id.in_(expired_ids))
            )
            # Deleta cupons vencidos
            result = await db.execute(
                delete(Coupon).where(Coupon.id.in_(expired_ids))
            )
            await db.commit()
            count = result.rowcount
            if count:
                logger.info(f"Deletados {count} cupons vencidos")


async def deactivate_missing_ml_coupons(seen_codes: set):
    """Desativa cupons ML que sumiram da listagem (só rodar após run COMPLETO).

    Cupom pode sumir antes de expirar (budget esgotado, campanha encerrada) —
    sem isso ficava is_active=True pra sempre. Desativa, não deleta: pode
    voltar, e o histórico de produtos é útil.
    """
    from app.db.session import AsyncSessionLocal
    from app.models.models import Coupon
    from sqlalchemy import update

    if not seen_codes:
        logger.warning("Run completo com 0 cupons vistos — suspeito; nada desativado")
        return
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            update(Coupon)
            .where(
                Coupon.provider == "mercadolivre",
                Coupon.is_active == True,
                Coupon.coupon_code.notin_(seen_codes),
            )
            .values(is_active=False, updated_at=datetime.now(timezone.utc))
        )
        await db.commit()
        if result.rowcount:
            logger.info(f"Desativados {result.rowcount} cupons ausentes da listagem ML")


async def cleanup_expired_coupons():
    """Função standalone para deletar cupons vencidos (chamada via cron)."""
    await deactivate_expired_coupons()


# ── parse helpers ──────────────────────────────────────────────────────────────
BR_TIMEZONE = timezone(timedelta(hours=-3), "BRT")  # Brasil sem DST desde 2019

_MONTHS_PT = {
    "janeiro": 1, "fevereiro": 2, "março": 3, "marco": 3, "abril": 4,
    "maio": 5, "junho": 6, "julho": 7, "agosto": 8,
    "setembro": 9, "outubro": 10, "novembro": 11, "dezembro": 12,
}


def parse_expiry(text: str) -> Optional[datetime]:
    """'Vence 15 de outubro' -> 23:59:59 BRT desse dia (ano seguinte se já passou).

    ML expira cupons às 23:59 horário de Brasília (=02:59Z — ver
    tracking.expiration_date). Fallback quando não há ISO no payload.
    """
    m = re.search(r"(\d+)\s+de\s+(\w+)", text or "")
    if not m:
        return None
    month = _MONTHS_PT.get(m.group(2).lower())
    if not month:
        return None
    now = datetime.now(timezone.utc)
    try:
        dt = datetime(now.year, month, int(m.group(1)), 23, 59, 59, tzinfo=BR_TIMEZONE)
        if dt < now:
            dt = dt.replace(year=now.year + 1)
        return dt
    except ValueError:
        return None


def _parse_iso_date(s: Optional[str]) -> Optional[datetime]:
    """'2026-10-16T02:59Z' / '2026-10-31T02:59:59Z' -> datetime UTC."""
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None


def _parse_br_money(s: str) -> Optional[float]:
    """'R$ 1.000' -> 1000.0 | 'R$ 50,99' -> 50.99 | None se sem número."""
    m = re.search(r"(\d{1,3}(?:\.\d{3})*(?:,\d{1,2})?|\d+(?:,\d{1,2})?|\d+)", s or "")
    if not m:
        return None
    v = m.group(1)
    if "." in v and "," in v:
        v = v.replace(".", "").replace(",", ".")
    elif "," in v:
        v = v.replace(",", ".")
    elif "." in v:
        parts = v.split(".")
        if not (len(parts) == 2 and len(parts[1]) in (1, 2)):
            v = v.replace(".", "")
    try:
        return float(v)
    except ValueError:
        return None


def parse_discount(text: str) -> dict:
    """Extrai desconto do texto. '21% OFF' -> {percent: 21}. 'R$ 80 OFF' -> {value: 80}."""
    result = {}
    m = re.search(r"(\d+(?:[.,]\d+)?)\s*%\s*OFF", text, re.I)
    if m:
        result["discount_percent"] = float(m.group(1).replace(",", "."))
        result["discount_text"] = f"{m.group(1)}% OFF"
        return result
    m = re.search(r"R\$\s*([\d.,]+)\s*OFF", text, re.I)
    if m:
        value = _parse_br_money(m.group(1))
        if value is not None:
            result["discount_value"] = value
            result["discount_text"] = f"R$ {m.group(1)} OFF"
            return result
    result["discount_text"] = text.strip()
    return result


def _product_url_from_ml_code(ml_code: str) -> str:
    """MLB4224318415 -> https://produto.mercadolivre.com.br/MLB-4224318415"""
    code = ml_code.strip().upper()
    if code.startswith("MLB") and len(code) > 3:
        return f"https://produto.mercadolivre.com.br/{code[:3]}-{code[3:]}"
    return f"https://produto.mercadolivre.com.br/{code}"


# ── extração do hydration blob ─────────────────────────────────────────────────
def _extract_rendering_ctx(html: str) -> Optional[dict]:
    """Extrai o objeto _n.ctx.r={...} do <script id="__NORDIC_RENDERING_CTX__">."""
    m = re.search(r'<script id="__NORDIC_RENDERING_CTX__"[^>]*>(.*?)</script>', html, re.S)
    if not m:
        return None
    raw = m.group(1)
    start = raw.find("{")
    if start < 0:
        return None
    try:
        data, _ = json.JSONDecoder().raw_decode(raw[start:])
        return data
    except json.JSONDecodeError as e:
        logger.warning(f"Falha ao parsear __NORDIC_RENDERING_CTX__: {e}")
        return None


def _extract_coupons_page(data: dict) -> tuple:
    """Extrai cupons normalizados + total de páginas do ctx de uma página.

    Retorna (lista_de_cupons, total_pages, total_coupons).
    """
    fcd = (data.get("appProps") or {}).get("pageProps", {}).get("filteredCouponsData") or {}
    ui_coupons = fcd.get("coupons") or []
    pagination = fcd.get("pagination") or {}
    total_pages = pagination.get("total") or 1
    total_coupons = (fcd.get("totalCouponsQuantity") or {}).get("number")

    # Dados limpos do tracking (campaign_id -> item_ids, discount, collectors...)
    tracking_by_id = {}
    try:
        for t in fcd["tracking"]["view"]["eventData"]["coupons_list"]:
            if t.get("campaign_id"):
                tracking_by_id[str(t["campaign_id"])] = t
    except Exception:
        pass

    coupons = []
    for c in ui_coupons:
        try:
            cid = str(c.get("campaignId") or "").strip()
            if not cid:
                continue
            t = tracking_by_id.get(cid) or {}

            title = (c.get("title") or {}).get("text") or ""
            subtitle = (c.get("initialSubtitle") or {}).get("text") or ""
            amount = c.get("amount") or {}
            status_id = ((c.get("status") or {}).get("id") or "").upper()
            action = c.get("action") or {}
            tracking_status = (t.get("status_id") or "").upper()
            if tracking_status:
                status_id = tracking_status

            coupon = {
                "coupon_code": f"MLC-{cid}",
                "campaign_id": cid,
                "status": status_id,
            }

            # Desconto: tracking (limpo) primeiro, fallback no parse do título
            dtype = (t.get("discount_type") or "").upper()
            dvalue = t.get("discount_value")
            if dtype == "PERCENT" and dvalue is not None:
                coupon["discount_percent"] = float(dvalue)
                coupon["discount_text"] = title or f"{dvalue}% OFF"
            elif dvalue is not None and dtype in ("ABSOLUTE", "NOMINAL", "FIXED", "VALUE"):
                coupon["discount_value"] = float(dvalue)
                coupon["discount_text"] = title or f"R$ {dvalue} OFF"
            else:
                coupon.update(parse_discount(title))

            # Loja: "Em produtos de Web Continental" -> "Web Continental"
            m_store = re.match(r"Em produtos de\s+(.+)", subtitle, re.I)
            coupon["store_name"] = m_store.group(1).strip() if m_store else "Mercado Livre"

            # Vencimento: ISO do tracking > futureCouponInfo > texto do card
            coupon["expires_at"] = (
                _parse_iso_date(t.get("expiration_date"))
                or _parse_iso_date((c.get("futureCouponInfo") or {}).get("expiration_date"))
            )
            if not coupon["expires_at"]:
                exp_text = (c.get("expirationDate") or {}).get("text") or ""
                coupon["expires_at"] = parse_expiry(exp_text)

            # Condições: compra mínima + limite. "Sem compra mínima."/"Sem
            # limite." são a AUSÊNCIA de condição — não entram no texto.
            cond_parts = []
            min_txt = (amount.get("minAmount") or "").strip()
            cap_txt = (amount.get("capAmount") or "").strip()
            if min_txt and not re.match(r"sem\b", min_txt, re.I):
                cond_parts.append(min_txt.rstrip("."))
            if cap_txt and not re.match(r"sem\b", cap_txt, re.I):
                cond_parts.append(cap_txt.rstrip("."))
            coupon["conditions"] = " · ".join(cond_parts) if cond_parts else None
            coupon["min_amount"] = _parse_br_money(min_txt)
            coupon["cap_amount"] = _parse_br_money(cap_txt)

            # URL destino ("Ver produtos"): ACTIVE já traz action.value;
            # INACTIVE reconstrói _CustId_{collector}?coupon_campaign_id=
            product_url = None
            if action.get("type") == "link" and action.get("value"):
                product_url = action["value"]
            else:
                collectors = (t.get("segmentations") or {}).get("collectors") or []
                if collectors:
                    product_url = (
                        f"https://lista.mercadolivre.com.br/_CustId_{collectors[0]}"
                        f"?coupon_campaign_id={cid}"
                    )
            coupon["product_url"] = product_url

            # Produtos amostra: item_ids do tracking + items[] (imagem/título) na mesma ordem
            item_ids = t.get("item_ids") or []
            ui_items = c.get("items") or []
            products = []
            for i, iid in enumerate(item_ids):
                ui = ui_items[i] if i < len(ui_items) else {}
                products.append({
                    "title": (ui.get("altText") or "").strip() or f"Produto {iid}",
                    "product_url": _product_url_from_ml_code(iid),
                    "image_url": ui.get("imageUrl"),
                    "price": None,
                    "ml_code": iid,
                })
            # items[] sem item_id correspondente (fallback)
            for ui in ui_items[len(products):]:
                img = ui.get("imageUrl") or ""
                mm = re.search(r"(MLB\d{6,})", img)
                if mm:
                    products.append({
                        "title": (ui.get("altText") or "").strip() or "Produto",
                        "product_url": _product_url_from_ml_code(mm.group(1)),
                        "image_url": img or None,
                        "price": None,
                        "ml_code": mm.group(1),
                    })
            coupon["products"] = products

            # product_url final: usa primeiro item se nada mais disponível
            if not coupon["product_url"]:
                if products:
                    coupon["product_url"] = products[0]["product_url"]
                else:
                    coupon["product_url"] = COUPONS_HOME_URL

            coupons.append(coupon)
        except Exception as e:
            logger.warning(f"Erro ao extrair cupom {c.get('campaignId')}: {e}")

    return coupons, total_pages, total_coupons


# ── fetch ──────────────────────────────────────────────────────────────────────
def _fetch_page(client: httpx.Client, url: str) -> Optional[str]:
    """GET com cookies. Retorna HTML ou None. Detecta login wall."""
    try:
        r = client.get(url)
    except (httpx.ConnectError, httpx.TimeoutException) as e:
        logger.warning(f"Erro de rede em {url}: {e}")
        return None
    except Exception as e:
        logger.warning(f"Erro em {url}: {e}")
        return None
    final = str(r.url)
    if "login" in final or "/auth" in final or "identification" in final:
        return "__LOGIN__"
    if r.status_code != 200 or "__NORDIC_RENDERING_CTX__" not in r.text:
        logger.warning(f"Resposta inesperada em {url}: status={r.status_code} len={len(r.text)}")
        return None
    return r.text


def _session_expired_notice() -> bool:
    """True se EXPIRED_FILE é recente — keeper já alertou (silêncio no log)."""
    if EXPIRED_FILE.exists():
        try:
            last = datetime.fromisoformat(EXPIRED_FILE.read_text().strip())
            elapsed = (datetime.now(timezone.utc) - last).total_seconds()
            return elapsed < EXPIRED_RECENT_HOURS * 3600
        except Exception:
            pass
    return False


# ── enriquecimento via API ML ──────────────────────────────────────────────────
ML_ITEMS_BATCH = 20  # limite do multiget /items?ids=


async def _enrich_products_with_prices(coupons: List[dict], token: Optional[str],
                                       cache: dict, client: httpx.AsyncClient):
    """Preenche price/title/url reais dos produtos via API oficial do ML.

    GET /items?ids=MLB1,...,MLB20 — resposta [{code, body:{price,title,permalink,...}}].
    Falhas são toleradas silenciosamente (produtos ficam com price=None).
    `cache` persiste entre páginas (muitos item_ids se repetem entre cupons).
    """
    if not token or cache.get("__disabled__"):
        return
    wanted = []
    for c in coupons:
        for p in c["products"]:
            mc = p.get("ml_code")
            if mc and mc not in cache:
                cache[mc] = None  # reserva: evita refetch em cupons seguintes
                wanted.append(mc)

    for i in range(0, len(wanted), ML_ITEMS_BATCH):
        chunk = wanted[i:i + ML_ITEMS_BATCH]
        try:
            r = await client.get(
                f"https://api.mercadolibre.com/items?ids={','.join(chunk)}",
                headers={"Authorization": f"Bearer {token}"},
                timeout=20,
            )
            if r.status_code != 200:
                logger.warning(f"ML items API {r.status_code} — pulando enriquecimento")
                cache["__disabled__"] = True
                break
            entries = r.json()
            # Multiget retorna [{code, body}] — 403 em TODOS os itens = app sem
            # escopo de leitura de items → desliga pro resto da rodada.
            if entries and all(
                (e.get("code") or 200) in (401, 403) for e in entries
            ):
                logger.info("ML items API sem acesso a /items (403) — enriquecimento desligado")
                cache["__disabled__"] = True
                break
            for entry in entries:
                # code != 200 = erro por item (body.status é int, não status do item)
                if (entry.get("code") or 200) != 200:
                    continue
                body = entry.get("body") or {}
                iid = body.get("id") or (entry.get("id") if isinstance(entry.get("id"), str) else None)
                if not iid:
                    continue
                price = body.get("price")
                permalink = body.get("permalink")
                title = body.get("title")
                status = body.get("status")
                cache[iid] = {
                    "price": price if isinstance(price, (int, float)) else None,
                    "permalink": permalink,
                    "title": title,
                    # Só marca indisponível com status explícito — campo ausente
                    # não é evidência (foi assim que um 403 zerou is_available)
                    "available": (status == "active") if isinstance(status, str) and status else True,
                }
        except Exception as e:
            logger.warning(f"ML items API erro: {e}")
            break
        await asyncio.sleep(0.4)

    # Aplica cache aos produtos desta página — SEMPRE, mesmo após falha parcial
    # (itens já buscados em batches anteriores não podem ser desperdiçados, e
    # produtos cujo ml_code já estava em cache de páginas anteriores dependem
    # exclusivamente deste bloco)
    for c in coupons:
        for p in c["products"]:
            info = cache.get(p.get("ml_code") or "")
            if not info:
                continue
            if info["price"]:
                p["price"] = float(info["price"])
            if info.get("permalink"):
                p["product_url"] = info["permalink"]
            if info.get("title") and (not p.get("title") or p["title"].startswith("Produto")):
                p["title"] = info["title"]
            p["available"] = info.get("available", True)


async def _get_ml_api_token() -> Optional[str]:
    """Token OAuth do ML (tabela ml_tokens) — None se indisponível."""
    try:
        from app.db.session import AsyncSessionLocal
        from app.services.ml_token_service import get_token
        async with AsyncSessionLocal() as db:
            return await get_token(db)
    except Exception as e:
        logger.warning(f"Sem token ML API (produtos ficarão sem preço): {e}")
        return None


# ── scraper ────────────────────────────────────────────────────────────────────
async def scrape_ml_coupons(max_pages: int = 0) -> Tuple[List[dict], bool]:
    """Coleta todos os cupons de /cupons/filter?all=true via HTTP + JSON SSR.

    Retorna (lista_de_cupons, completou). `completou` é False quando o scrape
    aborta antes do fim da listagem (login wall, falhas consecutivas, limites)
    — usado para NÃO desativar cupons ausentes numa coleta parcial.
    """
    cookies = _load_cookie_dict()
    if not cookies:
        logger.error("Sem cookies para requisição")
        return [], False

    api_token = await _get_ml_api_token()
    if api_token:
        logger.info("Token ML API disponível — produtos serão enriquecidos com preço real")
    price_cache: dict = {}

    ua = random.choice(USER_AGENTS)
    all_coupons = []
    seen_ids = set()
    total_pages = 1
    total_coupons = None

    with httpx.Client(
        cookies=cookies,
        follow_redirects=True,
        timeout=30,
        headers={
            "User-Agent": ua,
            "Accept-Language": "pt-BR,pt;q=0.9",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        },
    ) as client:
        page = 1
        consecutive_failures = 0
        while page <= total_pages:
            if max_pages and page > max_pages:
                break
            if page > MAX_PAGES_HARD_LIMIT:
                logger.warning(f"Hard limit de {MAX_PAGES_HARD_LIMIT} páginas atingido")
                break

            url = COUPONS_FILTER_URL if page == 1 else f"{COUPONS_FILTER_URL}&page={page}"
            html = _fetch_page(client, url)
            if html == "__LOGIN__":
                if _session_expired_notice():
                    logger.info("Cookies expirados — EXPIRED_FILE recente, keeper já alertou (silêncio)")
                else:
                    logger.error("Cookies expirados — redirecionou para login")
                return all_coupons, False  # coleta parcial
            if not html:
                consecutive_failures += 1
                if consecutive_failures >= 3:
                    logger.error("3 falhas consecutivas — abortando")
                    break
                await asyncio.sleep(5)
                continue
            consecutive_failures = 0

            data = _extract_rendering_ctx(html)
            if not data:
                # Falha de parse NÃO avança de página — retenta a mesma (antes
                # pulava e perdia até 30 cupons por página)
                consecutive_failures += 1
                if consecutive_failures >= 3:
                    logger.error("3 falhas consecutivas de parse — abortando")
                    break
                logger.warning(f"Página {page}: sem __NORDIC_RENDERING_CTX__ — retentando")
                await asyncio.sleep(5)
                continue

            page_coupons, total_pages, total_coupons = _extract_coupons_page(data)
            new = [c for c in page_coupons if c["campaign_id"] not in seen_ids]
            for c in new:
                seen_ids.add(c["campaign_id"])
            all_coupons.extend(new)
            logger.info(
                f"Página {page}/{total_pages}: {len(page_coupons)} cupons "
                f"({len(new)} novos) — total {len(all_coupons)}/{total_coupons or '?'}"
            )

            # Enriquece produtos com preço real (API ML) antes de salvar
            if new:
                try:
                    async with httpx.AsyncClient(timeout=20) as api_client:
                        await _enrich_products_with_prices(new, api_token, price_cache, api_client)
                except Exception as e:
                    logger.warning(f"Erro no enriquecimento página {page}: {e}")

            # Salva incrementalmente a cada página (não perde dados se cair no meio)
            if new:
                try:
                    await save_coupons(new)
                except Exception as e:
                    logger.warning(f"Erro ao salvar página {page}: {e}")

            if not page_coupons:
                logger.info("Página vazia — fim da listagem")
                break

            await asyncio.sleep(random.uniform(*PAGE_DELAY_RANGE))
            page += 1

    # Completo = varreu até depois da última página anunciada. Break por falha,
    # max_pages, hard limit ou página vazia antes do fim = coleta parcial.
    completed = page > total_pages
    logger.info(
        f"Total coletado: {len(all_coupons)} cupons únicos "
        f"(de ~{total_coupons} anunciados){'' if completed else ' — PARCIAL'}"
    )
    return all_coupons, completed


# ── main ───────────────────────────────────────────────────────────────────────
async def run(max_pages: int = 0, headless: bool = True, collect_only: bool = False):
    """Executa o scraper de cupons do ML (HTTP puro — sem browser)."""
    coupons = []

    # Lock para evitar execuções simultâneas do próprio scraper.
    # NÃO usa PROFILE_LOCK_FILE: não tocamos o perfil/browser — só lemos
    # .ml_cookies.json, e requests HTTP paralelos do keeper são inofensivos.
    lock = LockFile(LOCK_FILE)
    if not lock.acquire():
        logger.error(f"Outra instância do ml_coupon_scraper já está rodando (lock em {LOCK_FILE})")
        return []
    logger.info("Lock adquirido — iniciando scraping de cupons")

    if not _check_cookies_valid():
        logger.error("Cookies inválidos ou ausentes — abortando")
        lock.release()
        return []

    try:
        coupons, completed = await scrape_ml_coupons(max_pages=max_pages)

        # Desativa vencidos
        await deactivate_expired_coupons()

        # Cupons que sumiram da listagem (budget esgotado etc.) — só com
        # coleta completa, senão uma run parcial desativaria cupons válidos
        if completed:
            await deactivate_missing_ml_coupons({c["coupon_code"] for c in coupons})
        else:
            logger.info("Coleta parcial — cupons ausentes NÃO serão desativados")
    finally:
        lock.release()

    logger.info(f"\n{'='*60}")
    logger.info(f"SCRAPING DE CUPONS CONCLUÍDO: {len(coupons)} cupons")
    logger.info(f"{'='*60}")
    return coupons


def _str2bool(v) -> bool:
    """type=bool do argparse avalia 'false'/'0' como True — parse correto."""
    return str(v).strip().lower() in ("1", "true", "yes", "y", "on", "sim")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Scraper de cupons do ML")
    parser.add_argument("--max-pages", type=int, default=0, help="Limite de páginas (0 = todas)")
    parser.add_argument("--headless", type=_str2bool, nargs="?", const=True, default=True, help="Ignorado (scrape é HTTP puro)")
    parser.add_argument("--cleanup-only", action="store_true", help="Apenas deleta cupons vencidos")
    parser.add_argument("--collect-only", action="store_true", help="Ignorado (modelo antigo)")
    args = parser.parse_args()

    if args.cleanup_only:
        asyncio.run(cleanup_expired_coupons())
        sys.exit(0)

    result = asyncio.run(run(max_pages=args.max_pages, headless=args.headless, collect_only=args.collect_only))
    sys.exit(0 if result else 1)
