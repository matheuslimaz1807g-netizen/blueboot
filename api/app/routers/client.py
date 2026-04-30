"""Routers for the executable client: license validate/heartbeat, config, version."""
from __future__ import annotations

import sys

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.schemas import (
    ConfigIn,
    ConfigOut,
    LicenseHeartbeatRequest,
    LicenseValidateRequest,
    LicenseValidateResponse,
    OkResponse,
    VersionOut,
)
from app.services import config_service, license_service
from sqlalchemy import select
from app.models.models import AppVersion, License

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


@router.post("/license/heartbeat", response_model=OkResponse)
async def heartbeat(
    body: LicenseHeartbeatRequest,
    db: AsyncSession = Depends(get_db),
):
    ok = await license_service.record_heartbeat(db, body.license_key, body.machine_id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Licença inválida ou máquina não autorizada")
    return OkResponse()


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
