"""Read court_availability_slots; write featured_places."""

from __future__ import annotations

import logging
from collections import defaultdict
from collections.abc import Iterator
from datetime import datetime, timezone
from typing import Any

import httpx

from featured_places.client import (
    check_response,
    headers_json,
    patch_json,
    post_json,
    rest_table_url,
)
from featured_places.settings import Settings

logger = logging.getLogger(__name__)

TABLE_SLOTS = "court_availability_slots"
TABLE_FEATURED = "featured_places"
_PAGE_SIZE = 1000
_UPSERT_CHUNK = 500


def _featured_places_write_key(settings: Settings) -> str:
    sk = settings.supabase_service_role_key.strip()
    if sk:
        return sk
    return settings.supabase_anon_key


def _parse_scraped_at(raw: object) -> datetime | None:
    if raw is None:
        return None
    s = str(raw).replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _slot_rows_pages(
    client: httpx.Client,
    settings: Settings,
) -> Iterator[list[dict[str, Any]]]:
    """Yield pages of rows with fields needed to dedupe venues."""
    base = rest_table_url(settings.supabase_url, TABLE_SLOTS)
    params = {
        "select": "site_key,venue_name,venue_timezone,scraped_at",
        "order": "site_key.asc,scraped_at.desc",
    }
    key = settings.supabase_anon_key
    offset = 0
    while True:
        headers = headers_json(key, prefer_minimal=True)
        headers["Range"] = f"{offset}-{offset + _PAGE_SIZE - 1}"
        resp = client.get(base, params=params, headers=headers)
        check_response("GET court_availability_slots (paged)", resp)
        raw = resp.json()
        if not isinstance(raw, list) or not raw:
            break
        yield raw
        if len(raw) < _PAGE_SIZE:
            break
        offset += _PAGE_SIZE


def fetch_distinct_court_venues(
    client: httpx.Client,
    settings: Settings,
) -> list[dict[str, str]]:
    """
    One dict per distinct site_key: site_key, venue_name, venue_timezone.
    When names or timezones differ across rows, keep the row with latest scraped_at.
    """
    best: dict[str, dict[str, Any]] = {}
    best_scraped: dict[str, datetime | None] = defaultdict(lambda: None)

    for page in _slot_rows_pages(client, settings):
        for row in page:
            sk = row.get("site_key")
            if not sk:
                continue
            sk = str(sk)
            sa = _parse_scraped_at(row.get("scraped_at"))
            prev = best_scraped[sk]
            if prev is None or (sa is not None and sa >= prev):
                best_scraped[sk] = sa
                best[sk] = row

    out: list[dict[str, str]] = []
    for sk in sorted(best.keys()):
        row = best[sk]
        out.append(
            {
                "site_key": sk,
                "venue_name": str(row.get("venue_name") or sk),
                "venue_timezone": str(row.get("venue_timezone") or "Australia/Sydney"),
            }
        )
    return out


def venue_rows_to_featured_payloads(venues: list[dict[str, str]]) -> list[dict[str, Any]]:
    """Build PostgREST bodies for featured_places (badminton_court)."""
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    rows: list[dict[str, Any]] = []
    for v in venues:
        sk = v["site_key"]
        rows.append(
            {
                "name": v["venue_name"],
                "court_site_key": sk,
                "kind": "badminton_court",
                "extra": {"venue_timezone": v["venue_timezone"]},
                "updated_at": now,
            }
        )
    return rows


def upsert_featured_places(
    client: httpx.Client,
    settings: Settings,
    rows: list[dict[str, Any]],
) -> None:
    """
    Upsert on court_site_key (unique).

    Uses SUPABASE_SERVICE_ROLE_KEY when set (bypasses RLS); otherwise SUPABASE_ANON_KEY
    (requires anon INSERT/UPDATE policies — see sql/002_featured_places_rls_policies.sql).
    """
    if not rows:
        logger.info("No featured_places rows to upsert")
        return
    write_key = _featured_places_write_key(settings)
    if write_key != settings.supabase_anon_key:
        logger.info("featured_places upsert using service role key (RLS bypass)")
    base = rest_table_url(settings.supabase_url, TABLE_FEATURED)
    url = f"{base}?on_conflict=court_site_key"
    headers = headers_json(
        write_key,
        prefer_minimal=True,
        prefer_merge_duplicates=True,
    )
    total = 0
    for i in range(0, len(rows), _UPSERT_CHUNK):
        chunk = rows[i : i + _UPSERT_CHUNK]
        post_json(
            client,
            url,
            json=chunk,
            headers=headers,
            operation="POST featured_places (upsert chunk)",
        )
        total += len(chunk)
    logger.info("Upserted featured_places rows=%s", total)


def _missing_google_place_id(row: dict[str, Any]) -> bool:
    raw = row.get("google_place_id")
    if raw is None:
        return True
    return not str(raw).strip()


def fetch_featured_places_for_google_enrichment(
    client: httpx.Client,
    settings: Settings,
    *,
    court_site_key: str | None = None,
    missing_google_only: bool = True,
) -> list[dict[str, Any]]:
    """
    Rows suitable for Google Places enrichment (badminton_court with court_site_key).

    Reads with SUPABASE_ANON_KEY (SELECT policy allows anon).
    When missing_google_only, excludes rows that already have a non-empty google_place_id.
    """
    base = rest_table_url(settings.supabase_url, TABLE_FEATURED)
    params: dict[str, str] = {
        "select": "id,name,court_site_key,google_place_id,extra,kind",
        "kind": "eq.badminton_court",
        "order": "court_site_key.asc",
    }
    if court_site_key:
        params["court_site_key"] = f"eq.{court_site_key}"
    else:
        params["court_site_key"] = "not.is.null"
    if missing_google_only:
        params["or"] = "(google_place_id.is.null,google_place_id.eq.)"

    key = settings.supabase_anon_key
    headers = headers_json(key, prefer_minimal=True)
    out: list[dict[str, Any]] = []
    offset = 0
    while True:
        h = dict(headers)
        h["Range"] = f"{offset}-{offset + _PAGE_SIZE - 1}"
        resp = client.get(base, params=params, headers=h)
        check_response("GET featured_places (enrichment)", resp)
        raw = resp.json()
        if not isinstance(raw, list) or not raw:
            break
        out.extend(raw)
        if len(raw) < _PAGE_SIZE:
            break
        offset += _PAGE_SIZE

    if missing_google_only:
        out = [r for r in out if _missing_google_place_id(r)]
    return out


def patch_featured_place_fields(
    client: httpx.Client,
    settings: Settings,
    row_id: str,
    fields: dict[str, Any],
) -> None:
    """PATCH a single featured_places row by primary key id."""
    write_key = _featured_places_write_key(settings)
    base = rest_table_url(settings.supabase_url, TABLE_FEATURED)
    url = f"{base}?id=eq.{row_id}"
    headers = headers_json(write_key, prefer_minimal=True)
    patch_json(
        client,
        url,
        json=fields,
        headers=headers,
        operation="PATCH featured_places",
    )
