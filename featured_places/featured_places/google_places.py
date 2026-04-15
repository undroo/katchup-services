"""Google Places API (New) — Text Search helper for featured_places enrichment."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import httpx

logger = logging.getLogger(__name__)

PLACES_SEARCH_TEXT_URL = "https://places.googleapis.com/v1/places:searchText"
# Field paths for Text Search (New); no spaces in X-Goog-FieldMask.
_TEXT_SEARCH_FIELD_MASK = (
    "places.id,places.displayName,places.formattedAddress,"
    "places.location,places.rating,places.priceLevel"
)

# Sydney CBD-ish bias when venue_timezone is Australia/Sydney (meters).
# Places API (New) requires circle.radius in [0, 50000].
_SYDNEY_BIAS = {
    "circle": {
        "center": {"latitude": -33.8688, "longitude": 151.2093},
        "radius": 50000.0,
    }
}

_PRICE_LEVEL_TO_INT: dict[str, int] = {
    "PRICE_LEVEL_FREE": 0,
    "PRICE_LEVEL_INEXPENSIVE": 1,
    "PRICE_LEVEL_MODERATE": 2,
    "PRICE_LEVEL_EXPENSIVE": 3,
    "PRICE_LEVEL_VERY_EXPENSIVE": 4,
}


@dataclass(frozen=True)
class PlaceEnrichment:
    """Subset of Place fields mapped to featured_places columns."""

    google_place_id: str
    address: str | None
    latitude: float | None
    longitude: float | None
    location: str | None
    rating: float | None
    price_level: int | None


def _display_name_text(place: dict[str, Any]) -> str | None:
    dn = place.get("displayName")
    if isinstance(dn, dict):
        t = dn.get("text")
        if isinstance(t, str) and t.strip():
            return t.strip()
    return None


def _parse_place(place: dict[str, Any]) -> PlaceEnrichment | None:
    pid = place.get("id")
    if not isinstance(pid, str) or not pid.strip():
        return None
    lat: float | None = None
    lng: float | None = None
    loc = place.get("location")
    if isinstance(loc, dict):
        try:
            lat = float(loc["latitude"])
            lng = float(loc["longitude"])
        except (KeyError, TypeError, ValueError):
            lat, lng = None, None

    addr = place.get("formattedAddress")
    address = addr.strip() if isinstance(addr, str) and addr.strip() else None

    rating_raw = place.get("rating")
    rating: float | None = None
    if rating_raw is not None:
        try:
            rating = float(rating_raw)
        except (TypeError, ValueError):
            rating = None

    price_level: int | None = None
    pl = place.get("priceLevel")
    if isinstance(pl, str) and pl in _PRICE_LEVEL_TO_INT:
        price_level = _PRICE_LEVEL_TO_INT[pl]
    elif isinstance(pl, int) and 0 <= pl <= 4:
        price_level = pl

    return PlaceEnrichment(
        google_place_id=pid.strip(),
        address=address,
        latitude=lat,
        longitude=lng,
        location=_display_name_text(place),
        rating=rating,
        price_level=price_level,
    )


def text_query_for_venue(name: str) -> str:
    q = name.strip()
    if not q:
        return "badminton court Australia"
    return f"{q} badminton court Australia"


def search_text_first_place(
    client: httpx.Client,
    api_key: str,
    text_query: str,
    *,
    venue_timezone: str | None = None,
    max_result_count: int = 5,
    timeout: float = 30.0,
) -> PlaceEnrichment | None:
    """
    POST places:searchText; returns the first place in the response or None.

    Requires Places API (New) on the GCP project and a valid API key.
    """
    body: dict[str, Any] = {
        "textQuery": text_query,
        "languageCode": "en",
        "regionCode": "AU",
        "maxResultCount": max_result_count,
    }
    tz = (venue_timezone or "").strip()
    if tz == "Australia/Sydney":
        body["locationBias"] = _SYDNEY_BIAS

    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": _TEXT_SEARCH_FIELD_MASK,
    }
    resp = client.post(
        PLACES_SEARCH_TEXT_URL,
        json=body,
        headers=headers,
        timeout=timeout,
    )
    if not resp.is_success:
        logger.error(
            "Places searchText failed: status=%s body=%s",
            resp.status_code,
            resp.text[:2000],
        )
        resp.raise_for_status()

    data = resp.json()
    places = data.get("places")
    if not isinstance(places, list) or not places:
        logger.warning("Places searchText returned no places for query=%r", text_query)
        return None

    if len(places) > 1:
        logger.info(
            "Places searchText returned %s results; using the first for query=%r",
            len(places),
            text_query,
        )

    first = places[0]
    if not isinstance(first, dict):
        return None
    return _parse_place(first)
