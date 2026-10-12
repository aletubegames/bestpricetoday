"""
ml_session_keeper.py — Mantém a sessão do Mercado Livre Afiliados viva.

Estratégia (melhor prática para sessões longas):
1. Heartbeat leve via HTTP (httpx + cookies) a cada 30 min para evitar
   abrir o Chromium desnecessariamente e reduzir fingerprint.
   NÃO reescreve cookies a cada HTTP (era fonte de corrupção de sessão).
2. Tri-estado no HTTP: "alive" | "expired" | "network_error".
   - "alive" → mantém sessão, marca last_ok.
   - "expired" → sessão morta confirmada; NÃO abre browser se EXPIRED_FILE
     já existe (evita reabrir 288x/dia = padrão de bot). Só alerta Telegram
     a cada 6h. Retoma quando login manual novo reescreve cookies/storage_state.
   - "network_error" → DNS/rede caiu; NÃO abre browser, NÃO marca expired,
     NÃO alerta. Tenta de novo no próximo ciclo de 30min.
3. Renovação preventiva via browser a cada 6h mesmo com HTTP OK — refresh
   dos cookies antes que expirem. SÓ declara sucesso se pelo menos 1 página
   do portal carregar de verdade (URL final contém "mercadolivre" e não é
   about:blank/chrome-error://). Se nenhuma carregar (rede caiu), NÃO salva
   storage_state/cookies (evita gravar snapshot degradado que mata a sessão).
4. Backup rotativo do storage_state para poder restaurar se o perfil corromper.
5. Limpa SingletonLock do Chromium para evitar "profile in use" após crash.
6. Pool de User-Agents reais e atuais (Chrome 138+) com rotação aleatória
   por run — evita detecção de UA fixo/desatualizado.
7. Roda com janela real no Xvfb :99 (--headless=false no cron) — fingerprint
   de headless é detectável; o Xvfb já está sempre ativo no servidor.

Não substitui login manual quando a sessão realmente expirar, mas reduz
 drasticamente a frequência de logins ao manter o cookie ativo.

Uso:
  cd backend && venv/bin/python -m app.workers.ml_session_keeper
  cd backend && venv/bin/python -m app.workers.ml_session_keeper --headless=false
  cd backend && venv/bin/python -m app.workers.ml_session_keeper --http-only
"""
import asyncio
import fcntl
import json
import logging
import os
import random
import shutil
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx

logger = logging.getLogger("ml_session_keeper")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR.parent.parent
STORAGE_STATE_FILE = BACKEND_DIR / ".ml_storage_state.json"
COOKIES_FILE = BACKEND_DIR / ".ml_cookies.json"
PROFILE_DIR = BACKEND_DIR / ".ml_chrome_profile"
PROFILE_LOCK_FILE = BACKEND_DIR / ".ml_chrome_profile.lock"
LOCK_FILE = BACKEND_DIR / ".ml_session_keeper.lock"
LAST_OK_FILE = BACKEND_DIR / ".ml_session_last_ok"
EXPIRED_FILE = BACKEND_DIR / ".ml_session_expired"
ALERT_SENT_FILE = BACKEND_DIR / ".ml_session_alert_sent"
LAST_BROWSER_REFRESH_FILE = BACKEND_DIR / ".ml_session_last_browser_refresh"

BROWSER_REFRESH_INTERVAL = 21600  # 6 horas — renovação preventiva via browser
BROWSER_BACKOFF_INTERVAL = 7200   # 2 horas — backoff após browser falhar (não fica 288x/dia)
NETWORK_BACKOFF_INTERVAL = 1800   # 30 min — backoff curto após erro de rede (não confundir com sessão morta)
EXPIRED_RECENT_HOURS = 12         # janela para considerar EXPIRED_FILE "recente" (dedup de alertas)

KEEPALIVE_URLS = [
    "https://www.mercadolivre.com.br/afiliados",
    "https://www.mercadolivre.com.br/afiliados/hub",
    "https://www.mercadolivre.com.br/afiliados/coupons#hub",
    "https://www.mercadolivre.com.br/afiliados/home",
]

