from functools import lru_cache
from os import getenv

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = Field(default="Procuratorial Investigation Portrait Backend", alias="APP_NAME")
    app_env: str = Field(default="dev", alias="APP_ENV")
    api_prefix: str = Field(default="/api/v1", alias="API_PREFIX")
    algorithm_provider: str = Field(default="stub", alias="ALGORITHM_PROVIDER")
    memory_auto_writeback: bool = Field(default=False, alias="MEMORY_AUTO_WRITEBACK")
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:5173", "http://127.0.0.1:5173"]


@lru_cache
def get_settings() -> Settings:
    env_file = getenv("ENV_FILE")
    if env_file:
        return Settings(_env_file=env_file)
    return Settings()


settings = get_settings()
