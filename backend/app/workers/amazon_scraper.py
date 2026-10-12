"""
amazon_scraper.py — Scraper de produtos da Amazon.com.br.

Busca produtos populares na Amazon, extrai título/preço/imagem/URL e salva
na tabela affiliate_products com links de afiliado (tag=aletubegames-20).

Não usa a Product Advertising API (PA-API) — que requer 3 vendas qualificadas.
Em vez disso, faz scraping da página de busca da Amazon via Playwright.

Uso:
  cd backend && venv/bin/python -m app.workers.amazon_scraper
  cd backend && venv/bin/python -m app.workers.amazon_scraper --dry-run
  cd backend && venv/bin/python -m app.workers.amazon_scraper --queries "iphone,notebook,airfryer"
  cd backend && venv/bin/python -m app.workers.amazon_scraper --headless=false

Requer:
  playwright (pip install playwright)
  chromium-browser instalado

Variáveis no .env:
  AMAZON_PARTNER_TAG=aletubegames-20
"""

import asyncio
import os
import re
import logging
import shutil
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger("amazon_scraper")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

BROWSER_ARGS = ["--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage"]


def find_browser_executable() -> str | None:
    for candidate in (
        "/usr/bin/google-chrome",
        "/usr/bin/chromium-browser",
        "/usr/bin/chromium",
    ):
        if Path(candidate).is_file() and os.access(candidate, os.X_OK):
            return candidate
    return shutil.which("google-chrome") or shutil.which("chromium")


async def launch_browser(playwright, headless: bool):
    executable = find_browser_executable()
    if executable:
        logger.info(f"Usando navegador do sistema: {executable}")
        return await playwright.chromium.launch(
            headless=headless,
            executable_path=executable,
            args=BROWSER_ARGS,
        )

    try:
        return await playwright.chromium.launch(
            headless=headless,
            channel="chromium",
            args=BROWSER_ARGS,
        )
    except Exception as exc:
        raise RuntimeError(
            "Nenhum navegador compatível encontrado. Instale Google Chrome "
            "ou execute 'playwright install chromium'."
        ) from exc


# ── paths ─────────────────────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR.parent.parent
ENV_FILE = BACKEND_DIR / ".env"

# ── load .env ─────────────────────────────────────────────────────────────────
def load_env() -> dict:
    env = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                env[k.strip()] = v.strip()
    return env


# ── queries padrão (produtos populares de alta comissão) ──────────────────────
DEFAULT_QUERIES = [
    # Eletrônicos
    "iphone 16 pro max", "iphone 16", "iphone 15", "samsung galaxy s25",
    "samsung galaxy a55", "xiaomi redmi note 13", "motorola edge 50",
    "notebook dell", "notebook lenovo", "macbook air m3",
    "tablet samsung", "ipad 10", "kindle paperwhite",
    # Games
    "playstation 5", "xbox series x", "nintendo switch oled",
    "controle ps5", "controle xbox", "jogo ps5",
    # TV
    "smart tv 55", "smart tv 50", "smart tv 43", "smart tv 65",
    "tv lg oled", "tv samsung qled",
    # Eletrodomésticos
    "airfryer", "airfryer philips", "airfryer mondial", "airfryer electrolux",
    "geladeira frost free", "fogao 4 bocas", "microondas electrolux",
    "lava loucas", "aspirador robo",
    # Beleza
    "secador philips", "prancha babyliss", "barbeador philips",
    "perfume masculino", "perfume feminino",
    # Casa
    "ventilador parede", "ar condicionado split 12000",
    "lava rapido sem fio", "espremedor frutas",
    # Ferramentas
    "furadeira makita", "parafusadeira bosch", "fita led 5m",
    # Pet
    "racao 15kg", "racao gato 10kg", "arranhador gato",
    # Moda
    "tenis nike masculino", "tenis adidas feminino", "mochila notebook",
    # Informática
    "ssd nvme 1tb", "memoria ram 16gb", "mouse logitech", "teclado mecanico",
    "monitor 24", "monitor 27", "webcam logitech",
    # Áudio
    "fone bluetooth jbl", "airpods pro 2", "echo dot 5",
    "caixa de som bluetooth", "home theater",
]


