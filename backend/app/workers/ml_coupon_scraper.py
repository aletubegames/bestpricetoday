"""
ml_coupon_scraper.py — Scraper de cupons do portal de afiliados do Mercado Livre.

Navega /afiliados/coupons#hub, gera códigos para todos os cupons disponíveis,
coleta os códigos gerados e salva no banco (tabela coupons).

Fluxo:
1. Login (reusa cookies do ml_scraper)
2. Aba "Cupons disponíveis" — navega todas as páginas
3. Para cada cupom: clica "Gerar código" → digita código custom → confirma
4. Aba "Códigos gerados" — coleta todos os códigos com metadata
5. Salva no banco, marca vencidos como inativos

Uso:
  cd backend && venv/bin/python -m app.workers.ml_coupon_scraper
  cd backend && venv/bin/python -m app.workers.ml_coupon_scraper --max-pages 5
"""
import asyncio
import json
import logging
import random
import re
import string
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger("ml_coupon_scraper")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR.parent.parent
ENV_FILE = BACKEND_DIR / ".env"
COOKIES_FILE = BACKEND_DIR / ".ml_cookies.json"

COUPONS_URL = "https://www.mercadolivre.com.br/afiliados/coupons#hub"
CODE_PREFIX = "ALETUBE"  # prefixo automático do ML para códigos do afiliado


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
    from sqlalchemy import select, delete

    saved = 0
    total_products = 0
    async with AsyncSessionLocal() as db:
        for c in coupons:
            existing = await db.execute(
                select(Coupon).where(Coupon.coupon_code == c["coupon_code"])
            )
            existing = existing.scalar()
            if existing:
                # Atualiza
                existing.discount_text = c.get("discount_text")
                existing.discount_percent = c.get("discount_percent")
                existing.discount_value = c.get("discount_value")
                existing.expires_at = c.get("expires_at")
                existing.budget_remaining = c.get("budget_remaining")
                existing.conditions = c.get("conditions")
                existing.store_name = c.get("store_name")
                existing.product_url = c.get("product_url")
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
                    product_url=c.get("product_url"),
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
                        product_url=p["product_url"],
                        image_url=p.get("image_url"),
                        price=price,
                        ml_code=p.get("ml_code"),
                        is_available=True,
                    ))
                    total_products += 1

            saved += 1
        await db.commit()
    logger.info(f"Salvos {saved} cupons e {total_products} produtos no banco")
    return saved


async def deactivate_expired_coupons():
    """Deleta cupons vencidos do banco (data de vencimento já passou)."""
    from app.db.session import AsyncSessionLocal
    from app.models.models import Coupon
    from sqlalchemy import select, delete

    now = datetime.now(timezone.utc)
    async with AsyncSessionLocal() as db:
        # Deleta cupons vencidos
        result = await db.execute(
            delete(Coupon)
            .where(Coupon.expires_at < now)
        )
        await db.commit()
        count = result.rowcount
        if count:
            logger.info(f"Deletados {count} cupons vencidos")


async def cleanup_expired_coupons():
    """Função standalone para deletar cupons vencidos (chamada via cron)."""
    await deactivate_expired_coupons()


# ── parse helpers ──────────────────────────────────────────────────────────────
def parse_discount(text: str) -> dict:
    """Extrai desconto do texto. '21% OFF' -> {percent: 21}. 'R$ 80 OFF' -> {value: 80}."""
    result = {}
    m = re.search(r"(\d+(?:[.,]\d+)?)\s*%\s*OFF", text, re.I)
    if m:
        result["discount_percent"] = float(m.group(1).replace(",", "."))
        result["discount_text"] = f"{m.group(1)}% OFF"
        return result
    m = re.search(r"R\$\s*(\d+(?:[.,]\d+)?)\s*OFF", text, re.I)
    if m:
        result["discount_value"] = float(m.group(1).replace(".", "").replace(",", "."))
        result["discount_text"] = f"R$ {m.group(1)} OFF"
        return result
    result["discount_text"] = text.strip()
    return result


