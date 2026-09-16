from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    db_host: str = "localhost"
    db_port: int = 3306
    db_user: str = "yt-pao"
    db_password: str = "password"
    db_name: str = "yt_pao_db"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
