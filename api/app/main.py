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
from app.routers import admin, client, auth

logger = logging.getLogger(__name__)

settings = get_settings()

# CORS - Configuração segura por ambiente
allowed_origins = os.getenv("CORS_ALLOWED_ORIGINS", "").split(",") if os.getenv("CORS_ALLOWED_ORIGINS") else [
    "http://localhost:8080",
    "http://localhost:3000",
    "http://localhost:5173",
    "http://127.0.0.1:8080",
    "https://console.bluebotapp.com.br",
    "https://app.bluebotapp.com.br",
    "https://api.bluebotapp.com.br",
    "https://bluebotapp.com.br",
    "https://www.bluebotapp.com.br",
]

logger.info(f"CORS habilitado para origins: {allowed_origins}")
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

# O middleware CORS usará o allowed_origins definido acima

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Total-Count"],
    max_age=86400,  # Preflight cache por 24 horas
)

# 1. Routers da API (Processados Primeiro)
app.include_router(auth.router)
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

# 3. Painel do Cliente (SaaS Unificado)
client_app_path = "/app/client_app"
if not os.path.exists(client_app_path):
    client_app_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../client_app"))

if os.path.exists(client_app_path):
    logger.info(f"Montando Painel Cliente em /app_static a partir de: {client_app_path}")
    app.mount("/app_static", StaticFiles(directory=client_app_path, html=True), name="app_static")

@app.get("/")
async def root(request: Request):
    host = request.headers.get("host", "")
    # Se o acesso for pelo subdomínio de cliente
    if "app.bluebotapp.com.br" in host:
        return RedirectResponse(url="/app_static/")
    # Se for pelo subdomínio de admin ou geral
    return RedirectResponse(url="/panel/")

@app.get("/health")
async def health():
    return {"status": "ok"}
