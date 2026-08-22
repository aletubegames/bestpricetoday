"""
ml_telegram_login.py — Login do ML Afiliados via comando Telegram.

Fluxo:
1. Usuário manda /ml_login no Telegram
2. Bot abre Chromium no servidor, preenche email + senha automaticamente
3. Tenta clicar "Não sou um robô" do reCAPTCHA
4. Se passar → login completo, avisa "✅ Login feito"
5. Se der challenge de imagem → manda screenshot no Telegram e pede VNC

Uso (interno):
  from app.workers.ml_telegram_login import do_telegram_login
  result = await do_telegram_login(progress_callback)
"""
import asyncio
import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR.parent.parent
ENV_FILE = BACKEND_DIR / ".env"
COOKIES_FILE = BACKEND_DIR / ".ml_cookies.json"
STORAGE_STATE_FILE = BACKEND_DIR / ".ml_storage_state.json"
PROFILE_DIR = BACKEND_DIR / ".ml_chrome_profile"
PROFILE_LOCK_FILE = BACKEND_DIR / ".ml_chrome_profile.lock"
LAST_OK_FILE = BACKEND_DIR / ".ml_session_last_ok"
EXPIRED_FILE = BACKEND_DIR / ".ml_session_expired"
ALERT_SENT_FILE = BACKEND_DIR / ".ml_session_alert_sent"
SCREENSHOT_DIR = BACKEND_DIR / ".ml_login_screenshots"

PORTAL_URL = "https://www.mercadolivre.com.br/afiliados/hub#menu-lateral"
USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"


def _load_env() -> dict:
    env = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                env[k.strip()] = v.strip()
    return env


def _cleanup_singleton_lock():
    for name in ("SingletonLock", "SingletonCookie", "SingletonSocket"):
        p = PROFILE_DIR / name
        if p.exists():
            try:
                if p.is_symlink() or p.is_file():
                    p.unlink()
                else:
                    shutil.rmtree(p, ignore_errors=True)
            except Exception:
                pass


class LoginResult:
    def __init__(self, success: bool, message: str, screenshot_path: str = None, needs_vnc: bool = False):
        self.success = success
        self.message = message
        self.screenshot_path = screenshot_path
        self.needs_vnc = needs_vnc


