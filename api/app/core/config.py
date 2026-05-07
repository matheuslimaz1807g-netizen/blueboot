from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore", env_file=".env")

    DATABASE_URL: str = "postgresql+asyncpg://bluebot:S3cur3P@ss!2026#BlueBot@postgres:5432/bluebot"
    JWT_SECRET: str = "7d33672694b5f0741bfaf7cf73669a6bb46d85f9df8286e2d323fbf9dbf86a66"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60

    BLUEBOT_FERNET_KEY: str = "ptaiS0u-FfzRI0iG-scBtJphQyrPIzG5un0YCuiEBtU="
    INSTALL_TOKEN: str = "Bt-S3cur3-Inst@ll-2026!"

    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = "Adm1n-S3cur3-P@ss!2026#"

    API_BASE_URL: str = "https://api.bluebotapp.com.br"
    RATE_LIMIT_PER_MINUTE: int = 60
    RATE_LIMIT_STORAGE_URL: str = "memory://"
    APP_VERSION: str = "1.0.0"


@lru_cache
def get_settings() -> Settings:
    s = Settings()
    # Check if loaded from env or using default
    import os
    if s.ADMIN_USERNAME == "admin" and os.getenv("ADMIN_USERNAME") != "admin" and os.getenv("ADMIN_USERNAME") is not None:
        # This would indicate a loading failure
        pass 
    return s
