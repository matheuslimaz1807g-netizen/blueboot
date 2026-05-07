"""License service — generation, validation, heartbeat logic."""
from __future__ import annotations

import hashlib
import hmac
import json
import random
import string
import uuid
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password, verify_password
from app.models.models import License
from app.schemas.schemas import LicenseValidateResponse


# Characters without O, 0, I, 1 to avoid confusion
_SAFE_CHARS = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"

# HMAC salt for signing responses (must match client-side)
_HMAC_SALT = "BlueBot_License_HMAC_v1"


def _sign_response(data: dict, machine_id: str) -> dict:
    """Add HMAC signature to the response to prevent MITM tampering."""
    hmac_key = hashlib.sha256(f"{machine_id}:{_HMAC_SALT}".encode()).digest()
    # Convert datetime objects to ISO strings for deterministic serialization
    serializable = {}
    for k, v in data.items():
        if isinstance(v, datetime):
            serializable[k] = v.isoformat()
        else:
            serializable[k] = v
    # Sort keys for deterministic serialization
    serialized = json.dumps(serializable, sort_keys=True, separators=(",", ":"))
    signature = hmac.new(hmac_key, serialized.encode(), hashlib.sha256).hexdigest()
    data["signature"] = signature
    return data


def generate_license_key() -> str:
    """Generate a key in format APRO-XXXX-XXXX-XXXX using unambiguous characters."""
    blocks = ["".join(random.choices(_SAFE_CHARS, k=4)) for _ in range(3)]
    return "APRO-" + "-".join(blocks)


async def get_license_by_key(db: AsyncSession, key: str) -> License | None:
    result = await db.execute(select(License).where(License.key == key))
    return result.scalar_one_or_none()


def check_schedule(rules: dict | None) -> bool:
    """
    Check if the current time is within the allowed schedule.
    Returns True if allowed, False if blocked.
    If rules is None or not enabled, returns True (no restriction).
    Uses the timezone specified in rules (default: America/Sao_Paulo).
    """
    if not rules or not rules.get("enabled", False):
        return True

    import pytz
    tz_name = rules.get("timezone", "America/Sao_Paulo")
    try:
        tz = pytz.timezone(tz_name)
    except Exception:
        tz = pytz.timezone("America/Sao_Paulo")

    now = datetime.now(tz)
    current_hour = now.hour
    current_minute = now.minute
    current_weekday = now.weekday()  # 0=Monday, 6=Sunday

    # Convert Python weekday (0=Monday) to our schema (0=Sunday)
    current_dia = (current_weekday + 1) % 7

    # Check day of week
    dias_permitidos = rules.get("dias_semana", [0, 1, 2, 3, 4, 5, 6])
    if current_dia not in dias_permitidos:
        return False

    # Check time range
    hora_inicio = rules.get("hora_inicio", "00:00")
    hora_fim = rules.get("hora_fim", "23:59")

    try:
        h_i, m_i = map(int, hora_inicio.split(":"))
        h_f, m_f = map(int, hora_fim.split(":"))
    except (ValueError, TypeError):
        return True  # Invalid format, allow

    current_total = current_hour * 60 + current_minute
    start_total = h_i * 60 + m_i
    end_total = h_f * 60 + m_f

    if start_total <= end_total:
        # Normal range (e.g., 08:00-18:00)
        return start_total <= current_total <= end_total
    else:
        # Overnight range (e.g., 22:00-06:00)
        return current_total >= start_total or current_total <= end_total


async def validate_license(
    db: AsyncSession, key: str, machine_id: str
) -> LicenseValidateResponse:
    """
    Validates the license key and machine binding:
    - Key must exist and be active
    - If machine_id is not yet bound, bind it now (first activation)
    - If bound, machine_id must match
    - expires_at must be None (perpetual) or in the future
    - schedule_rules must allow current time (if configured)
    """
    lic = await get_license_by_key(db, key)

    if not lic or not lic.active:
        return LicenseValidateResponse(valid=False, plan="", expires_at=None)

    now = datetime.now(timezone.utc)

    # Check expiry
    if lic.expires_at and lic.expires_at < now:
        return LicenseValidateResponse(valid=False, plan=lic.plan, expires_at=lic.expires_at)

    # Check schedule rules
    if not check_schedule(lic.schedule_rules):
        return LicenseValidateResponse(
            valid=False,
            plan=lic.plan,
            expires_at=lic.expires_at,
            schedule_blocked=True,
        )

    # Machine binding
    if lic.machine_id is None:
        # First activation — bind machine
        await db.execute(
            update(License)
            .where(License.id == lic.id)
            .values(machine_id=machine_id, last_heartbeat=now)
        )
        await db.commit()
    elif lic.machine_id != machine_id:
        # Different machine — deny
        return LicenseValidateResponse(valid=False, plan=lic.plan, expires_at=lic.expires_at)
    else:
        await db.execute(
            update(License).where(License.id == lic.id).values(last_heartbeat=now)
        )
        await db.commit()

    return LicenseValidateResponse(valid=True, plan=lic.plan, expires_at=lic.expires_at)


async def record_heartbeat(
    db: AsyncSession, 
    key: str, 
    machine_id: str, 
    whatsapp_status: str | None = None,
    whatsapp_qr: str | None = None
) -> bool:
    """Update last_heartbeat and WhatsApp status."""
    lic = await get_license_by_key(db, key)
    if not lic or not lic.active:
        return False
    if lic.machine_id and lic.machine_id != machine_id:
        return False

    now = datetime.now(timezone.utc)
    values = {"last_heartbeat": now}
    if whatsapp_status is not None:
        values["whatsapp_status"] = whatsapp_status
    if whatsapp_qr is not None:
        values["whatsapp_qr"] = whatsapp_qr
        
    await db.execute(
        update(License).where(License.id == lic.id).values(**values)
    )
    await db.commit()
    return True


async def create_license(
    db: AsyncSession, plan: str, expires_days: int, note: str | None = None, password: str | None = None
) -> License:
    """Create a new license with a generated key and optional password."""
    try:
        key = generate_license_key()
        # Ensure key uniqueness (extremely unlikely collision but handle it)
        while await get_license_by_key(db, key):
            key = generate_license_key()

        now = datetime.now(timezone.utc)
        lic = License(
            key=key,
            plan=plan,
            active=True,
            expires_at=now + timedelta(days=expires_days),
            created_at=now,
            note=note,
            password=hash_password(password) if password else None,
        )
        db.add(lic)
        await db.commit()
        await db.refresh(lic)
        return lic
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Erro ao criar licença: {str(e)}")
