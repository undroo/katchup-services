"""PostgREST access to court_availability_slots (Supabase)."""

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import date, datetime, timezone
from typing import Any

import httpx

from app.db.venue_tags import BADMINTON_COURT_FINDER_VENUE_TAGS
from app.schemas.courts import (
    AvailabilityResponse,
    CourtAvailability,
    CourtSlot,
    SlotStatus,
)
from app.settings import Settings

logger = logging.getLogger(__name__)

TABLE = "court_availability_slots"
_BODY_LOG_MAX = 2000
_INSERT_CHUNK_SIZE = 500


def _log_postgrest_failure(operation: str, response: httpx.Response) -> None:
    text = response.text
    if len(text) > _BODY_LOG_MAX:
        text = text[:_BODY_LOG_MAX] + "..."
    logger.error(
        "PostgREST %s failed: status=%s body=%s",
        operation,
        response.status_code,
        text,
    )


def _check_response(operation: str, response: httpx.Response) -> None:
    if not response.is_success:
        _log_postgrest_failure(operation, response)
    response.raise_for_status()


def _rest_url(settings: Settings) -> str:
    return f"{settings.supabase_url.rstrip('/')}/rest/v1/{TABLE}"


def _headers(settings: Settings) -> dict[str, str]:
    key = settings.supabase_anon_key
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal",
    }


def _normalize_time(value: str) -> str:
    """DB time strings (e.g. 09:00:00) -> HH:MM matching scraper output."""
    parts = value.strip().split(":")
    if len(parts) < 2:
        return value.strip()
    h, m = int(parts[0]), int(parts[1])
    return f"{h:02d}:{m:02d}"


def _parse_scraped_at(raw: str) -> datetime:
    s = raw.replace("Z", "+00:00")
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def rows_from_availability(response: AvailabilityResponse) -> list[dict[str, Any]]:
    """Flatten AvailabilityResponse into PostgREST row dicts."""
    session_date = response.date.isoformat()
    scraped = response.scraped_at
    if scraped.tzinfo is None:
        scraped = scraped.replace(tzinfo=timezone.utc)
    scraped_iso = scraped.isoformat().replace("+00:00", "Z")

    rows: list[dict[str, Any]] = []
    for court in response.courts:
        for slot in court.slots:
            rows.append(
                {
                    "site_key": response.site,
                    "venue_name": response.venue_name,
                    "venue_timezone": "",  # filled by caller from site config
                    "session_date": session_date,
                    "court_name": court.court_name,
                    "slot_start": f"{slot.start_time}:00"
                    if len(slot.start_time) == 5
                    else slot.start_time,
                    "slot_end": f"{slot.end_time}:00"
                    if len(slot.end_time) == 5
                    else slot.end_time,
                    "status": slot.status.value,
                    "price": slot.price,
                    "scraped_at": scraped_iso,
                    "tags": list(BADMINTON_COURT_FINDER_VENUE_TAGS),
                }
            )
    return rows


def availability_from_rows(
    rows: list[dict[str, Any]],
    *,
    site_key: str,
    venue_name: str,
    venue_timezone: str,
    session_date: date,
    served_stale: bool | None = None,
) -> AvailabilityResponse | None:
    if not rows:
        return None

    by_court: dict[str, list[CourtSlot]] = defaultdict(list)
    max_scraped: datetime | None = None

    for row in rows:
        try:
            status = SlotStatus(row["status"])
        except ValueError:
            logger.warning("Unknown slot status %r, skipping row", row.get("status"))
            continue
        slot = CourtSlot(
            start_time=_normalize_time(str(row["slot_start"])),
            end_time=_normalize_time(str(row["slot_end"])),
            status=status,
            price=row.get("price"),
        )
        by_court[str(row["court_name"])].append(slot)
        raw_sa = row.get("scraped_at")
        if raw_sa:
            sa = _parse_scraped_at(str(raw_sa))
            if max_scraped is None or sa > max_scraped:
                max_scraped = sa

    if max_scraped is None:
        max_scraped = datetime.now(timezone.utc)

    courts = [
        CourtAvailability(court_name=name, slots=slots)
        for name, slots in sorted(by_court.items())
    ]

    return AvailabilityResponse(
        site=site_key,
        venue_name=venue_name,
        date=session_date,
        courts=courts,
        scraped_at=max_scraped,
        served_stale=served_stale,
    )


def _session_date_in_filter(dates: list[date]) -> str:
    """PostgREST `in` filter value for session_date."""
    inner = ",".join(d.isoformat() for d in dates)
    return f"in.({inner})"


