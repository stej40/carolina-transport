import os
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

VALID_PROFILES: tuple[str, ...] = ("local", "prod")
DEV_SECRET_PLACEHOLDER = "dev-only-secret-change-me-0123456789abcdef"
PROD_MIN_SECRET_LEN = 32


def _resolve_env_profile() -> tuple[str, Path]:
    """Map APP_ENV (default 'local') to the dotenv file of that profile."""
    profile = os.environ.get("APP_ENV", "local")
    if profile not in VALID_PROFILES:
        msg = (
            f"APP_ENV {profile!r} is not a valid profile; "
            f"expected one of: {', '.join(VALID_PROFILES)}"
        )
        raise ValueError(msg)
    return profile, Path(f".env.{profile}")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file_encoding="utf-8", extra="ignore")

    app_env: Literal["local", "prod"] = "local"

    debug: bool = False
    database_url: str = "postgresql+asyncpg://karolina:karolina@localhost:5432/karolina"
    secret_key: str = DEV_SECRET_PLACEHOLDER
    access_token_ttl_min: int = 15
    refresh_token_ttl_days: int = 30

    s3_endpoint: str = "http://localhost:9000"
    s3_access_key: str = "GKf1e2d3c4b5a69788796a5b4c"
    s3_secret_key: str = "a1b2c3d4e5f60718293a4b5c6d7e8f90a1b2c3d4e5f60718293a4b5c6d7e8f90"
    s3_bucket: str = "karolina-documents"
    s3_region: str = "garage"
    presign_ttl_sec: int = 900

    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:5174"]

    @model_validator(mode="after")
    def _prod_safety(self) -> "Settings":
        if self.app_env != "prod":
            return self
        if not Path(".env.prod").is_file():
            msg = "profile 'prod' requires the env file .env.prod in the API working directory"
            raise ValueError(msg)
        if self.debug:
            msg = "DEBUG must not be enabled in the prod profile"
            raise ValueError(msg)
        if self.secret_key == DEV_SECRET_PLACEHOLDER or len(self.secret_key) < PROD_MIN_SECRET_LEN:
            msg = (
                "SECRET_KEY in the prod profile must be a unique value "
                f"(>= {PROD_MIN_SECRET_LEN} chars, not the dev placeholder)"
            )
            raise ValueError(msg)
        return self


@lru_cache
def get_settings() -> Settings:
    _, env_file = _resolve_env_profile()
    return Settings(_env_file=env_file)


settings = get_settings()
