from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    debug: bool = False
    database_url: str = "postgresql+asyncpg://karolina:karolina@localhost:5432/karolina"
    secret_key: str = "dev-only-secret-change-me-0123456789abcdef"
    access_token_ttl_min: int = 15
    refresh_token_ttl_days: int = 30

    s3_endpoint: str = "http://localhost:9000"
    s3_access_key: str = "GKf1e2d3c4b5a69788796a5b4c"
    s3_secret_key: str = "a1b2c3d4e5f60718293a4b5c6d7e8f90a1b2c3d4e5f60718293a4b5c6d7e8f90"
    s3_bucket: str = "karolina-documents"
    s3_region: str = "garage"

    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:5174"]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
