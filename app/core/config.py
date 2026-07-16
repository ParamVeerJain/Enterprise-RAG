from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )
    APP_NAME: str = "enterprise-rag"
    ENV: str = "local"
    DEBUG: bool = False
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8001
    LOG_LEVEL: str = "INFO"
    LOG_DIR: Path = ROOT_DIR / "app" / "logs"

    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "admin"
    POSTGRES_PASSWORD: str = "password"
    POSTGRES_DB: str = "enterprise_rag"
    POSTGRES_SCHEMA: str = "enterprise_rag"
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_ECHO: bool = False

    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: str | None = None

    JWT_ISS: str = "enterprise-auth"
    JWT_ALG: str = "RS256"
    JWT_KID: str = "auth-rs256-1"
    JWT_TOKEN_VER: int = 2
    ACCESS_TTL_SECONDS: int = 15 * 60
    REFRESH_TTL_SECONDS: int = 30 * 24 * 60 * 60

    KEYS_DIR: Path = ROOT_DIR / "keys"
    PRIVATE_KEY_NAME: str = "jwt_private.pem"
    PUBLIC_KEY_NAME: str = "jwt_public.pem"
    RSA_KEY_SIZE: int = 2048

    MSG91_AUTH_KEY: str | None = None
    TWILIO_ACCOUNT_SID: str | None = None
    TWILIO_AUTH_TOKEN: str | None = None
    GOOGLE_OAUTH_CLIENT_ID: str | None = None
    GOOGLE_OAUTH_CLIENT_SECRET: str | None = None
    SENDGRID_API_KEY: str | None = None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def database_dsn(self) -> str:
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def redis_url(self) -> str:
        auth = f":{self.REDIS_PASSWORD}@" if self.REDIS_PASSWORD else ""
        return f"redis://{auth}{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    @property
    def private_key_path(self) -> Path:
        return self.KEYS_DIR / self.PRIVATE_KEY_NAME

    @property
    def public_key_path(self) -> Path:
        return self.KEYS_DIR / self.PUBLIC_KEY_NAME

    @property
    def is_prod(self) -> bool:
        return self.ENV.lower() in {"prod", "production"}


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()