# Pool de User-Agents mantido como lista para compatibilidade.
# O servidor usa um único perfil Linux/Chrome consistente por execução.
USER_AGENTS = [
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.7922.108 Safari/537.36",
]
USER_AGENT = USER_AGENTS[0]


def _pick_user_agent() -> str:
    """Escolhe um User-Agent aleatório do pool (rotação por run)."""
    return random.choice(USER_AGENTS)


# Arquivo de backoff: se o browser tentou renovar e falhou, espera BROWSER_BACKOFF_INTERVAL
# antes de tentar de novo. Evita padrão de bot (288 aberturas/dia).
BROWSER_BACKOFF_FILE = BACKEND_DIR / ".ml_session_browser_backoff"
# Backoff curto para erro de rede (DNS/internet caiu) — distinto do backoff de bot:
# não indica sessão morta, só "não tente abrir browser agora".
NETWORK_BACKOFF_FILE = BACKEND_DIR / ".ml_session_network_backoff"


class LockFile:
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


def _cleanup_orphan_chromiums():
    """Mata Chromium órfãos, EXCETO os de login manual (tem --login nos args)."""
    try:
        result = subprocess.run(
            ["ps", "-u", str(os.getuid()), "-o", "pid,comm,args", "--no-headers"],
            capture_output=True, text=True, timeout=10
        )
        killed = 0
        for line in result.stdout.splitlines():
            if not line.strip():
                continue
            parts = line.split(None, 2)
            if len(parts) < 2:
                continue
            pid_str, comm = parts[0], parts[1]
            args = parts[2] if len(parts) > 2 else ""
            if "--login" in args or "login_profile" in args:
                continue
            if "chromium" in comm.lower() or "mercadolivre.com.br/afiliados" in args:
                try:
                    pid = int(pid_str)
                    if pid != os.getpid():
                        os.kill(pid, 15)
                        killed += 1
                except (ValueError, ProcessLookupError, PermissionError):
                    continue
        if killed:
            logger.info(f"Cleanup: encerrados {killed} processos Chromium órfãos")
            time.sleep(2)
    except Exception as e:
        logger.warning(f"Cleanup: erro ao tentar matar processos órfãos: {e}")


def _cleanup_chrome_singleton_lock():
    """Remove arquivos de lock do Chromium que podem travar o perfil persistente."""
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
                logger.warning(f"Cleanup: não conseguiu remover {name}: {e}")
    if removed:
        logger.info(f"Cleanup: removido lock do Chrome: {', '.join(removed)}")


def _backup_storage_state():
    """Guarda backup rotativo do storage_state para recuperação."""
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


def _load_cookie_dict() -> dict:
    """Carrega cookies do arquivo JSON legado."""
    if not COOKIES_FILE.exists():
        return {}
    try:
        cookies = json.loads(COOKIES_FILE.read_text())
        return {c["name"]: c["value"] for c in cookies if "name" in c and "value" in c}
    except Exception:
        return {}


def _browser_backoff_active() -> bool:
    """True se estamos em backoff após browser falhar (não abrir browser de novo)."""
    if not BROWSER_BACKOFF_FILE.exists():
        return False
    try:
        last = datetime.fromisoformat(BROWSER_BACKOFF_FILE.read_text().strip())
        elapsed = (datetime.now(timezone.utc) - last).total_seconds()
        return elapsed < BROWSER_BACKOFF_INTERVAL
    except Exception:
        return False


def _mark_browser_backoff():
    """Registra que o browser tentou renovar e falhou — entra em backoff."""
    try:
        BROWSER_BACKOFF_FILE.write_text(datetime.now(timezone.utc).isoformat())
    except Exception:
        pass


def _clear_browser_backoff():
    """Limpa o backoff após sucesso ou login manual."""
    try:
        BROWSER_BACKOFF_FILE.unlink(missing_ok=True)
    except Exception:
        pass


