"""Testes do verificador de preço: compute_verdict, parse_start_payload,
build_history_narration e _youtube_title com histórico.
"""
import os

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from app.services.price_verdict import compute_verdict, VERDICT_LABELS
from app.workers.bestprice_bot import parse_start_payload
from app.workers.distributor import build_history_narration, _youtube_title, _price_matches

UTC = timezone.utc


def _pt(day_offset: int, hour: int = 12, price: float = 100.0, base=None):
    """Ponto (recorded_at, price) — day_offset dias antes de NOW."""
    base = base or NOW
    return (base - timedelta(days=day_offset)).replace(hour=hour, minute=0, second=0, microsecond=0), price


# NOW fixo: 2026-11-20 15:00 UTC = 12:00 em São Paulo (dia 20/11 local)
NOW = datetime(2026, 11, 20, 15, 0, 0, tzinfo=UTC)


def _history_10d(price: float = 100.0, today_price: float | None = None):
    """10 dias de histórico a `price` + snapshot de hoje (opcional)."""
    pts = [_pt(i, price=price) for i in range(1, 11)]
    if today_price is not None:
        pts.append(_pt(0, price=today_price))
    return pts


# ─── compute_verdict ─────────────────────────────────────────────────────────

def test_verdict_menor_preco():
    # 10 dias a R$100, hoje R$80 → menor preço já registrado
    v = compute_verdict(80.0, _history_10d(100.0, today_price=80.0), now=NOW)
    assert v["verdict"] == "menor_preco"
    assert v["verdict_label"] == VERDICT_LABELS["menor_preco"]
    assert v["min_price"] == 100.0
    assert v["median_30"] == 100.0
    assert v["pct_vs_median"] == 20.0
    assert v["days_monitored"] == 11


def test_verdict_abaixo_media():
    # min histórico R$80 (1 dia), resto R$100 → atual R$90: acima do min,
    # mas 10% abaixo da mediana → abaixo_media (não é menor preço)
    pts = [_pt(i, price=100.0) for i in range(2, 11)] + [_pt(1, price=80.0)]
    v = compute_verdict(90.0, pts, now=NOW)
    assert v["verdict"] == "abaixo_media"
    assert v["min_price"] == 80.0
    assert v["pct_vs_median"] == 10.0


def test_verdict_normal():
    v = compute_verdict(100.0, _history_10d(100.0), now=NOW)
    assert v["verdict"] == "normal"
    assert v["verdict_label"] == VERDICT_LABELS["normal"]


def test_verdict_acima_media():
    v = compute_verdict(110.0, _history_10d(100.0), now=NOW)
    assert v["verdict"] == "acima_media"
    assert v["pct_vs_median"] == -10.0


def test_verdict_sem_historico_menos_7_dias():
    # 5 dias de histórico → sem_historico, mas min/max/median preenchidos
    pts = [_pt(i, price=100.0) for i in range(1, 6)]
    v = compute_verdict(90.0, pts, now=NOW)
    assert v["verdict"] == "sem_historico"
    assert v["min_price"] == 100.0
    assert v["max_price"] == 100.0
    assert v["median_30"] == 100.0
    assert v["days_monitored"] == 5


def test_hoje_fora_do_min_e_mediana():
    # Snapshot de hoje com preço mínimo absoluto NÃO pode virar min_price/median
    pts = _history_10d(100.0, today_price=1.0)
    v = compute_verdict(95.0, pts, now=NOW)
    assert v["min_price"] == 100.0
    assert v["median_30"] == 100.0
    assert v["days_monitored"] == 11  # hoje conta nos dias monitorados
    assert v["sparkline"][-1]["p"] == 1.0  # mas entra no sparkline


def test_fuso_agrupa_dia_local_sp():
    # 01:00 UTC de 18/11 = 22:00 de 17/11 em São Paulo → dia local 17/11.
    # 01:00 UTC de 19/11 e 12:00 UTC de 18/11 → ambos dia local 18/11 em SP;
    # vale o ÚLTIMO recorded_at (19/11 01:00 UTC > 18/11 12:00 UTC) → 50.0.
    pts = [
        (datetime(2026, 11, 18, 1, 0, tzinfo=UTC), 33.0),   # 17/11 22h SP
        (datetime(2026, 11, 19, 1, 0, tzinfo=UTC), 50.0),   # 18/11 22h SP (último)
        (datetime(2026, 11, 18, 12, 0, tzinfo=UTC), 80.0),  # 18/11 09h SP
    ]
    pts += [_pt(i, price=100.0) for i in range(3, 13)]
    v = compute_verdict(100.0, pts, now=NOW)
    d17 = [p for p in v["sparkline"] if p["d"] == "2026-11-17"]
    d18 = [p for p in v["sparkline"] if p["d"] == "2026-11-18"]
    assert len(d17) == 1 and d17[0]["p"] == 33.0
    assert len(d18) == 1 and d18[0]["p"] == 50.0


