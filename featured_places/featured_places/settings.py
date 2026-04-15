"""Environment configuration for Supabase PostgREST (anon key), matching badminton-court-finder."""

from __future__ import annotations

from pathlib import Path

from pydantic import model_validator
from pydantic_settings import BaseSettings


def _get_env_file_from_parent_env_folder() -> str | None:
    """
    Returns the path to the .env file inside the 'env' directory,
    which is a sibling of the project root (same layout as badminton-court-finder).
    """
    package_dir = Path(__file__).parent.absolute()
    repo_root = package_dir.parent
    env_folder = repo_root.parent / "env"
    env_file = env_folder / ".env"
    return str(env_file) if env_file.exists() else None


class Settings(BaseSettings):
    """SUPABASE_URL and SUPABASE_ANON_KEY (same env/.env pattern as badminton-court-finder)."""

    supabase_url: str = ""
    supabase_anon_key: str = ""
    #: Optional. If set, featured_places writes use this key (bypasses RLS). Prefer for local/admin sync.
    supabase_service_role_key: str = ""
    #: Google Maps / Places API (New). Used by enrich_google_places script (see repo env.example).
    google_maps_api_key: str = ""

    model_config = {
        "env_prefix": "",
        "env_file": _get_env_file_from_parent_env_folder(),
        "extra": "ignore",
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