async def fetch_slots_for_site_dates(
    client: httpx.AsyncClient,
    settings: Settings,
    site_key: str,
    dates: list[date],
) -> dict[date, list[dict[str, Any]]]:
    """Single GET for all (site_key, session_date) pairs; rows grouped by session_date."""
    empty: dict[date, list[dict[str, Any]]] = {d: [] for d in dates}
    if not dates:
        return {}

    url = _rest_url(settings)
    params = {
        "site_key": f"eq.{site_key}",
        "session_date": _session_date_in_filter(sorted(set(dates))),
        "select": "*",
        "order": "session_date.asc,court_name.asc,slot_start.asc",
    }
    resp = await client.get(url, params=params, headers=_headers(settings))
    _check_response("GET court_availability_slots (batch dates)", resp)
    data = resp.json()
    if not isinstance(data, list):
        return empty

    grouped: dict[date, list[dict[str, Any]]] = {d: [] for d in sorted(set(dates))}
    for row in data:
        raw = row.get("session_date")
        if not raw:
            continue
        try:
            parts = str(raw).split("T")[0].split("-")
            if len(parts) != 3:
                continue
            y, m, d = int(parts[0]), int(parts[1]), int(parts[2])
            key = date(y, m, d)
        except (TypeError, ValueError):
            continue
        if key not in grouped:
            continue
        grouped[key].append(row)
    return grouped


async def fetch_slots_for_day(
    client: httpx.AsyncClient,
    settings: Settings,
    site_key: str,
    session_date: date,
) -> list[dict[str, Any]]:
    url = _rest_url(settings)
    params = {
        "site_key": f"eq.{site_key}",
        "session_date": f"eq.{session_date.isoformat()}",
        "select": "*",
        "order": "court_name.asc,slot_start.asc",
    }
    resp = await client.get(url, params=params, headers=_headers(settings))
    _check_response("GET court_availability_slots", resp)
    data = resp.json()
    if not isinstance(data, list):
        return []
    return data


async def replace_slots_for_day(
    client: httpx.AsyncClient,
    settings: Settings,
    response: AvailabilityResponse,
    venue_timezone: str,
) -> None:
    """Delete all rows for (site, date) then insert the new snapshot."""
    url = _rest_url(settings)
    headers = _headers(settings)
    params = {
        "site_key": f"eq.{response.site}",
        "session_date": f"eq.{response.date.isoformat()}",
    }
    del_resp = await client.delete(url, params=params, headers=headers)
    _check_response("DELETE court_availability_slots", del_resp)

    rows = rows_from_availability(response)
    for row in rows:
        row["venue_timezone"] = venue_timezone

    if not rows:
        logger.warning(
            "Supabase snapshot for site=%s date=%s: delete ok, no slots to insert (empty scrape)",
            response.site,
            response.date.isoformat(),
        )
        return

    ins_resp = await client.post(url, json=rows, headers=headers)
    _check_response("POST court_availability_slots", ins_resp)
    logger.info(
        "Supabase snapshot updated site=%s session_date=%s inserted_rows=%s",
        response.site,
        response.date.isoformat(),
        len(rows),
    )


async def replace_slots_many_days(
    client: httpx.AsyncClient,
    settings: Settings,
    responses: list[AvailabilityResponse],
    venue_timezone: str,
) -> None:
    """Delete all rows for (site, any of these dates) then insert snapshots (chunked POST)."""
    if not responses:
        return
    site = responses[0].site
    for r in responses:
        if r.site != site:
            raise ValueError("replace_slots_many_days requires a single site_key")

    url = _rest_url(settings)
    headers = _headers(settings)
    unique_dates = sorted({r.date for r in responses})
    params = {
        "site_key": f"eq.{site}",
        "session_date": _session_date_in_filter(unique_dates),
    }
    del_resp = await client.delete(url, params=params, headers=headers)
    _check_response("DELETE court_availability_slots (batch dates)", del_resp)

    all_rows: list[dict[str, Any]] = []
    for response in responses:
        rows = rows_from_availability(response)
        for row in rows:
            row["venue_timezone"] = venue_timezone
        all_rows.extend(rows)

    if not all_rows:
        logger.warning(
            "Supabase batch snapshot site=%s dates=%s: delete ok, no rows to insert",
            site,
            [d.isoformat() for d in unique_dates],
        )
        return

    for i in range(0, len(all_rows), _INSERT_CHUNK_SIZE):
        chunk = all_rows[i : i + _INSERT_CHUNK_SIZE]
        ins_resp = await client.post(url, json=chunk, headers=headers)
        _check_response("POST court_availability_slots (batch chunk)", ins_resp)
    logger.info(
        "Supabase batch snapshot updated site=%s session_dates=%s inserted_rows=%s",
        site,
        [d.isoformat() for d in unique_dates],
        len(all_rows),
    )


def max_scraped_at(rows: list[dict[str, Any]]) -> datetime | None:
    best: datetime | None = None
    for row in rows:
        raw = row.get("scraped_at")
        if not raw:
            continue
        sa = _parse_scraped_at(str(raw))
        if best is None or sa > best:
            best = sa
    return best
