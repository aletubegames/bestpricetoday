"""
ml_scraper.py — Scraper do portal de afiliados do Mercado Livre.

Faz login, navega por todas as categorias, coleta produtos com links de afiliado
e atualiza a tabela affiliate_products no banco de dados.

Uso:
  cd backend && venv/bin/python -m app.workers.ml_scraper
  cd backend && venv/bin/python -m app.workers.ml_scraper --dry-run
  cd backend && venv/bin/python -m app.workers.ml_scraper --headless=false  # debug

Requer:
  playwright (pip install playwright)
  chromium-browser instalado no sistema

Variáveis no .env:
  ML_AFFILIATE_EMAIL=seu@email.com
  ML_AFFILIATE_PASSWORD=sua_senha
"""

import asyncio
import fcntl
import os
import random
import re
import shutil
import sys
import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger("ml_scraper")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# ── paths ─────────────────────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR.parent.parent
ENV_FILE = BACKEND_DIR / ".env"

# Estado de sessão (cookies) — backup/legado, mantido para compatibilidade
COOKIES_FILE = BACKEND_DIR / ".ml_cookies.json"
STORAGE_STATE_FILE = BACKEND_DIR / ".ml_storage_state.json"

# Perfil persistente do Chromium — mantém TODO o estado do navegador entre
# execuções (cookies, localStorage, IndexedDB, cache, histórico, service workers).
# É como um Chrome normal que você usa todo dia — o ML não detecta como "perfil novo".
# Substitui o approach de storage_state (cookies JSON) que durava ~7 dias.
PROFILE_DIR = BACKEND_DIR / ".ml_chrome_profile"

# Lock compartilhado entre scraper e session keeper (não podem usar o mesmo perfil ao mesmo tempo)
PROFILE_LOCK_FILE = BACKEND_DIR / ".ml_chrome_profile.lock"

# Checkpoint — salva progresso para retomar de onde parou
CHECKPOINT_FILE = BACKEND_DIR / ".ml_scraper_checkpoint.json"

PORTAL_URL = "https://www.mercadolivre.com.br/afiliados/hub#menu-lateral"
LOGIN_URL = "https://www.mercadolivre.com.br/afiliados/hub#menu-lateral"


