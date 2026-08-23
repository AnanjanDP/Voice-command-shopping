from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    groq_api_key: str | None = None
    database_url: str = "sqlite:///./shopping.db"
    allowed_origins: str = "http://localhost:5173"
    secret_key: str = "development-only-change-me"


@lru_cache
def get_settings() -> Settings:
    return Settings()
