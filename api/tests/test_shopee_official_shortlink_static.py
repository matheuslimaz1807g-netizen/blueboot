from __future__ import annotations

from pathlib import Path


def test_shopee_converter_uses_official_graphql_signature():
    shopee = Path(__file__).resolve().parents[2].joinpath(
        "executable", "affiliates", "shopee.py"
    ).read_text(encoding="utf-8")

    assert "https://open-api.affiliate.shopee.com.br/graphql" in shopee
    assert "generateShortLink" in shopee
    assert "hashlib.sha256" in shopee
    assert "Credential={app_id}" in shopee
    assert "Timestamp={timestamp}" in shopee
    assert "Signature={signature}" in shopee
    assert "subIds" in shopee
    assert "APPID:SECRET" in shopee
    assert "tinyurl.com" not in shopee
    assert "is.gd" not in shopee


def test_pipeline_passes_shopee_credentials_to_converter():
    pipeline = Path(__file__).resolve().parents[2].joinpath("executable", "pipeline.py").read_text(
        encoding="utf-8"
    )

    assert 'shopee.convert(expanded_link, config.get("shopee_token", ""))' in pipeline
    assert "Conversao Shopee ativa, mas APPID/SECRET ausentes" in pipeline
