"""Google Places API (New) — Text Search helper for featured_places enrichment."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any
from urllib.parse import quote

import httpx

logger = logging.getLogger(__name__)

PLACES_SEARCH_TEXT_URL = "https://places.googleapis.com/v1/places:searchText"
# Field paths for Text Search (New); no spaces in X-Goog-FieldMask.
_TEXT_SEARCH_FIELD_MASK = (
    "places.id,places.displayName,places.formattedAddress,"
    "places.location,places.rating,places.priceLevel,places.photos"
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
    preview_image_url: str | None


def _first_photo_name(place: dict[str, Any]) -> str | None:
    photos = place.get("photos")
    if not isinstance(photos, list) or not photos:
        return None
    first = photos[0]
    if isinstance(first, dict):
        n = first.get("name")
        if isinstance(n, str) and n.strip():
            return n.strip()
    return None


def resolve_place_photo_url(
    client: httpx.Client,
    api_key: str,
    photo_resource_name: str,
    *,
    max_height_px: int = 400,
    timeout: float = 30.0,
) -> str | None:
    """
    GET Place Photo (New) media; follow redirects to the CDN image URL.

    Stores the final https URL (typically googleusercontent.com) so we do not persist the API key.
    """
    name = photo_resource_name.strip()
    if not name:
        return None
    # Resource name is path-shaped, e.g. places/ChIJ.../photos/AWn5...
    path = quote(name, safe="/")
    url = f"https://places.googleapis.com/v1/{path}/media"
    headers = {
        "X-Goog-Api-Key": api_key,
    }
    resp = client.get(
        url,
        params={"maxHeightPx": max_height_px},
        headers=headers,
        follow_redirects=True,
        timeout=timeout,
    )
    if not resp.is_success:
        logger.warning(
            "Place photo media failed: status=%s name=%s",
            resp.status_code,
            name[:120],
        )
        return None
    final = str(resp.url)
    if not final.startswith("https://"):
        return None
    ct = (resp.headers.get("content-type") or "").lower()
    # Inline image on the Places host is not a shareable URL (no key on client).
    if ct.startswith("image/") and "places.googleapis.com" in final:
        logger.warning(
            "Place photo returned inline image on places.googleapis.com; skip preview_image_url"
        )
        return None
    if "places.googleapis.com" in final:
        return None
    return final


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
        preview_image_url=None,
    )


def parse_place_with_photo_url(
    place: dict[str, Any],
    *,
    preview_image_url: str | None,
) -> PlaceEnrichment | None:
    """Like _parse_place but attaches a resolved preview_image_url (CDN) if provided."""
    base = _parse_place(place)
    if base is None:
        return None
    return PlaceEnrichment(
        google_place_id=base.google_place_id,
        address=base.address,
        latitude=base.latitude,
        longitude=base.longitude,
        location=base.location,
        rating=base.rating,
        price_level=base.price_level,
        preview_image_url=preview_image_url,
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
    photo_name = _first_photo_name(first)
    preview_url: str | None = None
    if photo_name:
        preview_url = resolve_place_photo_url(client, api_key, photo_name)
        if preview_url is None:
            logger.info(
                "No redirect URL for place photo; leaving preview_image_url unset (place id=%s)",
                first.get("id"),
            )
    return parse_place_with_photo_url(first, preview_image_url=preview_url)
