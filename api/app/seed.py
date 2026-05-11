"""
seed.py — Populate the database with test data for local simulation.

Run with:  python -m app.seed
Requires the API containers to be running (docker compose up -d).
"""
from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionFactory
from app.models.models import License, AppVersion
from app.services.license_service import generate_license_key


async def seed():
    async with AsyncSessionFactory() as db:
        # ── Create test licenses ──────────────────────────────────────────────
        now = datetime.now(timezone.utc)

        licenses_data = [
            {
                "key": "APRO-AAAA-BBBB-CCCC",
                "plan": "basic",
                "active": True,
                "expires_at": now + timedelta(days=365),
                "machine_id": None,  # Will be bound on first activation
                "schedule_rules": None,  # No restriction
            },
            {
                "key": "APRO-DDDD-EEEE-FFFF",
                "plan": "pro",
                "active": True,
                "expires_at": now + timedelta(days=365),
                "machine_id": None,
                "schedule_rules": {
                    "enabled": True,
                    "dias_semana": [1, 2, 3, 4, 5],  # Seg-Sex
                    "hora_inicio": "08:00",
                    "hora_fim": "18:00",
                    "timezone": "America/Sao_Paulo",
                },
            },
            {
                "key": "APRO-GGGG-HHHH-IIII",
                "plan": "basic",
                "active": True,
                "expires_at": now - timedelta(days=1),  # Already expired
                "machine_id": None,
                "schedule_rules": None,
            },
            {
                "key": "APRO-JJJJ-KKKK-LLLL",
                "plan": "basic",
                "active": False,  # Inactive
                "expires_at": now + timedelta(days=365),
                "machine_id": None,
                "schedule_rules": None,
            },
        ]

        for lic_data in licenses_data:
            # Check if already exists
            result = await db.execute(
                select(License).where(License.key == lic_data["key"])
            )
            existing = result.scalar_one_or_none()
            if existing:
                print(f"  ⏭️  License {lic_data['key']} already exists, skipping.")
                continue

            lic = License(
                id=uuid.uuid4(),
                key=lic_data["key"],
                plan=lic_data["plan"],
                active=lic_data["active"],
                expires_at=lic_data["expires_at"],
                created_at=now,
            )
            db.add(lic)
            print(f"  ✅ Created license: {lic_data['key']} ({lic_data['plan']})")

        # ── Create a sample app version ───────────────────────────────────────
        result = await db.execute(
            select(AppVersion).where(AppVersion.version == "1.0.0")
        )
        existing_version = result.scalar_one_or_none()
        if not existing_version:
            v = AppVersion(
                id=uuid.uuid4(),
                version="1.0.0",
                download_url_win="https://example.com/ApenasPromo_1.0.0.exe",
                download_url_linux="https://example.com/ApenasPromo_1.0.0",
                sha256_win="abc123def456",
                sha256_linux="789ghi012jkl",
                changelog="Versão inicial",
                released_at=now,
                is_latest=True,
            )
            db.add(v)
            print("  ✅ Created app version 1.0.0")
        else:
            print("  ⏭️  App version 1.0.0 already exists.")

        await db.commit()

    print("\n🎉 Seed completed! Test licenses:")
    print("   - APRO-AAAA-BBBB-CCCC  (basic, valid)")
    print("   - APRO-DDDD-EEEE-FFFF  (pro, valid)")
    print("   - APRO-GGGG-HHHH-IIII  (basic, expired)")
    print("   - APRO-JJJJ-KKKK-LLLL  (basic, inactive)")
    print("\nAdmin login: use ADMIN_USERNAME and ADMIN_PASSWORD from your environment")
    print("🌐 API docs: http://localhost:8000/docs")


if __name__ == "__main__":
    asyncio.run(seed())
