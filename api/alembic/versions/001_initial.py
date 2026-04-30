"""Initial migration — create all tables.

Revision ID: 001
Revises:
Create Date: 2026-04-25
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── licenses ──────────────────────────────────────────────────────────────
    op.create_table(
        "licenses",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("key", sa.String(20), unique=True, nullable=False, index=True),
        sa.Column(
            "plan",
            sa.Enum("basic", "pro", name="plan_enum"),
            nullable=False,
            default="basic",
        ),
        sa.Column("machine_id", sa.String(128), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, default=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_heartbeat", sa.DateTime(timezone=True), nullable=True),
    )

    # ── client_configs ────────────────────────────────────────────────────────
    op.create_table(
        "client_configs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "license_id",
            UUID(as_uuid=True),
            sa.ForeignKey("licenses.id", ondelete="CASCADE"),
            unique=True,
            nullable=False,
        ),
        sa.Column("phone", sa.String(20), nullable=True),
        sa.Column("sources", JSONB(), nullable=True, default=list),
        sa.Column("destination_telegram", sa.String(256), nullable=True),
        sa.Column("delay_segundos", sa.Integer(), nullable=False, default=3),
        sa.Column("whatsapp_endpoint", sa.String(512), nullable=True),
        sa.Column("send_telegram", sa.Boolean(), nullable=False, default=True),
        sa.Column("send_whatsapp", sa.Boolean(), nullable=False, default=True),
        sa.Column("conv_shopee", sa.Boolean(), nullable=False, default=True),
        sa.Column("conv_ali", sa.Boolean(), nullable=False, default=True),
        sa.Column("conv_ml", sa.Boolean(), nullable=False, default=True),
        sa.Column("filtros", JSONB(), nullable=True, default=dict),
        sa.Column("shopee_token_enc", sa.Text(), nullable=True),
        sa.Column("ali_key_enc", sa.Text(), nullable=True),
        sa.Column("ali_secret_enc", sa.Text(), nullable=True),
        sa.Column("ali_tracking_enc", sa.Text(), nullable=True),
        sa.Column("ml_token_enc", sa.Text(), nullable=True),
        sa.Column("api_id_enc", sa.Text(), nullable=True),
        sa.Column("api_hash_enc", sa.Text(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    # ── app_versions ──────────────────────────────────────────────────────────
    op.create_table(
        "app_versions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("version", sa.String(32), unique=True, nullable=False),
        sa.Column("download_url_win", sa.String(1024), nullable=True),
        sa.Column("download_url_linux", sa.String(1024), nullable=True),
        sa.Column("sha256_win", sa.String(64), nullable=True),
        sa.Column("sha256_linux", sa.String(64), nullable=True),
        sa.Column("changelog", sa.Text(), nullable=True),
        sa.Column("released_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_latest", sa.Boolean(), nullable=False, default=True),
    )

    # ── log_entries ───────────────────────────────────────────────────────────
    op.create_table(
        "log_entries",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "license_id",
            UUID(as_uuid=True),
            sa.ForeignKey("licenses.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "nivel",
            sa.Enum("info", "success", "error", name="nivel_enum"),
            nullable=False,
        ),
        sa.Column("mensagem", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, index=True),
    )


def downgrade() -> None:
    op.drop_table("log_entries")
    op.drop_table("app_versions")
    op.drop_table("client_configs")
    op.drop_table("licenses")
    op.execute("DROP TYPE IF EXISTS plan_enum")
    op.execute("DROP TYPE IF EXISTS nivel_enum")
