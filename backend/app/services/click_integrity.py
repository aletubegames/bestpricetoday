"""
Integridade de cliques — classificação de bots e deduplicação.

Motivação (auditoria de 2026-10-19 em click_events):
  - 1093 cliques no total
  - 732 (67%) do crawler `facebookexternalhit` (preview de link)
  - boa parte dos cliques restantes vinha de um punhado de IPs
    (mesmo dispositivo IPv6 EUI-64 repetindo o mesmo produto até 18x)
  - cliques humanos plausíveis: ~9%

Este módulo centraliza:
  1. BOT_UA_PATTERNS / BOT_IP_NETWORKS — quem não é humano
  2. is_bot() — usado no registro do clique
  3. is_duplicate_click() — dedup 1 clique por (IP + oferta) por janela
     (default 60 min, configurável em CLICK_DEDUP_WINDOW_MINUTES)

Filosofia: falhar aberto. Se a checagem de dedup der erro, registra o clique
(perder um clique é pior que contar um a mais).
"""
import ipaddress
import os
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import ClickEvent

logger = logging.getLogger("click_integrity")


# User-Agents de bots/crawlers que NÃO representam cliques reais de usuários.
# Inclui auto-registros internos (distributor posta com UA python-httpx),
# previews de links (Facebook/Telegram/WhatsApp) e crawlers de SEO.
BOT_UA_PATTERNS = (
    # previews / redes sociais
    "facebookexternalhit", "meta-externalagent", "TelegramBot", "WhatsApp",
    "Slackbot", "Twitterbot", "Discordbot", "LinkedInBot", "Pinterestbot",
    "vkShare", "Iframely", "Embedly",
    # HTTP clients programáticos
    "python-httpx", "python-requests", "aiohttp", "curl/", "wget/",
    "Go-http-client", "okhttp/", "axios/", "node-fetch", "Java/",
    # crawlers de busca / SEO / analytics
    "GPTBot", "CCBot", "bingbot", "Googlebot", "Baiduspider", "YandexBot",
    "DuckDuckBot", "PetalBot", "ByteSpider", "Amazonbot", "Applebot",
    "SemrushBot", "AhrefsBot", "DataForSeoBot", "MJ12bot", "DotBot",
    "trendictionbot", "Mediatoolkitbot", "AwarioBot", "Brandwatch",
    "Screaming Frog", "SiteAuditBot",
    # headless / testes / preview de browser
    "HeadlessChrome", "Chrome-Lighthouse", "Lighthouse", "Google-Safety",
    "AHC/", "Nexus 5X", "PhantomJS", "SlimerJS", "Puppeteer", "Playwright",
)


# Faixas de IP de infraestrutura de crawler conhecida.
# Meta (Facebook/Instagram) — crawler que se passa por Chrome.
# Descoberto na auditoria: 2a03:2880::/29 aparecia com UA de navegador.
BOT_IP_NETWORKS = tuple(
    ipaddress.ip_network(net) for net in (
        "2a03:2880::/29",   # Meta Platforms Ireland (AS32934)
    )
)


def _dedup_window_minutes() -> int:
    try:
        return int(os.getenv("CLICK_DEDUP_WINDOW_MINUTES", "60"))
    except ValueError:
        return 60


def is_bot_user_agent(user_agent: str | None) -> bool:
    """True se o UA bate com qualquer padrão de bot conhecido."""
    if not user_agent:
        return False
    ua = user_agent.lower()
    return any(p.lower() in ua for p in BOT_UA_PATTERNS)


def is_bot_ip(ip_address: str | None) -> bool:
    """True se o IP pertence a uma faixa de infraestrutura de crawler."""
    if not ip_address:
        return False
    try:
        ip = ipaddress.ip_address(ip_address.strip())
    except ValueError:
        return False
    return any(ip in net for net in BOT_IP_NETWORKS)


def is_bot(user_agent: str | None, ip_address: str | None) -> bool:
    """Classificação combinada UA + IP."""
    return is_bot_user_agent(user_agent) or is_bot_ip(ip_address)


async def is_duplicate_click(
    db: AsyncSession,
    ip_address: str | None,
    offer_id: str | None,
    window_minutes: int | None = None,
) -> bool:
    """
    True se já existe clique do mesmo IP na mesma oferta dentro da janela.

    Sem IP ou sem oferta não há como deduplicar — retorna False.
    Falha aberto: qualquer exceção vira False (registra o clique).
    """
    if not ip_address or not offer_id:
        return False

    window = window_minutes if window_minutes is not None else _dedup_window_minutes()
    if window <= 0:
        return False

    cutoff = datetime.now(timezone.utc) - timedelta(minutes=window)
    try:
        result = await db.execute(
            select(ClickEvent.id)
            .where(
                ClickEvent.ip_address == ip_address,
                ClickEvent.offer_id == offer_id,
                ClickEvent.clicked_at >= cutoff,
            )
            .limit(1)
        )
        return result.scalar() is not None
    except Exception as exc:  # noqa: BLE001 — dedup nunca deve quebrar o redirect
        logger.warning("dedup check falhou (falha aberta): %s", exc)
        return False