def parse_price(raw: str) -> Optional[float]:
    """Extrai float de 'R$ 1.998,90' -> 1998.90"""
    if not raw:
        return None
    # Remove tudo que não for dígito, vírgula ou ponto
    m = re.search(r"R\$\s*([\d.,]+)", raw)
    if not m:
        # Tenta sem R$
        m = re.search(r"([\d.,]+)", raw)
        if not m:
            return None
    num = m.group(1)
    # Formato brasileiro: 1.998,90
    if "." in num and "," in num:
        num = num.replace(".", "").replace(",", ".")
    elif "," in num and "." not in num:
        num = num.replace(",", ".")
    elif "." in num and "," not in num:
        # Pode ser 1998.90 ou 1.998 (ambíguo)
        parts = num.split(".")
        if len(parts[-1]) == 3 and len(parts) == 2:
            # 1.998 -> 1998
            num = num.replace(".", "")
    try:
        return round(float(num), 2)
    except ValueError:
        return None


def build_affiliate_url(product_url: str, partner_tag: str) -> str:
    """Adiciona tag de afiliado à URL da Amazon."""
    if not product_url:
        return ""
    # Remove fragment
    url = product_url.split("#")[0]
    # Adiciona ou substitui o tag
    if "tag=" in url:
        url = re.sub(r"tag=[^&]+", f"tag={partner_tag}", url)
    elif "?" in url:
        url = f"{url}&tag={partner_tag}"
    else:
        url = f"{url}?tag={partner_tag}"
    return url


def build_search_url(query: str, partner_tag: str) -> str:
    """Cria URL de busca da Amazon com tag de afiliado."""
    encoded = urllib.parse.quote_plus(query)
    return f"https://www.amazon.com.br/s?k={encoded}&tag={partner_tag}"


