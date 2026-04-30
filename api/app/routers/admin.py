"""Admin API — protected by JWT, for the developer panel."""
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy import select, update, desc, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_admin_user
from app.core.security import create_access_token, verify_password, hash_password
from app.core.config import get_settings
from app.models.models import AppVersion, License, LogEntry, ClientConfig, PendingMachine
from app.schemas.schemas import (
    AdminLoginRequest,
    AdminLoginResponse,
    ConfigIn,
    ConfigOut,
    LicenseCreateRequest,
    LicenseOut,
    LicensePatchRequest,
    LogEntryOut,
    OkResponse,
    PendingMachineOut,
    LinkMachineRequest,
    VersionIn,
    VersionOut,
)
from app.services import config_service, license_service

router = APIRouter(prefix="/admin")
settings = get_settings()

# Rate limiter specifically for login (5 attempts per minute)
login_limiter = Limiter(key_func=get_remote_address, default_limits=["5/minute"])


@router.post("/login", response_model=AdminLoginResponse)
@login_limiter.limit("5/minute")
async def admin_login(body: AdminLoginRequest, request: Request):
    if body.username != settings.ADMIN_USERNAME or body.password != settings.ADMIN_PASSWORD:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciais inválidas")
    token = create_access_token({"sub": body.username, "role": "admin"}, expires_minutes=60)
    return AdminLoginResponse(access_token=token)


# ── Licenses ──────────────────────────────────────────────────────────────────

@router.get("/licenses", response_model=list[LicenseOut])
async def list_licenses(
    db: AsyncSession = Depends(get_db),
    _admin=Depends(get_admin_user),
):
    result = await db.execute(select(License).order_by(desc(License.created_at)))
    return result.scalars().all()


@router.post("/licenses", response_model=LicenseOut, status_code=201)
async def create_license(
    body: LicenseCreateRequest,
    db: AsyncSession = Depends(get_db),
    _admin=Depends(get_admin_user),
):
    return await license_service.create_license(db, body.plan, body.expires_days, body.note)


@router.patch("/licenses/{license_id}", response_model=LicenseOut)
async def patch_license(
    license_id: uuid.UUID,
    body: LicensePatchRequest,
    db: AsyncSession = Depends(get_db),
    _admin=Depends(get_admin_user),
):
    result = await db.execute(select(License).where(License.id == license_id))
    lic = result.scalar_one_or_none()
    if not lic:
        raise HTTPException(status_code=404, detail="Licença não encontrada")

    values: dict = {}
    if body.active is not None:
        values["active"] = body.active
    if body.plan is not None:
        values["plan"] = body.plan
    if body.expires_days is not None:
        values["expires_at"] = datetime.now(timezone.utc) + timedelta(days=body.expires_days)
    if body.schedule_rules is not None:
        values["schedule_rules"] = body.schedule_rules
    if body.note is not None:
        values["note"] = body.note

    if values:
        await db.execute(update(License).where(License.id == license_id).values(**values))
        await db.commit()
        await db.refresh(lic)
    return lic


# ── Per-license config ────────────────────────────────────────────────────────

@router.get("/licenses/{license_id}/config", response_model=ConfigOut | None)
async def get_license_config(
    license_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _admin=Depends(get_admin_user),
):
    result = await db.execute(select(License).where(License.id == license_id))
    lic = result.scalar_one_or_none()
    if not lic:
        raise HTTPException(status_code=404, detail="Licença não encontrada")
    return await config_service.get_config(db, lic)


@router.put("/licenses/{license_id}/config", response_model=ConfigOut)
async def put_license_config(
    license_id: uuid.UUID,
    body: ConfigIn,
    db: AsyncSession = Depends(get_db),
    _admin=Depends(get_admin_user),
):
    result = await db.execute(select(License).where(License.id == license_id))
    lic = result.scalar_one_or_none()
    if not lic:
        raise HTTPException(status_code=404, detail="Licença não encontrada")
    return await config_service.upsert_config(db, lic, body)


# ── Logs ──────────────────────────────────────────────────────────────────────

@router.get("/licenses/{license_id}/logs", response_model=list[LogEntryOut])
async def get_license_logs(
    license_id: uuid.UUID,
    limit: int = Query(default=200, le=1000),
    db: AsyncSession = Depends(get_db),
    _admin=Depends(get_admin_user),
):
    result = await db.execute(
        select(LogEntry)
        .where(LogEntry.license_id == license_id)
        .order_by(desc(LogEntry.created_at))
        .limit(limit)
    )
    return result.scalars().all()


# ── Versions ──────────────────────────────────────────────────────────────────

@router.get("/versions", response_model=list[VersionOut])
async def list_versions(
    db: AsyncSession = Depends(get_db),
    _admin=Depends(get_admin_user),
):
    result = await db.execute(select(AppVersion).order_by(desc(AppVersion.released_at)))
    return result.scalars().all()


@router.post("/versions", response_model=VersionOut, status_code=201)
async def post_version(
    body: VersionIn,
    db: AsyncSession = Depends(get_db),
    _admin=Depends(get_admin_user),
):
    # Mark all previous versions as not latest
    await db.execute(update(AppVersion).values(is_latest=False))

    v = AppVersion(
        version=body.version,
        download_url_win=body.download_url_win,
        download_url_linux=body.download_url_linux,
        sha256_win=body.sha256_win,
        sha256_linux=body.sha256_linux,
        changelog=body.changelog,
        is_latest=True,
    )
    db.add(v)
    await db.commit()
    await db.refresh(v)
    return v


# ── Pending Machines (Auto-Discovery) ──────────────────────────────────────────

@router.get("/pending", response_model=list[PendingMachineOut])
async def list_pending_machines(
    db: AsyncSession = Depends(get_db),
    _admin=Depends(get_admin_user),
):
    result = await db.execute(select(PendingMachine).order_by(desc(PendingMachine.last_seen)))
    return result.scalars().all()


@router.post("/link", response_model=OkResponse)
async def link_machine_to_license(
    body: LinkMachineRequest,
    db: AsyncSession = Depends(get_db),
    _admin=Depends(get_admin_user),
):
    # 1. Verificar se a licença existe
    result = await db.execute(select(License).where(License.id == body.license_id))
    lic = result.scalar_one_or_none()
    if not lic:
        raise HTTPException(status_code=404, detail="Licença não encontrada")

    # 2. Atualizar a licença com o machine_id
    await db.execute(
        update(License)
        .where(License.id == body.license_id)
        .values(machine_id=body.machine_id)
    )
    
    # 3. Remover da lista de pendentes
    await db.execute(delete(PendingMachine).where(PendingMachine.machine_id == body.machine_id))
    
    await db.commit()
    return OkResponse(message="Máquina vinculada com sucesso")


@router.delete("/pending/{machine_id}", response_model=OkResponse)
async def delete_pending_machine(
    machine_id: str,
    db: AsyncSession = Depends(get_db),
    _admin=Depends(get_admin_user),
):
    await db.execute(delete(PendingMachine).where(PendingMachine.machine_id == machine_id))
    await db.commit()
    return OkResponse(message="Máquina removida da lista")
