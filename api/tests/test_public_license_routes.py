from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import sys
from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.database import get_db
from app.routers import license as license_router
from app.schemas.schemas import LicenseValidateResponse


class FakeResult:
    def __init__(self, value: Any):
        self.value = value

    def scalar_one_or_none(self) -> Any:
        return self.value


class FakeSession:
    def __init__(self, *results: Any):
        self.results = list(results)
        self.added: list[Any] = []
        self.commits = 0

    async def execute(self, _statement: Any) -> FakeResult:
        value = self.results.pop(0) if self.results else None
        return FakeResult(value)

    def add(self, value: Any) -> None:
        self.added.append(value)

    async def commit(self) -> None:
        self.commits += 1


def make_client(session: FakeSession) -> TestClient:
    app = FastAPI()
    app.include_router(license_router.router)

    async def override_db():
        yield session

    app.dependency_overrides[get_db] = override_db
    return TestClient(app)


def test_public_license_routes_are_registered():
    paths = {route.path for route in license_router.router.routes}

    assert "/license/discover" in paths
    assert "/license/validate" in paths
    assert "/license/heartbeat" in paths
    assert "/license/auth-code" in paths
    assert "/config/{license_key}" in paths


def test_discover_creates_pending_machine_when_unassigned(monkeypatch):
    monkeypatch.setattr(license_router.settings, "INSTALL_TOKEN", "test-install-token")
    session = FakeSession(None, None)
    client = make_client(session)

    response = client.post(
        "/license/discover",
        headers={"X-Install-Token": "test-install-token"},
        json={
            "machine_id": "machine-1234567890",
            "hostname": "bluebot-host",
            "platform": "Linux",
            "label": "BlueBot",
        },
    )

    assert response.status_code == 200
    assert response.json() == {"pending": True}
    assert len(session.added) == 1
    assert session.added[0].machine_id == "machine-1234567890"
    assert session.commits == 1


def test_validate_license_returns_signed_payload(monkeypatch):
    async def fake_validate_license(_db, key, machine_id):
        assert key == "APRO-AAAA-BBBB-CCCC"
        assert machine_id == "machine-1234567890"
        return LicenseValidateResponse(
            valid=True,
            plan="basic",
            expires_at=datetime(2026, 12, 31, tzinfo=timezone.utc),
        )

    monkeypatch.setattr(license_router.license_service, "validate_license", fake_validate_license)

    session = FakeSession()
    client = make_client(session)

    response = client.post(
        "/license/validate",
        json={"license_key": "APRO-AAAA-BBBB-CCCC", "machine_id": "machine-1234567890"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["valid"] is True
    assert data["plan"] == "basic"
    assert data["signature"]
