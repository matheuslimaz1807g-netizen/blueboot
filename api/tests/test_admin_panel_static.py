from __future__ import annotations

import subprocess
import shutil
from pathlib import Path

import pytest


def test_admin_panel_script_is_valid_javascript(tmp_path):
    if not shutil.which("node"):
        pytest.skip("node is required to validate admin panel JavaScript syntax")

    html = Path(__file__).resolve().parents[2].joinpath("admin", "index.html").read_text(
        encoding="utf-8"
    )
    scripts = []
    remaining = html
    while "<script" in remaining:
        start_tag = remaining.index("<script")
        start = remaining.index(">", start_tag) + 1
        end = remaining.index("</script>", start)
        scripts.append(remaining[start:end])
        remaining = remaining[end + len("</script>") :]

    script_file = tmp_path / "admin-index.js"
    script_file.write_text(scripts[-1], encoding="utf-8")

    subprocess.run(["node", "--check", str(script_file)], check=True)


def test_clients_tab_loads_license_data_when_opened_empty():
    html = Path(__file__).resolve().parents[2].joinpath("admin", "index.html").read_text(
        encoding="utf-8"
    )

    assert 'id: "clients"' in html
    assert "if (tabId === \"clients\") this.loadClients(true);" in html
    assert "async loadClients(fetchIfEmpty = false)" in html
    assert "await this.loadLicenses(false);" in html
