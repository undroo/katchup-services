from __future__ import annotations

from datetime import date
from typing import Annotated, Optional

import httpx
from fastapi import APIRouter, Depends, Header, HTTPException, Query

from app.schemas.courts import (
    AvailabilityBatchBody,
    AvailabilityBatchResponse,
    AvailabilityRefreshBody,
    AvailabilityResponse,
    SiteInfo,
    SitesListResponse,
)
from app.scrapers.sites import SITE_REGISTRY
from app.scrapers.yepbooking import YepBookingSiteConfig
from app.services.availability_service import get_availability, get_availability_batch
from app.settings import settings

router = APIRouter(prefix="/courts", tags=["courts"])


@router.get("/sites", response_model=SitesListResponse)
async def list_sites() -> SitesListResponse:
    sites = [
        SiteInfo(key=key, venue_name=cfg.venue_name, timezone=cfg.timezone)
        for key, cfg in sorted(SITE_REGISTRY.items(), key=lambda kv: kv[0])
    ]
    return SitesListResponse(sites=sites)


def _get_http_client() -> httpx.AsyncClient:
    """Overridden at app startup via dependency_overrides."""
    raise RuntimeError("http client not initialised")


def _require_refresh_api_key(
    x_refresh_api_key: Annotated[
        Optional[str], Header(alias="X-Refresh-Api-Key")
    ] = None,
) -> None:
    expected = settings.refresh_api_key.strip()
    if not expected:
        return
    if x_refresh_api_key != expected:
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing X-Refresh-Api-Key header.",
        )


def _resolve_site(site: str) -> YepBookingSiteConfig:
    config = SITE_REGISTRY.get(site)
    if config is None:
        available = ", ".join(sorted(SITE_REGISTRY.keys()))
        raise HTTPException(
            status_code=400,
            detail=f"Unknown site '{site}'. Available: {available}",
        )
    return config


@router.post("/availability/batch", response_model=AvailabilityBatchResponse)
async def get_availability_batch_endpoint(
    body: AvailabilityBatchBody,
    client: httpx.AsyncClient = Depends(_get_http_client),
) -> AvailabilityBatchResponse:
    config = _resolve_site(body.site)
    unique = sorted(set(body.dates))
    if not unique:
        raise HTTPException(status_code=400, detail="dates must not be empty.")
    max_n = settings.availability_batch_max_dates
    if len(unique) > max_n:
        raise HTTPException(
            status_code=400,
            detail=f"At most {max_n} distinct dates allowed per batch request.",
        )
    return await get_availability_batch(config, unique, client)


@router.get("/availability", response_model=AvailabilityResponse)
async def get_availability_endpoint(
    site: str = Query(description="Site key, e.g. 'botany'"),
    date_param: date = Query(alias="date", description="Date in YYYY-MM-DD format"),
    client: httpx.AsyncClient = Depends(_get_http_client),
) -> AvailabilityResponse:
    config = _resolve_site(site)
    try:
        return await get_availability(config, date_param, client, force_refresh=False)
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Upstream error: {exc.response.status_code}",
        ) from exc
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Failed to reach {site}: {exc}",
        ) from exc


@router.post("/availability/refresh", response_model=AvailabilityResponse)
async def refresh_availability(
    body: AvailabilityRefreshBody,
    client: httpx.AsyncClient = Depends(_get_http_client),
    _: None = Depends(_require_refresh_api_key),
) -> AvailabilityResponse:
    config = _resolve_site(body.site)
    try:
        return await get_availability(
            config, body.date, client, force_refresh=True
        )
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Upstream error: {exc.response.status_code}",
        ) from exc
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Failed to reach {body.site}: {exc}",
        ) from exc
