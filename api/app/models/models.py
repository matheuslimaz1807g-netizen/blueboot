from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    Enum as SAEnum,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class License(Base):
    __tablename__ = "licenses"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    key: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    plan: Mapped[str] = mapped_column(
        SAEnum("basic", "pro", name="plan_enum"), nullable=False, default="basic"
    )
    machine_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    last_heartbeat: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    schedule_rules: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True, default=dict
    )

    config: Mapped["ClientConfig | None"] = relationship(
        "ClientConfig", back_populates="license", uselist=False, cascade="all, delete-orphan"
    )
    logs: Mapped[list["LogEntry"]] = relationship(
        "LogEntry", back_populates="license", cascade="all, delete-orphan"
    )


class ClientConfig(Base):
    __tablename__ = "client_configs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    license_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("licenses.id", ondelete="CASCADE"), unique=True, nullable=False
    )

    # Telegram
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    sources: Mapped[list | None] = mapped_column(JSONB, nullable=True, default=list)
    destination_telegram: Mapped[str | None] = mapped_column(String(256), nullable=True)
    delay_segundos: Mapped[int] = mapped_column(Integer, default=3, nullable=False)

    # WhatsApp
    whatsapp_endpoint: Mapped[str | None] = mapped_column(String(512), nullable=True)

    # Toggles
    send_telegram: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    send_whatsapp: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    conv_shopee: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    conv_ali: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    conv_ml: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Filters
    filtros: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default=dict)

    # Affiliate credentials (Fernet-encrypted)
    shopee_token_enc: Mapped[str | None] = mapped_column(Text, nullable=True)
    ali_key_enc: Mapped[str | None] = mapped_column(Text, nullable=True)
    ali_secret_enc: Mapped[str | None] = mapped_column(Text, nullable=True)
    ali_tracking_enc: Mapped[str | None] = mapped_column(Text, nullable=True)
    ml_token_enc: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Telegram API Credentials (Encrypted)
    api_id_enc: Mapped[str | None] = mapped_column(Text, nullable=True)
    api_hash_enc: Mapped[str | None] = mapped_column(Text, nullable=True)

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )

    license: Mapped["License"] = relationship("License", back_populates="config")


class AppVersion(Base):
    __tablename__ = "app_versions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    version: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    download_url_win: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    download_url_linux: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    sha256_win: Mapped[str | None] = mapped_column(String(64), nullable=True)
    sha256_linux: Mapped[str | None] = mapped_column(String(64), nullable=True)
    changelog: Mapped[str | None] = mapped_column(Text, nullable=True)
    released_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    is_latest: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class LogEntry(Base):
    __tablename__ = "log_entries"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    license_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("licenses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    nivel: Mapped[str] = mapped_column(
        SAEnum("info", "success", "error", name="nivel_enum"), nullable=False
    )
    mensagem: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False, index=True
    )

    license: Mapped["License"] = relationship("License", back_populates="logs")
