"""Config service — fetch and store encrypted client configurations."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decrypt_field, encrypt_field
from app.models.models import ClientConfig, License
from app.schemas.schemas import ConfigIn, ConfigOut


async def get_config(db: AsyncSession, license: License) -> ConfigOut | None:
    """Return decrypted config for a license, or None if not configured yet."""
    from sqlalchemy.orm import selectinload
    result = await db.execute(
        select(License).where(License.id == license.id).options(selectinload(License.config))
    )
    lic = result.scalar_one_or_none()
    if not lic or not lic.config:
        return None

    cfg = lic.config
    return ConfigOut(
        phone=cfg.phone,
        sources=cfg.sources or [],
        destination_telegram=cfg.destination_telegram,
        delay_segundos=cfg.delay_segundos,
        whatsapp_endpoint=cfg.whatsapp_endpoint,
        send_telegram=cfg.send_telegram,
        send_whatsapp=cfg.send_whatsapp,
        conv_shopee=cfg.conv_shopee,
        conv_ali=cfg.conv_ali,
        conv_ml=cfg.conv_ml,
        filtros=cfg.filtros or {},
        shopee_token=decrypt_field(cfg.shopee_token_enc) if cfg.shopee_token_enc else None,
        ali_key=decrypt_field(cfg.ali_key_enc) if cfg.ali_key_enc else None,
        ali_secret=decrypt_field(cfg.ali_secret_enc) if cfg.ali_secret_enc else None,
        ali_tracking=decrypt_field(cfg.ali_tracking_enc) if cfg.ali_tracking_enc else None,
        ml_token=decrypt_field(cfg.ml_token_enc) if cfg.ml_token_enc else None,
        api_id=decrypt_field(cfg.api_id_enc) if cfg.api_id_enc else None,
        api_hash=decrypt_field(cfg.api_hash_enc) if cfg.api_hash_enc else None,
        session_string=decrypt_field(cfg.session_string_enc) if cfg.session_string_enc else None,
    )


async def upsert_config(db: AsyncSession, license: License, data: ConfigIn) -> ConfigOut:
    """Create or update the ClientConfig for a license, encrypting all credential fields."""
    # Query config explicitly to avoid lazy-load MissingGreenlet
    result = await db.execute(
        select(ClientConfig).where(ClientConfig.license_id == license.id)
    )
    cfg = result.scalar_one_or_none()
    if cfg is None:
        cfg = ClientConfig(license_id=license.id)
        db.add(cfg)

    cfg.phone = data.phone
    cfg.sources = data.sources
    cfg.destination_telegram = data.destination_telegram
    cfg.delay_segundos = data.delay_segundos
    cfg.whatsapp_endpoint = data.whatsapp_endpoint
    cfg.send_telegram = data.send_telegram
    cfg.send_whatsapp = data.send_whatsapp
    cfg.conv_shopee = data.conv_shopee
    cfg.conv_ali = data.conv_ali
    cfg.conv_ml = data.conv_ml
    cfg.filtros = data.filtros

    # Only overwrite encrypted fields when a new value is provided
    if data.shopee_token:
        cfg.shopee_token_enc = encrypt_field(data.shopee_token)
    if data.ali_key:
        cfg.ali_key_enc = encrypt_field(data.ali_key)
    if data.ali_secret:
        cfg.ali_secret_enc = encrypt_field(data.ali_secret)
    if data.ali_tracking:
        cfg.ali_tracking_enc = encrypt_field(data.ali_tracking)
    if data.ml_token:
        cfg.ml_token_enc = encrypt_field(data.ml_token)
    if data.api_id:
        cfg.api_id_enc = encrypt_field(data.api_id)
    if data.api_hash:
        cfg.api_hash_enc = encrypt_field(data.api_hash)
    if data.session_string:
        cfg.session_string_enc = encrypt_field(data.session_string)

    await db.commit()
    await db.refresh(cfg)

    # Return decrypted view directly from cfg (avoid MissingGreenlet)
    return ConfigOut(
        phone=cfg.phone,
        sources=cfg.sources or [],
        destination_telegram=cfg.destination_telegram,
        delay_segundos=cfg.delay_segundos,
        whatsapp_endpoint=cfg.whatsapp_endpoint,
        send_telegram=cfg.send_telegram,
        send_whatsapp=cfg.send_whatsapp,
        conv_shopee=cfg.conv_shopee,
        conv_ali=cfg.conv_ali,
        conv_ml=cfg.conv_ml,
        filtros=cfg.filtros or {},
        shopee_token=decrypt_field(cfg.shopee_token_enc) if cfg.shopee_token_enc else None,
        ali_key=decrypt_field(cfg.ali_key_enc) if cfg.ali_key_enc else None,
        ali_secret=decrypt_field(cfg.ali_secret_enc) if cfg.ali_secret_enc else None,
        ali_tracking=decrypt_field(cfg.ali_tracking_enc) if cfg.ali_tracking_enc else None,
        ml_token=decrypt_field(cfg.ml_token_enc) if cfg.ml_token_enc else None,
        api_id=decrypt_field(cfg.api_id_enc) if cfg.api_id_enc else None,
        api_hash=decrypt_field(cfg.api_hash_enc) if cfg.api_hash_enc else None,
        session_string=decrypt_field(cfg.session_string_enc) if cfg.session_string_enc else None,
    )
