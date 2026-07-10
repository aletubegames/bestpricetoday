"""
visitor_tracking.py — Registra visitantes online no Redis.

Usado pelo middleware do FastAPI para manter sessões ativas (TTL 5 min).
O endpoint /api/v1/admin/online consome essas chaves.
"""
from __future__ import annotations
import hashlib
import json
import time

from fastapi import Request
from app.core.cache import get_redis
from app.core.logging import logger


def _get_client_ip(request: Request) -> str:
    """Extrai IP real respeitando proxies / Cloudflare."""
    cf = request.headers.get("cf-connecting-ip")
    if cf:
        return cf.strip()
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    xri = request.headers.get("x-real-ip")
    if xri:
        return xri.strip()
    return request.client.host if request.client else "unknown"


def _anonymize_ip(ip: str) -> str:
    """Mascara os últimos octetos do IP por privacidade."""
    if ip in ("unknown", "127.0.0.1", "localhost", "0.0.0.0"):
        return ip
    if "." in ip:
        parts = ip.split(".")
        if len(parts) == 4 and all(p.isdigit() for p in parts):
            return f"{parts[0]}.{parts[1]}.xxx.xxx"
    if ":" in ip:
        parts = ip.split(":")
        if len(parts) >= 4:
            return ":".join(parts[:3]) + ":xxxx:xxxx"
    return ip


def _detect_device(ua: str) -> str:
    ua_l = ua.lower()
    if "tablet" in ua_l or "ipad" in ua_l:
        return "tablet"
    if (
        "mobile" in ua_l
        or "iphone" in ua_l
        or "android" in ua_l
        or "windows phone" in ua_l
    ):
        return "mobile"
    return "desktop"


def _detect_os(ua: str) -> str:
    ua_l = ua.lower()
    if "windows" in ua_l:
        return "Windows"
    if "mac os x" in ua_l or "darwin" in ua_l:
        return "macOS"
    if "iphone" in ua_l or "ipad" in ua_l or "ios" in ua_l:
        return "iOS"
    if "android" in ua_l:
        return "Android"
    if "cros" in ua_l or "chrome os" in ua_l:
        return "Chrome OS"
    if "linux" in ua_l:
        return "Linux"
    return "unknown"


def _detect_browser(ua: str) -> str:
    ua_l = ua.lower()
    if "edg" in ua_l:
        return "Edge"
    if "opera" in ua_l or "opr" in ua_l or "opt" in ua_l:
        return "Opera"
    if "samsungbrowser" in ua_l:
        return "Samsung Browser"
    if "chrome" in ua_l or "chromium" in ua_l or "crios" in ua_l:
        return "Chrome"
    if "firefox" in ua_l or "fxios" in ua_l:
        return "Firefox"
    if "safari" in ua_l:
        return "Safari"
    return "unknown"


def _geo_header(request: Request, *names: str) -> str:
    for name in names:
        val = (
            request.headers.get(name)
            or request.headers.get(name.replace("-", "_"))
            or ""
        )
        if val:
            return val.strip()
    return ""


def _is_real_browser(ua: str) -> bool:
    """Ignora requests sem UA ou de ferramentas/bots."""
    if not ua:
        return False
    lowered = ua.lower()
    ignored = (
        "curl", "wget", "python-requests", "urllib", "axios", "postman",
        "insomnia", "httpie", "node-fetch", "undici", "fastapi", "headlesschrome",
        "phantomjs", "selenium", "bot", "spider", "crawl", "scraper",
    )
    return not any(token in lowered for token in ignored)


async def track_visitor(request: Request) -> None:
    """
    Cria/atualiza uma chave visitor:<hash> no Redis para cada requisição.
    TTL de 5 minutos. Silencioso se Redis falhar.
    """
    path = request.url.path
    # Ignora rotas internas e estáticas para não poluir
    if path.startswith(("/static/", "/_next/", "/health", "/docs", "/redoc", "/openapi.json")):
        return

    ua = request.headers.get("user-agent", "")
    if not _is_real_browser(ua):
        return

    ip = _get_client_ip(request)
    ip_anon = _anonymize_ip(ip)

    # Hash identificador estável por IP + UA (não inclui path, para manter sessão)
    vid = hashlib.sha256(f"{ip}|{ua}".encode()).hexdigest()[:16]
    key = f"visitor:{vid}"

    try:
        r = await get_redis()
        now = time.time()
        raw = await r.get(key)

        if raw:
            data = json.loads(raw)
        else:
            data = {
                "hash": vid,
                "first_seen": now,
                "ip_anon": ip_anon,
                "pages": [],
            }

        data["last_seen"] = now
        data["device"] = _detect_device(ua)
        data["os"] = _detect_os(ua)
        data["browser"] = _detect_browser(ua)
        data["country"] = (
            _geo_header(request, "cf-ipcountry", "x-geo-country", "x-country-code")
            or "Desconhecido"
        )
        data["city"] = _geo_header(request, "cf-ipcity", "x-city") or ""
        data["region"] = (
            _geo_header(request, "cf-region", "cf-region-code", "x-region")
            or ""
        )

        pages = data.get("pages", [])
        pages.append({"path": path, "ts": now})
        # mantém histórico curto
        data["pages"] = pages[-20:]
        data["page_count"] = len(data["pages"])
        data["online_seconds"] = int(now - data.get("first_seen", now))
        data["current_page"] = data["pages"][-1]["path"] if data["pages"] else "/"

        await r.setex(key, 60, json.dumps(data))
    except Exception as exc:
        logger.warning(f"Visitor tracking failed for {path}: {exc}")
