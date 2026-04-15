from __future__ import annotations

import logging
import sys
from contextlib import asynccontextmanager
from typing import AsyncIterator
from urllib.parse import urlparse

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers.v1 import courts as courts_router
from app.settings import settings

logger = logging.getLogger(__name__)


def _configure_app_logging_to_stdout() -> None:
    """Route package loggers to stdout at INFO so operators see cache/persist lines."""
    app_log = logging.getLogger("app")
    if app_log.handlers:
        return
    app_log.setLevel(logging.INFO)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("[%(name)s] %(levelname)s: %(message)s"))
    app_log.addHandler(handler)
    # Keep propagate=True so logs still reach the root logger (pytest caplog, uvicorn).


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    _configure_app_logging_to_stdout()
    if settings.supabase_enabled:
        host = urlparse(settings.supabase_url).netloc or settings.supabase_url.strip()
        logger.info("Supabase persist enabled (host=%s).", host)
    else:
        logger.info(
            "Supabase not configured; court availability uses live scraping only."
        )
    client = httpx.AsyncClient(
        timeout=httpx.Timeout(settings.request_timeout),
        limits=httpx.Limits(
            max_connections=settings.max_connections,
            max_keepalive_connections=settings.max_connections,
        ),
        follow_redirects=True,
    )
    app.dependency_overrides[courts_router._get_http_client] = lambda: client
    try:
        yield
    finally:
        await client.aclose()


app = FastAPI(
    title="Badminton Court Finder",
    description=(
        "Scrapes badminton venue websites for court availability. "
        "Human-readable API docs: **/docs** (Swagger) and **/redoc**. "
        "Machine-readable schema: **/openapi.json**."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(courts_router.router, prefix="/v1")

_cors_origins = [o.strip() for o in settings.cors_allow_origins.split(",") if o.strip()]
if _cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_cors_origins,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
