from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    DATABASE_URL: str = "postgresql+asyncpg://bluebot:bluebot_secret@localhost:5432/bluebot"
    JWT_SECRET: str = "change_me_jwt_secret"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60

    BLUEBOT_FERNET_KEY: str = "change_me_fernet_key"
    INSTALL_TOKEN: str = "mudar-para-senha-secreta"

    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = "change_me"

    API_BASE_URL: str = "http://localhost:8000"
    RATE_LIMIT_PER_MINUTE: int = 60
    APP_VERSION: str = "1.0.0"


@lru_cache
def get_settings() -> Settings:
    return Settings()
