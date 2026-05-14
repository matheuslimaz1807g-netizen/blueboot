"""
license.py — Machine-bound license validation with offline grace period.

Compiled to .pyd/.so via Cython before PyInstaller packaging to prevent
reverse engineering of the validation logic.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import platform
import socket
import subprocess
import threading
import time
import uuid
import urllib3
from datetime import datetime, timezone
from typing import Optional

import requests

from utils import should_verify_ssl

# Suppress SSL warnings only when verification is disabled
if not should_verify_ssl("https://example.com"):
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ── Constants ─────────────────────────────────────────────────────────────────
# API_BASE is set at build time and baked into the compiled module.
# In production, this is always set. Empty = dev mode only.
_API_BASE_DEFAULT: str = "https://api.yourdomain.com"
HEARTBEAT_INTERVAL: int = 15              # 15 seconds (for faster status sync)
OFFLINE_GRACE_SECONDS: int = 30 * 60    # 30 minutes (reduced from 4h)
REQUEST_TIMEOUT: int = 10

# HMAC key for verifying server responses (derived from machine_id + server secret)
# This prevents MITM from forging validation responses
_HMAC_KEY_SALT: str = "BlueBot_License_HMAC_v1"


def _get_hmac_key(machine_id: str) -> bytes:
    """Derive HMAC key from machine_id for response verification."""
    return hashlib.sha256(f"{machine_id}:{_HMAC_KEY_SALT}".encode()).digest()


def get_api_base() -> str:
    """Return API_BASE from environment, falling back to compiled default."""
    return os.environ.get("APRO_API_BASE", _API_BASE_DEFAULT)


class LicenseError(Exception):
    """Raised when the license is invalid, expired, or machine mismatch."""
    pass


# ── Machine fingerprint ────────────────────────────────────────────────────────

_MACHINE_ID_FILE = "/app/data/machine_id"


def get_machine_id() -> str:
    """
    Returns a STABLE machine fingerprint that persists across container restarts.

    Uses a file-based approach:
    - If /app/data/machine_id exists, reads and returns it (persistent across restarts)
    - Otherwise, generates a new ID from hardware fingerprint and saves it

    This ensures the machine_id NEVER changes between Docker container restarts,
    preventing license validation failures.
    """
    # Try to read existing persistent machine_id
    try:
        if os.path.exists(_MACHINE_ID_FILE):
            with open(_MACHINE_ID_FILE, "r") as f:
                stored = f.read().strip()
                if stored and len(stored) == 64:
                    return stored
    except Exception:
        pass

    # Generate from hardware fingerprint (stable across reboots)
    parts = []
    try:
        mac = str(uuid.getnode())
        parts.append(mac)
    except Exception:
        parts.append("unknown_mac")

    try:
        hostname = socket.gethostname()
        parts.append(hostname)
    except Exception:
        parts.append("unknown_host")

    # Try to get Windows machine GUID for extra stability
    if platform.system() == "Windows":
        try:
            result = subprocess.run(
                ["wmic", "csproduct", "get", "uuid"],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                lines = result.stdout.strip().split("\n")
                if len(lines) >= 2:
                    guid = lines[1].strip()
                    if guid:
                        parts.append(guid)
        except Exception:
            pass
    elif platform.system() == "Linux":
        # Linux machine-id (stable on real machines, may change in Docker)
        for p in ["/etc/machine-id", "/var/lib/dbus/machine-id"]:
            if os.path.exists(p):
                try:
                    with open(p, "r") as f:
                        parts.append(f.read().strip())
                        break
                except: pass

    raw = "|".join(parts)
    mid = hashlib.sha256(raw.encode()).hexdigest()

    # Save to persistent file for future restarts
    try:
        os.makedirs(os.path.dirname(_MACHINE_ID_FILE), exist_ok=True)
        with open(_MACHINE_ID_FILE, "w") as f:
            f.write(mid)
    except Exception:
        pass

    return mid


# ── Remote validation ─────────────────────────────────────────────────────────

def validate_license(key: str, machine_id: str) -> dict:
    """
    POST /license/validate → { valid, plan, expires_at, signature }

    Verifies the HMAC signature of the response to prevent MITM tampering.

    Raises:
        LicenseError: if the license is invalid, expired, or machine mismatch
        requests.RequestException: if the server is unreachable
    """
    url = f"{get_api_base()}/license/validate"
    try:
        resp = requests.post(
            url,
            json={"license_key": key, "machine_id": machine_id},
            timeout=REQUEST_TIMEOUT,
            verify=should_verify_ssl(url),
        )
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as exc:
        raise exc  # Caller handles offline grace period

    if not data.get("valid"):
        raise LicenseError(
            "Licença inválida, expirada ou não autorizada para esta máquina."
        )

    # Verify HMAC signature of the response
    signature = data.pop("signature", None)
    if signature:
        hmac_key = _get_hmac_key(machine_id)
        # Sort keys for deterministic serialization
        serialized = json.dumps(data, sort_keys=True, separators=(",", ":"))
        expected_sig = hmac.new(hmac_key, serialized.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected_sig, signature):
            raise LicenseError("Resposta de licença adulterada — possível ataque MITM.")

    return data  # { valid: True, plan: "basic"|"pro", expires_at: "..." | null }


def _heartbeat_worker(key: str, machine_id: str, stop_event: threading.Event, on_grace_expired=None, status_callback=None, logs_callback=None) -> None:
    """Background thread that PINGs the server every HEARTBEAT_INTERVAL seconds."""
    last_success: float = time.time()

    while not stop_event.is_set():
        # Payload base do heartbeat
        payload = {"license_key": key, "machine_id": machine_id}
        
        # Coleta status extra (ex: WhatsApp) se houver um callback definido
        if status_callback:
            try:
                extra = status_callback()
                if isinstance(extra, dict):
                    payload.update(extra)
            except:
                pass

        # Coleta logs pendentes para enviar ao servidor
        if logs_callback:
            try:
                pending_logs = logs_callback()
                if pending_logs:
                    payload["logs"] = pending_logs[:50]  # Max 50 per heartbeat
            except:
                pass

        url = f"{get_api_base()}/license/heartbeat"
        try:
            resp = requests.post(
                url,
                json=payload,
                timeout=REQUEST_TIMEOUT,
                verify=should_verify_ssl(url),
            )
            resp.raise_for_status()
            last_success = time.time()
        except Exception:
            elapsed = time.time() - last_success
            if elapsed > OFFLINE_GRACE_SECONDS:
                if on_grace_expired:
                    on_grace_expired()
        
        # Espera pelo próximo ciclo
        stop_event.wait(timeout=HEARTBEAT_INTERVAL)


# Module-level stop event so callers can shut down heartbeat cleanly
_heartbeat_stop = threading.Event()
_heartbeat_on_expired = None


def start_heartbeat(key: str, machine_id: str, on_grace_expired: Optional[callable] = None, status_callback: Optional[callable] = None, logs_callback: Optional[callable] = None) -> None:
    """Start the heartbeat daemon thread. Call once after successful validation."""
    global _heartbeat_on_expired
    _heartbeat_on_expired = on_grace_expired
    _heartbeat_stop.clear()
    t = threading.Thread(
        target=_heartbeat_worker,
        args=(key, machine_id, _heartbeat_stop, on_grace_expired, status_callback, logs_callback),
        daemon=True,
        name="LicenseHeartbeat",
    )
    t.start()


def stop_heartbeat() -> None:
    """Signal the heartbeat thread to stop (called on clean shutdown)."""
    _heartbeat_stop.set()
