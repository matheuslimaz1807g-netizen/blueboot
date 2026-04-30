"""FastAPI application entry point for the license/config API."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.core.config import get_settings
from app.core.database import engine, Base
from app.routers import admin, client

settings = get_settings()

limiter = Limiter(key_func=get_remote_address, default_limits=[f"{settings.RATE_LIMIT_PER_MINUTE}/minute"])


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Tables are created by Alembic migrations; this is a safety fallback for dev
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(
    title="BlueBot License & Config API",
    version=settings.APP_VERSION,
    docs_url=None,  # Disable Swagger in production
    redoc_url=None,
    lifespan=lifespan,
)

# Rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS — allow only the executable's localhost requests
# In production, CORS is handled by nginx; this is a safety net
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8080",
        "http://127.0.0.1:8080",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)

# Routers
app.include_router(client.router, tags=["Client"])
app.include_router(admin.router, tags=["Admin"])


@app.get("/health")
async def health():
    return {"status": "ok"}