def parse_expiry(text: str) -> Optional[datetime]:
    """Converte 'Vence em 1 de julho' para datetime.
    Assume ano atual (ou próximo se mês já passou)."""
    text = text.replace("Vence em", "").strip()
    months = {
        "janeiro": 1, "fevereiro": 2, "março": 3, "abril": 4,
        "maio": 5, "junho": 6, "julho": 7, "agosto": 8,
        "setembro": 9, "outubro": 10, "novembro": 11, "dezembro": 12,
    }
    m = re.match(r"(\d+)\s+de\s+(\w+)", text, re.I)
    if not m:
        return None
    day = int(m.group(1))
    month_name = m.group(2).lower()
    month = months.get(month_name)
    if not month:
        return None
    year = datetime.now().year
    dt = datetime(year, month, day, 23, 59, 59, tzinfo=timezone.utc)
    # Se já passou, assume próximo ano
    if dt < datetime.now(timezone.utc):
        dt = datetime(year + 1, month, day, 23, 59, 59, tzinfo=timezone.utc)
    return dt


def parse_budget(text: str) -> Optional[str]:
    """Extrai orçamento restante do texto."""
    m = re.search(r"Orçamento restante:\s*(R\$\s*[\d.,]+)", text, re.I)
    if m:
        return m.group(1).strip()
    return None


def parse_store(text: str) -> Optional[str]:
    """Extrai nome da loja do texto do card."""
    m = re.search(r"Em produtos de\s+(.+?)(?:Ver produtos|Condições|Gerar|$)", text, re.I)
    if m:
        return m.group(1).strip()
    return None


