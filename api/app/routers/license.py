"""Public license API used by managed BlueBot instances."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db
from app.models.models import License, PendingMachine
from app.schemas.schemas import (
    ConfigIn,
    ConfigOut,
    LicenseHeartbeatRequest,
    LicenseValidateRequest,
    MachineDiscoveryRequest,
    OkResponse,
)
from app.services import config_service, license_service
from app.services.license_service import _sign_response

router = APIRouter(tags=["Public License"])
settings = get_settings()


def _ensure_install_token(token: str | None) -> None:
    expected = settings.INSTALL_TOKEN
    if expected and token != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="INSTALL_TOKEN invalido",
        )


async def _get_authorized_license(
    db: AsyncSession, license_key: str, machine_id: str
) -> License:
    result = await db.execute(select(License).where(License.key == license_key))
    lic = result.scalar_one_or_none()
    if not lic or not lic.active:
        raise HTTPException(status_code=401, detail="Licenca invalida ou inativa")
    if lic.machine_id and lic.machine_id != machine_id:
        raise HTTPException(status_code=401, detail="Maquina nao autorizada")
    return lic


@router.post("/license/discover")
async def discover_machine(
    body: MachineDiscoveryRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    x_install_token: str | None = Header(default=None, alias="X-Install-Token"),
):
    """Register a machine waiting for admin approval, or return its assigned key."""
    _ensure_install_token(x_install_token)

    license_result = await db.execute(
        select(License).where(License.machine_id == body.machine_id, License.active.is_(True))
    )
    lic = license_result.scalar_one_or_none()
    if lic:
        return {"pending": False, "assigned_key": lic.key}

    pending_result = await db.execute(
        select(PendingMachine).where(PendingMachine.machine_id == body.machine_id)
    )
    pending = pending_result.scalar_one_or_none()
    now = datetime.now(timezone.utc)
    client_host = request.client.host if request.client else None

    if pending:
        pending.hostname = body.hostname
        pending.platform = body.platform
        pending.label = body.label
        pending.ip_address = client_host
        pending.last_seen = now
    else:
        db.add(
            PendingMachine(
                machine_id=body.machine_id,
                hostname=body.hostname,
                platform=body.platform,
                label=body.label,
                ip_address=client_host,
                first_seen=now,
                last_seen=now,
            )
        )

    await db.commit()
    return {"pending": True}


@router.post("/license/validate")
async def validate_license(
    body: LicenseValidateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Validate license key and machine binding for the executable."""
    result = await license_service.validate_license(db, body.license_key, body.machine_id)
    payload = result.model_dump()
    return _sign_response(payload, body.machine_id)


@router.post("/license/heartbeat", response_model=OkResponse)
async def heartbeat(
    body: LicenseHeartbeatRequest,
    db: AsyncSession = Depends(get_db),
):
    ok = await license_service.record_heartbeat(
        db,
        body.license_key,
        body.machine_id,
        body.whatsapp_status,
        body.whatsapp_qr,
        body.logs,
        body.queue,
    )
    if not ok:
        raise HTTPException(status_code=401, detail="Licenca invalida")
    return OkResponse(message="heartbeat registrado")


@router.get("/license/auth-code")
async def get_auth_code(
    license_key: str,
    machine_id: str,
    db: AsyncSession = Depends(get_db),
):
    lic = await _get_authorized_license(db, license_key, machine_id)
    if not lic.pending_code and not lic.pending_password:
        return {"has_code": False}

    payload = {
        "has_code": True,
        "code": lic.pending_code or "",
        "password": lic.pending_password or "",
    }
    lic.pending_code = None
    lic.pending_password = None
    lic.pending_code_at = None
    await db.commit()
    return payload


@router.get("/config/{license_key}", response_model=ConfigOut)
async def get_config_by_key(
    license_key: str,
    machine_id: str,
    db: AsyncSession = Depends(get_db),
):
    lic = await _get_authorized_license(db, license_key, machine_id)
    return await config_service.get_or_create_config(db, lic.id)


@router.put("/config/{license_key}", response_model=ConfigOut)
async def update_config_by_key(
    license_key: str,
    body: ConfigIn,
    machine_id: str,
    db: AsyncSession = Depends(get_db),
):
    lic = await _get_authorized_license(db, license_key, machine_id)
    return await config_service.update_config(db, lic.id, body)