def test_dois_pontos_mesmo_dia_ultimo_vence():
    pts = [
        (datetime(2026, 11, 18, 10, 0, tzinfo=UTC), 70.0),
        (datetime(2026, 11, 18, 20, 0, tzinfo=UTC), 90.0),  # mais tarde → vence
    ]
    pts += [_pt(i, price=100.0) for i in range(3, 13)]
    v = compute_verdict(100.0, pts, now=NOW)
    day18 = [p for p in v["sparkline"] if p["d"] == "2026-11-18"]
    assert len(day18) == 1
    assert day18[0]["p"] == 90.0


def test_rise_pct_21d_detectado():
    # today-21d = 2026-10-30 → older = prev < 30/10 (offsets 22+), recent = offsets 1-21
    pts = []
    for i in range(22, 32):   # 22-31 dias atrás → older (9 pontos a R$100)
        pts.append(_pt(i, price=100.0))
    for i in range(1, 22):    # 1-21 dias atrás → recent (21 pontos a R$120)
        pts.append(_pt(i, price=120.0))
    v = compute_verdict(120.0, pts, now=NOW)
    assert v["rise_pct_21d"] == 20.0


def test_rise_pct_21d_abaixo_de_10_retorna_none():
    pts = []
    for i in range(22, 32):
        pts.append(_pt(i, price=100.0))
    for i in range(1, 22):
        pts.append(_pt(i, price=105.0))  # +5% → abaixo do threshold
    v = compute_verdict(105.0, pts, now=NOW)
    assert v["rise_pct_21d"] is None


def test_rise_suprimido_quando_menor_preco():
    # Caso real (Teclado Redragon): ~200 por 24d, pico 220 nos offsets
    # 19-21, depois 162, últimos 4 dias 138, atual 137.91.
    # rise cru seria 220/200-1 = 10% — mas verdict=menor_preco zera o badge.
    pts = [_pt(i, price=200.0) for i in range(22, 46)]   # 24d baseline
    pts += [_pt(i, price=220.0) for i in (19, 20, 21)]   # pico
    pts += [_pt(i, price=162.0) for i in range(5, 19)]   # depois do pico
    pts += [_pt(i, price=138.0) for i in range(1, 5)]    # últimos 4 dias
    v = compute_verdict(137.91, pts, now=NOW)
    assert v["verdict"] == "menor_preco"
    assert v["min_price"] == 138.0
    assert v["median_30"] == 162.0
    assert v["rise_pct_21d"] is None


def test_rise_mantido_quando_preco_nao_esta_baixo():
    # "Black Fraude": 200 por 25d, subiu p/ 260 nos últimos 10d, voltou a 200.
    # median_30=200 → verdict normal (nem menor nem abaixo) → badge fica.
    pts = [_pt(i, price=200.0) for i in range(11, 36)]   # 25d baseline
    pts += [_pt(i, price=260.0) for i in range(1, 11)]   # últimos 10d
    v = compute_verdict(200.0, pts, now=NOW)
    assert v["verdict"] == "normal"
    assert v["rise_pct_21d"] == 30.0


def test_rise_spike_de_1_dia_nao_conta():
    # 150 estável + UM dia a 499 na janela recente (erro de coleta, caso real
    # do Smartwatch Peje Pro). Pico = 2º maior → 150 → rise 0% → None.
    pts = [_pt(i, price=150.0) for i in range(1, 41) if i != 5]
    pts.append(_pt(5, price=499.0))
    v = compute_verdict(151.0, pts, now=NOW)
    assert v["verdict"] == "normal"
    assert v["min_price"] == 150.0
    assert v["rise_pct_21d"] is None


# ─── parse_start_payload ─────────────────────────────────────────────────────

def test_parse_start_payload_valido():
    uid = uuid.uuid4()
    assert parse_start_payload(f"bf_{uid}") == uid


def test_parse_start_payload_sem_prefixo():
    uid = uuid.uuid4()
    assert parse_start_payload(str(uid)) is None
    assert parse_start_payload("abc123") is None
    assert parse_start_payload("") is None
    assert parse_start_payload(None) is None


def test_parse_start_payload_uuid_invalido():
    assert parse_start_payload("bf_nao-e-uuid") is None
    assert parse_start_payload("bf_") is None
    assert parse_start_payload("bf_123") is None


# ─── build_history_narration ─────────────────────────────────────────────────

def _hist(verdict="menor_preco", median=130.0, days=30):
    return {
        "verdict": verdict,
        "median_30": median,
        "days_monitored": days,
    }


def test_narration_menor_preco():
    n = build_history_narration("Fone Bluetooth", 99.9, _hist("menor_preco"), NOW)
    assert n is not None
    assert "menor preço que já registramos" in n
    assert "monitor" in n and "30 dias" in n
    assert "descrição" in n  # CTA link na descrição