# ── scraper ────────────────────────────────────────────────────────────────────
async def scrape_ml_coupons(page, context=None, max_pages: int = 0) -> List[dict]:
    """Scrapeia cupons do ML. Retorna lista de cupons gerados.

    Args:
        page: página do Playwright já logada
        context: contexto do browser (para abrir novas abas em "Ver produtos")
        max_pages: limite de páginas (0 = todas)
    """
    logger.info(f"Navegando para {COUPONS_URL}")
    await page.goto(COUPONS_URL, wait_until="networkidle", timeout=30000)
    await page.wait_for_timeout(3000)

    # Verifica se está logado
    if "login" in page.url.lower() or "auth" in page.url.lower():
        logger.error("Não está logado — redirecionou para login")
        return []

    # ── FASE 1: Gerar códigos para cupons disponíveis ──
    logger.info("=== FASE 1: Gerando códigos ===")

    # Espera o SPA carregar completamente (a paginação aparece depois)
    logger.info("Esperando SPA carregar...")
    await page.wait_for_timeout(8000)

    # Garante que está na aba "Cupons disponíveis"
    try:
        await page.locator('#coupons-tabs-tab-0').click()
        await page.wait_for_timeout(2000)
    except Exception:
        pass

    total_pages = 1
    try:
        # A paginação mostra: 1 2 3 4 5 6 7 8 9 536 Seguinte
        # Pega o maior numero nos botoes de paginacao
        total_pages = await page.evaluate("""() => {
            const btns = document.querySelectorAll('.andes-pagination__button:not(.andes-pagination__button--back):not(.andes-pagination__button--next) a, .andes-pagination__button--current');
            let max = 0;
            btns.forEach(b => {
                const t = (b.innerText || '').trim();
                const n = parseInt(t);
                if (!isNaN(n) && n > max) max = n;
            });
            return max || 1;
        }""")
    except Exception:
        pass
    logger.info(f"Total de páginas: {total_pages}")

    if max_pages > 0:
        total_pages = min(total_pages, max_pages)
        logger.info(f"Limitando a {total_pages} páginas")

    generated_count = 0
    for page_num in range(1, total_pages + 1):
        logger.info(f"\n--- Página {page_num}/{total_pages} ---")

        if page_num > 1:
            # Clica no botão "Seguinte" com Playwright (JS click não dispara React handlers)
            try:
                is_disabled = await page.evaluate("""() => {
                    const btn = document.querySelector('.andes-pagination__button--next');
                    if (!btn) return true;
                    return btn.classList.contains('andes-pagination__button--disabled') || btn.disabled;
                }""")
                if is_disabled:
                    logger.info("Botão Seguinte disabled — fim das páginas disponíveis")
                    break

                # Playwright click (triggera event handlers do React)
                next_btn = page.locator('.andes-pagination__button--next')
                await next_btn.click(timeout=10000)
                await page.wait_for_timeout(5000)  # 5s entre páginas (humano)

                # Garante que está na aba "Cupons disponíveis"
                await page.locator('#coupons-tabs-tab-0').click()
                await page.wait_for_timeout(3000)
            except Exception as e:
                logger.warning(f"Erro ao paginar: {e}")
                break

        # Processa TODOS os botões habilitados da página.
        # Após gerar um cupom, o botão fica disabled. Re-busca a cada iteração.
        processed = 0
        max_per_page = 50  # safety limit
        while processed < max_per_page:
            # Busca info do primeiro botão habilitado via JS (não clica, só encontra)
            info = await page.evaluate("""() => {
                const btns = document.querySelectorAll('button[data-testid=button-create-action]');
                for (let i = 0; i < btns.length; i++) {
                    const btn = btns[i];
                    if (btn.disabled || btn.classList.contains('andes-button--disabled')) continue;
                    let card = btn.closest('.available-coupon-item');
                    let discText = '', storeName = '', expiryText = '';
                    if (card) {
                        const titleEl = card.querySelector('.available-coupon-item__title');
                        discText = titleEl ? titleEl.innerText.trim() : '';
                        const catEl = card.querySelector('.available-coupon-item__category');
                        storeName = catEl ? catEl.innerText.replace('Em produtos de ', '').trim() : '';
                        const expEl = card.querySelector('.available-coupon-item__expiration span');
                        expiryText = expEl ? expEl.innerText.trim() : '';
                    }
                    return {index: i, total: btns.length, disc: discText, store: storeName, expiry: expiryText};
                }
                return null;
            }""")

            if info is None:
                logger.info(f"  Sem mais botões habilitados na página (processados: {processed})")
                break

            idx = info['index']
            total = info['total']
            disc_text = info['disc']
            store_name = info['store']
            logger.info(f"  Cupom {idx+1}/{total}: {disc_text} — {store_name} ({info['expiry']})")

            # Clica no botão usando Playwright (triggera event handlers corretamente)
            try:
                btn = page.locator('button[data-testid=button-create-action]').nth(idx)
                await btn.click(timeout=10000)
                await page.wait_for_timeout(1500)
            except Exception as e:
                logger.warning(f"  Erro ao clicar no botão {idx+1}: {e}")
                continue

            # Espera modal aparecer
            try:
                await page.wait_for_selector('.generate-code-modal', timeout=8000)
            except Exception:
                logger.warning(f"  Modal não apareceu — pulando")
                continue

            # Digita código aleatório no input do modal
            random_code = ''.join(random.choices(
                string.ascii_uppercase + string.digits, k=6
            ))
            try:
                input_el = page.locator('#generate-code-modal__textfield')
                await input_el.fill(random_code)
                await page.wait_for_timeout(800)
            except Exception as e:
                logger.warning(f"  Erro ao preencher input: {e}")
                await page.evaluate("""() => {
                    document.querySelectorAll('.andes-modal__close-button').forEach(b => b.click());
                }""")
                await page.wait_for_timeout(1000)
                continue

            # Clica em "Gerar código" no modal
            try:
                gen_btn = page.locator('.generate-code-modal button[data-testid=generate-code-modal__button]')
                disabled = await gen_btn.evaluate('el => el.disabled')
                if disabled:
                    logger.info(f"  Botão disabled no modal — pulando")
                    await page.evaluate("""() => {
                        document.querySelectorAll('.andes-modal__close-button').forEach(b => b.click());
                    }""")
                    await page.wait_for_timeout(1000)
                    continue

                await gen_btn.click()
                await page.wait_for_timeout(5000)  # 5s após gerar (comportamento humano)
                generated_count += 1
                processed += 1
                logger.info(f"  ✓ Código gerado: {CODE_PREFIX}{random_code} ({disc_text} — {store_name})")
            except Exception as e:
                logger.warning(f"  Erro ao confirmar: {e}")

            # Fecha todos os modais, overlays e notificações
            try:
                await page.evaluate("""() => {
                    document.querySelectorAll('.andes-modal__close-button').forEach(b => b.click());
                    document.querySelectorAll('.andes-modal__overlay, .andes-mask').forEach(e => e.remove());
                    document.querySelectorAll('.andes-snackbar, .andes-toast, [class*=toast], [class*=notification], [class*=snackbar]').forEach(e => e.remove());
                    document.dispatchEvent(new KeyboardEvent('keydown', {key: 'Escape', keyCode: 27}));
                }""")
                await page.wait_for_timeout(2000)
            except Exception:
                pass

            # Volta pra aba "Cupons disponíveis" (o SPA pode trocar de aba após gerar)
            try:
                await page.evaluate("""() => {
                    const tab = document.querySelector('#coupons-tabs-tab-0');
                    if (tab) tab.click();
                }""")
                await page.wait_for_timeout(3000)
            except Exception:
                pass

            # Delay aleatório extra entre gerações (2-5s) — comportamento humano
            await page.wait_for_timeout(random.randint(2000, 5000))

    logger.info(f"\nTotal de códigos gerados: {generated_count}")

    # ── FASE 2: Coletar códigos gerados ──
    logger.info("\n=== FASE 2: Coletando códigos gerados ===")

    # Vai para aba "Códigos gerados"
    try:
        await page.locator('#coupons-tabs-tab-1').click()
        await page.wait_for_timeout(3000)
    except Exception as e:
        logger.error(f"Erro ao ir para aba Códigos gerados: {e}")
        return []

    all_coupons = []
    seen_codes = set()
    collected_pages = 0

    while True:
        collected_pages += 1
        logger.info(f"  Coletando página {collected_pages} de códigos gerados...")

        # Extrai todos os cupons gerados da página atual
        items = await page.evaluate(r'''() => {
            const cards = document.querySelectorAll('[class*=generated-coupon-item]');
            const results = [];
            for (const card of cards) {
                const text = card.innerText.replace(/\n/g, ' ').replace(/\s+/g, ' ').trim();
                if (text.length > 10) results.push(text);
            }
            return results;
        }''')

        for text in items:
            # Extrai código: "#ALETUBEXXXXXX"
            m = re.search(r"#([A-Z0-9]{6,20})", text)
            if not m:
                continue
            code = m.group(1)
            if code in seen_codes:
                continue
            seen_codes.add(code)

            # Parse metadata
            coupon = {"coupon_code": code}
            coupon.update(parse_discount(text))
            coupon["expires_at"] = parse_expiry(text)
            coupon["budget_remaining"] = parse_budget(text)
            coupon["store_name"] = parse_store(text)

            # Coleta condições clicando no ícone de info do card
            # E coleta produtos da loja clicando em "Ver produtos"
            try:
                # 1. Coleta condições
                conditions = await page.evaluate(r'''(code) => {
                    const cards = document.querySelectorAll('[class*=generated-coupon-item]');
                    for (const card of cards) {
                        if (card.innerText.includes(code)) {
                            const infoIcon = card.querySelector('[data-testid=info-icon]');
                            if (infoIcon) {
                                infoIcon.click();
                                return true;
                            }
                        }
                    }
                    return false;
                }''', code)

                if conditions:
                    await page.wait_for_timeout(1500)
                    cond_text = await page.evaluate(r'''() => {
                        const modal = document.querySelector('.andes-modal:not([style*="display: none"])');
                        if (!modal) return '';
                        const body = modal.querySelector('.andes-modal__body, .andes-modal__content');
                        return (body || modal).innerText.replace(/\n/g, ' ').replace(/\s+/g, ' ').trim();
                    }''')
                    coupon["conditions"] = cond_text if cond_text else None
                    logger.info(f"    Condições: {cond_text[:80]}..." if cond_text else "    Sem condições")

                    # Fecha modal
                    await page.evaluate(r'''() => {
                        document.querySelectorAll('.andes-modal__close-button').forEach(b => b.click());
                    }''')
                    await page.wait_for_timeout(800)
                else:
                    coupon["conditions"] = None

                # 2. Coleta produtos da loja clicando em "Ver produtos"
                # O link abre nova aba com URL: https://lista.mercadolivre.com.br/loja/{NOME_LOJA}/
                # Nessa página, coletamos TODOS os produtos da loja
                coupon["products"] = []
                try:
                    # Clica em "Ver produtos" com Playwright (abre nova aba)
                    ver_link = page.locator(f'[class*=generated-coupon-item]:has-text("{code}") a.generated-coupon-item__link').first
                    if await ver_link.count() > 0:
                        async with context.expect_page(timeout=15000) as new_page_info:
                            await ver_link.click()
                        new_page = await new_page_info.value
                        await new_page.wait_for_timeout(3000)
                        store_url = new_page.url
                        coupon["product_url"] = store_url

                        # Extrai nome da loja da URL
                        m_store = re.search(r'/loja/([^/]+)/?', store_url)
                        if m_store:
                            coupon["store_name"] = m_store.group(1)
                            logger.info(f"    Loja: {m_store.group(1)}")

                        # Coleta produtos da loja (navega até 5 páginas)
                        products_collected = 0
                        for prod_page in range(5):
                            await new_page.wait_for_timeout(2000)
                            prods = await new_page.evaluate(r'''() => {
                                // Seleciona apenas os cards de produto reais
                                const items = document.querySelectorAll('section.poly-card, .ui-search-layout__item, li.ui-search-layout__item');
                                const seen = new Set();
                                const results = [];
                                items.forEach(item => {
                                    const titleEl = item.querySelector('a.poly-component__title, a.ui-search-link__title-card, h3.poly-component__title, h2 a');
                                    if (!titleEl) return;
                                    const title = titleEl.innerText.trim();
                                    const href = titleEl.getAttribute('href') || titleEl.closest('a')?.getAttribute('href') || '';
                                    if (!title || !href) return;
                                    // MLB code
                                    let mlCode = '';
                                    const m = href.match(/(MLB\d+)/);
                                    if (m) mlCode = m[1];
                                    // Dedup por MLB code ou href
                                    const key = mlCode || href;
                                    if (seen.has(key)) return;
                                    seen.add(key);
                                    // Preço — ML estrutura na listagem:
                                    // .poly-price__amount => "R$1.670" ou "R$479" (preço real, sem centavos na listagem)
                                    // .poly-price__current => "R$47924% OFF" (preço+desconto colado — NAO USAR)
                                    // .andes-money-amount--cents => "R$167" (parcela, NAO é o preço — NAO USAR)
                                    // .poly-price__previous => "R$630,33" (preço riscado anterior)
                                    let price = null;
                                    let priceEl = item.querySelector('.poly-price__amount');
                                    if (!priceEl) priceEl = item.querySelector('.poly-price__current');
                                    if (priceEl) {
                                        let priceText = priceEl.textContent.trim();
                                        // Extrai número após R$ — para no primeiro não-dígito (evita pegar "24" do "24% OFF")
                                        const m2 = priceText.match(/R\$\s*(\d{1,3}(?:\.\d{3})*(?:,\d{2})?|\d+(?:,\d{2})?|\d+)/);
                                        if (m2) {
                                            let p = m2[1];
                                            // BR format: "." = thousands, "," = decimal
                                            if (p.includes('.') && p.includes(',')) {
                                                p = p.replace(/\./g, '').replace(',', '.');
                                            } else if (p.includes(',') && !p.includes('.')) {
                                                p = p.replace(',', '.');
                                            } else if (p.includes('.') && !p.includes(',')) {
                                                // "." sem "," — é separador de milhar (ex: "1.670" = 1670)
                                                // Mas se terminar com ".XX" (2 digitos), pode ser decimal
                                                const parts = p.split('.');
                                                if (parts.length === 2 && parts[1].length === 2) {
                                                    // "31.99" → 31.99 (decimal)
                                                } else {
                                                    // "1.670" → 1670 (thousands)
                                                    p = p.replace(/\./g, '');
                                                }
                                            }
                                            price = parseFloat(p) || null;
                                            if (price > 50000 || price < 0.01) price = null;
                                        }
                                    }
                                    // Imagem — tenta vários seletores
                                    let img = '';
                                    const imgEl = item.querySelector('img.poly-component__picture, img[src*="mlstatic.com/D_"], img[data-src*="mlstatic.com/D_"], picture img, figure img');
                                    if (imgEl) {
                                        img = imgEl.getAttribute('src') || imgEl.getAttribute('data-src') || '';
                                    }
                                    // Se não achou, constrói a URL a partir do MLB code
                                    if (!img && mlCode) {
                                        img = `https://http2.mlstatic.com/D_NQ_NP_${mlCode}-MLB.webp`;
                                    }
                                    results.push({title, href, price, img, mlCode});
                                });
                                return results;
                            }''')

                            for p in prods:
                                if p['title'] and p['href']:
                                    coupon["products"].append({
                                        "title": p['title'],
                                        "product_url": p['href'],
                                        "image_url": p['img'] if p['img'] else None,
                                        "price": p['price'],
                                        "ml_code": p['mlCode'] if p['mlCode'] else None,
                                    })
                                    products_collected += 1

                            # Tenta paginar
                            try:
                                next_btn = new_page.locator('.andes-pagination__button--next')
                                if await next_btn.count() > 0:
                                    is_disabled = await next_btn.evaluate('el => el.classList.contains("andes-pagination__button--disabled")')
                                    if is_disabled:
                                        break
                                    await next_btn.click()
                                    await new_page.wait_for_timeout(3000)
                                else:
                                    break
                            except Exception:
                                break

                        logger.info(f"    {products_collected} produtos coletados da loja")
                        await new_page.close()
                        await page.wait_for_timeout(2000)

                except Exception as e:
                    logger.debug(f"    Erro ao coletar produtos da loja: {e}")

            except Exception as e:
                logger.debug(f"    Erro ao coletar condições: {e}")
                coupon["conditions"] = None

            all_coupons.append(coupon)

        logger.info(f"  {len(items)} items na página, {len(all_coupons)} total")

        # Tenta paginar
        try:
            next_btn = page.locator('[class*=generated] .andes-pagination__button--next, [role=tabpanel] .andes-pagination__button--next')
            if await next_btn.count() > 0:
                disabled = await next_btn.evaluate('el => el.disabled || el.classList.contains("andes-pagination__button--disabled")')
                if disabled:
                    logger.info("  Sem mais páginas")
                    break
                await next_btn.click()
                await page.wait_for_timeout(2000)
            else:
                logger.info("  Sem botão de paginação")
                break
        except Exception:
            break

        if collected_pages >= 50:  # safety limit
            break

    logger.info(f"\nTotal de cupons coletados: {len(all_coupons)}")
    return all_coupons