def _network_backoff_active() -> bool:
    """True se estamos em backoff curto após erro de rede (não abrir browser)."""
    if not NETWORK_BACKOFF_FILE.exists():
        return False
    try:
        last = datetime.fromisoformat(NETWORK_BACKOFF_FILE.read_text().strip())
        elapsed = (datetime.now(timezone.utc) - last).total_seconds()
        return elapsed < NETWORK_BACKOFF_INTERVAL
    except Exception:
        return False


def _mark_network_backoff():
    """Registra erro de rede — backoff curto de 30min (não é sessão morta)."""
    try:
        NETWORK_BACKOFF_FILE.write_text(datetime.now(timezone.utc).isoformat())
    except Exception:
        pass


def _clear_network_backoff():
    try:
        NETWORK_BACKOFF_FILE.unlink(missing_ok=True)
    except Exception:
        pass


def _expired_recent() -> bool:
    """True se EXPIRED_FILE existe e é recente (< EXPIRED_RECENT_HOURS).
    Usado para dedup de alertas (scraper/keeper não precisam re-alertar
    pelo mesmo incidente)."""
    if not EXPIRED_FILE.exists():
        return False
    try:
        last = datetime.fromisoformat(EXPIRED_FILE.read_text().strip())
        elapsed = (datetime.now(timezone.utc) - last).total_seconds()
        return elapsed < EXPIRED_RECENT_HOURS * 3600
    except Exception:
        return False


def _login_manual_newer_than_expired() -> bool:
    """True se houve login manual novo após a sessão expirar.
    Detecta comparando mtime de .ml_cookies.json/.ml_storage_state.json
    com o timestamp de EXPIRED_FILE. Se True, o caller deve limpar o flag
    expired e retomar o ciclo normal."""
    if not EXPIRED_FILE.exists():
        return True  # não há flag expired — nada a recuperar
    try:
        expired_ts = datetime.fromisoformat(EXPIRED_FILE.read_text().strip())
    except Exception:
        return True
    # Pega o mtime mais recente entre cookies e storage_state
    candidates = []
    for f in (COOKIES_FILE, STORAGE_STATE_FILE):
        if f.exists():
            try:
                mtime = datetime.fromtimestamp(f.stat().st_mtime, tz=timezone.utc)
                candidates.append(mtime)
            except Exception:
                pass
    if not candidates:
        return False
    newest = max(candidates)
    # Login manual novo = arquivos de sessão mais novos que o flag expired (+30s de tolerância)
    return (newest - expired_ts).total_seconds() > 30


