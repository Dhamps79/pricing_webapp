from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Live Spreadsheet"
    environment: str = "development"

    # Provide a sensible default so tests and local runs don't fail when
    # DATABASE_URL is not set in the environment. This default will be
    # overridden by the DATABASE_URL environment variable when present.
    database_url: str = "sqlite+aiosqlite:///./test.db"

    cors_origins: str = (
        "http://localhost:5173,"
        "http://127.0.0.1:5173"
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def cors_origin_list(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.cors_origins.split(",")
            if origin.strip()
        ]


@lru_cache
def get_settings() -> Settings:
    return Settings()