async def scrape_search(page, query: str, partner_tag: str, dry_run: bool = False) -> int:
    """Faz scraping de uma busca na Amazon. Retorna número de produtos coletados."""
    search_url = build_search_url(query, partner_tag)
    logger.info(f"  Buscando: '{query}' -> {search_url}")

    try:
        await page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(2000)  # espera carregar produtos
    except Exception as e:
        logger.warning(f"  Erro ao carregar página: {e}")
        return 0

    # Tenta fechar popup de cookies se existir
    try:
        cookie_btn = await page.query_selector("#sp-cc-accept, [data-testid='cookie-accept']")
        if cookie_btn:
            await cookie_btn.click()
            await page.wait_for_timeout(500)
    except Exception:
        pass

    count = 0
    vistos = set()

    # Amazon usa div[data-component-type='s-search-result'] para cada produto
    try:
        results = await page.query_selector_all("div[data-component-type='s-search-result']")
    except Exception as e:
        logger.warning(f"  Erro ao buscar resultados: {e}")
        return 0

    logger.info(f"  Encontrados {len(results)} resultados na página")

    for card in results[:20]:  # máximo 20 por query
        try:
            # Título
            title_el = await card.query_selector("h2 a span, h2 span")
            title = (await title_el.inner_text()).strip() if title_el else ""
            if not title or title in vistos:
                continue
            vistos.add(title)

            # Link do produto
            # Amazon usa /sspa/click?...url=%2F... para anúncios patrocinados
            # e /dp/ASIN para produtos orgânicos. O link pode estar em:
            # - a.a-link-normal (container do card)
            # - h2 a (título)
            # - a.s-line-clamp-4 (título clicável)
            product_url = ""
            link_selectors = [
                "a.a-link-normal[href*='/dp/']",
                "a.a-link-normal[href*='/sspa/click']",
                "h2 a",
                "a.s-line-clamp-4",
            ]
            for sel in link_selectors:
                link_el = await card.query_selector(sel)
                if not link_el:
                    continue
                href = await link_el.get_attribute("href") or ""
                if not href or href == "#" or href.startswith("javascript:"):
                    continue
                # Se for anúncio patrocinado (/sspa/click?...url=...), extrai URL real
                if "/sspa/click" in href and "url=" in href:
                    m = re.search(r"url=([^&]+)", href)
                    if m:
                        decoded = urllib.parse.unquote(m.group(1))
                        if decoded.startswith("/"):
                            product_url = "https://www.amazon.com.br" + decoded
                        else:
                            product_url = decoded
                elif href.startswith("/dp/") or "/dp/" in href:
                    if href.startswith("/"):
                        product_url = "https://www.amazon.com.br" + href
                    else:
                        product_url = href
                elif href.startswith("/"):
                    product_url = "https://www.amazon.com.br" + href
                elif href.startswith("https://"):
                    product_url = href

                # Limpa URL: remove ref e parâmetros, mantém só /dp/ASIN
                if "/dp/" in product_url:
                    m = re.search(r"(/dp/[A-Z0-9]+)", product_url)
                    if m:
                        product_url = "https://www.amazon.com.br" + m.group(1)
                        break  # URL limpa encontrada

                if product_url:
                    break

            if not product_url:
                continue

            # Preço — Amazon tem vários formatos
            price = None
            # Método 1: span.a-price > span.a-offscreen
            price_el = await card.query_selector("span.a-price span.a-offscreen")
            if price_el:
                price_text = await price_el.inner_text()
                price = parse_price(price_text)

            # Método 2: div.a-price
            if not price:
                price_el = await card.query_selector("div.a-price span.a-offscreen")
                if price_el:
                    price_text = await price_el.inner_text()
                    price = parse_price(price_text)

            # Método 3: texto com R$
            if not price:
                price_els = await card.query_selector_all("span.a-color-price, span.a-offscreen")
                for pel in price_els:
                    txt = await pel.inner_text()
                    if "R$" in txt:
                        price = parse_price(txt)
                        if price:
                            break

            # Imagem
            image_url = ""
            img_el = await card.query_selector("img.s-image")
            if img_el:
                image_url = await img_el.get_attribute("src") or ""

            # Rating (estrelas)
            rating = None
            rating_el = await card.query_selector("span.a-icon-alt")
            if rating_el:
                rating_text = await rating_el.inner_text()
                m = re.search(r"([\d.,]+)\s*de\s*5", rating_text)
                if m:
                    try:
                        rating = float(m.group(1).replace(",", "."))
                    except ValueError:
                        pass

            # Avaliações count
            review_count = None
            review_el = await card.query_selector("span.a-size-base.s-underline-text")
            if review_el:
                review_text = await review_el.inner_text()
                review_text = review_text.replace(".", "").replace(",", "")
                m = re.search(r"(\d+)", review_text)
                if m:
                    review_count = int(m.group(1))

            # Prime
            is_prime = False
            prime_el = await card.query_selector("i.a-icon-prime, span.a-icon-prime")
            if prime_el:
                is_prime = True

            # Cupom — Amazon mostra "com o cupom XXXXXX" ou badge de cupom no card
            coupon_code = None
            coupon_text = None
            try:
                # Procura por texto de cupom no card
                card_text = await card.inner_text()
                # Padrão: "com o cupom ABC123" — código deve ter pelo menos 1 dígito
                # (evita pegar palavras como "ENTREGA", "FRETE", etc)
                m = re.search(r"(?:com o cupom|Cupom de)\s+([A-Z0-9]{6,20})", card_text, re.I)
                if m:
                    code = m.group(1).upper()
                    # Só aceita se tiver pelo menos 1 dígito (códigos reais têm números)
                    if re.search(r'\d', code):
                        coupon_code = code
                        coupon_text = m.group(0)
                # Se não encontrou código, procura badge de cupom (sem código, auto-aplicado)
                if not coupon_code:
                    coupon_badge = await card.query_selector(
                        '[id*="coupon"], [class*="coupon"], a[href*="/promotion/psp/"]'
                    )
                    if coupon_badge:
                        badge_text = await coupon_badge.inner_text()
                        # Só registra se tiver desconto real (X% OFF ou R$ X OFF)
                        if re.search(r'\d+\s*%\s*OFF|R\$\s*\d+\s*OFF', badge_text, re.I):
                            coupon_text = badge_text.strip()
            except Exception:
                pass

            # Gera link de afiliado
            affiliate_url = build_affiliate_url(product_url, partner_tag)

            # Pula se não tem preço (produto indisponível)
            if not price or price <= 0:
                logger.debug(f"    Sem preço — pulando: {title[:40]}")
                continue

            notes_parts = []
            if rating:
                notes_parts.append(f"rating={rating}")
            if review_count:
                notes_parts.append(f"reviews={review_count}")
            if is_prime:
                notes_parts.append("prime=true")
            if coupon_code:
                notes_parts.append(f"coupon={coupon_code}")
            notes_parts.append(f"source=amazon_scraper")
            notes = " | ".join(notes_parts)

            produto = {
                "nome": title,
                "preco": f"R$ {price}",
                "link_prod": affiliate_url,
                "Codigo_ML": "",  # Amazon não usa MLB
                "categoria": query,  # usa a query como categoria
                "image_url": image_url,
                "notes": notes,
            }

            # Se detectou cupom, salva na tabela coupons
            if not dry_run and (coupon_code or coupon_text):
                try:
                    await save_amazon_coupon(
                        code=coupon_code,
                        discount_text=coupon_text,
                        product_url=product_url,
                        title=title,
                    )
                    if coupon_code:
                        logger.info(f"    🏷️ Cupom detectado: {coupon_code}")
                    else:
                        logger.info(f"    🏷️ Cupom (auto): {coupon_text[:40]}")
                except Exception as e:
                    logger.debug(f"    Erro ao salvar cupom: {e}")

            count += 1
            logger.info(f"    [{count}] R$ {price:>10.2f}  {title[:60]}")

            if not dry_run:
                await save_single_product(produto, provider="amazon")

        except Exception as e:
            logger.debug(f"    Erro ao processar card: {e}")
            continue

    logger.info(f"  Query '{query}': {count} produtos coletados")
    return count