def _http_session_alive() -> str:
    """Heartbeat leve: tenta acessar o portal usando cookies salvos.

    Retorna tri-estado:
      - "alive"         : sessão ativa (200 sem redirect pra login)
      - "expired"       : sessão morta confirmada (redirect jms/login/auth)
      - "network_error" : DNS/rede caiu — NÃO confundir com sessão morta.
                          Não abre browser, não marca expired, não alerta.

    NÃO persiste cookies recebidos via Set-Cookie — isso era fonte de
    corrupção de sessão (cookies de página de loading/cache sobrescreviam
    os cookies reais). Cookies só são salvos quando o browser confirma
    a sessão ativa em _browser_keep_session()."""
    cookies = _load_cookie_dict()
    if not cookies:
        logger.info("HTTP keepalive: sem cookies salvos — sessão expirada")
        return "expired"

    ua = _pick_user_agent()
    saw_network_error = False
    try:
        with httpx.Client(
            cookies=cookies,
            headers={"User-Agent": ua, "Accept-Language": "pt-BR,pt;q=0.9"},
            follow_redirects=True,
            timeout=20.0,
        ) as client:
            for url in KEEPALIVE_URLS[:2]:
                try:
                    r = client.get(url)
                    final = str(r.url).lower()
                    body = r.text[:500].lower()
                    if "login" in final or "auth" in final or "jms" in final or "senha" in body or "password" in body:
                        logger.info(f"HTTP keepalive detectou redirect/login: {r.url}")
                        return "expired"
                    if r.status_code < 400:
                        logger.info(f"HTTP keepalive OK: {r.url} ({r.status_code})")
                        return "alive"
                except httpx.ConnectError as e:
                    logger.warning(f"HTTP keepalive erro de conexão em {url}: {e}")
                    saw_network_error = True
                    continue
                except httpx.TimeoutException as e:
                    logger.warning(f"HTTP keepalive timeout em {url}: {e}")
                    saw_network_error = True
                    continue
                except Exception as e:
                    # Erro genérico — pode ser rede; não assume expirado
                    logger.warning(f"HTTP keepalive erro em {url}: {e}")
                    saw_network_error = True
                    continue
    except (httpx.ConnectError, httpx.TimeoutException) as e:
        logger.warning(f"HTTP keepalive falhou (rede): {e}")
        return "network_error"
    except Exception as e:
        logger.warning(f"HTTP keepalive falhou: {e}")
        return "network_error"

    if saw_network_error:
        logger.warning("HTTP keepalive: todas as tentativas falharam por rede")
        return "network_error"
    # Não houve redirect de login nem 200 — comportamento inesperado, trata como expirado
    logger.warning("HTTP keepalive: sem resposta conclusiva — assumindo expirado")
    return "expired"


def _apply_stealth(context_or_page, user_agent: str = None):
    """Aplica playwright-stealth se disponível."""
    try:
        from playwright_stealth import Stealth
        stealth = Stealth(
            navigator_user_agent_override=user_agent,
            navigator_languages_override=("pt-BR", "pt"),
            navigator_platform_override="Linux x86_64",
        )
        if hasattr(stealth, "apply_stealth_async"):
            return stealth.apply_stealth_async(context_or_page)
    except Exception as e:
        logger.warning(f"Stealth não aplicado: {e}")
    return None


async def _human_like_browsing(page, url: str):
    """Simula comportamento humano básico na página."""
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(random.randint(2000, 4000))

        # Rola suavemente
        for _ in range(random.randint(1, 3)):
            await page.evaluate("window.scrollBy(0, Math.random()*300 + 100)")
            await page.wait_for_timeout(random.randint(800, 1500))

        # Clica em link interno aleatório (navegação real) se houver
        try:
            links = await page.locator('a[href*="/afiliados"]').all()
            if links:
                target = random.choice(links[:5])
                await target.click()
                await page.wait_for_timeout(random.randint(2000, 4000))
        except Exception:
            pass

    except Exception as e:
        logger.warning(f"Erro durante browsing human-like em {url}: {e}")


def _mark_last_ok():
    try:
        LAST_OK_FILE.write_text(datetime.now(timezone.utc).isoformat())
    except Exception:
        pass


def _browser_refresh_due() -> bool:
    """Verifica se é hora de fazer renovação preventiva via browser."""
    if not LAST_BROWSER_REFRESH_FILE.exists():
        return True
    try:
        last = datetime.fromisoformat(LAST_BROWSER_REFRESH_FILE.read_text().strip())
        elapsed = (datetime.now(timezone.utc) - last).total_seconds()
        return elapsed >= BROWSER_REFRESH_INTERVAL
    except Exception:
        return True


def _mark_browser_refresh():
    try:
        LAST_BROWSER_REFRESH_FILE.write_text(datetime.now(timezone.utc).isoformat())
    except Exception:
        pass


