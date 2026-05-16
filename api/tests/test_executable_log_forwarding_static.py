from __future__ import annotations

from pathlib import Path


def test_executable_uses_pending_remote_log_queue_for_heartbeat():
    main_py = Path(__file__).resolve().parents[2].joinpath("executable", "main.py").read_text(
        encoding="utf-8"
    )

    assert "_pending_remote_logs: deque[dict] = deque(maxlen=MAX_LOGS)" in main_py
    assert "_pending_remote_logs.append(entry)" in main_py
    assert "_pending_remote_logs.popleft()" in main_py
    assert "_last_sent_log_index" not in main_py
