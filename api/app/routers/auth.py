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

@router.post("/login/admin", response_model=AdminLoginResponse)
@limiter.limit("5/minute")
async def admin_login(body: AdminLoginRequest, request: Request):
    """Admin login using username/password from env."""
    username = body.username.strip()
    password = body.password.strip()

    if username != settings.ADMIN_USERNAME or password != settings.ADMIN_PASSWORD:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Credenciais administrativas inválidas"
        )
    
    token = create_access_token({"sub": username, "role": "admin"}, expires_minutes=120)
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