async def _mark_session_expired():
    """Registra que a sessão expirou e envia alerta Telegram repetidamente (a cada 6h) até resolver."""
    try:
        EXPIRED_FILE.write_text(datetime.now(timezone.utc).isoformat())
    except Exception:
        pass
    # Envia alerta Telegram a cada 6h (não só uma vez) — usuário pode ter perdido o primeiro
    should_alert = True
    if ALERT_SENT_FILE.exists():
        try:
            last_alert = datetime.fromisoformat(ALERT_SENT_FILE.read_text().strip())
            elapsed = (datetime.now(timezone.utc) - last_alert).total_seconds()
            if elapsed < 21600:  # 6h
                should_alert = False
        except Exception:
            pass
    if should_alert:
        try:
            ALERT_SENT_FILE.write_text(datetime.now(timezone.utc).isoformat())
        except Exception:
            pass
        await _send_telegram_alert()


def _clear_session_expired():
    try:
        EXPIRED_FILE.unlink(missing_ok=True)
    except Exception:
        pass
    try:
        ALERT_SENT_FILE.unlink(missing_ok=True)
    except Exception:
        pass


async def _send_telegram_alert():
    """Envia alerta no Telegram quando a sessão do ML expira."""
    try:
        from app.core.config import settings
        token = settings.TELEGRAM_BOT_TOKEN
        chat_id = str(settings.TELEGRAM_CHANNEL_ID) if settings.TELEGRAM_CHANNEL_ID else "5899118807"
        if not token:
            return
        last_ok = LAST_OK_FILE.read_text().strip() if LAST_OK_FILE.exists() else "desconhecido"
        msg = (
            "⚠️ *SESSÃO ML EXPIRADA*\n\n"
            "A sessão do Mercado Livre Afiliados expirou.\n"
            f"Última renovação OK: `{last_ok}`\n\n"
            "Para resolver, manda `/ml_login` aqui no Telegram.\n"
            "O bot vai tentar login automático (email + senha + reCAPTCHA).\n"
            "Se o reCAPTCHA pedir challenge de imagem, conecta via VNC."
        )
        async with httpx.AsyncClient(timeout=15) as client:
            await client.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                json={"chat_id": chat_id, "text": msg, "parse_mode": "Markdown"},
            )
        logger.info("Alerta Telegram enviado: sessão ML expirada")
    except Exception as e:
        logger.warning(f"Erro ao enviar alerta Telegram: {e}")


