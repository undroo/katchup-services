import os
from pathlib import Path

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _get_env_file_from_parent_env_folder() -> str:
    """
    Returns the path to the .env file inside the 'env' directory,
    which is a sibling of the current file's parent (i.e., ../../env/.env relative to this file).
    """
    # Get the current file's directory (app/)
    app_dir = Path(__file__).parent.absolute()
    # Get the parent of the current file's directory (project root)
    repo_root = app_dir.parent
    # The env folder: <repo_root>/env/.env
    env_folder = repo_root / "env"
    env_file = env_folder / ".env"
    return str(env_file) if env_file.exists() else None


class Settings(BaseSettings):
    request_timeout: float = 15.0
    rate_limit_delay: float = 1.0
    max_connections: int = 10
    # Comma-separated origins for browser clients (e.g. Activity Hub). Empty = no CORS middleware.
    cors_allow_origins: str = ""
    # Supabase PostgREST (project URL, e.g. https://xxx.supabase.co). Empty = scrape-only mode.
    supabase_url: str = ""
    supabase_anon_key: str = ""
    court_data_max_age_seconds: int = 3600
    court_min_scrape_interval_seconds: int = 3600
    availability_batch_max_dates: int = 31
    # If set, POST /v1/courts/availability/refresh requires header X-Refresh-Api-Key.
    refresh_api_key: str = ""

    model_config = {
        "env_prefix": "",
        "env_file": _get_env_file_from_parent_env_folder(),
    }

    @model_validator(mode="after")
    def _supabase_pair(self) -> "Settings":
        has_url = bool(self.supabase_url.strip())
        has_key = bool(self.supabase_anon_key.strip())
        if has_url != has_key:
            raise ValueError(
                "Set both SUPABASE_URL and SUPABASE_ANON_KEY, or leave both empty."
            )
        return self

    @property
    def supabase_enabled(self) -> bool:
        return bool(self.supabase_url.strip() and self.supabase_anon_key.strip())


settings = Settings()