# ── main ───────────────────────────────────────────────────────────────────────
async def run(max_pages: int = 0, headless: bool = True, collect_only: bool = False):
    """Executa o scraper de cupons do ML."""
    from playwright.async_api import async_playwright

    env = load_env()
    email = env.get("ML_AFFILIATE_EMAIL", "")
    password = env.get("ML_AFFILIATE_PASSWORD", "")

    async with async_playwright() as p:
        chromium_path = None
        for path in ["/usr/bin/chromium-browser", "/usr/bin/chromium", "/usr/bin/google-chrome"]:
            if Path(path).exists():
                chromium_path = path
                break

        launch_kwargs = {
            "headless": headless,
            "args": ["--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage"],
        }
        if chromium_path:
            launch_kwargs["executable_path"] = chromium_path

        browser = await p.chromium.launch(**launch_kwargs)
        context = await browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        )

        if COOKIES_FILE.exists():
            try:
                cookies = json.loads(COOKIES_FILE.read_text())
                await context.add_cookies(cookies)
                logger.info(f"Cookies carregados: {len(cookies)}")
            except Exception as e:
                logger.warning(f"Erro ao carregar cookies: {e}")

        page = await context.new_page()

        # Vai direto pra pagina de coupons (não precisa passar pela principal)
        await page.goto(COUPONS_URL, wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(8000)  # espera SPA carregar

        if "login" in page.url.lower() or "auth" in page.url.lower():
            logger.error("Cookies expirados — rode ml_scraper --login primeiro")
            await browser.close()
            return []

        if collect_only:
            # Só Fase 2: coleta cupons já gerados (sem gerar novos)
            logger.info("=== MODO COLLECT-ONLY: pulando Fase 1 ===")
            # Vai direto pra aba "Códigos gerados"
            try:
                await page.locator('#coupons-tabs-tab-1').click()
                await page.wait_for_timeout(3000)
            except Exception as e:
                logger.error(f"Erro ao ir para aba Códigos gerados: {e}")
                await browser.close()
                return []

            # Reutiliza a lógica de coleta da Fase 2
            all_coupons = []
            seen_codes = set()
            collected_pages = 0

            while True:
                collected_pages += 1
                logger.info(f"  Coletando página {collected_pages} de códigos gerados...")

                items = await page.evaluate(r'''() => {
                    const cards = document.querySelectorAll('[class*=generated-coupon-item]');
                    const results = [];
                    for (const card of cards) {
                        const text = card.innerText.replace(/\n/g, ' ').replace(/\s+/g, ' ').trim();
                        if (text.length > 10) results.push(text);
                    }
                    return results;
                }''')

                for text in items:
                    m = re.search(r"#([A-Z0-9]{6,20})", text)
                    if not m:
                        continue
                    code = m.group(1)
                    if code in seen_codes:
                        continue
                    seen_codes.add(code)

                    coupon = {"coupon_code": code}
                    coupon.update(parse_discount(text))
                    coupon["expires_at"] = parse_expiry(text)
                    coupon["budget_remaining"] = parse_budget(text)
                    coupon["store_name"] = parse_store(text)
                    coupon["products"] = []

                    # Coleta condições
                    try:
                        conditions = await page.evaluate(r'''(code) => {
                            const cards = document.querySelectorAll('[class*=generated-coupon-item]');
                            for (const card of cards) {
                                if (card.innerText.includes(code)) {
                                    const infoIcon = card.querySelector('[data-testid=info-icon]');
                                    if (infoIcon) { infoIcon.click(); return true; }
                                }
                            }
                            return false;
                        }''', code)

                        if conditions:
                            await page.wait_for_timeout(1500)
                            cond_text = await page.evaluate(r'''() => {
                                const modal = document.querySelector('.andes-modal:not([style*="display: none"])');
                                if (!modal) return '';
                                const body = modal.querySelector('.andes-modal__body, .andes-modal__content');
                                return (body || modal).innerText.replace(/\n/g, ' ').replace(/\s+/g, ' ').trim();
                            }''')
                            coupon["conditions"] = cond_text if cond_text else None
                            await page.evaluate(r'''() => {
                                document.querySelectorAll('.andes-modal__close-button').forEach(b => b.click());
                            }''')
                            await page.wait_for_timeout(800)
                        else:
                            coupon["conditions"] = None
                    except Exception:
                        coupon["conditions"] = None

                    # Coleta produtos da loja
                    try:
                        ver_link = page.locator(f'[class*=generated-coupon-item]:has-text("{code}") a.generated-coupon-item__link').first
                        if await ver_link.count() > 0:
                            async with context.expect_page(timeout=15000) as new_page_info:
                                await ver_link.click()
                            new_page = await new_page_info.value
                            await new_page.wait_for_timeout(3000)
                            store_url = new_page.url
                            coupon["product_url"] = store_url

                            m_store = re.search(r'/loja/([^/]+)/?', store_url)
                            if m_store:
                                coupon["store_name"] = m_store.group(1)
                                logger.info(f"    Loja: {m_store.group(1)}")

                            # Coleta produtos (até 5 páginas)
                            products_collected = 0
                            for prod_page in range(5):
                                await new_page.wait_for_timeout(2000)
                                prods = await new_page.evaluate(r'''() => {
                                    const items = document.querySelectorAll('section.poly-card, .ui-search-layout__item, li.ui-search-layout__item');
                                    const seen = new Set();
                                    const results = [];
                                    items.forEach(item => {
                                        const titleEl = item.querySelector('a.poly-component__title, a.ui-search-link__title-card, h3.poly-component__title, h2 a');
                                        if (!titleEl) return;
                                        const title = titleEl.innerText.trim();
                                        const href = titleEl.getAttribute('href') || titleEl.closest('a')?.getAttribute('href') || '';
                                        if (!title || !href) return;
                                        let mlCode = '';
                                        const m = href.match(/(MLB\d+)/);
                                        if (m) mlCode = m[1];
                                        const key = mlCode || href;
                                        if (seen.has(key)) return;
                                        seen.add(key);
                                        let price = null;
                                        let priceEl = item.querySelector('.poly-price__amount');
                                        if (!priceEl) priceEl = item.querySelector('.poly-price__current');
                                        if (priceEl) {
                                            let priceText = priceEl.textContent.trim();
                                            const m2 = priceText.match(/R\$\s*(\d{1,3}(?:\.\d{3})*(?:,\d{2})?|\d+(?:,\d{2})?|\d+)/);
                                            if (m2) {
                                                let p = m2[1];
                                                if (p.includes('.') && p.includes(',')) {
                                                    p = p.replace(/\./g, '').replace(',', '.');
                                                } else if (p.includes(',') && !p.includes('.')) {
                                                    p = p.replace(',', '.');
                                                } else if (p.includes('.') && !p.includes(',')) {
                                                    const parts = p.split('.');
                                                    if (parts.length === 2 && parts[1].length === 2) {
                                                        // decimal
                                                    } else {
                                                        p = p.replace(/\./g, '');
                                                    }
                                                }
                                                price = parseFloat(p) || null;
                                                if (price > 50000 || price < 0.01) price = null;
                                            }
                                        }
                                        let img = '';
                                        const imgEl = item.querySelector('img.poly-component__picture, img[src*="mlstatic.com/D_"], img[data-src*="mlstatic.com/D_"], picture img, figure img');
                                        if (imgEl) {
                                            img = imgEl.getAttribute('src') || imgEl.getAttribute('data-src') || '';
                                        }
                                        if (!img && mlCode) {
                                            img = `https://http2.mlstatic.com/D_NQ_NP_${mlCode}-MLB.webp`;
                                        }
                                        results.push({title, href, price, img, mlCode});
                                    });
                                    return results;
                                }''')

                                for pr in prods:
                                    if pr['title'] and pr['href']:
                                        coupon["products"].append({
                                            "title": pr['title'],
                                            "product_url": pr['href'],
                                            "image_url": pr['img'] if pr['img'] else None,
                                            "price": pr['price'],
                                            "ml_code": pr['mlCode'] if pr['mlCode'] else None,
                                        })
                                        products_collected += 1

                                try:
                                    next_btn = new_page.locator('.andes-pagination__button--next')
                                    if await next_btn.count() > 0:
                                        is_disabled = await next_btn.evaluate('el => el.classList.contains("andes-pagination__button--disabled")')
                                        if is_disabled:
                                            break
                                        await next_btn.click()
                                        await new_page.wait_for_timeout(3000)
                                    else:
                                        break
                                except Exception:
                                    break

                            logger.info(f"    {products_collected} produtos coletados da loja")
                            await new_page.close()
                            await page.wait_for_timeout(2000)
                    except Exception as e:
                        logger.debug(f"    Erro ao coletar produtos: {e}")

                    all_coupons.append(coupon)
                    # Salva incrementalmente (não perde dados se for interrompido)
                    try:
                        await save_coupons([coupon])
                    except Exception as e:
                        logger.debug(f"    Erro ao salvar incremental: {e}")

                logger.info(f"  {len(items)} items na página, {len(all_coupons)} total")

                # Tenta paginar
                try:
                    next_btn = page.locator('[class*=generated] .andes-pagination__button--next, [role=tabpanel] .andes-pagination__button--next')
                    if await next_btn.count() > 0:
                        disabled = await next_btn.evaluate('el => el.disabled || el.classList.contains("andes-pagination__button--disabled")')
                        if disabled:
                            logger.info("  Sem mais páginas")
                            break
                        await next_btn.click()
                        await page.wait_for_timeout(2000)
                    else:
                        logger.info("  Sem botão de paginação")
                        break
                except Exception:
                    break

                if collected_pages >= 50:
                    break

            coupons = all_coupons
        else:
            # Modo normal: Fase 1 (gerar) + Fase 2 (coletar)
            coupons = await scrape_ml_coupons(page, context=context, max_pages=max_pages)

        # Salva no banco
        if coupons:
            await save_coupons(coupons)

        # Desativa vencidos
        await deactivate_expired_coupons()

        await browser.close()

    logger.info(f"\n{'='*60}")
    logger.info(f"SCRAPING DE CUPONS CONCLUÍDO: {len(coupons)} cupons")
    logger.info(f"{'='*60}")
    return coupons


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Scraper de cupons do ML")
    parser.add_argument("--max-pages", type=int, default=0, help="Limite de páginas (0 = todas)")
    parser.add_argument("--headless", type=bool, default=True, help="Headless mode")
    parser.add_argument("--cleanup-only", action="store_true", help="Apenas deleta cupons vencidos")
    parser.add_argument("--collect-only", action="store_true", help="Só coleta cupons já gerados (sem gerar novos)")
    args = parser.parse_args()

    if args.cleanup_only:
        asyncio.run(cleanup_expired_coupons())
        sys.exit(0)

    result = asyncio.run(run(max_pages=args.max_pages, headless=args.headless, collect_only=args.collect_only))
    sys.exit(0 if result else 1)
