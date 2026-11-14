"""Helpers compartilhados do Marketplace FB (watcher + poster).

- Sessão: cookies exportados em .fb_cookies.json (perfil pessoal).
- Browser: Chromium real no Xvfb (DISPLAY=:99), nunca headless —
  fingerprint headless é detectável pela Meta.
- Toda espera é aleatorizada pra não parecer bot.
- Kill switch: se cair em login/checkpoint/CAPTCHA, alerta no Telegram
  e NÃO insiste (evita padrão de bot que derruba a conta).
"""
import json, os, random, time, urllib.request, urllib.parse

BASE = "/home/alessandro/backend"
COOKIES_FILE = f"{BASE}/.fb_cookies.json"
PROFILE_DIR = f"{BASE}/.fb_mkt_profile"
STATE_FILE = f"{BASE}/.fb_mkt_state.json"
QUEUE_DIR = f"{BASE}/fb_mkt_queue"
LOCK_FILE = f"{BASE}/.fb_mkt.lock"
PAUSE_FILE = f"{BASE}/.fb_mkt_paused"   # existe -> watcher/poster dormem

FB_UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
         "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")

LOGIN_MARKERS = ("login", "checkpoint", "two_factor", "captcha")


def h_sleep(a, b=None):
    """Sleep aleatório: h_sleep(3,8) -> entre 3 e 8s; h_sleep(5) -> 5s +-40%."""
    if b is None:
        a, b = a * 0.6, a * 1.4
    time.sleep(random.uniform(a, b))


def tg_alert(msg):
    """Alerta no Telegram do dono (mesmo bot do site)."""
    try:
        env = {}
        with open(f"{BASE}/.env") as f:
            for ln in f:
                if "=" in ln and not ln.startswith("#"):
                    k, v = ln.strip().split("=", 1)
                    env[k] = v
        token = env.get("TELEGRAM_BOT_TOKEN")
        chat = env.get("TELEGRAM_ADMIN_CHAT_ID") or env.get("TELEGRAM_CHAT_ID")
        if not token or not chat:
            print("tg_alert sem token/chat:", msg[:80])
            return
        data = urllib.parse.urlencode(
            {"chat_id": chat, "text": msg[:3800]}).encode()
        urllib.request.urlopen(
            f"https://api.telegram.org/bot{token}/sendMessage",
            data=data, timeout=15)
    except Exception as e:
        print("tg_alert falhou:", e)


def load_cookies():
    with open(COOKIES_FILE) as f:
        return json.load(f)


def load_state():
    try:
        with open(STATE_FILE) as f:
            return json.load(f)
    except Exception:
        return {"seen": {}, "replied": {}, "posted_log": []}


def save_state(st):
    st["seen"] = dict(list(st["seen"].items())[-2000:])
    st["replied"] = dict(list(st["replied"].items())[-2000:])
    tmp = STATE_FILE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(st, f)
    os.replace(tmp, STATE_FILE)


def _chrome_path():
    for path in ("/usr/bin/chromium-browser", "/usr/bin/chromium",
                 "/usr/bin/google-chrome", "/opt/google/chrome/chrome"):
        if os.path.exists(path):
            return path
    return None


def open_browser(p, headless=False):
    """Chromium persistente no Xvfb. Retorna (browser_context, page)."""
    kwargs = dict(
        user_data_dir=PROFILE_DIR,
        headless=headless,
        args=["--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage",
              "--disable-blink-features=AutomationControlled",
              "--disable-features=IsolateOrigins,site-per-process",
              "--start-maximized"],
        user_agent=FB_UA,
        viewport={"width": 1366, "height": 850},
        locale="pt-BR",
        timezone_id="America/Sao_Paulo",
    )
    exe = _chrome_path()
    if exe:
        kwargs["executable_path"] = exe
    ctx = p.chromium.launch_persistent_context(**kwargs)
    ctx.add_cookies(load_cookies())
    page = ctx.pages[0] if ctx.pages else ctx.new_page()
    return ctx, page


def detect_block(page):
    """True se a Meta jogou login/checkpoint — retorna o motivo."""
    url = page.url.lower()
    for m in LOGIN_MARKERS:
        if m in url:
            return f"url:{m}"
    try:
        body = page.inner_text("body")[:3000].lower()
        for m in ("entre no facebook", "log into facebook",
                  "confirmar sua identidade", "unusual activity"):
            if m in body:
                return f"body:{m[:30]}"
    except Exception:
        pass
    return None


def pause_all(reason):
    """Cria PAUSE_FILE: watcher e poster dormem até intervenção."""
    with open(PAUSE_FILE, "w") as f:
        f.write(f"{time.strftime('%Y-%m-%d %H:%M')} {reason}\n")


def is_paused():
    return os.path.exists(PAUSE_FILE)
