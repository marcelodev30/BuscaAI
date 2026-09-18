from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "BuscaAI"
    debug: bool = False
    database_url: str = "postgresql+asyncpg://buscaai:buscaai@localhost:5432/buscaai"

    storage_dir: str = "./storage"

    # Elasticsearch externo: a aplicação não sobe o serviço, só se conecta.
    elasticsearch_url: str = "http://localhost:9200"
    elasticsearch_user: str = ""
    elasticsearch_password: str = ""
    elasticsearch_index: str = "buscaai-chunks"

    embedding_model: str = "BAAI/bge-m3"
    embedding_dimensions: int = 1024
    embedding_batch_size: int = 16

    google_client_id: str = ""

    jwt_secret: str = "dev-secret-change-me"
    jwt_algorithm: str = "HS256"
    jwt_access_expires_minutes: int = 60 * 4
    jwt_refresh_expires_days: int = 7


@lru_cache
def get_settings() -> Settings:
    return Settings()
