from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.database import get_db
from app.core.security import create_access_token, verify_password
from app.core.config import get_settings
from app.models.models import License
from app.schemas.schemas import AdminLoginRequest, AdminLoginResponse, ClientLoginRequest

router = APIRouter(prefix="/auth", tags=["Authentication"])
settings = get_settings()
limiter = Limiter(key_func=get_remote_address)

import pyotp

@router.post("/login/admin")
@limiter.limit("5/minute")
async def admin_login(body: AdminLoginRequest, request: Request):
    """Admin login with optional 2FA support."""
    username = body.username.strip()
    password = body.password.strip()

    if username != settings.ADMIN_USERNAME or password != settings.ADMIN_PASSWORD:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Credenciais administrativas inválidas"
        )
    
    # Se o 2FA estiver configurado no .env, não entrega o token ainda
    if settings.ADMIN_TOTP_SECRET:
        return {
            "require_2fa": True,
            "message": "Código de autenticação de dois fatores necessário"
        }

    token = create_access_token({"sub": username, "role": "admin"}, expires_minutes=120)
    return AdminLoginResponse(access_token=token)

@router.post("/login/admin/verify")
@limiter.limit("5/minute")
async def admin_2fa_verify(body: dict, request: Request):
    """Verify 2FA code and return the final admin token."""
    code = body.get("code")
    if not settings.ADMIN_TOTP_SECRET:
        raise HTTPException(status_code=400, detail="2FA não está ativado")
    
    totp = pyotp.TOTP(settings.ADMIN_TOTP_SECRET)
    if not totp.verify(code):
        raise HTTPException(status_code=401, detail="Código 2FA inválido")
    
    token = create_access_token({"sub": settings.ADMIN_USERNAME, "role": "admin"}, expires_minutes=120)
    return AdminLoginResponse(access_token=token)

@router.post("/login/client", response_model=AdminLoginResponse)
@limiter.limit("10/minute")
async def client_login(body: ClientLoginRequest, request: Request, db: AsyncSession = Depends(get_db)):
    """Client login using License Key and License Password."""
    license_key = body.license_key.strip()
    password = body.password.strip()

    result = await db.execute(select(License).where(License.key == license_key))
    lic = result.scalar_one_or_none()

    if not lic:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Chave de licença não encontrada"
        )
    
    if not lic.active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Esta licença está desativada"
        )

    if not lic.password or not verify_password(password, lic.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Senha da licença incorreta"
        )
    
    # O 'sub' do JWT para clientes é o ID (UUID) da licença para isolamento total
    token = create_access_token({"sub": str(lic.id), "role": "client"}, expires_minutes=settings.JWT_EXPIRE_MINUTES)
    return AdminLoginResponse(access_token=token)
