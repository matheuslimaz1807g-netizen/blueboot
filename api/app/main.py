"""FastAPI application entry point for the license/config API."""
from __future__ import annotations
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
import os
import logging

# Configuração de Logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from app.core.config import get_settings
from app.core.database import engine, Base
from app.routers import admin, client

settings = get_settings()

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Banco de dados sincronizado com sucesso.")
    except Exception as e:
        logger.error(f"Erro ao sincronizar banco: {e}")
    yield

app = FastAPI(
    title="BlueBot License & Config API",
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

# CORS Total para evitar qualquer bloqueio no navegador
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 1. Routers da API (Processados Primeiro)
app.include_router(client.router)
app.include_router(admin.router)

# 2. Painel Admin (Arquivos Estáticos)
# Usamos /panel para evitar conflito com o prefixo /admin da API
admin_path = "/app/admin"
if not os.path.exists(admin_path):
    # Fallback para desenvolvimento local
    admin_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../admin"))

if os.path.exists(admin_path):
    logger.info(f"Montando Painel Admin em /panel a partir de: {admin_path}")
    app.mount("/panel", StaticFiles(directory=admin_path, html=True), name="panel")

@app.get("/")
async def root():
    # Redireciona a raiz direto para o painel
    return RedirectResponse(url="/panel/")

@app.get("/health")
async def health():
    return {"status": "ok"}