def test_narration_abaixo_media():
    n = build_history_narration("Fone Bluetooth", 120.0, _hist("abaixo_media", median=140.0), NOW)
    assert n is not None
    assert "abaixo da média dos últimos trinta dias" in n


def test_narration_normal_retorna_none():
    assert build_history_narration("Fone", 100.0, _hist("normal"), NOW) is None
    assert build_history_narration("Fone", 100.0, {}, NOW) is None
    assert build_history_narration("Fone", 100.0, None, NOW) is None


def test_narration_gancho_black_friday():
    # 20/11 → período Black Friday
    now_bf = datetime(2026, 11, 20, 15, 0, tzinfo=UTC)
    n = build_history_narration("Fone", 99.9, _hist("menor_preco"), now_bf)
    assert n.startswith("Black Friday: esse desconto é real?")
    # 05/11 → fora do período
    now_out = datetime(2026, 11, 5, 15, 0, tzinfo=UTC)
    n2 = build_history_narration("Fone", 99.9, _hist("menor_preco"), now_out)
    assert n2.startswith("Esse desconto é real?")
    assert "Black Friday" not in n2


# ─── _youtube_title com histórico ────────────────────────────────────────────

def test_youtube_title_com_history_menor_preco():
    offer = {
        "title": "Fone Bluetooth TWS Pro Max com cancelamento de ruído",
        "final_price": 99.9,
        "history": _hist("menor_preco", days=30),
    }
    t = _youtube_title(offer)
    assert len(t) <= 100
    assert "menor preço" in t


def test_youtube_title_com_history_abaixo_media():
    offer = {
        "title": "Smartwatch Samsung Galaxy Watch com GPS",
        "final_price": 450.0,
        "history": _hist("abaixo_media", days=20),
    }
    t = _youtube_title(offer)
    assert len(t) <= 100
    assert "abaixo da média de 30 dias" in t


def test_youtube_title_sem_history_comportamento_atual():
    offer = {"title": "Produto Qualquer", "final_price": 50.0}
    t = _youtube_title(offer)
    assert len(t) <= 100
    assert "menor preço em" not in t or "Black Friday" not in t


def test_youtube_title_history_sufixo_intacto_titulo_longo():
    # Título comprido: o sufixo factual NUNCA pode ser cortado — só o nome
    # do produto é encurtado (com "…").
    offer = {
        "title": "Fritadeira Airfryer Elétrica Philips Walita Série 5000 Digital 5 Litros Inox 220V Com Timer e 8 Programações",
        "final_price": 129.0,
        "history": _hist("menor_preco", days=45),
    }
    with patch("app.workers.distributor._is_black_friday_period", return_value=False):
        t = _youtube_title(offer)
    assert len(t) <= 100
    assert t.endswith("— menor preço em 45 dias")
    assert "…" in t  # nome do produto foi encurtado
    assert not t.startswith("Black Friday:")


def test_youtube_title_history_prefixo_bf_sufixo_intacto():
    offer = {
        "title": "Fritadeira Airfryer Elétrica Philips Walita Série 5000 Digital 5 Litros Inox 220V Com Timer e 8 Programações",
        "final_price": 129.0,
        "history": _hist("menor_preco", days=45),
    }
    with patch("app.workers.distributor._is_black_friday_period", return_value=True):
        t = _youtube_title(offer)
    assert len(t) <= 100
    assert t.startswith("Black Friday: ")
    assert t.endswith("— menor preço em 45 dias")


def test_youtube_title_history_abaixo_media_sufixo_intacto():
    offer = {
        "title": "Smartphone Samsung Galaxy A55 5G 256GB Tela 6.6 AMOLED Câmera Tripla 50MP Selfie 32MP",
        "final_price": 450.0,
        "history": _hist("abaixo_media", days=20),
    }
    with patch("app.workers.distributor._is_black_friday_period", return_value=True):
        t = _youtube_title(offer)
    assert len(t) <= 100
    assert t.endswith(": abaixo da média de 30 dias")


# ─── _price_matches ──────────────────────────────────────────────────────────

def test_price_matches():
    assert _price_matches(100.0, 100.0) is True    # igual
    assert _price_matches(100.9, 100.0) is True   # 0,9% acima → dentro de 1%
    assert _price_matches(99.5, 100.0) is True    # 0,5% abaixo → dentro de 1%
    assert _price_matches(101.5, 100.0) is False  # 1,5% acima → fora
    assert _price_matches(98.4, 100.0) is False   # 1,6% abaixo → fora
    assert _price_matches(None, 100.0) is False
    assert _price_matches(100.0, None) is False
    assert _price_matches(0, 100.0) is False
    assert _price_matches(100.0, 0) is False
    assert _price_matches(-10, 100.0) is False
    assert _price_matches("abc", 100.0) is False
