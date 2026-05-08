from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import decode_token

bearer_scheme = HTTPBearer()


async def get_admin_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> dict:
    """Validate JWT and confirm role=admin for admin-only endpoints."""
    try:
        payload = decode_token(credentials.credentials)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido ou expirado",
        )

    if payload.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso restrito ao painel admin",
        )
    return payload


async def get_current_license(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> License:
    """Validate JWT and return the associated License object. Used for client-facing endpoints."""
    try:
        payload = decode_token(credentials.credentials)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sessão inválida ou expirada",
        )

    if payload.get("role") != "client":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso não autorizado",
        )

    license_id = payload.get("sub")
    if not license_id:
        raise HTTPException(status_code=401, detail="Token malformado")

    from app.models.models import License
    from sqlalchemy import select

    result = await db.execute(select(License).where(License.id == license_id))
    lic = result.scalar_one_or_none()

    if not lic or not lic.active:
        raise HTTPException(status_code=401, detail="Licença inativa ou não encontrada")

    return lic
