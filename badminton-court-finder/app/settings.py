from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    request_timeout: float = 15.0
    rate_limit_delay: float = 1.0
    max_connections: int = 10
    # Comma-separated origins for browser clients (e.g. Activity Hub). Empty = no CORS middleware.
    cors_allow_origins: str = ""

    model_config = {"env_prefix": ""}


settings = Settings()
