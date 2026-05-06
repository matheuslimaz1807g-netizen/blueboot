"""Routers for the executable client: license validate/heartbeat, config, version."""
from __future__ import annotations

import sys

from fastapi import APIRouter, Depends, HTTPException, Query, Header, status, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.config import get_settings
from app.schemas.schemas import (
    ConfigIn,
    ConfigOut,
    LicenseHeartbeatRequest,
    LicenseValidateRequest,
    LicenseValidateResponse,
    MachineDiscoveryRequest,
    OkResponse,
    VersionOut,
)
from app.services import config_service, license_service
from sqlalchemy import select, update
from app.models.models import AppVersion, License, PendingMachine

router = APIRouter()


# ── License ───────────────────────────────────────────────────────────────────

@router.post("/license/validate", response_model=LicenseValidateResponse)
async def validate_license(
    body: LicenseValidateRequest,
    db: AsyncSession = Depends(get_db),
):
    result = await license_service.validate_license(db, body.license_key, body.machine_id)
    # Sign the response with HMAC to prevent MITM tampering
    signed = license_service._sign_response(result.model_dump(), body.machine_id)
    return signed


@router.post("/license/discover", response_model=LicenseValidateResponse)
async def discover_machine(
    body: MachineDiscoveryRequest,
    x_install_token: str | None = Header(None, alias="X-Install-Token"),
    db: AsyncSession = Depends(get_db),
    settings = Depends(get_settings),
):
    # SEGURANÇA: Validar Token Global de Instalação
    if not x_install_token or x_install_token != settings.INSTALL_TOKEN:
        raise HTTPException(status_code=403, detail="Token de instalação inválido ou ausente")

    # 1. Verificar se esta máquina já possui uma licença vinculada
    result = await db.execute(select(License).where(License.machine_id == body.machine_id))
    lic = result.scalar_one_or_none()
    
    if lic and lic.active:
        res = LicenseValidateResponse(
            valid=True,
            plan=lic.plan,
            expires_at=lic.expires_at,
            assigned_key=lic.key
        )
        return license_service._sign_response(res.model_dump(), body.machine_id)

    # 2. Se não tem licença, registrar na lista de pendentes para o Admin ver
    result = await db.execute(select(PendingMachine).where(PendingMachine.machine_id == body.machine_id))
    pending = result.scalar_one_or_none()
    
    if not pending:
        pending = PendingMachine(
            machine_id=body.machine_id,
            hostname=body.hostname,
            platform=body.platform,
            label=body.label
        )
        db.add(pending)
    else:
        pending.hostname = body.hostname
        pending.platform = body.platform
        pending.label = body.label
    
    await db.commit()
    
    return LicenseValidateResponse(valid=False, plan="", expires_at=None)


@router.post("/license/heartbeat", response_model=OkResponse)
async def heartbeat(
    body: LicenseHeartbeatRequest,
    db: AsyncSession = Depends(get_db),
):
    ok = await license_service.record_heartbeat(
        db, 
        body.license_key, 
        body.machine_id,
        whatsapp_status=body.whatsapp_status,
        whatsapp_qr=body.whatsapp_qr
    )
    if not ok:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Licença inválida ou máquina não autorizada")
    return OkResponse()


@router.get("/license/auth-code")
async def get_pending_auth_code(
    license_key: str = Query(..., min_length=5),
    machine_id: str = Query(..., min_length=10),
    db: AsyncSession = Depends(get_db),
):
    lic = await _get_verified_license(license_key, machine_id, db)
    if not lic.pending_code:
        return {"has_code": False}
    
    code = lic.pending_code
    password = lic.pending_password
    
    # Consome (zera para não usar de novo)
    lic.pending_code = None
    lic.pending_password = None
    lic.pending_code_at = None
    await db.commit()
    
    return {"has_code": True, "code": code, "password": password}


# ── Config ────────────────────────────────────────────────────────────────────

async def _get_verified_license(
    license_key: str,
    machine_id: str,
    db: AsyncSession,
) -> License:
    """Helper: load license and verify machine_id matches."""
    lic = await license_service.get_license_by_key(db, license_key)
    if not lic or not lic.active:
        raise HTTPException(status_code=404, detail="Licença não encontrada ou inativa")
    if lic.machine_id and lic.machine_id != machine_id:
        raise HTTPException(status_code=403, detail="machine_id não autorizado")
    return lic


@router.get("/config/{license_key}", response_model=ConfigOut)
async def get_config(
    license_key: str,
    machine_id: str = Query(..., min_length=10),
    db: AsyncSession = Depends(get_db),
):
    lic = await _get_verified_license(license_key, machine_id, db)
    cfg = await config_service.get_config(db, lic)
    if cfg is None:
        raise HTTPException(status_code=404, detail="Configuração ainda não definida")
    return cfg


@router.put("/config/{license_key}", response_model=ConfigOut)
async def put_config(
    license_key: str,
    body: ConfigIn,
    machine_id: str = Query(..., min_length=10),
    db: AsyncSession = Depends(get_db),
):
    lic = await _get_verified_license(license_key, machine_id, db)
    return await config_service.upsert_config(db, lic, body)


# ── Version ───────────────────────────────────────────────────────────────────

@router.get("/version/latest", response_model=VersionOut)
async def get_latest_version(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(AppVersion).where(AppVersion.is_latest == True).order_by(AppVersion.released_at.desc())
    )
    version = result.scalar_one_or_none()
    if not version:
        raise HTTPException(status_code=404, detail="Nenhuma versão publicada")
    return version
