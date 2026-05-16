from __future__ import annotations

from pathlib import Path


def test_executable_uses_client_activity_queue_for_heartbeat():
    main_py = Path(__file__).resolve().parents[2].joinpath("executable", "main.py").read_text(
        encoding="utf-8"
    )

    assert "_pending_remote_logs: deque[dict] = deque(maxlen=MAX_LOGS)" in main_py
    assert "def add_client_activity_log(nivel: str, mensagem: str) -> None:" in main_py
    assert "_pending_remote_logs.append(activity_entry)" in main_py
    assert "BotRunner(log_callback=add_log, activity_callback=add_client_activity_log)" in main_py
    assert "_logs.append(entry)" in main_py
    assert "_pending_remote_logs.append(entry)" not in main_py
    assert "_pending_remote_logs.popleft()" in main_py
    assert "_last_sent_log_index" not in main_py