async def save_amazon_coupon(code: str = None, discount_text: str = None,
                              product_url: str = None, title: str = None):
    """Salva cupom da Amazon detectado na página do produto."""
    from app.db.session import AsyncSessionLocal
    from app.models.models import Coupon
    from sqlalchemy import select
    from datetime import datetime, timezone
    import re as _re

    # Se não tem código, gera um identificador único baseado na URL
    coupon_code = code or f"AUTO_{_re.search(r'/dp/([A-Z0-9]+)', product_url or '').group(1) if _re.search(r'/dp/([A-Z0-9]+)', product_url or '') else 'UNKNOWN'}"

    # Parse desconto do texto
    discount_percent = None
    discount_value = None
    if discount_text:
        m = _re.search(r"(\d+(?:[.,]\d+)?)\s*%", discount_text)
        if m:
            discount_percent = float(m.group(1).replace(",", "."))
        m = _re.search(r"R\$\s*(\d+(?:[.,]\d+)?)", discount_text)
        if m:
            discount_value = float(m.group(1).replace(".", "").replace(",", "."))

    async with AsyncSessionLocal() as db:
        existing = await db.execute(
            select(Coupon).where(Coupon.coupon_code == coupon_code)
        )
        existing = existing.scalar()
        if existing:
            existing.discount_text = discount_text
            existing.discount_percent = discount_percent
            existing.discount_value = discount_value
            existing.product_url = product_url
            existing.is_active = True
            existing.updated_at = datetime.now(timezone.utc)
        else:
            coupon = Coupon(
                provider="amazon",
                store_name="Amazon",
                coupon_code=coupon_code,
                discount_text=discount_text,
                discount_percent=discount_percent,
                discount_value=discount_value,
                product_url=product_url,
                is_active=True,
            )
            db.add(coupon)
        await db.commit()


async def save_single_product(r: dict, provider: str = "amazon") -> bool:
    """Salva UM produto no banco (upsert). Retorna True se salvou."""
    try:
        from app.db.session import AsyncSessionLocal
        from app.models.models import AffiliateProduct, AffiliatePriceHistory
        from sqlalchemy import select
    except ImportError as e:
        logger.error(f"Erro ao importar banco: {e}")
        return False

    link = r.get("link_prod", "").strip()
    if not link:
        return False

    price = parse_price(r.get("preco", ""))
    image_url = r.get("image_url", "")
    notes = r.get("notes", "")

    try:
        async with AsyncSessionLocal() as db:
            # Busca por URL (upsert)
            stmt = select(AffiliateProduct).where(AffiliateProduct.affiliate_url == link)
            result = await db.execute(stmt)
            existing = result.scalar_one_or_none()

            if existing:
                # Salva snapshot do preço a cada execução do scraper (diária)
                # Mas só 1 por dia por produto (evita duplicatas se o scraper rodar 2x)
                if price is not None and price > 0:
                    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
                    already_today = await db.execute(
                        select(AffiliatePriceHistory).where(
                            AffiliatePriceHistory.product_id == existing.id,
                            AffiliatePriceHistory.recorded_at >= today_start,
                        ).limit(1)
                    )
                    if not already_today.scalar_one_or_none():
                        db.add(AffiliatePriceHistory(
                            product_id=existing.id,
                            provider="amazon",
                            price=price,
                        ))
                existing.title = r.get("nome", "")
                existing.price = price
                existing.category = r.get("categoria", "")
                existing.image_url = image_url or existing.image_url
                existing.notes = notes
                existing.is_active = True
                existing.updated_at = datetime.now(timezone.utc)
            else:
                product = AffiliateProduct(
                    ml_code=r.get("Codigo_ML", ""),
                    affiliate_url=link,
                    title=r.get("nome", ""),
                    price=price,
                    commission_pct=None,  # Amazon não mostra % no scraping
                    category=r.get("categoria", ""),
                    image_url=image_url,
                    notes=notes,
                    is_active=True,
                )
                db.add(product)
                await db.flush()  # precisa do ID
                # Snapshot inicial do preço
                if price is not None:
                    db.add(AffiliatePriceHistory(
                        product_id=product.id,
                        provider="amazon",
                        price=price,
                    ))

            await db.commit()
            return True
    except Exception as e:
        logger.warning(f"  Erro ao salvar produto: {e}")
        return False


