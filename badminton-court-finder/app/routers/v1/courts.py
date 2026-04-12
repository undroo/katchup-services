from datetime import date

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query

from app.schemas.courts import AvailabilityResponse, SiteInfo, SitesListResponse
from app.scrapers.sites import SITE_REGISTRY
from app.scrapers.yepbooking import YepBookingScraper

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


@router.get("/availability", response_model=AvailabilityResponse)
async def get_availability(
    site: str = Query(description="Site key, e.g. 'botany'"),
    date_param: date = Query(alias="date", description="Date in YYYY-MM-DD format"),
    client: httpx.AsyncClient = Depends(_get_http_client),
) -> AvailabilityResponse:
    config = SITE_REGISTRY.get(site)
    if config is None:
        available = ", ".join(sorted(SITE_REGISTRY.keys()))
        raise HTTPException(
            status_code=400,
            detail=f"Unknown site '{site}'. Available: {available}",
        )

    scraper = YepBookingScraper(config)
    try:
        return await scraper.scrape_availability(client, date_param)
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
