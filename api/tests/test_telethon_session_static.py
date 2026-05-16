from __future__ import annotations

from pathlib import Path


def test_bot_runner_lets_telethon_validate_string_session():
    bot_runner = Path(__file__).resolve().parents[2].joinpath("executable", "bot_runner.py").read_text(
        encoding="utf-8"
    )

    assert "base64.b64decode" not in bot_runner
    assert "session = StringSession(session_string)" in bot_runner
