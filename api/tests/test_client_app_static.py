from __future__ import annotations

import subprocess
import shutil
from pathlib import Path

import pytest


def _client_app_html() -> str:
    return Path(__file__).resolve().parents[2].joinpath("client_app", "index.html").read_text(
        encoding="utf-8"
    )


def test_client_app_script_is_valid_javascript(tmp_path):
    if not shutil.which("node"):
        pytest.skip("node is required to validate client app JavaScript syntax")

    html = _client_app_html()
    scripts = []
    remaining = html
    while "<script" in remaining:
        start_tag = remaining.index("<script")
        start = remaining.index(">", start_tag) + 1
        end = remaining.index("</script>", start)
        scripts.append(remaining[start:end])
        remaining = remaining[end + len("</script>") :]

    script_file = tmp_path / "client-app-index.js"
    script_file.write_text(scripts[-1], encoding="utf-8")

    subprocess.run(["node", "--check", str(script_file)], check=True)


def test_client_activity_log_keeps_all_supported_levels():
    html = _client_app_html()

    assert "fmtDate(d)" in html
    assert "fmtRelative(d)" in html
    assert "Array.isArray(logs)" in html
    assert "allowedLevels = ['info', 'success', 'warning', 'error']" in html
    assert "Nenhuma atividade registrada" in html


def test_client_app_exposes_autonomous_license_config_without_whatsapp_endpoint():
    html = _client_app_html()
    client_router = Path(__file__).resolve().parents[1].joinpath("app", "routers", "client.py").read_text(
        encoding="utf-8"
    )

    assert "x-model=\"config.api_id\"" in html
    assert "x-model=\"config.api_hash\"" in html
    assert "x-model=\"config.shopee_token\"" in html
    assert "x-model=\"config.ali_key\"" in html
    assert "x-model=\"config.ali_secret\"" in html
    assert "x-model=\"config.ali_tracking\"" in html
    assert "x-model=\"config.ml_token\"" in html
    assert "x-model=\"config.ml_cookies\"" in html
    assert "delete body.whatsapp_endpoint" in html
    assert 'model_copy(update={"whatsapp_endpoint": current.whatsapp_endpoint})' in client_router


def test_client_app_has_bot_start_stop_control():
    html = _client_app_html()

    assert "Bot ligado" in html
    assert "toggleBot" in html
    assert "config.bot_enabled" in html
    assert "Startar Bot" in html
    assert "Stop do Bot" in html


def test_client_app_uses_clean_operational_ui_contract():
    html = _client_app_html()

    assert "clean-ui-contract" in html
    assert ".panel-surface" in html
    assert ".brand-mark { background: #6366f1; }" in html
    assert "bg-[radial-gradient" not in html
    assert "glass" not in html
    assert "accent-gradient" not in html
    assert "rounded-3xl" not in html
    assert "shadow-2xl" not in html