async def _browser_keep_session(headless: bool = True) -> bool:
    """Abre o Chromium com perfil persistente e renova a sessão.

    Sucesso só com prova real: pelo menos 1 página do portal precisa
    carregar de verdade (URL final contém "mercadolivre" e não é
    about:blank/chrome-error://). Se nenhuma carregar (rede/DNS caiu),
    NÃO salva storage_state/cookies (evita gravar snapshot degradado
    que mata a sessão) e aplica backoff curto de rede (30min).

    Se a sessão realmente expirou (página caiu em login/jms/auth),
    marca expired + backoff de bot (2h) e NÃO salva cookies."""
    from playwright.async_api import async_playwright

    if not PROFILE_DIR.exists():
        logger.error("Perfil persistente não existe. Rode ml_scraper --login primeiro.")
        return False

    _cleanup_chrome_singleton_lock()
    _backup_storage_state()

    # UA aleatório por run (evita detecção de UA fixo)
    ua = _pick_user_agent()

    try:
        async with async_playwright() as p:
            chromium_path = None
            for path in ["/usr/bin/chromium-browser", "/usr/bin/chromium", "/usr/bin/google-chrome"]:
                if Path(path).exists():
                    chromium_path = path
                    break

            persistent_kwargs = {
                "user_data_dir": str(PROFILE_DIR),
                "headless": headless,
                "viewport": {"width": 1366, "height": 768},
                "user_agent": ua,
                "locale": "pt-BR",
                "timezone_id": "America/Sao_Paulo",
                "args": [
                    "--no-sandbox",
                    "--disable-gpu",
                    "--disable-dev-shm-usage",
                    "--disable-blink-features=AutomationControlled",
                    "--disable-features=IsolateOrigins,site-per-process",
                ],
            }
            if chromium_path:
                persistent_kwargs["executable_path"] = chromium_path

            context = await p.chromium.launch_persistent_context(**persistent_kwargs)
            page = await context.new_page()

            # Aplica stealth
            await _apply_stealth(context, user_agent=ua)

            # Guarda na injeção de cookies: só injeta storage_state se for
            # mais novo que o cookie DB do perfil (evita sobrescrever cookies
            # frescos do perfil com snapshot velho).
            if STORAGE_STATE_FILE.exists():
                try:
                    profile_cookies_db = PROFILE_DIR / "Default" / "Cookies"
                    inject = True
                    if profile_cookies_db.exists():
                        ss_mtime = STORAGE_STATE_FILE.stat().st_mtime
                        db_mtime = profile_cookies_db.stat().st_mtime
                        if ss_mtime <= db_mtime:
                            inject = False
                            logger.info(
                                f"storage_state ({datetime.fromtimestamp(ss_mtime).isoformat()}) "
                                f"não é mais novo que o cookie DB do perfil "
                                f"({datetime.fromtimestamp(db_mtime).isoformat()}) — não injeta"
                            )
                    if inject:
                        state = json.loads(STORAGE_STATE_FILE.read_text())
                        state_cookies = state.get("cookies", [])
                        if state_cookies:
                            await context.add_cookies(state_cookies)
                            logger.info(f"Carregados {len(state_cookies)} cookies do storage_state no perfil")
                except Exception as e:
                    logger.warning(f"Erro ao carregar storage_state: {e}")

            session_expired = False
            pages_loaded = 0  # contador de páginas que carregaram de verdade
            urls = list(KEEPALIVE_URLS)
            random.shuffle(urls)

            for url in urls:
                try:
                    await _human_like_browsing(page, url)
                    final_url = (page.url or "").lower()
                    # Prova real de carregamento: URL contém mercadolivre e não é erro/about:blank
                    if "mercadolivre" in final_url and "chrome-error://" not in final_url and final_url != "about:blank":
                        if "login" in final_url or "auth" in final_url or "jms" in final_url:
                            logger.error(f"Sessão expirada ao acessar {url} — login manual necessário")
                            session_expired = True
                            break
                        pages_loaded += 1
                        logger.info(f"Página acessada: {page.url}")
                    else:
                        logger.warning(f"Página NÃO carregou corretamente: {final_url} (url={url}) — possível erro de rede")
                except Exception as e:
                    logger.warning(f"Erro ao acessar {url}: {e}")

            # CASO 1: sessão expirada — NÃO salva cookies, marca expired + backoff de bot
            if session_expired:
                await context.close()
                await _mark_session_expired()
                _mark_browser_backoff()  # backoff 2h — não abre browser de novo
                logger.warning("Sessão expirada — cookies NÃO salvos para evitar sobrescrever login manual")
                return False

            # CASO 2: nenhuma página carregou — erro de rede, NÃO salva nada
            if pages_loaded == 0:
                await context.close()
                _mark_network_backoff()  # backoff curto 30min — não é sessão morta
                logger.warning(
                    "Nenhuma página do portal carregou (rede/DNS caiu?) — "
                    "storage_state/cookies NÃO salvos para evitar snapshot degradado"
                )
                return False

            # CASO 3: pelo menos 1 página carregou e nenhuma caiu em login — sucesso real
            try:
                await context.storage_state(path=str(STORAGE_STATE_FILE))
            except Exception:
                pass
            try:
                cookies = await context.cookies()
                COOKIES_FILE.write_text(json.dumps(cookies, indent=2))
                logger.info(f"Cookies renovados: {len(cookies)} (páginas carregadas: {pages_loaded})")
            except Exception as e:
                logger.warning(f"Erro ao salvar cookies: {e}")

            await context.close()

            _clear_session_expired()
            _clear_browser_backoff()  # sucesso — limpa backoff
            _clear_network_backoff()
            _mark_last_ok()
            _mark_browser_refresh()
            return True

    except Exception as e:
        logger.error(f"Erro durante browser keep-alive: {e}")
        _mark_browser_backoff()  # erro também entra em backoff
        return False


