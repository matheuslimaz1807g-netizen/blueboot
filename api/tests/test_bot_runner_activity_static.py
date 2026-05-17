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


def test_bot_runner_rate_limits_product_delivery_queue():
    bot_runner = Path(__file__).resolve().parents[2].joinpath("executable", "bot_runner.py").read_text(
        encoding="utf-8"
    )

    assert "_DELIVERY_INTERVAL_SECONDS = 10 * 60" in bot_runner
    assert "self._delivery_queue = asyncio.Queue()" in bot_runner
    assert "async def _delivery_worker() -> None:" in bot_runner
    assert "await self._delivery_queue.put((fingerprint, message))" in bot_runner
    assert "timeout=_DELIVERY_INTERVAL_SECONDS" in bot_runner
    assert "delivery_queue_size" in bot_runner
    assert "next_dispatch_seconds" in bot_runner
    assert "asyncio.create_task(self._process_and_count(message))" not in bot_runner


def test_bot_runner_deduplicates_products_before_queueing():
    bot_runner = Path(__file__).resolve().parents[2].joinpath("executable", "bot_runner.py").read_text(
        encoding="utf-8"
    )

    assert "def _product_fingerprint(self, message) -> str:" in bot_runner
    assert "def _remember_product(self, fingerprint: str) -> bool:" in bot_runner
    assert "def _finish_product(self, fingerprint: str, remember_recent: bool) -> None:" in bot_runner
    assert "_PRODUCT_DEDUP_TTL_SECONDS = 24 * 60 * 60" in bot_runner
    assert "self._pending_product_fingerprints" in bot_runner
    assert "self._recent_product_fingerprints" in bot_runner
    assert "Produto duplicado ignorado antes da fila" in bot_runner
    assert "await self._delivery_queue.put((fingerprint, message))" in bot_runner
