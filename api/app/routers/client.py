from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
import logging

logger = logging.getLogger(__name__)

from app.core.database import get_db
from app.core.dependencies import get_current_license
from app.models.models import License, LogEntry, ClientConfig
from app.schemas.schemas import LicenseOut, LogEntryOut, ConfigOut, ConfigIn, OkResponse
from app.services import config_service

router = APIRouter(prefix="/client", tags=["Client Dashboard"])

@router.get("/me", response_model=LicenseOut)
async def get_me(lic: License = Depends(get_current_license)):
    """Return the currently logged in license info."""
    return lic

@router.get("/config", response_model=ConfigOut)
async def get_my_config(
    lic: License = Depends(get_current_license),
    db: AsyncSession = Depends(get_db)
):
    """Return the configuration for the current license only."""
    try:
        result = await db.execute(select(ClientConfig).where(ClientConfig.license_id == lic.id))
        cfg = result.scalar_one_or_none()
        if not cfg:
            # Create default config if missing
            return await config_service.get_or_create_config(db, lic.id)
        return cfg
    except Exception as e:
        logger.error(f"Erro ao buscar config para licença {lic.id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Erro interno ao buscar configurações")

@router.put("/config", response_model=ConfigOut)
async def update_my_config(
    body: ConfigIn,
    lic: License = Depends(get_current_license),
    db: AsyncSession = Depends(get_db)
):
    """Update configuration for the current license only."""
    try:
        return await config_service.update_config(db, lic.id, body)
    except Exception as e:
        logger.error(f"Erro ao atualizar config para licença {lic.id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Erro ao salvar configurações: {str(e)}")

@router.get("/logs", response_model=list[LogEntryOut])
async def get_my_logs(
    limit: int = 50,
    lic: License = Depends(get_current_license),
    db: AsyncSession = Depends(get_db)
):
    """Return the logs for the current license only."""
    result = await db.execute(
        select(LogEntry)
        .where(LogEntry.license_id == lic.id)
        .order_by(desc(LogEntry.created_at))
        .limit(limit)
    )
    return result.scalars().all()

@router.get("/whatsapp/qr")
async def get_my_qr(lic: License = Depends(get_current_license)):
    """Return the current WhatsApp QR code for this license."""
    if not lic.whatsapp_qr:
        return {"status": lic.whatsapp_status or "disconnected", "qr": None}
    return {"status": lic.whatsapp_status, "qr": lic.whatsapp_qr}
