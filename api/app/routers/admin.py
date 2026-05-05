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
    if body.machine_id is not None:
        values["machine_id"] = body.machine_id
    elif "machine_id" in body.model_dump(exclude_unset=True) and body.machine_id is None:
        # Explicitly set to null to unbind the machine
        values["machine_id"] = None

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
    
    # 4. Auditoria: Registrar o vínculo nos Logs
    audit_log = LogEntry(
        license_id=lic.id,
        nivel="success",
        mensagem=f"Máquina vinculada via Auto-Descoberta (ID: {body.machine_id[:16]}...)"
    )
    db.add(audit_log)

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


# ── Auth Code (Telegram verification) ──────────────────────────────────────────

@router.post("/licenses/{license_id}/auth-code", response_model=OkResponse)
async def send_auth_code(
    license_id: int,
    body: dict,
    db: AsyncSession = Depends(get_db),
    _admin=Depends(get_admin_user),
):
    """
    Envia o código de verificação do Telegram para o bot.
    O painel admin chama este endpoint, que redireciona para o dashboard do bot.
    """
    code = body.get("code", "").strip()
    password = body.get("password", "").strip()
    
    if not code and not password:
        raise HTTPException(status_code=400, detail="Código ou senha é obrigatório")
    
    # Buscar a licença para obter o machine_id
    result = await db.execute(select(License).where(License.id == license_id))
    lic = result.scalar_one_or_none()
    if not lic or not lic.machine_id:
        raise HTTPException(status_code=404, detail="Licença não encontrada ou sem máquina vinculada")
    
    # O bot roda na porta 8080 dentro da rede Docker
    # O nome do host é o nome do container do bot
    bot_url = f"http://bot:8080/api/auth-code"
    
    import httpx
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                bot_url,
                json={"code": code, "password": password},
                headers={"Authorization": "Basic YWRtaW46YWRtaW4xMjM="}  # admin:admin123
            )
            if resp.status_code == 200:
                data = resp.json()
                if data.get("ok"):
                    # Se conseguiu autenticar, salva a session_string na config
                    session_str = data.get("session_string")
                    if session_str:
                        cfg = await config_service.get_config(db, lic)
                        if cfg:
                            # Atualiza a config com a nova session_string
                            from app.schemas.schemas import ConfigIn
                            config_data = ConfigIn(
                                phone=cfg.phone,
                                sources=cfg.sources,
                                destination_telegram=cfg.destination_telegram,
                                delay_segundos=cfg.delay_segundos,
                                whatsapp_endpoint=cfg.whatsapp_endpoint,
                                send_telegram=cfg.send_telegram,
                                send_whatsapp=cfg.send_whatsapp,
                                conv_shopee=cfg.conv_shopee,
                                conv_ali=cfg.conv_ali,
                                conv_ml=cfg.conv_ml,
                                filtros=cfg.filtros,
                                shopee_token=cfg.shopee_token,
                                ali_key=cfg.ali_key,
                                ali_secret=cfg.ali_secret,
                                ali_tracking=cfg.ali_tracking,
                                ml_token=cfg.ml_token,
                                api_id=cfg.api_id,
                                api_hash=cfg.api_hash,
                                session_string=session_str,
                            )
                            await config_service.upsert_config(db, lic, config_data)
                    
                    return OkResponse(message="Código enviado e autenticado com sucesso!")
                elif data.get("requires_password"):
                    return OkResponse(message="Senha de duas etapas necessária. Envie novamente com a senha.")
                else:
                    raise HTTPException(status_code=400, detail=data.get("error", "Erro ao autenticar"))
            else:
                raise HTTPException(status_code=502, detail=f"Erro ao comunicar com o bot: {resp.status_code}")
    except httpx.ConnectError:
        raise HTTPException(status_code=502, detail="Não foi possível conectar ao bot. Verifique se ele está rodando.")
