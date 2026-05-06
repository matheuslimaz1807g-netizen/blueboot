from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, EmailStr, Field


# ── Shared ────────────────────────────────────────────────────────────────────

class OkResponse(BaseModel):
    ok: bool = True
    message: str = "ok"


# ── Schedule Rules ────────────────────────────────────────────────────────────

class ScheduleRules(BaseModel):
    """Restrict when the bot can run for this license."""
    enabled: bool = False
    dias_semana: list[int] = Field(
        default_factory=lambda: [0, 1, 2, 3, 4, 5, 6],
        description="Dias da semana permitidos (0=domingo, 6=sábado)",
    )
    hora_inicio: str = Field(default="00:00", pattern=r"^\d{2}:\d{2}$")
    hora_fim: str = Field(default="23:59", pattern=r"^\d{2}:\d{2}$")
    timezone: str = Field(default="America/Sao_Paulo", max_length=64)


# ── License ───────────────────────────────────────────────────────────────────

class LicenseValidateRequest(BaseModel):
    license_key: str = Field(..., pattern=r"^APRO-[A-Z2-9]{4}-[A-Z2-9]{4}-[A-Z2-9]{4}$")
    machine_id: str = Field(..., min_length=10, max_length=128)


class LicenseHeartbeatRequest(BaseModel):
    license_key: str
    machine_id: str
    whatsapp_status: str | None = None
    whatsapp_qr: str | None = None


class LicenseValidateResponse(BaseModel):
    valid: bool
    plan: str
    expires_at: datetime | None
    schedule_blocked: bool = False
    assigned_key: str | None = None # Se o admin vinculou, retorna a chave aqui

class MachineDiscoveryRequest(BaseModel):
    machine_id: str
    hostname: str | None = None
    platform: str | None = None
    label: str | None = None # Robot name from .env

class PendingMachineOut(BaseModel):
    id: uuid.UUID
    machine_id: str
    hostname: str | None
    ip_address: str | None
    platform: str | None
    label: str | None
    first_seen: datetime
    last_seen: datetime

    model_config = {"from_attributes": True}

class LinkMachineRequest(BaseModel):
    machine_id: str
    license_id: uuid.UUID


class LicenseOut(BaseModel):
    id: uuid.UUID
    key: str
    plan: str
    machine_id: str | None
    active: bool
    expires_at: datetime | None
    created_at: datetime
    last_heartbeat: datetime | None
    schedule_rules: dict | None = None
    note: str | None = None
    whatsapp_status: str | None = None
    whatsapp_qr: str | None = None
    password: str | None = None

    model_config = {"from_attributes": True}


# ── Client Login (SaaS) ──────────────────────────────────────────────────────

class ClientLoginRequest(BaseModel):
    license_key: str
    password: str


# ── ClientConfig ──────────────────────────────────────────────────────────────

class ConfigIn(BaseModel):
    """Fields sent by the executable when saving config via PUT /config/{key}."""
    phone: str | None = None
    sources: list[str] = Field(default_factory=list)
    destination_telegram: str | None = None
    delay_segundos: int = Field(default=3, ge=1, le=60)
    whatsapp_endpoint: str | None = None
    send_telegram: bool = True
    send_whatsapp: bool = True
    conv_shopee: bool = True
    conv_ali: bool = True
    conv_ml: bool = True
    filtros: dict[str, Any] = Field(default_factory=dict)
    # Plain-text credentials (API encrypts before storing)
    shopee_token: str | None = None
    ali_key: str | None = None
    ali_secret: str | None = None
    ali_tracking: str | None = None
    ml_token: str | None = None
    api_id: str | None = None
    api_hash: str | None = None
    session_string: str | None = None
    bot_dashboard_url: str | None = None


class ConfigOut(BaseModel):
    """Decrypted config returned to the executable."""
    phone: str | None
    sources: list[str]
    destination_telegram: str | None
    delay_segundos: int
    whatsapp_endpoint: str | None
    send_telegram: bool
    send_whatsapp: bool
    conv_shopee: bool
    conv_ali: bool
    conv_ml: bool
    filtros: dict[str, Any]
    shopee_token: str | None
    ali_key: str | None
    ali_secret: str | None
    ali_tracking: str | None
    ml_token: str | None
    api_id: str | None
    api_hash: str | None
    session_string: str | None
    bot_dashboard_url: str | None


# ── AppVersion ────────────────────────────────────────────────────────────────

class VersionOut(BaseModel):
    version: str
    download_url_win: str | None
    download_url_linux: str | None
    sha256_win: str | None
    sha256_linux: str | None
    changelog: str | None
    released_at: datetime

    model_config = {"from_attributes": True}


class VersionIn(BaseModel):
    version: str
    download_url_win: str | None = None
    download_url_linux: str | None = None
    sha256_win: str | None = None
    sha256_linux: str | None = None
    changelog: str | None = None


# ── Admin ────────────────────────────────────────────────────────────────────

class AdminLoginRequest(BaseModel):
    username: str
    password: str


class AdminLoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LicenseCreateRequest(BaseModel):
    plan: str = Field(default="basic", pattern=r"^(basic|pro)$")
    expires_days: int = Field(default=30, ge=1, le=3650)
    note: str | None = Field(default=None, max_length=256)
    password: str | None = Field(default=None, max_length=64)


class LicensePatchRequest(BaseModel):
    active: bool | None = None
    plan: str | None = Field(default=None, pattern=r"^(basic|pro)$")
    expires_days: int | None = Field(default=None, ge=1, le=3650)
    schedule_rules: dict | None = None
    note: str | None = Field(default=None, max_length=256)
    machine_id: str | None = Field(default=None, description="Set to null to unbind machine")
    password: str | None = Field(default=None, max_length=64)


# ── LogEntry ──────────────────────────────────────────────────────────────────

class LogEntryOut(BaseModel):
    id: uuid.UUID
    nivel: str
    mensagem: str
    created_at: datetime

    model_config = {"from_attributes": True}
