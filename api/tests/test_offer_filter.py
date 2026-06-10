from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2].joinpath("executable")))

from offer_filter import daily_status, should_post


def make_config(tmp_path: Path, **overrides):
    config = {
        "enabled": True,
        "db_path": str(tmp_path / "offer_filter.sqlite3"),
        "max_posts_per_day": 10,
        "max_per_category_day": 2,
        "min_score": 60,
        "min_discount_pct": 25,
        "min_price": 15,
        "max_price": 500,
        "peak_hours": [],
        "min_score_bypass_limit": 80,
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
    # Cálculo do score esperado:
    #   brand(jbl)       = +20
    #   eletronicos      = +10
    #   preço 89,90      = +10
    #   desconto 55%     = +20
    #   beneficios(3+)   = +10 (pix + cupom + frete)
    #   total = 70
    assert offer.score == 70
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
    # Ofertas com marca reconhecida + desconto forte, mas sem score >= 80 (bypass)
    # Ambas são da categoria "eletronicos", limite = 1
    first = "Oferta\nFone JBL Bluetooth\nDe R$ 180,00 por R$ 89,90\nhttps://example.com/jbl"
    second = "Oferta\nMouse Logitech Gamer\nDe R$ 150,00 por R$ 69,90\nhttps://example.com/logitech"

    first_ok, _ = should_post(first, config)
    second_ok, second_offer = should_post(second, config)

    assert first_ok is True
    assert second_ok is False
    assert second_offer.reject_reason.startswith("limite de categoria")


def test_should_post_rejects_low_discount_when_original_price_exists(tmp_path):
    text = "Oferta genérica sem marca\nDe R$ 199,90 por R$ 179,90\nhttps://example.com/outros"

    ok, offer = should_post(text, make_config(tmp_path))

    assert ok is False
    assert "sem diferencial" in offer.reject_reason


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

    # Usar min_score baixo para testar apenas timezone, não o score mínimo
    config = make_config(tmp_path, min_score=30)
    # Texto que detecta categoria "eletronicos" via "fone", tem cupom + pix + frete
    text = "Oferta imperdivel\nFone JBL Bluetooth com frete gratis\nDe R$ 199,00 por R$ 89,00 no Pix\nCupom: AUDIO10\nhttps://example.com"

    ok, offer = should_post(text, config)
    status = daily_status(config)

    assert status["data"] == "2026-06-05"
    assert status["postados_hoje"] == 1


def test_should_post_bypasses_daily_limit_for_premium_offers(tmp_path):
    config = make_config(tmp_path, max_posts_per_day=1, min_score=60)

    # Oferta boa com marca e desconto (score ~60-70, respeita limite)
    comum1 = "Oferta\nTenis Kappa com desconto\nDe R$ 150,00 por R$ 79,90\nhttps://example.com/kappa"
    ok1, offer1 = should_post(comum1, config)
    # Kappa (brand +20) + moda (+8) + price 79.90 (+10) + desconto 46.7% (+15)
    # Score = 20+8+10+15 = 53 < 60 → REJEITADO

    # Vamos usar um produto que passe (score >= 60)
    comum1 = "Oferta\nTenis Adidas Superstar\nDe R$ 299,00 por R$ 149,90\nhttps://example.com/adidas"
    ok1, offer1 = should_post(comum1, config)
    # Adidas (brand +20) + moda (+8) + price 149.90 (+10) + desconto 49.9% (+20? 49.9 < 50, so 15 from 40%+)
    # 49.9% discount → 40%+ → +15
    # Score = 20+8+10+15 = 53 < 60 → still rejected

    # O problema é que moda tem score_bonus 8 (not priority). Let me use eletronicos
    comum1 = "Oferta\nFone JBL Tune 510BT\nDe R$ 199,00 por R$ 89,90\nhttps://example.com/jbl"
    ok1, offer1 = should_post(comum1, config)
    # JBL (brand +20) + eletronicos (+10) + price 89.90 (+10) + desconto 54.8% (+20)
    # Score = 20+10+10+20 = 60 >= 60 → APROVADO
    assert ok1 is True
    assert offer1.score >= 60

    # Segunda oferta deve ser rejeitada por limite diário (max_posts_per_day=1)
    comum2 = "Oferta\nMouse Logitech G203\nDe R$ 120,00 por R$ 49,90\nhttps://example.com/logitech"
    ok2, offer2 = should_post(comum2, config)
    assert ok2 is False
    assert offer2.reject_reason.startswith("limite diário atingido")

    # Oferta premium com score >= 80 deve ignorar o limite
    premium = """
    Oferta Imperdivel
    Celular Samsung Galaxy S23 com frete gratis e cupom
    De R$ 3999,00 por R$ 1199,00 no Pix
    Cupom: GALAXY100
    https://example.com/galaxy
    """
    ok3, offer3 = should_post(premium, config)
    # Samsung (brand +20) + eletronicos (+10) + price 1199 (+5) + desconto 70% (+30)
    # + beneficios 3+ (+10) + premium (+5) + is_price_drop(0)
    # Score = 20+10+5+30+10+5 = 80 >= 80 → BYPASS
    assert offer3.score >= 80
    assert ok3 is True


def test_should_post_rejects_moda_barata(tmp_path):
    """Moda com preço abaixo de R$80 deve ser rejeitada."""
    text = "Oferta\nCamiseta comum\nDe R$ 59,90 por R$ 29,90\nhttps://example.com/camiseta"

    ok, offer = should_post(text, make_config(tmp_path))
    assert ok is False
    assert "moda barata" in offer.reject_reason


def test_should_post_rejects_saude_beleza_barata(tmp_path):
    """Saúde e beleza com preço abaixo de R$70 deve ser rejeitada."""
    text = "Oferta\nPerfume importado\nDe R$ 89,90 por R$ 49,90\nhttps://example.com/perfume"

    ok, offer = should_post(text, make_config(tmp_path))
    assert ok is False
    assert "saúde/beleza barata" in offer.reject_reason


def test_should_post_rejects_outros_with_low_score(tmp_path):
    """Categoria 'outros' com score < 70 deve ser rejeitada."""
    text = "Oferta\nProduto diverso sem marca\nDe R$ 100,00 por R$ 59,90\nhttps://example.com/produto"

    ok, offer = should_post(text, make_config(tmp_path))
    # Sem marca, categoria "outros" (score_bonus=0), preço 59.90 (+10), desconto 40.1% (+15)
    # Score = 0+0+0+10+15 = 25 < 70 → REJEITADO (outros with score < 70)
    assert ok is False
    assert "outros" in offer.reject_reason or "score insuficiente" in offer.reject_reason


def test_should_post_rejects_generic_product(tmp_path):
    """Produto claramente genérico sem marca deve ser rejeitado."""
    text = "Oferta\nCarregador genérico universal\nDe R$ 50,00 por R$ 29,90\nhttps://example.com/generico"

    ok, offer = should_post(text, make_config(tmp_path))
    # "generico" → detectado como genérico → penalidade -10
    # eletronicos +10, price 29.90 +10, desconto 40.2% +15
    # brand? "generico" não é marca → 0
    # Score antes da penalidade: 10+10+15 = 35
    # Após penalidade: 25
    # Score < 60 → REJEITADO (score insuficiente)
    assert ok is False