# ── profile lock ──────────────────────────────────────────────────────────────
class ProfileLock:
    """Lock compartilhado entre scraper e session keeper.
    Chromium não permite dois processos no mesmo user_data_dir."""
    def __init__(self, path: Path):
        self.path = path
        self.fd = None

    def acquire(self, timeout: int = 60) -> bool:
        self.fd = open(self.path, "w")
        elapsed = 0
        while True:
            try:
                fcntl.flock(self.fd.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                self.fd.write(str(os.getpid()))
                self.fd.flush()
                return True
            except (IOError, OSError):
                if elapsed >= timeout:
                    self.fd.close()
                    self.fd = None
                    return False
                time.sleep(5)
                elapsed += 5

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


def backup_storage_state():
    """Guarda backup rotativo do storage_state antes de sobrescrever."""
    if not STORAGE_STATE_FILE.exists():
        return
    for i in range(2, 0, -1):
        src = BACKEND_DIR / f".ml_storage_state.json.bak.{i}"
        dst = BACKEND_DIR / f".ml_storage_state.json.bak.{i+1}"
        if src.exists():
            try:
                shutil.move(str(src), str(dst))
            except Exception:
                pass
    try:
        shutil.copy(str(STORAGE_STATE_FILE), str(BACKEND_DIR / ".ml_storage_state.json.bak.1"))
    except Exception as e:
        logger.warning(f"Backup storage_state falhou: {e}")


def cleanup_chrome_singleton_lock():
    """Remove arquivos de lock do Chromium no perfil persistente."""
    removed = []
    for name in ("SingletonLock", "SingletonCookie", "SingletonSocket"):
        p = PROFILE_DIR / name
        if p.exists():
            try:
                if p.is_symlink() or p.is_file():
                    p.unlink()
                else:
                    shutil.rmtree(p, ignore_errors=True)
                removed.append(name)
            except Exception as e:
                logger.warning(f"Não conseguiu remover {name}: {e}")
    if removed:
        logger.info(f"Removido lock do Chrome: {', '.join(removed)}")


# ── checkpoint ────────────────────────────────────────────────────────────────
def load_checkpoint() -> dict:
    """Carrega checkpoint. Retorna {'category_index': int} ou vazio."""
    if CHECKPOINT_FILE.exists():
        try:
            return json.loads(CHECKPOINT_FILE.read_text())
        except Exception:
            pass
    return {}


def save_checkpoint(category_index: int):
    """Salva índice da categoria atual no checkpoint."""
    try:
        CHECKPOINT_FILE.write_text(json.dumps({"category_index": category_index}))
    except Exception as e:
        logger.warning(f"Erro ao salvar checkpoint: {e}")


def clear_checkpoint():
    """Remove checkpoint após conclusão."""
    try:
        CHECKPOINT_FILE.unlink(missing_ok=True)
    except Exception:
        pass


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


# ── parsing helpers ───────────────────────────────────────────────────────────
def parse_price(raw: str) -> Optional[float]:
    """Extrai float de 'R$ 1.998 9% OFF' -> 1998.0"""
    if not raw:
        return None
    m = re.search(r"R\$\s*([\d.,]+)", raw)
    if not m:
        return None
    num = m.group(1)
    if "." in num and "," in num:
        num = num.replace(".", "").replace(",", ".")
    elif "." in num and "," not in num:
        parts = num.split(".")
        if len(parts[-1]) == 3 and len(parts) == 2:
            num = num.replace(".", "")
    try:
        return round(float(num), 2)
    except ValueError:
        return None


def parse_commission(raw: str) -> Optional[float]:
    """Extrai '15%' -> 15.0, 'GANHOS 16%' -> 16.0"""
    if not raw:
        return None
    m = re.search(r"([\d.,]+)\s*%", raw)
    if not m:
        return None
    try:
        return float(m.group(1).replace(",", "."))
    except ValueError:
        return None


def parse_rating(raw: str) -> Optional[float]:
    if not raw:
        return None
    m = re.search(r"([\d.,]+)", raw)
    if not m:
        return None
    try:
        return float(m.group(1).replace(",", "."))
    except ValueError:
        return None


def parse_sold_count(raw: str) -> Optional[int]:
    if not raw:
        return None
    text = raw.lower().replace(".", "")
    m = re.search(r"(\d+)\s*mil", text)
    if m:
        return int(m.group(1)) * 1000
    m = re.search(r"(\d+)", text)
    if m:
        return int(m.group(1))
    return None


# Fila global de links de afiliado capturados pela API createLink
affiliate_links_queue = []


# ── scraper ───────────────────────────────────────────────────────────────────
async def scrape_category(page, category_name: str, dry_run: bool = False) -> int:
    """Scrapeia a categoria atualmente aberta na página. Salva cada item no banco imediatamente.
    Retorna número de produtos coletados."""
    count = 0
    vistos = set()
    sem_novos = 0

    logger.info(f"  Scraping categoria: {category_name}")

    while sem_novos < 8:
        # Espera os cards carregarem
        await page.wait_for_timeout(1500)

        try:
            cards = await page.query_selector_all(".poly-card__content")
        except Exception as e:
            logger.warning(f"  Página navegou durante scrape: {e}")
            await page.wait_for_timeout(3000)
            continue
        novos = 0

        for card in cards:
            try:
                nome_el = await card.query_selector("a.poly-component__title")
                nome = (await nome_el.inner_text()).strip() if nome_el else ""
                if not nome or nome in vistos:
                    continue
                vistos.add(nome)
                novos += 1

                # Pega link direto do produto (href do <a> do título)
                link_prod = ""
                codigo_ml = ""
                seller_name = ""
                if nome_el:
                    href = await nome_el.get_attribute("href") or ""
                    if href:
                        if href.startswith("/"):
                            href = "https://www.mercadolivre.com.br" + href
                        link_prod = href
                        # Extrai código MLB do link
                        m = re.search(r"(MLB\d+)", href)
                        if m:
                            codigo_ml = m.group(1)

                # Tenta pegar o nome do vendedor/loja do card
                # ML mostra "por {NOME_LOJA}" ou link da loja no card
                try:
                    seller_el = await card.query_selector("a.poly-component__seller, [class*=seller], .poly-component__store")
                    if seller_el:
                        seller_name = (await seller_el.inner_text()).strip()
                        # Remove "por " ou "Loja " do início
                        seller_name = re.sub(r"^(por\s+|Loja\s+|Vendido por\s+)", "", seller_name, flags=re.I)
                except Exception:
                    pass

                # Se não achou no card, tenta extrair da URL do produto
                if not seller_name and link_prod:
                    # ML às vezes tem /loja/{NOME}/ na URL do produto
                    m_seller = re.search(r"/loja/([^/]+)/?", link_prod)
                    if m_seller:
                        seller_name = m_seller.group(1)

                # Scrolla até o card
                await card.scroll_into_view_if_needed()
                await page.wait_for_timeout(300)

                badge_el = await card.query_selector(".poly-component__highlight")
                badge = (await badge_el.inner_text()).strip() if badge_el else ""

                avaliacao_el = await card.query_selector(".poly-phrase-label.poly-fs-xs.poly-fw-regular")
                avaliacao = (await avaliacao_el.inner_text()).strip() if avaliacao_el else ""

                vendidos_el = await card.query_selector(".poly-phrase-label.poly-fs-xs:not(.poly-fw-regular)")
                vendidos = (await vendidos_el.inner_text()).strip() if vendidos_el else ""
                vendidos = re.sub(r"^\|\s*\+?", "", vendidos).strip()

                ganhos_el = await card.query_selector(".poly-component__label.poly-fw-semibold")
                ganhos = (await ganhos_el.inner_text()).strip() if ganhos_el else ""

                preco_el = await card.query_selector(".poly-price__current")
                preco = (await preco_el.inner_text()).replace("\n", " ").strip() if preco_el else ""

                parcelas_el = await card.query_selector(".poly-price__installments")
                parcelas = (await parcelas_el.inner_text()).replace("\n", " ").strip() if parcelas_el else ""

                desconto_el = await card.query_selector("[class*='discount__amount'], .poly-price__original")
                desconto = (await desconto_el.inner_text()).replace("\n", " ").strip() if desconto_el else ""

                # Captura URL da imagem (não baixa, só a URL do ML)
                # A imagem está no elemento pai (li.poly-card), não no .poly-card__content
                image_url = ""
                # Método 1: busca img.poly-component__picture dentro do card
                img_el = await card.query_selector("img.poly-component__picture")
                if not img_el:
                    # Método 2: busca no elemento pai via evaluate_handle
                    parent_handle = await card.evaluate_handle("el => el.closest('li.poly-card, .poly-card, article')")
                    if parent_handle:
                        img_el = await parent_handle.query_selector("img.poly-component__picture")
                if not img_el:
                    # Método 3: qualquer img com mlstatic dentro do card
                    img_el = await card.query_selector("img[src*='mlstatic.com/D_']")
                if img_el:
                    image_url = await img_el.get_attribute("src") or ""
                    if image_url and image_url.startswith("//"):
                        image_url = "https:" + image_url

                # Tenta abrir o modal de compartilhar para pegar link de afiliado (meli.la)
                affiliate_link = ""
                # Limpa a fila antes de clicar (para pegar só o link deste produto)
                before_count = len(affiliate_links_queue)
                share_btn = await card.query_selector(".andes-button--quiet")
                if share_btn:
                    try:
                        await share_btn.scroll_into_view_if_needed()
                        await share_btn.click()
                        await page.wait_for_timeout(2000)

                        # Espera o link aparecer na fila (interceptado pela API createLink)
                        for _ in range(15):
                            if len(affiliate_links_queue) > before_count:
                                affiliate_link = affiliate_links_queue[before_count]
                                break
                            await page.wait_for_timeout(500)

                        # Fecha modal
                        close_btn = await page.query_selector(".andes-modal__close, [aria-label='Fechar']")
                        if close_btn:
                            await close_btn.click()
                        await page.wait_for_timeout(300)
                    except Exception as e:
                        logger.debug(f"  Modal share falhou: {e}")

                # SÓ usa link de afiliado (meli.la). Se não conseguiu, PULA o produto.
                if not affiliate_link:
                    logger.debug(f"    Sem link meli.la — pulando: {nome[:40]}")
                    continue

                produto = {
                    "nome": nome,
                    "badge": badge,
                    "preco": preco,
                    "parcelas": parcelas,
                    "desconto": desconto,
                    "ganhos": ganhos,
                    "avaliacao": avaliacao,
                    "vendidos": vendidos,
                    "link_prod": affiliate_link,
                    "Codigo_ML": codigo_ml,
                    "categoria": category_name,
                    "image_url": image_url,
                    "seller_name": seller_name,
                }

                count += 1
                logger.info(f"    [{count}] {nome[:60]}")

                # SALVA IMEDIATAMENTE no banco (não espera terminar)
                if not dry_run and affiliate_link:
                    await save_single_product(produto)

            except Exception as e:
                logger.warning(f"    Erro ao processar card: {e}")
                continue

        sem_novos = sem_novos + 1 if novos == 0 else 0
        await page.evaluate("window.scrollBy(0, 800)")
        await page.wait_for_timeout(1500)

    logger.info(f"  Categoria {category_name}: {count} produtos coletados")
    return count


async def get_categories(page) -> list:
    """Extrai categorias do HTML da página (JSON embutido em filters)."""
    try:
        html = await page.content()
        # Procura o bloco filters no JSON embutido
        m = re.search(r'"filters":\[(\{[^]]+)\]', html)
        if not m:
            logger.warning("Bloco filters não encontrado no HTML")
            return []
        block = m.group(1)
        cats = re.findall(r'"id":"(MLB\d+)","name":"([^"]+)"', block)
        logger.info(f"Categorias encontradas: {len(cats)}")
        for i, (cid, name) in enumerate(cats):
            logger.info(f"  {i}: {cid} → {name}")
        return cats  # lista de tuplas (id, name)
    except Exception as e:
        logger.error(f"Erro ao obter categorias: {e}")
        return []


async def select_category(page, cat_id: str, cat_name: str) -> bool:
    """Seleciona uma categoria no dropdown #category. Retorna True se sucesso."""
    try:
        # Abre o dropdown de categorias
        cat_btn = await page.query_selector("#category")
        if not cat_btn:
            logger.warning(f"  Botão #category não encontrado")
            return False
        await cat_btn.click()
        await page.wait_for_timeout(1500)

        # Procura a opção pelo texto da categoria
        option = await page.query_selector(f"text={cat_name}")
        if option:
            await option.click()
            await page.wait_for_timeout(3000)
            logger.info(f"  Categoria selecionada: {cat_name}")
            return True
        else:
            # Fallback: procura por data-id
            option = await page.query_selector(f"[data-id='{cat_id}']")
            if option:
                await option.click()
                await page.wait_for_timeout(3000)
                logger.info(f"  Categoria selecionada (por id): {cat_name}")
                return True
            logger.warning(f"  Opção '{cat_name}' não encontrada no dropdown")
            await page.keyboard.press("Escape")
            return False
    except Exception as e:
        logger.error(f"  Erro ao selecionar categoria {cat_name}: {e}")
        return False


async def toggle_extra_commission(page) -> bool:
    """Ativa o filtro 'Ganhos extras' (#extra_commission)."""
    try:
        btn = await page.query_selector("#extra_commission")
        if not btn:
            logger.warning("Botão #extra_commission não encontrado")
            return False
        # Verifica se já está ativo
        pressed = await btn.get_attribute("aria-pressed")
        if pressed == "true":
            logger.info("Filtro 'Ganhos extras' já estava ativo")
            return True
        await btn.click()
        await page.wait_for_timeout(2000)
        logger.info("Filtro 'Ganhos extras' ativado")
        return True
    except Exception as e:
        logger.warning(f"Erro ao ativar Ganhos extras: {e}")
        return False


async def login(page, email: str, password: str, headless: bool) -> bool:
    """Faz login no ML. Retorna True se sucesso."""
    logger.info("Navegando para o portal de afiliados...")

    # Navega para o portal de afiliados
    await page.goto(PORTAL_URL, wait_until="domcontentloaded", timeout=30000)
    await page.wait_for_timeout(3000)

    # Verifica se já está logado (cookies salvos funcionam)
    if "afiliados" in page.url and "login" not in page.url.lower():
        logger.info(f"Já estava logado (sessão ativa via cookies) — URL: {page.url}")
        return True

    if not headless:
        # Modo interativo: usuário faz login manualmente (email + senha + 2FA)
        logger.info("=" * 60)
        logger.info("MODO LOGIN MANUAL")
        logger.info("1. Faça login no ML (email, senha, 2FA)")
        logger.info("2. Aguarde até chegar na página de afiliados")
        logger.info("Aguardando até 5 minutos...")
        logger.info("=" * 60)

        for i in range(300):
            try:
                await page.wait_for_timeout(1000)
                url = page.url.lower()
                # Detecta login quando URL contém "afiliados" e não tem "login"
                if "afiliados" in url and "login" not in url and "auth" not in url:
                    logger.info(f"Login detectado! URL: {page.url}")
                    await page.wait_for_timeout(3000)
                    return True
            except Exception:
                # Página pode ter navegado
                await page.wait_for_timeout(2000)
                continue

        logger.error("Timeout: login não completado em 5 minutos")
        return False
    else:
        # Headless: só funciona se cookies válidos
        logger.error("Cookies expirados. Rode com --login para refazer login manual.")
        return False


async def run_scraper(headless: bool = True, dry_run: bool = False) -> int:
    """Executa o scraper completo. Retorna total de produtos coletados."""
    env = load_env()
    email = env.get("ML_AFFILIATE_EMAIL", "")
    password = env.get("ML_AFFILIATE_PASSWORD", "")

    # Se não tem credenciais mas tem cookies, tenta usar cookies
    has_cookies = COOKIES_FILE.exists() and COOKIES_FILE.stat().st_size > 10
    if not email or not password:
        if has_cookies:
            logger.info("Sem email/senha no .env — usando cookies salvos")
        else:
            logger.error("ML_AFFILIATE_EMAIL e ML_AFFILIATE_PASSWORD não configurados e sem cookies. Rode com --login primeiro.")
            return 0

    try:
        from playwright.async_api import async_playwright
    except ImportError:
        logger.error("Playwright não instalado. Rode: pip install playwright")
        return 0

    all_produtos = []
    total_count = 0

    # Carrega checkpoint (para retomar de onde parou)
    checkpoint = load_checkpoint()
    start_category = checkpoint.get("category_index", 0)
    if start_category > 0:
        logger.info(f"RETOMANDO do checkpoint: categoria {start_category}")

    # Adquire lock do perfil persistente (compartilhado com session keeper)
    profile_lock = ProfileLock(PROFILE_LOCK_FILE)
    if not profile_lock.acquire():
        holder = ""
        try:
            if PROFILE_LOCK_FILE.exists():
                holder = f" (PID {PROFILE_LOCK_FILE.read_text().strip()})"
        except Exception:
            pass
        logger.error(f"Perfil Chromium em uso por outro processo{holder}. Tente novamente mais tarde.")
        return 0

    # Migração: se o perfil persistente não existe mas tem storage_state antigo,
    # copia o storage_state para o perfil na primeira execução
    if not PROFILE_DIR.exists() and STORAGE_STATE_FILE.exists():
        logger.info("Migrando storage_state legado para perfil persistente...")

    PROFILE_DIR.mkdir(parents=True, exist_ok=True)

    # Limpa lock do Chrome e faz backup do storage_state antes de usar
    cleanup_chrome_singleton_lock()
    backup_storage_state()

    async with async_playwright() as p:
        # Detecta chromium disponível: sistema (servidor) ou playwright (local)
        chromium_path = None
        for path in ["/usr/bin/chromium-browser", "/usr/bin/chromium", "/usr/bin/google-chrome"]:
            if Path(path).exists():
                chromium_path = path
                break

        # launch_persistent_context mantém TODO o estado do navegador em disco
        # (cookies, localStorage, IndexedDB, cache, histórico, service workers).
        # O ML vê um usuário estabelecido, não um "perfil novo" a cada execução.
        persistent_kwargs = {
            "user_data_dir": str(PROFILE_DIR),
            "headless": headless,
            "viewport": {"width": 1280, "height": 800},
            "user_agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "locale": "pt-BR",
            "timezone_id": "America/Sao_Paulo",
            "args": [
                "--no-sandbox",
                "--disable-gpu",
                "--disable-dev-shm-usage",
                "--disable-blink-features=AutomationControlled",
                "--disable-features=IsolateOrigins,site-per-process",
                "--disable-infobars",
                "--disable-notifications",
            ],
        }
        if chromium_path:
            persistent_kwargs["executable_path"] = chromium_path
            logger.info(f"Usando chromium do sistema: {chromium_path}")
        else:
            logger.info("Usando chromium do playwright")

        logger.info(f"Perfil persistente: {PROFILE_DIR}")
        context = await p.chromium.launch_persistent_context(**persistent_kwargs)

        # Migração: se é primeira execução do perfil e tem storage_state legado,
        # carrega os cookies antigos no perfil novo
        if STORAGE_STATE_FILE.exists() and not (PROFILE_DIR / "Default" / "Cookies").exists():
            try:
                cookies = json.loads(COOKIES_FILE.read_text()) if COOKIES_FILE.exists() else []
                if cookies:
                    await context.add_cookies(cookies)
                    logger.info(f"Migração: {len(cookies)} cookies legados carregados no perfil persistente")
            except Exception as e:
                logger.warning(f"Migração: erro ao carregar cookies legados: {e}")

        page = await context.new_page()

        # Aplica stealth para evitar detecção de automation
        try:
            from playwright_stealth import Stealth
            await Stealth(
                navigator_user_agent_override=persistent_kwargs["user_agent"],
                navigator_languages_override=("pt-BR", "pt"),
                navigator_platform_override="Linux x86_64",
            ).apply_stealth_async(page)
            logger.info("Stealth aplicado na página")
        except Exception as e:
            logger.warning(f"Não foi possível aplicar stealth: {e}")

        # Intercepta a API createLink para capturar links de afiliado (meli.la)
        global affiliate_links_queue
        affiliate_links_queue = []

        async def on_response(resp):
            if "createLink" in resp.url:
                try:
                    body = await resp.text()
                    import json as _json
                    data = _json.loads(body)
                    if "urls" in data:
                        for u in data["urls"]:
                            short = u.get("short_url", "")
                            if short:
                                affiliate_links_queue.append(short)
                                logger.info(f"  Link afiliado capturado: {short}")
                except Exception:
                    pass

        page.on("response", on_response)

        # Override clipboard para capturar links
        await page.expose_function("__capture_clipboard", lambda text: setattr(page, "_clipboard_text", text))

        # Login
        ok = await login(page, email, password, headless)
        if not ok:
            await context.close()
            profile_lock.release()
            return 0

        # Só desativa produtos depois de confirmar que está logado
        if start_category == 0 and not dry_run:
            await deactivate_all_products()

        # Salva storage state e cookies para próximas execuções
        try:
            await context.storage_state(path=str(STORAGE_STATE_FILE))
            logger.info(f"Storage state salvo em {STORAGE_STATE_FILE}")
        except Exception as e:
            logger.warning(f"Erro ao salvar storage state: {e}")
        try:
            cookies = await context.cookies()
            COOKIES_FILE.write_text(json.dumps(cookies, indent=2))
            logger.info(f"Cookies salvos: {len(cookies)} cookies")
        except Exception as e:
            logger.warning(f"Erro ao salvar cookies: {e}")

        # Navega para a página de produtos afiliados
        # O portal pode redirecionar, então esperamos estabilizar
        await page.goto(PORTAL_URL, wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(8000)  # espera SPA carregar

        logger.info(f"URL atual: {page.url}")

        # Ativa o filtro "Ganhos extras"
        await toggle_extra_commission(page)
        await page.wait_for_timeout(2000)

        # Obtém lista de categorias (do JSON embutido no HTML)
        categorias = await get_categories(page)
        if not categorias:
            logger.warning("Nenhuma categoria encontrada — scrapeando página atual")
            count = await scrape_category(page, "Geral", dry_run)
            total_count += count
        else:
            last_keepalive = time.time()
            # Scrapeia cada categoria (a partir do checkpoint)
            for i, (cat_id, cat_name) in enumerate(categorias):
                if i < start_category:
                    logger.info(f"Pulando categoria {i+1} (já feita): {cat_name}")
                    continue

                # Keepalive da sessão a cada 25 minutos
                if time.time() - last_keepalive > 1500:
                    try:
                        logger.info("Keepalive: acessando portal afiliados para renovar sessão")
                        await page.goto("https://www.mercadolivre.com.br/afiliados/hub", wait_until="domcontentloaded", timeout=30000)
                        await page.wait_for_timeout(3000)
                        await page.goto(PORTAL_URL, wait_until="domcontentloaded", timeout=30000)
                        await page.wait_for_timeout(3000)
                        last_keepalive = time.time()
                    except Exception as e:
                        logger.warning(f"Keepalive falhou: {e}")

                logger.info(f"\n{'='*60}")
                logger.info(f"Categoria {i+1}/{len(categorias)}: {cat_name} ({cat_id})")
                logger.info(f"{'='*60}")

                # Salva checkpoint ANTES de começar a categoria
                save_checkpoint(i)

                ok = await select_category(page, cat_id, cat_name)
                if not ok:
                    logger.warning(f"Pulando categoria {cat_name}")
                    continue

                count = await scrape_category(page, cat_name, dry_run)
                total_count += count

                logger.info(f"Total parcial: {total_count} produtos")

        # Coleta métricas de desempenho (após scraping, navega para página de Métricas)
        metrics = await scrape_metrics_summary(page)
        if not dry_run:
            await save_metrics_snapshot(metrics)

        # Scrape de cupons (após produtos, reusa mesma sessão/logada)
        if not dry_run:
            coupons = []
            try:
                logger.info("\n=== INICIANDO SCRAPE DE CUPONS ===")
                from app.workers.ml_coupon_scraper import scrape_ml_coupons, save_coupons, deactivate_expired_coupons
                coupons = await scrape_ml_coupons(page, max_pages=0)
                if coupons:
                    await save_coupons(coupons)
                await deactivate_expired_coupons()
                logger.info(f"=== CUPONS: {len(coupons)} coletados ===\n")
            except Exception as e:
                logger.warning(f"Erro no scrape de cupons: {e}")

        await context.close()

    # Libera lock do perfil persistente
    profile_lock.release()

    # Limpa checkpoint após concluir tudo
    clear_checkpoint()

    logger.info(f"\n{'='*60}")
    logger.info(f"SCRAPING CONCLUÍDO: {total_count} produtos totais")
    logger.info(f"{'='*60}")

    return total_count


async def deactivate_all_products():
    """Desativa produtos ML existentes no início do scrape (sobrescrever).
    NÃO desativa produtos da Amazon (notes contém 'amazon_scraper').
    Também deleta produtos inativos com >30 dias (auto-cleanup)."""
    try:
        from app.db.session import AsyncSessionLocal
        from app.models.models import AffiliateProduct
        from sqlalchemy import select, func, delete
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

        # Cleanup histórico: deleta registros com mais de 2 anos
        from app.models.models import AffiliatePriceHistory
        hist_cutoff = datetime.now(timezone.utc) - timedelta(days=730)
        old_hist = await db.execute(
            select(func.count()).select_from(AffiliatePriceHistory).where(
                AffiliatePriceHistory.recorded_at < hist_cutoff,
            )
        )
        hist_count = old_hist.scalar() or 0
        if hist_count > 0:
            await db.execute(
                delete(AffiliatePriceHistory).where(
                    AffiliatePriceHistory.recorded_at < hist_cutoff,
                )
            )
            await db.commit()
            logger.info(f"{hist_count} registros de histórico (>2 anos) deletados (auto-cleanup)")

        # Só desativa produtos ML antigos (não Amazon)
        result = await db.execute(
            select(AffiliateProduct).where(
                AffiliateProduct.is_active == True,
                func.lower(AffiliateProduct.notes).like("%ml_scraper%"),
            )
        )
        old = result.scalars().all()
        for p in old:
            p.is_active = False
        await db.commit()
        if old:
            logger.info(f"{len(old)} produtos ML antigos desativados (Amazon preservado)")


async def save_single_product(r: dict) -> bool:
    """Salva UM produto no banco imediatamente (upsert). Retorna True se salvou."""
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
    commission = parse_commission(r.get("ganhos", ""))
    rating = parse_rating(r.get("avaliacao", ""))
    sold = parse_sold_count(r.get("vendidos", ""))
    image_url = r.get("image_url", "")

    notes_parts = []
    notes_parts.append("source=ml_scraper")  # Marca como produto ML para filtro do endpoint /affiliate/products
    if r.get("badge"):
        notes_parts.append(f"badge={r['badge']}")
    if rating:
        notes_parts.append(f"avaliacao={rating}")
    if sold:
        notes_parts.append(f"vendidos={sold}")
    if r.get("parcelas"):
        notes_parts.append(f"parcelas={r['parcelas']}")
    if r.get("desconto"):
        notes_parts.append(f"desconto={r['desconto']}")
    notes = " | ".join(notes_parts)

    try:
        async with AsyncSessionLocal() as db:
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
                            provider="mercadolivre",
                            price=price,
                        ))
                existing.title = r.get("nome", "")
                existing.price = price
                existing.commission_pct = commission
                existing.category = r.get("categoria", "")
                existing.seller_name = r.get("seller_name") or existing.seller_name
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
                    commission_pct=commission,
                    category=r.get("categoria", ""),
                    seller_name=r.get("seller_name"),
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
                        provider="mercadolivre",
                        price=price,
                    ))

            await db.commit()
            return True
    except Exception as e:
        logger.warning(f"  Erro ao salvar produto: {e}")
        return False


