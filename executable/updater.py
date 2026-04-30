"""
updater.py — Auto-update the executable from the remote API.

Checks for a newer version, downloads it, verifies SHA-256,
replaces the current executable, and restarts the process.
"""
from __future__ import annotations

import hashlib
import os
import platform
import shutil
import sys
import tempfile
import time

import requests

REQUEST_TIMEOUT: int = 60


def _sha256_of_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _version_tuple(v: str) -> tuple[int, ...]:
    """Convert '1.2.3' → (1, 2, 3) for comparison."""
    return tuple(int(x) for x in v.strip().split(".") if x.isdigit())


def check_and_update(current_version: str, api_base: str) -> None:
    """
    1. GET {api_base}/version/latest
    2. Compare version strings
    3. If newer:  download → verify SHA-256 → replace → restart
    """
    try:
        resp = requests.get(f"{api_base}/version/latest", timeout=15)
        resp.raise_for_status()
        data = resp.json()
    except Exception:
        # No update server reachable — silently skip
        return

    remote_version: str = data.get("version", "0.0.0")

    if _version_tuple(remote_version) <= _version_tuple(current_version):
        return  # Already up to date

    # Determine the correct download URL and expected hash
    is_windows = platform.system() == "Windows"
    url_key = "download_url_win" if is_windows else "download_url_linux"
    sha_key = "sha256_win" if is_windows else "sha256_linux"

    download_url: str | None = data.get(url_key)
    expected_sha: str | None = data.get(sha_key)

    if not download_url:
        return  # No binary available for this OS

    print(f"[Updater] Nova versão disponível: {remote_version}. Baixando...")

    # Download to a temp file
    try:
        dl_resp = requests.get(download_url, stream=True, timeout=REQUEST_TIMEOUT)
        dl_resp.raise_for_status()
    except Exception as exc:
        print(f"[Updater] Falha no download: {exc}")
        return

    tmp_dir = tempfile.mkdtemp()
    suffix = ".exe" if is_windows else ""
    tmp_path = os.path.join(tmp_dir, f"ApenasPromo_new{suffix}")

    with open(tmp_path, "wb") as f:
        for chunk in dl_resp.iter_content(chunk_size=65536):
            f.write(chunk)

    # Verify SHA-256
    if expected_sha:
        actual_sha = _sha256_of_file(tmp_path)
        if actual_sha.lower() != expected_sha.lower():
            print("[Updater] SHA-256 inválido. Abortando atualização.")
            shutil.rmtree(tmp_dir, ignore_errors=True)
            return

    # Replace current executable
    current_exe = sys.executable
    backup_path = current_exe + ".bak"

    try:
        if os.path.exists(backup_path):
            os.remove(backup_path)
        shutil.move(current_exe, backup_path)
        shutil.move(tmp_path, current_exe)

        if not is_windows:
            os.chmod(current_exe, 0o755)
    except Exception as exc:
        print(f"[Updater] Falha ao substituir executável: {exc}")
        # Restore backup
        if os.path.exists(backup_path):
            shutil.move(backup_path, current_exe)
        shutil.rmtree(tmp_dir, ignore_errors=True)
        return

    shutil.rmtree(tmp_dir, ignore_errors=True)
    print(f"[Updater] Atualizado para {remote_version}. Reiniciando...")
    time.sleep(1)

    # Restart the process
    os.execv(current_exe, [current_exe] + sys.argv[1:])
