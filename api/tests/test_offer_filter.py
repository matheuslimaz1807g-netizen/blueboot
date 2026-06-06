from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2].joinpath("executable")))

from offer_filter import daily_status, should_post


def make_config(tmp_path: Path, **overrides):
    config = {
        "enabled": True,
        "db_path": str(tmp_path / "offer_filter.sqlite3"),
        "max_posts_per_day": 2,
        "max_per_category_day": 1,
        "min_score": 40,
        "min_discount_pct": 25,
        "min_price": 15,
        "max_price": 500,
        "peak_hours": [],
    }
    config.update(overrides)
    return config


def test_should_post_approves_strong_offer_and_persists_status(tmp_path):
    text = """
    Canal de ofertas
    Fone JBL Bluetooth com frete gratis
    De R$ 199,90 por R$ 89,90 no Pix
    Cupom: AUDIO10
    https://example.com/produto
    """

    ok, offer = should_post(text, make_config(tmp_path))
    status = daily_status(make_config(tmp_path))

    assert ok is True
    assert offer.category == "eletronicos"
    assert offer.brand == "jbl"
    assert offer.discount_pct == 55.0
    assert offer.score >= 40
    assert status["postados_hoje"] == 1
    assert status["por_categoria"]["eletronicos"] == 1


def test_should_post_rejects_duplicate_even_after_new_call(tmp_path):
    config = make_config(tmp_path, max_per_category_day=5)
    text = "Oferta\nMouse sem fio Logitech\nDe R$ 120,00 por R$ 59,90\nhttps://example.com/a"

    first_ok, _ = should_post(text, config)
    second_ok, second_offer = should_post(text, config)

    assert first_ok is True
    assert second_ok is False
    assert second_offer.reject_reason == "duplicata"


def test_should_post_rejects_by_daily_category_limit(tmp_path):
    config = make_config(tmp_path, max_posts_per_day=10, max_per_category_day=1)
    first = "Oferta\nCarregador Anker USB-C\nDe R$ 180,00 por R$ 89,90\nhttps://example.com/a"
    second = "Oferta\nFone Samsung Bluetooth\nDe R$ 220,00 por R$ 99,90\nhttps://example.com/b"

    first_ok, _ = should_post(first, config)
    second_ok, second_offer = should_post(second, config)

    assert first_ok is True
    assert second_ok is False
    assert second_offer.reject_reason.startswith("limite de categoria")


def test_should_post_rejects_low_discount_when_original_price_exists(tmp_path):
    text = "Oferta genérica sem marca\nDe R$ 199,90 por R$ 179,90\nhttps://example.com/outros"

    ok, offer = should_post(text, make_config(tmp_path))

    assert ok is False
    assert "sem diferencial: desconto baixo (10.0%)" in offer.reject_reason


def test_should_post_can_be_disabled_without_persisting(tmp_path):
    config = make_config(tmp_path, enabled=False)

    ok, offer = should_post("Texto qualquer sem preco", config)
    status = daily_status(config)

    assert ok is True
    assert offer.reject_reason is None
    assert status["postados_hoje"] == 0


def test_should_post_uses_brazil_timezone(tmp_path, monkeypatch):
    from datetime import datetime, timezone, timedelta
    import offer_filter

    br_tz = timezone(timedelta(hours=-3))
    mock_now = datetime(2026, 6, 5, 22, 30, 0, tzinfo=br_tz)

    class MockDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            if tz is not None:
                return mock_now.astimezone(tz)
            return mock_now.replace(tzinfo=None)

    monkeypatch.setattr(offer_filter, "datetime", MockDateTime)

    config = make_config(tmp_path)
    text = "Oferta imperdivel JBL com frete gratis\nDe R$ 199,00 por R$ 89,00\nhttps://example.com"

    ok, offer = should_post(text, config)
    status = daily_status(config)

    assert status["data"] == "2026-06-05"
    assert status["postados_hoje"] == 1


def test_should_post_bypasses_daily_limit_for_premium_offers(tmp_path):
    config = make_config(tmp_path, max_posts_per_day=1, min_score=38)

    comum1 = "Oferta\nTenis Kappa\nDe R$ 100,00 por R$ 69,90\nhttps://example.com/kappa"
    ok1, offer1 = should_post(comum1, config)
    assert ok1 is True

    comum2 = "Oferta\nMeia Adidas\nDe R$ 40,00 por R$ 25,90\nhttps://example.com/adidas"
    ok2, offer2 = should_post(comum2, config)
    assert ok2 is False
    assert offer2.reject_reason.startswith("limite diário atingido")

    premium = """
    Oferta Imperdivel
    Celular Samsung Galaxy S23 com frete gratis e cupom
    De R$ 3999,00 por R$ 1199,00 no Pix
    Cupom: GALAXY100
    https://example.com/galaxy
    """
    ok3, offer3 = should_post(premium, config)
    assert offer3.score >= 70
    assert ok3 is True

