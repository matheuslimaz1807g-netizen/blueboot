from __future__ import annotations

from pathlib import Path


def test_bot_runner_emits_client_facing_product_activity():
    bot_runner = Path(__file__).resolve().parents[2].joinpath("executable", "bot_runner.py").read_text(
        encoding="utf-8"
    )

    assert "activity_callback: Optional[Callable[[str, str], None]] = None" in bot_runner
    assert "self._activity = activity_callback" in bot_runner
    assert "produto enviado" in bot_runner
    assert "Total hoje" in bot_runner
