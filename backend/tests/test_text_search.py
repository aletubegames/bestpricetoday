"""Testes do text_search: normalize/tokens/compact e _score compacto dos providers."""
import os

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

from app.services import text_search
from app.services.providers.mercadolivre import _score as ml_score, _tokenize as ml_tokenize
from app.services.providers.amazon import _score as amz_score


# ─── normalize ───────────────────────────────────────────────────────────────

def test_normalize_unicode_e_espacos():
    assert text_search.normalize("  Café   COM\tLeite!! ") == "cafe com leite"
    assert text_search.normalize("Fritadeira Elétrica") == "fritadeira eletrica"
    assert text_search.normalize("") == ""
    assert text_search.normalize(None) == ""


def test_normalize_hifen_e_pontuacao():
    # não-alfanumérico vira espaço (não remove)
    assert text_search.normalize("Air-Fryer 4,2L") == "air fryer 4 2l"
    assert text_search.normalize("iPhone_15!!!Pro") == "iphone 15 pro"


# ─── compact ─────────────────────────────────────────────────────────────────

def test_compact_remove_espacos():
    # Espelha bpt_compact do Postgres
    assert text_search.compact("Fritadeira Elétrica Air-Fryer 4,2L") == "fritadeiraeletricaairfryer42l"
    assert text_search.compact("iPhone 15 Pro") == "iphone15pro"
    assert text_search.compact("") == ""
    assert text_search.compact(None) == ""


# ─── tokens ──────────────────────────────────────────────────────────────────

def test_tokens_stopwords():
    assert text_search.tokens("fritadeira de air fryer") == ["fritadeira", "air", "fryer"]
    assert text_search.tokens("fone de ouvido para celular") == ["fone", "ouvido", "celular"]
    # stopwords PT: de/da/do/para/com/em/e/o/a/os/as/um/uma
    assert "de" not in text_search.tokens("air fryer de 5 litros")


def test_tokens_len_e_max():
    # len > 1: tokens de 1 char caem ("a", "4"); len == 2 passam ("tv", "4k")
    assert text_search.tokens("tv 4k") == ["tv", "4k"]
    assert text_search.tokens("a o e") == []
    # máx 8 tokens
    many = " ".join(f"palavra{i}" for i in range(12))
    assert len(text_search.tokens(many)) == 8


def test_tokens_hifen_e_acento():
    assert text_search.tokens("smart-watch") == ["smart", "watch"]
    assert text_search.tokens("Elétrica") == ["eletrica"]
    assert text_search.tokens("iphone15") == ["iphone15"]


# ─── is_pg ───────────────────────────────────────────────────────────────────

def test_is_pg_none_e_objeto_qualquer():
    assert text_search.is_pg(None) is False
    assert text_search.is_pg(object()) is False


# ─── _score compacto (providers) ─────────────────────────────────────────────

def test_ml_score_airfryer_casa_air_fryer():
    # "airfryer" (query colada) deve pontuar > 0 em título "Air Fryer"
    assert ml_score("Philips Air Fryer 4,2L", ["airfryer"]) > 0
    # e o inverso: tokens separados casam título colado
    assert ml_score("Philips Airfryer", ["air", "fryer"]) == 1.0
    # acento não zera
    assert ml_score("Fritadeira Elétrica 220V", ["eletrica"]) == 1.0
    # irrelevante continua 0
    assert ml_score("Smartwatch Samsung", ["airfryer"]) == 0.0


def test_amazon_score_compacto():
    assert amz_score("Echo Dot 5ª Geração", ["echo", "dot"]) > 0
    assert amz_score("Smart TV 50 Polegadas", ["smarttv"]) > 0
