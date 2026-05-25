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


def test_executable_suppresses_noisy_runtime_logs_by_default():
    root = Path(__file__).resolve().parents[2]
    main_py = root.joinpath("executable", "main.py").read_text(encoding="utf-8")
    config_loader = root.joinpath("executable", "config_loader.py").read_text(encoding="utf-8")
    bot_runner = root.joinpath("executable", "bot_runner.py").read_text(encoding="utf-8")

    assert '@app.route("/health")' in main_py
    assert 'logging.getLogger("werkzeug").disabled = True' in main_py
    assert "BLUEBOT_VERBOSE_CONFIG" in config_loader
    assert "Config Mesclada" not in config_loader
    assert "Heartbeat: Bot monitorando" not in bot_runner
    assert "ML_COOKIES sincronizado" not in main_py
