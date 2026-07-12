from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Atlas AI"
    app_version: str = "1.0.0"
    app_env: str = "development"

    debug: bool = True

    database_url: str
    redis_url: str

    openai_api_key: str

    chroma_host:str = "localhost"
    chroma_port: int = 8001

    max_upload_size_mb: int = 100

    log_level: str = "INFO"

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()

settings = get_settings()