async def keep_session(headless: bool = True) -> bool:
    lock = LockFile(LOCK_FILE)
    if not lock.acquire():
        logger.warning("Outra instância do session keeper já está rodando")
        return False

    try:
        # Lock do perfil compartilhado com o scraper
        profile_lock = LockFile(PROFILE_LOCK_FILE)
        if not profile_lock.acquire():
            logger.warning("Perfil em uso pelo scraper — pulando renovação nesta rodada")
            return False

        try:
            # 0. Verifica se houve login manual novo após sessão expirada.
            # Se sim, limpa o flag expired e retoma o ciclo normal.
            if EXPIRED_FILE.exists() and _login_manual_newer_than_expired():
                logger.info("Login manual novo detectado (cookies/storage_state mais novos que EXPIRED_FILE) — limpando flag expired")
                _clear_session_expired()
                _clear_browser_backoff()
                _clear_network_backoff()

            # 1. Tenta heartbeat HTTP leve (tri-estado, não abre browser)
            state = _http_session_alive()

            if state == "network_error":
                # Rede/DNS caiu — NÃO abre browser, NÃO marca expired, NÃO alerta.
                # Tenta de novo no próximo ciclo de 30min.
                _mark_network_backoff()
                logger.warning("HTTP keepalive: erro de rede — não abre browser, tenta no próximo ciclo")
                return False

            if state == "alive":
                _mark_last_ok()
                _clear_session_expired()
                _clear_network_backoff()
                logger.info("Sessão mantida via HTTP keepalive")

                # 2. Renovação preventiva via browser a cada 6h mesmo com HTTP OK
                if _browser_refresh_due():
                    if _browser_backoff_active():
                        logger.info("Renovação preventiva via browser pendente — em backoff de bot, pulando")
                    elif _network_backoff_active():
                        logger.info("Renovação preventiva via browser pendente — em backoff de rede, pulando")
                    else:
                        logger.info("Renovação preventiva via browser — refresh periódico")
                        return await _browser_keep_session(headless=headless)
                return True

            # state == "expired" — sessão morta confirmada pelo HTTP
            # Se EXPIRED_FILE já existe, NÃO abre browser (evita 288 aberturas/dia
            # = padrão de bot que agrava o flag anti-bot do ML). Só alerta a cada 6h.
            if EXPIRED_FILE.exists():
                logger.warning("Sessão expirada (HTTP) — EXPIRED_FILE já existe, não abre browser (evita padrão de bot)")
                await _mark_session_expired()  # só envia alerta Telegram a cada 6h (dedup interno)
                return False

            # EXPIRED_FILE não existe ainda — primeira detecção de expiração.
            # Verifica backoff antes de abrir browser (pode ter falhado há pouco).
            if _browser_backoff_active():
                logger.info("HTTP detectou expiração e browser em backoff — esperando próximo ciclo (login manual necessário)")
                await _mark_session_expired()
                return False

            # Abre browser UMA VEZ para confirmar expiração (pode ser falso positivo
            # do HTTP — ex.: redirect temporário). Se o browser também confirmar,
            # _browser_keep_session marca expired + backoff.
            logger.info("HTTP detectou expiração — abrindo browser UMA VEZ para confirmar")
            return await _browser_keep_session(headless=headless)
        finally:
            profile_lock.release()
    finally:
        lock.release()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Session keeper para ML Afiliados")
    parser.add_argument("--headless", default="true", help="true/false (default: true)")
    parser.add_argument("--http-only", action="store_true", help="Tenta HTTP keepalive sem abrir browser")
    args = parser.parse_args()
    headless = args.headless.lower() != "false"

    if args.http_only:
        # Modo utilitário: apenas testa HTTP keepalive (tri-estado)
        state = _http_session_alive()
        print(f"HTTP session state: {state}")
        raise SystemExit(0 if state == "alive" else 1)

    ok = asyncio.run(keep_session(headless=headless))
    raise SystemExit(0 if ok else 1)
