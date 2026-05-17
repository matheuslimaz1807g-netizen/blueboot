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
    assert "allowedLevels = ['success', 'error']" in html
    assert "Nenhuma atividade registrada" in html


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
