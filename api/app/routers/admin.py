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
    ClientLoginRequest,
)
from app.services import config_service, license_service

router = APIRouter(prefix="/admin")
settings = get_settings()

@router.get("/", include_in_schema=False)
async def admin_root_redirect():
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/panel/")

@router.get("/whatsapp", include_in_schema=False)
async def admin_whatsapp_redirect():
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/panel/")

# Rate limiter specifically for login (5 attempts per minute)
login_limiter = Limiter(key_func=get_remote_address, default_limits=["5/minute"])


@router.post("/login", response_model=AdminLoginResponse)
@login_limiter.limit("5/minute")
async def admin_login(body: AdminLoginRequest, request: Request):
    # Strip spaces to avoid "15 vs 14" character errors
    username = body.username.strip()
    password = body.password.strip()

    # Log para depuração (Remover após resolver)
    from app.main import logger
    logger.info(f"[AUTH] Tentativa de login para usuário: {username}")
    logger.info(f"[AUTH] Esperado: {settings.ADMIN_USERNAME} | Recebido: {username}")
    
    # Check password length and presence
    pwd_match = (password == settings.ADMIN_PASSWORD)
    logger.info(f"[AUTH] Senha coincide: {pwd_match}")
    if not pwd_match:
        exp_len = len(settings.ADMIN_PASSWORD)
        rec_len = len(password)
        logger.info(f"[AUTH] Comprimento: Esperado {exp_len} | Recebido {rec_len}")
        
        if exp_len == rec_len:
            diffs = []
            for i in range(exp_len):
                if settings.ADMIN_PASSWORD[i] != password[i]:
                    diffs.append(f"Pos {i}: {ord(settings.ADMIN_PASSWORD[i])} vs {ord(password[i])}")
            logger.info(f"[AUTH] Diferenças: {', '.join(diffs)}")

    if username != settings.ADMIN_USERNAME or password != settings.ADMIN_PASSWORD:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciais inválidas")
    
    token = create_access_token({"sub": username, "role": "admin"}, expires_minutes=60)
    return AdminLoginResponse(access_token=token)


# ── Licenses ──────────────────────────────────────────────────────────────────

# Rate limiter for login is already defined above

@router.post("/licenses", response_model=LicenseOut, status_code=201)
async def create_license(
    body: LicenseCreateRequest,
    db: AsyncSession = Depends(get_db),
    _admin=Depends(get_admin_user),
):
    return await license_service.create_license(db, body.plan, body.expires_days, body.note, body.password)


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
    if body.password is not None:
        values["password"] = body.password
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
    license_id: uuid.UUID,
    body: dict,
    db: AsyncSession = Depends(get_db),
    _admin=Depends(get_admin_user),
):
    """
    Envia o código de verificação do Telegram (salva no banco para o bot buscar via pull).
    """
    code = body.get("code", "").strip()
    password = body.get("password", "").strip()

    if not code and not password:
        raise HTTPException(status_code=400, detail="Código ou senha é obrigatório")

    # Buscar a licença
    result = await db.execute(select(License).where(License.id == license_id))
    lic = result.scalar_one_or_none()
    if not lic or not lic.machine_id:
        raise HTTPException(status_code=404, detail="Licença não encontrada ou sem máquina vinculada")

    from datetime import datetime, timezone
    lic.pending_code = code
    lic.pending_password = password
    lic.pending_code_at = datetime.now(timezone.utc)
    
    await db.commit()
    return OkResponse(message="Código salvo! O bot irá coletá-lo nos próximos segundos.")


# ── Public License View (No admin auth required) ──────────────────────────────

@router.get("/license/public/{key}", response_model=LicenseOut)
async def get_public_license_status(
    key: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Rota pública para clientes visualizarem o status de seu próprio robô via chave.
    """
    result = await db.execute(select(License).where(License.key == key))
    lic = result.scalar_one_or_none()
    if not lic:
        raise HTTPException(status_code=404, detail="Licença não encontrada")
    return lic


@router.post("/client/login", response_model=OkResponse)
async def client_login(
    body: ClientLoginRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Login para clientes usando chave e senha da licença.
    """
    result = await db.execute(select(License).where(License.key == body.license_key))
    lic = result.scalar_one_or_none()
    
    if not lic or not lic.active:
        raise HTTPException(status_code=401, detail="Licença inválida ou inativa")
    
    if not lic.password:
        raise HTTPException(status_code=400, detail="Esta licença não possui senha definida pelo administrador")

    if not verify_password(body.password, lic.password):
        raise HTTPException(status_code=401, detail="Senha incorreta")
        
    return OkResponse(message="Login realizado com sucesso")


# ── WhatsApp Proxy ──────────────────────────────────────────────────────────

@router.get("/whatsapp/status")
async def get_whatsapp_status(_admin=Depends(get_admin_user)):
    """
    Proxy para buscar o status do WhatsApp do container 'bot' (porta 8080).
    """
    import httpx
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get("http://bot:8080/api/whatsapp/status")
            return resp.json()
    except Exception as e:
        return {"status": "error", "message": f"Não foi possível conectar ao robô: {str(e)}"}

