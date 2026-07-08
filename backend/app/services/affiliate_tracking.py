"""Helper compartilhado para injeção de tracking de afiliado em URLs.

Centraliza a lógica de adicionar matt_word/matt_tool (Mercado Livre)
em URLs de afiliado. Usado por:
- links.py (redirect /r/{code} e /r/{code}/go)
- affiliate.py (endpoints de cupons e produtos)
- ml_coupon_scraper.py (ao salvar product_url no banco)

Regras:
- URLs meli.la/* NÃO são modificadas (atribuição vem da conta geradora;
  parâmetros anexados se perdem no redirect do ML).
- URLs mercadolivre.com.br/* e mercadolivre.com/* recebem matt_word+matt_tool.
- matt_word/matt_tool pré-existentes são REMOVIDOS e substituídos pelos
  canônicos do settings (evita duplicação com valores conflitantes —
  o ML lê o primeiro parâmetro, que poderia ser um matt_tool antigo).
- Se ML_AFFILIATE_MATT_WORD ou ML_AFFILIATE_MATT_TOOL estiverem vazios,
  retorna a URL original (no-op).
- Fragmentos (#...) são preservados no final da URL.
"""
from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse

from app.core.config import settings

_ML_HOSTS = ("mercadolivre.com.br", "mercadolivre.com", "www.mercadolivre.com.br", "www.mercadolivre.com")


def add_ml_affiliate_tracking(url: str) -> str:
    """Adiciona matt_word + matt_tool em URLs do Mercado Livre.

    Retorna a URL original (inalterada) se:
    - url for vazia/None
    - não for URL do domínio mercadolivre.com(.br)
    - MATT_WORD ou MATT_TOOL não estiverem configurados

    matt_word/matt_tool pré-existentes são substituídos pelos canônicos.
    """
    if not url:
        return url
    if not settings.ML_AFFILIATE_MATT_WORD or not settings.ML_AFFILIATE_MATT_TOOL:
        return url

    # Só injeta em URLs do domínio do ML (não em meli.la)
    try:
        parsed = urlparse(url)
        host = parsed.hostname or ""
    except Exception:
        return url
    if not any(host == h or host.endswith("." + h) for h in _ML_HOSTS):
        return url

    # Remove matt_word/matt_tool antigos e adiciona os canônicos no final
    query = [(k, v) for k, v in parse_qsl(parsed.query, keep_blank_values=True)
             if k not in ("matt_word", "matt_tool")]
    query.append(("matt_word", settings.ML_AFFILIATE_MATT_WORD))
    query.append(("matt_tool", settings.ML_AFFILIATE_MATT_TOOL))

    return urlunparse(parsed._replace(query=urlencode(query)))
