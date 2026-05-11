import hashlib

from pydantic import AliasChoices, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore", env_file=".env")

    DATABASE_URL: str
    JWT_SECRET: str | None = None
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60

    BLUEBOT_FERNET_KEY: str = Field(validation_alias=AliasChoices("BLUEBOT_FERNET_KEY", "FERNET_KEY"))
    INSTALL_TOKEN: str

    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str
    ADMIN_TOTP_SECRET: str | None = None

    API_BASE_URL: str = "https://api.bluebotapp.com.br"
    RATE_LIMIT_PER_MINUTE: int = 60
    RATE_LIMIT_STORAGE_URL: str = "memory://"
    APP_VERSION: str = "1.0.0"

    @model_validator(mode="after")
    def reject_insecure_defaults(self):
        insecure_fields = []
        if not self.JWT_SECRET:
            derived = hashlib.sha256(f"{self.INSTALL_TOKEN}:{self.BLUEBOT_FERNET_KEY}".encode()).hexdigest()
            object.__setattr__(self, "JWT_SECRET", derived)

        for field_name in ("DATABASE_URL", "JWT_SECRET", "BLUEBOT_FERNET_KEY", "INSTALL_TOKEN", "ADMIN_PASSWORD"):
            value = getattr(self, field_name, "")
            normalized = value.lower()
            if not value or "change_me" in normalized or "your_" in normalized:
                insecure_fields.append(field_name)
        if insecure_fields:
            joined = ", ".join(insecure_fields)
            raise ValueError(f"Variaveis obrigatorias ausentes ou inseguras: {joined}")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
