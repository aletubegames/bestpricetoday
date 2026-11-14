"""Busca textual tolerante a acento, hífen/espaço e erro de digitação.

Espelha no Python as funções SQL da migração e7f8a9b0c1d2:

- ``bpt_norm(text)``  → ``normalize()``: minúsculo, sem acento (NFKD),
  não-alfanumérico vira espaço, strip.
- ``bpt_compact(text)`` → ``compact()``: ``normalize`` sem espaços.

``match_all``/``match_cols`` geram cláusulas SQLAlchemy sobre
``bpt_compact(col)``/``bpt_norm(col)`` (índices GIN trigram em prod).
Em binds que não são PostgreSQL (SQLite dos testes) caem pro fallback
``lower(col) LIKE %tok%`` — sem os benefícios, mas funcional.

``fuzzy_clause``/``fuzzy_rank`` usam ``word_similarity`` do pg_trgm
(só PostgreSQL — chamar apenas quando ``is_pg(bind)`` for True).
"""
import re
import unicodedata

from sqlalchemy import and_, func, or_

# Stopwords pt-BR — movidas de providers/mercadolivre.py (compartilhadas).
STOPWORDS = {"de", "da", "do", "para", "com", "em", "e", "o", "a", "os", "as", "um", "uma"}

_NON_ALNUM = re.compile(r"[^a-z0-9]+")


def normalize(text: str | None) -> str:
    """Equivalente Python do ``bpt_norm``: lower, sem acento, [^a-z0-9]+ → espaço."""
    if not text:
        return ""
    t = unicodedata.normalize("NFKD", str(text).lower())
    t = "".join(c for c in t if not unicodedata.combining(c))
    return _NON_ALNUM.sub(" ", t).strip()


def compact(text: str | None) -> str:
    """Equivalente Python do ``bpt_compact``."""
    return normalize(text).replace(" ", "")


def tokens(query: str | None, max_tokens: int = 8) -> list[str]:
    """Tokens da query para match compacto: sem stopwords, len > 1, máx 8.

    Todos saem de ``normalize`` → só [a-z0-9], seguros para LIKE sem escape.
    """
    if not query:
        return []
    return [
        t
        for t in normalize(query).split()
        if t not in STOPWORDS and len(t) > 1
    ][:max_tokens]


def is_pg(obj) -> bool:
    """True se o bind/session/engine recebido é PostgreSQL.

    Aceita AsyncSession, Session, Engine ou AsyncEngine.
    """
    try:
        # Engine/AsyncEngine direto
        eng = getattr(obj, "sync_engine", obj)
        dialect = getattr(eng, "dialect", None)
        if dialect is None:
            target = getattr(obj, "sync_session", obj) or obj
            bind = (
                target.get_bind()
                if hasattr(target, "get_bind")
                else getattr(target, "bind", None)
            )
            if bind is None:
                return False
            eng = (
                getattr(bind, "sync_engine", None)
                or getattr(bind, "engine", None)
                or bind
            )
            dialect = getattr(eng, "dialect", None)
        return getattr(dialect, "name", "") == "postgresql"
    except Exception:
        return False


def match_cols(cols, toks: list[str], pg: bool = True):
    """AND entre tokens; cada token casa em QUALQUER uma das colunas (OR).

    ``cols``: lista de colunas SQLAlchemy (ex.: title, category, notes).
    Retorna None se não houver tokens/colunas.
    """
    if not toks or not cols:
        return None
    if pg:
        return and_(
            *[
                or_(*[func.bpt_compact(c).like(f"%{t}%") for c in cols])
                for t in toks
            ]
        )
    return and_(
        *[
            or_(*[func.lower(c).like(f"%{t}%") for c in cols])
            for t in toks
        ]
    )


def match_all(column, toks: list[str], pg: bool = True):
    """AND: cada token aparece no ``bpt_compact`` da coluna.

    "air fryer" → {air, fryer} casa "Airfryer"; "airfryer" casa "Air Fryer";
    "eletrica" casa "Elétrica". Retorna None se não houver tokens.
    """
    return match_cols([column], toks, pg=pg)


def fuzzy_clause(column, query: str):
    """``word_similarity(normalize(query), bpt_norm(col)) >= 0.45``.

    Só PostgreSQL (pg_trgm) — chamar sob ``is_pg(bind)``.
    """
    return func.word_similarity(normalize(query), func.bpt_norm(column)) >= 0.45


def fuzzy_rank(column, query: str):
    """ORDER BY ``word_similarity`` desc. Só PostgreSQL."""
    return func.word_similarity(normalize(query), func.bpt_norm(column)).desc()
