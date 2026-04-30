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

# Suppress SSL warnings for self-signed certificates (local dev/testing)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ── Constants ─────────────────────────────────────────────────────────────────
# API_BASE is set at build time and baked into the compiled module.
# In production, this is always set. Empty = dev mode only.
_API_BASE_DEFAULT: str = "https://api.yourdomain.com"
HEARTBEAT_INTERVAL: int = 15 * 60       # 15 minutes
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

def get_machine_id() -> str:
    """
    Returns a stable SHA-256 fingerprint of this machine by combining:
    - Primary network interface MAC address
    - Hostname
    - Windows machine GUID (if available)

    The result is deterministic across reboots and does not change unless
    the NIC or hostname changes.
    """
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

    # Adiciona ID do Docker se disponível
    if os.path.exists("/proc/self/cgroup"):
        try:
            with open("/proc/self/cgroup", "r") as f:
                parts.append(f.read())
        except: pass

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
        # Linux machine-id
        for p in ["/etc/machine-id", "/var/lib/dbus/machine-id"]:
            if os.path.exists(p):
                try:
                    with open(p, "r") as f:
                        parts.append(f.read().strip())
                        break
                except: pass

    raw = "|".join(parts)
    return hashlib.sha256(raw.encode()).hexdigest()


# ── Remote validation ─────────────────────────────────────────────────────────

def validate_license(key: str, machine_id: str) -> dict:
    """
    POST /license/validate → { valid, plan, expires_at, signature }

    Verifies the HMAC signature of the response to prevent MITM tampering.

    Raises:
        LicenseError: if the license is invalid, expired, or machine mismatch
        requests.RequestException: if the server is unreachable
    """
    try:
        resp = requests.post(
            f"{get_api_base()}/license/validate",
            json={"license_key": key, "machine_id": machine_id},
            timeout=REQUEST_TIMEOUT,
            verify=False,
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


def _heartbeat_worker(key: str, machine_id: str, stop_event: threading.Event, on_grace_expired=None) -> None:
    """Background thread that PINGs the server every HEARTBEAT_INTERVAL seconds."""
    last_success: float = time.time()

    while not stop_event.is_set():
        stop_event.wait(timeout=HEARTBEAT_INTERVAL)
        if stop_event.is_set():
            break

        try:
            resp = requests.post(
                f"{get_api_base()}/license/heartbeat",
                json={"license_key": key, "machine_id": machine_id},
                timeout=REQUEST_TIMEOUT,
                verify=False,
            )
            resp.raise_for_status()
            last_success = time.time()
        except Exception:
            elapsed = time.time() - last_success
            if elapsed > OFFLINE_GRACE_SECONDS:
                if on_grace_expired:
                    on_grace_expired()


# Module-level stop event so callers can shut down heartbeat cleanly
_heartbeat_stop = threading.Event()
_heartbeat_on_expired = None


def start_heartbeat(key: str, machine_id: str, on_grace_expired: Optional[callable] = None) -> None:
    """Start the heartbeat daemon thread. Call once after successful validation."""
    global _heartbeat_on_expired
    _heartbeat_on_expired = on_grace_expired
    _heartbeat_stop.clear()
    t = threading.Thread(
        target=_heartbeat_worker,
        args=(key, machine_id, _heartbeat_stop, on_grace_expired),
        daemon=True,
        name="LicenseHeartbeat",
    )
    t.start()


def stop_heartbeat() -> None:
    """Signal the heartbeat thread to stop (called on clean shutdown)."""
    _heartbeat_stop.set()