async def scrape_metrics_summary(page) -> dict:
    """Coleta métricas da página de Métricas do portal de afiliados ML.

    Navega para a URL de dashboard com filtro de período (ontem) e faz parse
    do texto visível. Estrutura confirmada em 2026-06-26 via scraping real:

      Métricas
      Período: Ontem
      Dados atualizados em 25 de junho de 2026
      Cliques totais: 0
      Compradores totais: 0
      Ordens estimadas: 0
      Prod. estimados: 0
      Detalhe dos ganhos:
        Parceria do Mercado Livre: R$ 0
        Parceria do vendedor: R$ 0
        Vendas brutas: R$ 0
        Vendas não efetivadas: 0
        Vendas estimadas: R$ 0
        Ganho estimado: R$ 0

    Retorna dict com todos os campos. Não quebra se não encontrar.
    """
    from datetime import datetime, timedelta, timezone

    # URL com filtro de período: ontem (dia anterior ao de hoje)
    # O ML usa formato ISO com timezone -03:00
    yesterday = datetime.now(timezone.utc) - timedelta(days=1)
    today = datetime.now(timezone.utc)
    # Ajusta para -03:00 (horário Brasília)
    def iso_br(dt):
        br = dt.astimezone(timezone(timedelta(hours=-3)))
        return br.strftime("%Y-%m-%dT00:00:00.000-03:00")
    time_range = f"{iso_br(yesterday)}--{iso_br(today)}"
    METRICS_URL = f"https://www.mercadolivre.com.br/afiliados/dashboard?filter_time_range={time_range}#hub"

    result = {
        "clicks": None,
        "orders": None,
        "estimated_earnings": None,
        "confirmed_earnings": None,
        "period_until": None,
        "buyers": None,
        "estimated_products": None,
        "gross_sales": None,
        "cancelled_sales": None,
        "estimated_sales": None,
        "ml_partnership_earnings": None,
        "seller_partnership_earnings": None,
    }

    try:
        logger.info(f"Navegando para Métricas: {METRICS_URL[:90]}...")
        await page.goto(METRICS_URL, wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(8000)  # SPA carrega

        # Se redirecionou para login, cookies expiraram
        if "login" in page.url.lower():
            logger.warning("Métricas: cookies expirados, redirecionou para login")
            return result

        body_text = await page.inner_text("body")

        # Helper: extrai primeiro número inteiro após um label
        # (pula linhas de descrição entre o label e o valor)
        def extract_int(label):
            idx = body_text.find(label)
            if idx < 0:
                return None
            # Procura o primeiro número standalone após o label (não porcentagem)
            after = body_text[idx + len(label):]
            # Pula linhas que não começam com número, pega o primeiro número
            for line in after.split("\n"):
                line = line.strip()
                if not line:
                    continue
                # Número standalone (não porcentagem, não "—")
                m = re.match(r"^(\d[\d.]*)$", line)
                if m:
                    return int(m.group(1).replace(".", ""))
                # Se a linha tem texto (descrição), continua
                # Se chegou num "—" ou "%", não é o valor
            return None

        # Helper: extrai valor em R$ após um label
        def extract_money(label):
            idx = body_text.find(label)
            if idx < 0:
                return None
            after = body_text[idx + len(label):]
            # Procura "R$" seguido de número (pode estar em linhas separadas)
            for line in after.split("\n"):
                line = line.strip()
                if not line:
                    continue
                # "R$" sozinho numa linha → próxima linha tem o número
                if line == "R$":
                    continue
                # "R$ 0" ou "R$ 1.234,56" na mesma linha
                m = re.match(r"^R\$\s*([\d.,]+)$", line)
                if m:
                    val = m.group(1).replace(".", "").replace(",", ".")
                    try:
                        return float(val)
                    except ValueError:
                        return None
                # Número standalone após ter visto "R$"
                m = re.match(r"^([\d.,]+)$", line)
                if m and "R$" in after[:after.find(line)]:
                    val = m.group(1).replace(".", "").replace(",", ".")
                    try:
                        return float(val)
                    except ValueError:
                        return None
            return None

        # Período: "Dados atualizados em 25 de junho de 2026"
        m = re.search(r"Dados atualizados em\s+(.+?)(?:\n|$)", body_text)
        if m:
            result["period_until"] = m.group(1).strip()

        # Métricas principais
        result["clicks"] = extract_int("Cliques totais")
        result["buyers"] = extract_int("Compradores totais")
        result["orders"] = extract_int("Ordens estimadas")
        result["estimated_products"] = extract_int("Prod. estimados")
        result["cancelled_sales"] = extract_int("Vendas não efetivadas")

        # Ganhos (R$)
        result["ml_partnership_earnings"] = extract_money("Parceria do Mercado Livre")
        result["seller_partnership_earnings"] = extract_money("Parceria do vendedor")
        result["gross_sales"] = extract_money("Vendas brutas")
        result["estimated_sales"] = extract_money("Vendas estimadas")
        result["estimated_earnings"] = extract_money("Ganho estimado")

        logger.info(
            f"Métricas ML: cliques={result['clicks']} "
            f"ordens={result['orders']} "
            f"compradores={result['buyers']} "
            f"ganho=R$ {result['estimated_earnings']} "
            f"vendas_brutas=R$ {result['gross_sales']} "
            f"período={result['period_until']}"
        )

        # Se não encontrou nada, loga warning
        if all(v is None for v in [result["clicks"], result["orders"], result["estimated_earnings"]]):
            logger.warning("Métricas ML: nenhum valor encontrado — estrutura pode ter mudado")

    except Exception as e:
        logger.warning(f"Erro ao coletar métricas ML: {e}")

    return result


async def save_metrics_snapshot(data: dict):
    """Salva snapshot de métricas no banco (tabela affiliate_metrics_snapshots)."""
    try:
        from app.db.session import AsyncSessionLocal
        from app.models.models import AffiliateMetricsSnapshot
    except ImportError as e:
        logger.error(f"Erro ao importar banco: {e}")
        return False

    try:
        async with AsyncSessionLocal() as db:
            snapshot = AffiliateMetricsSnapshot(
                provider="mercadolivre",
                period_until=data.get("period_until"),
                clicks=data.get("clicks"),
                orders=data.get("orders"),
                estimated_earnings=data.get("estimated_earnings"),
                raw_data=data,
            )
            db.add(snapshot)
            await db.commit()
            logger.info("Snapshot de métricas salvo no banco")
            return True
    except Exception as e:
        logger.warning(f"Erro ao salvar snapshot de métricas: {e}")
        return False


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Scraper ML Afiliados")
    parser.add_argument("--dry-run", action="store_true", help="Não salva no banco")
    parser.add_argument("--headless", default="true", help="true/false (default: true)")
    parser.add_argument("--login", action="store_true", help="Modo login manual: abre navegador visível para fazer login + 2FA e salva cookies")
    args = parser.parse_args()

    if args.login:
        # Modo login: abre navegador visível com perfil persistente, usuário faz login + 2FA
        # O perfil persistente mantém a sessão por semanas/meses (não precisa copiar cookies)
        print("=" * 60)
        print("MODO LOGIN MANUAL — perfil persistente")
        print("1. O navegador vai abrir com o perfil persistente")
        print("2. Faça login no ML e complete o 2FA")
        print("3. A sessão será mantida no perfil (sem precisar copiar cookies)")
        print("=" * 60)
        total = asyncio.run(run_scraper(headless=False, dry_run=True))
        print(f"\nPerfil persistente: {PROFILE_DIR}")
        print(f"Total coletado no teste: {total}")
        sys.exit(0 if total >= 0 else 1)

    headless = args.headless.lower() != "false"
    total = asyncio.run(run_scraper(headless=headless, dry_run=args.dry_run))
    print(f"\nTotal: {total} produtos coletados")
    sys.exit(0 if total > 0 else 1)


if __name__ == "__main__":
    main()
