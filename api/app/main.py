"""FastAPI application entry point for the license/config API."""
from __future__ import annotations
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
import os
import logging

# Configuração de Logs para facilitar o debug
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from app.core.config import get_settings
from app.core.database import engine, Base
from app.routers import admin, client

settings = get_settings()

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield

app = FastAPI(
    title="BlueBot License & Config API",
    version=settings.APP_VERSION,
    docs_url=None,
    redoc_url=None,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers (API)
app.include_router(client.router, tags=["Client"])
app.include_router(admin.router, tags=["Admin"])

# Painel Admin (Arquivos Estáticos)
# No Docker, montamos a pasta admin em /app/admin
admin_path = "/app/admin"
if os.path.exists(admin_path):
    logger.info(f"Montando arquivos estáticos de: {admin_path}")
    app.mount("/admin", StaticFiles(directory=admin_path, html=True), name="admin")
else:
    logger.warning(f"AVISO: Pasta admin não encontrada em {admin_path}")

@app.get("/")
async def root():
    return RedirectResponse(url="/admin/")

@app.get("/health")
async def health():
    return {"status": "ok"}