async def do_telegram_login(progress_cb=None) -> LoginResult:
    """Faz login automático no ML Afiliados.
    progress_cb: async callback function(str) para atualizar status no Telegram.
    """
    async def _progress(msg: str):
        if progress_cb:
            try:
                await progress_cb(msg)
            except Exception:
                pass

    env = _load_env()
    email = env.get("ML_AFFILIATE_EMAIL", "")
    password = env.get("ML_AFFILIATE_PASSWORD", "")

    if not email or not password:
        return LoginResult(False, "❌ ML_AFFILIATE_EMAIL ou ML_AFFILIATE_PASSWORD não configurados no .env")

    await _progress("🔄 Abrindo navegador no servidor...")

    # Garante DISPLAY para headless=False (backend systemd não tem DISPLAY)
    os.environ.setdefault("DISPLAY", ":99")

    # Lock do perfil
    import fcntl
    lock_fd = None
    try:
        lock_fd = open(PROFILE_LOCK_FILE, "w")
        fcntl.flock(lock_fd.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        lock_fd.write(str(os.getpid()))
        lock_fd.flush()
    except (IOError, OSError):
        if lock_fd:
            lock_fd.close()
            lock_fd = None
        return LoginResult(False, "❌ Perfil Chromium em uso pelo scraper. Tente novamente em alguns minutos.")

    _cleanup_singleton_lock()
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)

    try:
        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            chromium_path = None
            for path in ["/usr/bin/chromium-browser", "/usr/bin/chromium", "/usr/bin/google-chrome"]:
                if Path(path).exists():
                    chromium_path = path
                    break

            # Headless=False para reCAPTCHA funcionar melhor
            persistent_kwargs = {
                "user_data_dir": str(PROFILE_DIR),
                "headless": False,
                "viewport": {"width": 1280, "height": 800},
                "user_agent": USER_AGENT,
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

            context = await p.chromium.launch_persistent_context(**persistent_kwargs)
            page = await context.new_page()

            # Aplica stealth
            try:
                from playwright_stealth import Stealth
                await Stealth(
                    navigator_user_agent_override=USER_AGENT,
                    navigator_languages_override=("pt-BR", "pt"),
                    navigator_platform_override="Linux x86_64",
                ).apply_stealth_async(page)
            except Exception:
                pass

            # Carrega cookies do storage_state no perfil (caso perfil esteja desatualizado)
            if STORAGE_STATE_FILE.exists():
                try:
                    state = json.loads(STORAGE_STATE_FILE.read_text())
                    state_cookies = state.get("cookies", [])
                    if state_cookies:
                        await context.add_cookies(state_cookies)
                        await _progress(f"📋 {len(state_cookies)} cookies carregados do backup")
                except Exception as e:
                    logger_warning(f"Erro ao carregar storage_state: {e}")

            await _progress("🌐 Navegando para o portal de afiliados...")
            await page.goto(PORTAL_URL, wait_until="domcontentloaded", timeout=60000)
            await page.wait_for_timeout(3000)

            # Verifica se já está logado
            current_url = page.url.lower()
            if "afiliados" in current_url and "login" not in current_url and "auth" not in current_url:
                await _save_session(context)
                await _clear_expired_flags()
                await context.close()
                return LoginResult(True, "✅ Já estava logado! Sessão renovada.")

            await _progress("📧 Preenchendo email...")
            screenshot1 = SCREENSHOT_DIR / "step1_email.png"
            await page.screenshot(path=str(screenshot1))

            # Preenche email
            try:
                email_input = page.locator(
                    'input[name="user_id"], input[name="email"], input[type="email"], '
                    'input[placeholder*="e-mail" i], input[placeholder*="email" i]'
                ).first
                await email_input.fill(email)
                await page.wait_for_timeout(500)

                # Clica continuar
                continue_btn = page.locator(
                    'button[type="submit"], button:has-text("Continuar"), '
                    'button:has-text("Continue"), input[type="submit"]'
                ).first
                await continue_btn.click()
                await page.wait_for_timeout(4000)
            except Exception as e:
                screenshot = SCREENSHOT_DIR / "error_email.png"
                await page.screenshot(path=str(screenshot))
                await context.close()
                return LoginResult(False, f"❌ Erro ao preencher email: {e}", str(screenshot), True)

            await _progress("🔒 Preenchendo senha...")
            screenshot2 = SCREENSHOT_DIR / "step2_password.png"
            await page.screenshot(path=str(screenshot2))

            # Verifica se tem reCAPTCHA antes da senha
            current_url = page.url.lower()
            page_text = ""
            try:
                page_text = await page.content()
            except Exception:
                pass

            # Preenche senha
            try:
                password_input = page.locator('input[name="password"], input[type="password"]').first
                await password_input.fill(password)
                await page.wait_for_timeout(500)
            except Exception as e:
                # Pode ser que o reCAPTCHA esteja bloqueando
                screenshot = SCREENSHOT_DIR / "error_password.png"
                await page.screenshot(path=str(screenshot))
                await context.close()
                return LoginResult(
                    False,
                    f"❌ Não consegui preencher a senha. Pode ser reCAPTCHA bloqueando.\nConecta via VNC para resolver.",
                    str(screenshot),
                    True,
                )

            await _progress("🤖 Tentando reCAPTCHA...")

            # Tenta clicar no reCAPTCHA checkbox
            recaptcha_passed = False
            try:
                # Tenta clicar no checkbox do reCAPTCHA v2
                recaptcha_frame = page.frame_locator('iframe[title*="reCAPTCHA"], iframe[src*="recaptcha"]')
                checkbox = recaptcha_frame.locator('.recaptcha-checkbox-border, #recaptcha-anchor')
                if await checkbox.count() > 0:
                    await checkbox.first.click()
                    await page.wait_for_timeout(3000)
                    # Verifica se passou
                    aria_checked = await checkbox.first.get_attribute("aria-checked")
                    if aria_checked == "true":
                        recaptcha_passed = True
                        await _progress("✅ reCAPTCHA passado automaticamente!")
            except Exception:
                pass

            # Clica em Entrar/Iniciar sessão
            await _progress("🔑 Clicando em Entrar...")
            try:
                submit_btn = page.locator(
                    'button[type="submit"], button:has-text("Entrar"), '
                    'button:has-text("Iniciar sessão"), input[type="submit"]'
                ).first
                await submit_btn.click()
                await page.wait_for_timeout(5000)
            except Exception as e:
                screenshot = SCREENSHOT_DIR / "error_submit.png"
                await page.screenshot(path=str(screenshot))
                await context.close()
                return LoginResult(False, f"❌ Erro ao clicar em Entrar: {e}", str(screenshot), True)

            # Verifica resultado
            await _progress("⏳ Verificando login...")
            final_url = page.url.lower()
            screenshot_final = SCREENSHOT_DIR / "step3_final.png"
            await page.screenshot(path=str(screenshot_final))

            # Verifica se tem challenge de imagem do reCAPTCHA
            page_content = ""
            try:
                page_content = await page.content()
            except Exception:
                pass

            has_image_challenge = (
                "recaptcha" in page_content.lower() and
                ("image" in page_content.lower() or "challenge" in page_content.lower()) and
                "afiliados" not in final_url
            )

            if "afiliados" in final_url and "login" not in final_url and "auth" not in final_url:
                # Login sucesso!
                await _save_session(context)
                await _clear_expired_flags()
                await context.close()
                await _progress("✅ Login realizado com sucesso!")
                return LoginResult(True, "✅ Login no ML Afiliados realizado! Sessão salva e renovada.")

            if has_image_challenge or ("recaptcha" in page_content.lower() and "afiliados" not in final_url):
                # reCAPTCHA challenge de imagem — precisa VNC
                await context.close()
                await _progress("⚠️ reCAPTCHA challenge de imagem detectado")
                return LoginResult(
                    False,
                    "⚠️ O ML pediu challenge de imagem do reCAPTCHA.\n\n"
                    "Não consigo resolver automaticamente. Conecta via VNC:\n"
                    "```\nssh -L 6080:localhost:6080 alessandro@192.168.15.45\n```\n"
                    "Depois acessa: http://localhost:6080/vnc.html\n\n"
                    "O navegador já está aberto na tela do captcha.",
                    str(screenshot_final),
                    True,
                )

            # Verifica se pediu 2FA
            if "two-factor" in page_content.lower() or "2fa" in page_content.lower() or "verificação" in page_content.lower():
                await context.close()
                await _progress("📱 2FA necessário")
                return LoginResult(
                    False,
                    "📱 O ML pediu verificação 2FA.\n\n"
                    "Conecta via VNC para completar:\n"
                    "```\nssh -L 6080:localhost:6080 alessandro@192.168.15.45\n```\n"
                    "Depois acessa: http://localhost:6080/vnc.html",
                    str(screenshot_final),
                    True,
                )

            # Não conseguiu detectar o que aconteceu
            await context.close()
            await _progress("❓ Login não confirmado")
            return LoginResult(
                False,
                "❓ Não consegui confirmar o login. Veja o screenshot.\n"
                "Se necessário, conecta via VNC para completar manualmente.",
                str(screenshot_final),
                True,
            )

    except Exception as e:
        return LoginResult(False, f"❌ Erro durante login: {e}")
    finally:
        if lock_fd:
            try:
                fcntl.flock(lock_fd.fileno(), fcntl.LOCK_UN)
                lock_fd.close()
            except Exception:
                pass
        try:
            PROFILE_LOCK_FILE.unlink(missing_ok=True)
        except Exception:
            pass


async def _save_session(context):
    """Salva storage state e cookies."""
    try:
        await context.storage_state(path=str(STORAGE_STATE_FILE))
    except Exception:
        pass
    try:
        cookies = await context.cookies()
        COOKIES_FILE.write_text(json.dumps(cookies, indent=2))
    except Exception:
        pass
    try:
        LAST_OK_FILE.write_text(datetime.now(timezone.utc).isoformat())
    except Exception:
        pass


def _clear_expired_flags():
    """Limpa flags de expiração."""
    for f in [EXPIRED_FILE, ALERT_SENT_FILE]:
        try:
            f.unlink(missing_ok=True)
        except Exception:
            pass