async def deactivate_amazon_products(older_than: datetime | None = None):
    """Desativa produtos Amazon que não foram atualizados neste lote.
    NÃO desativa produtos do ML (notes sem 'amazon_scraper').
    Também deleta produtos inativos com >30 dias (auto-cleanup)."""
    try:
        from app.db.session import AsyncSessionLocal
        from app.models.models import AffiliateProduct
        from sqlalchemy import select, func, delete, or_
        from datetime import datetime, timezone, timedelta
    except ImportError:
        return

    async with AsyncSessionLocal() as db:
        # Auto-cleanup: deleta produtos inativos há mais de 30 dias
        cutoff = datetime.now(timezone.utc) - timedelta(days=30)
        old_inactive = await db.execute(
            select(func.count()).select_from(AffiliateProduct).where(
                AffiliateProduct.is_active == False,
                AffiliateProduct.updated_at < cutoff,
            )
        )
        old_count = old_inactive.scalar() or 0
        if old_count > 0:
            await db.execute(
                delete(AffiliateProduct).where(
                    AffiliateProduct.is_active == False,
                    AffiliateProduct.updated_at < cutoff,
                )
            )
            await db.commit()
            logger.info(f"{old_count} produtos inativos (>30 dias) deletados (auto-cleanup)")

        # Só desativa produtos Amazon (não ML) que ficaram fora do lote.
        filters = [
            AffiliateProduct.is_active == True,
            func.lower(AffiliateProduct.notes).like("%amazon_scraper%"),
        ]
        if older_than is not None:
            filters.append(or_(
                AffiliateProduct.updated_at.is_(None),
                AffiliateProduct.updated_at < older_than,
            ))
        result = await db.execute(select(AffiliateProduct).where(*filters))
        old = result.scalars().all()
        for p in old:
            p.is_active = False
        await db.commit()
        if old:
            logger.info(f"{len(old)} produtos Amazon antigos desativados (ML preservado)")


async def run_scraper(queries: list[str] = None, dry_run: bool = False, headless: bool = True):
    """Executa o scraper completo."""
    from playwright.async_api import async_playwright

    env = load_env()
    partner_tag = env.get("AMAZON_PARTNER_TAG", "aletubegames-20")

    if not partner_tag:
        logger.error("AMAZON_PARTNER_TAG não configurado no .env")
        return

    full_catalog_sync = queries is None
    if queries is None:
        queries = DEFAULT_QUERIES

    logger.info(f"=== Amazon Scraper ===")
    logger.info(f"Partner tag: {partner_tag}")
    logger.info(f"Queries: {len(queries)}")
    logger.info(f"Dry run: {dry_run}")
    logger.info(f"Headless: {headless}")

    run_started = datetime.now(timezone.utc)
    total = 0
    async with async_playwright() as p:
        browser = await launch_browser(p, headless)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.7922.108 Safari/537.36",
            viewport={"width": 1280, "height": 800},
            locale="pt-BR",
        )

        page = await context.new_page()

        for i, query in enumerate(queries):
            logger.info(f"\n--- Query {i+1}/{len(queries)}: '{query}' ---")
            try:
                count = await scrape_search(page, query, partner_tag, dry_run)
                total += count
            except Exception as e:
                logger.error(f"  Erro na query '{query}': {e}")
                continue

            # Pausa entre queries para não ser bloqueado
            await asyncio.sleep(2)

        await browser.close()

    if not dry_run and total > 0 and full_catalog_sync:
        await deactivate_amazon_products(older_than=run_started)

    logger.info(f"\n=== Concluído: {total} produtos coletados de {len(queries)} queries ===")
    return total


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Amazon scraper")
    parser.add_argument("--dry-run", action="store_true", help="Não salva no banco")
    parser.add_argument("--headless", default="true", help="Modo headless (true/false)")
    parser.add_argument("--queries", default=None, help="Queries separadas por vírgula")
    args = parser.parse_args()

    queries = None
    if args.queries:
        queries = [q.strip() for q in args.queries.split(",") if q.strip()]

    headless = args.headless.lower() != "false"

    total = asyncio.run(run_scraper(queries=queries, dry_run=args.dry_run, headless=headless))
    if not args.dry_run and not total:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
