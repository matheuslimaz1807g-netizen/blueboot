from __future__ import annotations

import asyncio
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.schemas.schemas import ConfigIn
from app.services import config_service


class FakeResult:
    def __init__(self, value: Any):
        self.value = value

    def scalar_one_or_none(self) -> Any:
        return self.value


class FakeSession:
    def __init__(self, config: Any):
        self.config = config
        self.commits = 0
        self.refreshes = 0

    async def execute(self, _statement: Any) -> FakeResult:
        return FakeResult(self.config)

    def add(self, _value: Any) -> None:
        pass

    async def commit(self) -> None:
        self.commits += 1

    async def refresh(self, _value: Any) -> None:
        self.refreshes += 1


def make_existing_config() -> SimpleNamespace:
    return SimpleNamespace(
        phone=None,
        sources=[],
        destination_telegram=None,
        delay_segundos=3,
        whatsapp_endpoint=None,
        send_telegram=True,
        send_whatsapp=False,
        conv_shopee=True,
        conv_ali=True,
        conv_ml=True,
        filtros={},
        shopee_token_enc=None,
        ali_key_enc=None,
        ali_secret_enc=None,
        ali_tracking_enc=None,
        ml_token_enc=None,
        ml_cookies_enc="encrypted-old-cookie",
        api_id_enc=None,
        api_hash_enc=None,
        session_string_enc=None,
        bot_dashboard_url=None,
    )


def test_upsert_config_updates_ml_cookies_when_value_is_provided(monkeypatch):
    monkeypatch.setattr(config_service, "encrypt_field", lambda value: f"encrypted:{value}")
    monkeypatch.setattr(config_service, "decrypt_field", lambda value: value.removeprefix("encrypted:"))
    cfg = make_existing_config()
    db = FakeSession(cfg)
    license_obj = SimpleNamespace(id="license-id")

    result = asyncio.run(
        config_service.upsert_config(
            db,
            license_obj,
            ConfigIn(ml_cookies="new-cookie"),
        )
    )

    assert cfg.ml_cookies_enc == "encrypted:new-cookie"
    assert result.ml_cookies == "new-cookie"
    assert db.commits == 1
    assert db.refreshes == 1


def test_upsert_config_clears_ml_cookies_when_empty_string_is_sent(monkeypatch):
    monkeypatch.setattr(config_service, "encrypt_field", lambda value: f"encrypted:{value}")
    cfg = make_existing_config()
    db = FakeSession(cfg)
    license_obj = SimpleNamespace(id="license-id")

    result = asyncio.run(
        config_service.upsert_config(
            db,
            license_obj,
            ConfigIn(ml_cookies=""),
        )
    )

    assert cfg.ml_cookies_enc is None
    assert result.ml_cookies is None
