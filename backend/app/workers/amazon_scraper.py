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
import sys
import json
import logging
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger("amazon_scraper")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

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

            count += 1
            logger.info(f"    [{count}] R$ {price:>10.2f}  {title[:60]}")

            if not dry_run:
                await save_single_product(produto, provider="amazon")

        except Exception as e:
            logger.debug(f"    Erro ao processar card: {e}")
            continue

    logger.info(f"  Query '{query}': {count} produtos coletados")
    return count


async def save_single_product(r: dict, provider: str = "amazon") -> bool:
    """Salva UM produto no banco (upsert). Retorna True se salvou."""
    try:
        from app.db.session import AsyncSessionLocal
        from app.models.models import AffiliateProduct
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

            await db.commit()
            return True
    except Exception as e:
        logger.warning(f"  Erro ao salvar produto: {e}")
        return False


async def run_scraper(queries: list[str] = None, dry_run: bool = False, headless: bool = True):
    """Executa o scraper completo."""
    from playwright.async_api import async_playwright

    env = load_env()
    partner_tag = env.get("AMAZON_PARTNER_TAG", "aletubegames-20")

    if not partner_tag:
        logger.error("AMAZON_PARTNER_TAG não configurado no .env")
        return

    if queries is None:
        queries = DEFAULT_QUERIES

    logger.info(f"=== Amazon Scraper ===")
    logger.info(f"Partner tag: {partner_tag}")
    logger.info(f"Queries: {len(queries)}")
    logger.info(f"Dry run: {dry_run}")
    logger.info(f"Headless: {headless}")

    total = 0
    async with async_playwright() as p:
        # Usa chromium do sistema (channel) em vez do bundled playwright
        try:
            browser = await p.chromium.launch(headless=headless, channel="chromium")
        except Exception:
            try:
                browser = await p.chromium.launch(
                    headless=headless,
                    executable_path="/usr/bin/chromium-browser",
                    args=["--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage"],
                )
            except Exception:
                browser = await p.chromium.launch(
                    headless=headless,
                    args=["--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage"],
                )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
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

    asyncio.run(run_scraper(queries=queries, dry_run=args.dry_run, headless=headless))


if __name__ == "__main__":
    main()
