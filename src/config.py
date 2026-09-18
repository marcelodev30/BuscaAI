from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "BuscaAI"
    debug: bool = False
    database_url: str = "postgresql+asyncpg://buscaai:buscaai@localhost:5432/buscaai"

    storage_dir: str = "./storage"

    google_client_id: str = ""

    jwt_secret: str = "dev-secret-change-me"
    jwt_algorithm: str = "HS256"
    jwt_access_expires_minutes: int = 60 * 4
    jwt_refresh_expires_days: int = 7


@lru_cache
def get_settings() -> Settings:
    return Settings()
