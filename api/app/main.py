"""FastAPI application entry point for the license/config API."""
from __future__ import annotations
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
import os
import logging
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.core.config import get_settings
from app.core.database import engine, Base
from app.routers import admin, client

settings = get_settings()

# Rate limiter - configuração global
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[f"{settings.RATE_LIMIT_PER_MINUTE}/minute"],
    storage_uri=settings.RATE_LIMIT_STORAGE_URL
)

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

# Integrar slowapi com FastAPI
app.state.limiter = limiter

@app.exception_handler(RateLimitExceeded)
async def ratelimit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={"detail": "Muitas requisições. Por favor, aguarde e tente novamente."}
    )

# CORS - Restrito a domínios autorizados (ajustar conforme ambiente)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://painel.bluebot.com",
        "https://admin.bluebot.com",
        "http://localhost:3000",  # Dev
        "http://localhost:8080",  # Bot panel
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Requested-With"],
    expose_headers=["X-Total-Count"],
)  # Recomendado: Configurar via .env em produção

# 1. Routers da API (Processados Primeiro)
app.include_router(client.router)
app.include_router(admin.router)

# 2. Painel Admin (Arquivos Estáticos)
# Usamos /panel para evitar conflito com o prefixo /admin da API
# No Docker, a pasta admin é montada em /app/admin
admin_path = "/app/admin"
if not os.path.exists(admin_path):
    # Fallback para desenvolvimento local (fora do Docker)
    admin_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../admin"))
    if not os.path.exists(admin_path):
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
