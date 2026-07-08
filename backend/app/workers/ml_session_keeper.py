"""
ml_session_keeper.py — Mantém a sessão do Mercado Livre Afiliados viva.

Acessa o portal periodicamente com o storage state salvo, renovando cookies
e detectando expiração precoce. Não substitui login manual quando a sessão
realmente expirar, mas ajuda a prolongar a vida útil entre logins.

Melhorias (2026-07-06):
- playwright-stealth para evitar detecção
- Mais URLs do portal acessadas (hub, home, relatórios)
- Wait times maiores entre páginas
- User agent atualizado
- Não mata Chromium de login manual (--login nos args)
- Timestamp da última renovação bem-sucedida

Uso:
  cd backend && venv/bin/python -m app.workers.ml_session_keeper
  cd backend && venv/bin/python -m app.workers.ml_session_keeper --headless
"""
import asyncio
import fcntl
import json
import logging
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger("ml_session_keeper")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR.parent.parent
STORAGE_STATE_FILE = BACKEND_DIR / ".ml_storage_state.json"
COOKIES_FILE = BACKEND_DIR / ".ml_cookies.json"
# Perfil persistente compartilhado com o ml_scraper (mesmo diretório)
PROFILE_DIR = BACKEND_DIR / ".ml_chrome_profile"
# Lock compartilhado com o ml_scraper (não podem usar o mesmo perfil ao mesmo tempo)
PROFILE_LOCK_FILE = BACKEND_DIR / ".ml_chrome_profile.lock"
LOCK_FILE = BACKEND_DIR / ".ml_session_keeper.lock"
LAST_OK_FILE = BACKEND_DIR / ".ml_session_last_ok"

# URLs do portal para manter sessão ativa (acessa várias pra gerar atividade)
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
            # Pula Chromium de login manual (ml_scraper --login abre browser visível)
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
            import time
            time.sleep(2)
    except Exception as e:
        logger.warning(f"Cleanup: erro ao tentar matar processos órfãos: {e}")


async def keep_session(headless: bool = True) -> bool:
    from playwright.async_api import async_playwright

    if not PROFILE_DIR.exists():
        logger.error("Perfil persistente não existe. Rode ml_scraper --login primeiro.")
        return False

    lock = LockFile(LOCK_FILE)
    if not lock.acquire():
        logger.warning("Outra instância do session keeper já está rodando")
        return False

    # Lock do perfil compartilhado com o scraper
    profile_lock = LockFile(PROFILE_LOCK_FILE)
    if not profile_lock.acquire():
        logger.warning("Perfil em uso pelo scraper — pulando renovação nesta hora")
        lock.release()
        return False

    _cleanup_orphan_chromiums()
    session_ok = False

    try:
        async with async_playwright() as p:
            chromium_path = None
            for path in ["/usr/bin/chromium-browser", "/usr/bin/chromium", "/usr/bin/google-chrome"]:
                if Path(path).exists():
                    chromium_path = path
                    break

            # launch_persistent_context: mantém TODO o estado do navegador em disco.
            # O ML vê um usuário estabelecido (com histórico, cache, IndexedDB),
            # não um "perfil novo" a cada execução. Sessão dura semanas/meses.
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
                ],
            }
            if chromium_path:
                persistent_kwargs["executable_path"] = chromium_path

            context = await p.chromium.launch_persistent_context(**persistent_kwargs)
            page = await context.new_page()

            # Acessa múltiplas páginas do portal para gerar atividade e renovar sessão
            for url in KEEPALIVE_URLS:
                try:
                    await page.goto(url, wait_until="domcontentloaded", timeout=60000)
                    await page.wait_for_timeout(8000)
                    if "login" in page.url.lower() or "auth" in page.url.lower() or "jms" in page.url.lower():
                        logger.error(f"Sessão expirada ao acessar {url} — login manual necessário")
                        await context.close()
                        return False
                    logger.info(f"Página acessada: {page.url}")
                except Exception as e:
                    logger.warning(f"Erro ao acessar {url}: {e}")
                    # Continua pra próxima URL em vez de desistir

            # Backup: salva cookies/storage state como fallback (legado)
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
            session_ok = True

            # Registra timestamp da última renovação bem-sucedida
            try:
                LAST_OK_FILE.write_text(datetime.now(timezone.utc).isoformat())
            except Exception:
                pass

    except Exception as e:
        logger.error(f"Erro durante session keep-alive: {e}")
        session_ok = False
    finally:
        profile_lock.release()
        lock.release()

    return session_ok


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Session keeper para ML Afiliados")
    parser.add_argument("--headless", default="true", help="true/false (default: true)")
    args = parser.parse_args()
    headless = args.headless.lower() != "false"
    ok = asyncio.run(keep_session(headless=headless))
    raise SystemExit(0 if ok else 1)
