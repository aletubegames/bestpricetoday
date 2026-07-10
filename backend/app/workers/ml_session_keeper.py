"""
ml_session_keeper.py — Mantém a sessão do Mercado Livre Afiliados viva.

Estratégia (melhor prática para sessões longas):
1. Heartbeat leve via HTTP (requests + cookies) a cada 15 min para evitar
   abrir o Chromium desnecessariamente e reduzir fingerprint.
2. Se o HTTP detectar expiração, tenta reativar via browser automation
   com perfil persistente + playwright-stealth.
3. Backup rotativo do storage_state para poder restaurar se o perfil corromper.
4. Limpa SingletonLock do Chromium para evitar "profile in use" após crash.

Não substitui login manual quando a sessão realmente expirar, mas reduz
 drasticamente a frequência de logins ao manter o cookie ativo.

Uso:
  cd backend && venv/bin/python -m app.workers.ml_session_keeper
  cd backend && venv/bin/python -m app.workers.ml_session_keeper --headless=false
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

KEEPALIVE_URLS = [
    "https://www.mercadolivre.com.br/afiliados",
    "https://www.mercadolivre.com.br/afiliados/hub",
    "https://www.mercadolivre.com.br/afiliados/coupons#hub",
    "https://www.mercadolivre.com.br/afiliados/home",
]

USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"


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


def _http_session_alive() -> bool:
    """Heartbeat leve: tenta acessar o portal usando cookies salvos.
    Retorna True se a sessão ainda estiver ativa (não redirecionou para login)."""
    cookies = _load_cookie_dict()
    if not cookies:
        logger.info("HTTP keepalive: sem cookies salvos, necessário browser")
        return False

    try:
        with httpx.Client(
            cookies=cookies,
            headers={"User-Agent": USER_AGENT, "Accept-Language": "pt-BR,pt;q=0.9"},
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
                        return False
                    if r.status_code < 400:
                        logger.info(f"HTTP keepalive OK: {r.url} ({r.status_code})")
                        return True
                except Exception as e:
                    logger.warning(f"HTTP keepalive erro em {url}: {e}")
                    continue
    except Exception as e:
        logger.warning(f"HTTP keepalive falhou: {e}")
    return False


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


async def _mark_session_expired():
    """Registra que a sessão expirou e envia alerta Telegram (uma vez por expiração)."""
    try:
        EXPIRED_FILE.write_text(datetime.now(timezone.utc).isoformat())
    except Exception:
        pass
    # Envia alerta Telegram só uma vez por expiração
    if ALERT_SENT_FILE.exists():
        return
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
    """Abre o Chromium com perfil persistente e renova a sessão."""
    from playwright.async_api import async_playwright

    if not PROFILE_DIR.exists():
        logger.error("Perfil persistente não existe. Rode ml_scraper --login primeiro.")
        return False

    _cleanup_orphan_chromiums()
    _cleanup_chrome_singleton_lock()
    _backup_storage_state()

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
                "user_agent": USER_AGENT,
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
            await _apply_stealth(context, user_agent=USER_AGENT)

            session_expired = False
            urls = list(KEEPALIVE_URLS)
            random.shuffle(urls)

            for url in urls:
                try:
                    await _human_like_browsing(page, url)
                    final_url = page.url.lower()
                    if "login" in final_url or "auth" in final_url or "jms" in final_url:
                        logger.error(f"Sessão expirada ao acessar {url} — login manual necessário")
                        session_expired = True
                        break
                    logger.info(f"Página acessada: {page.url}")
                except Exception as e:
                    logger.warning(f"Erro ao acessar {url}: {e}")

            # Salva storage state e cookies
            try:
                await context.storage_state(path=str(STORAGE_STATE_FILE))
            except Exception:
                pass
            try:
                cookies = await context.cookies()
                COOKIES_FILE.write_text(json.dumps(cookies, indent=2))
                logger.info(f"Cookies renovados: {len(cookies)}")
            except Exception as e:
                logger.warning(f"Erro ao salvar cookies: {e}")

            await context.close()

            if session_expired:
                await _mark_session_expired()
                return False

            _clear_session_expired()
            _mark_last_ok()
            return True

    except Exception as e:
        logger.error(f"Erro durante browser keep-alive: {e}")
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
            # 1. Tenta heartbeat HTTP leve (não abre browser)
            if _http_session_alive():
                _mark_last_ok()
                _clear_session_expired()
                logger.info("Sessão mantida via HTTP keepalive")
                return True

            # 2. Se HTTP falhou, abre o Chromium para renovar
            logger.info("HTTP keepalive não confirmou sessão — abrindo browser")
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
        # Modo utilitário: apenas testa HTTP keepalive
        alive = _http_session_alive()
        print(f"HTTP session alive: {alive}")
        raise SystemExit(0 if alive else 1)

    ok = asyncio.run(keep_session(headless=headless))
    raise SystemExit(0 if ok else 1)
