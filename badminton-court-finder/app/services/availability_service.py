"""Read-through cache: Supabase when fresh, else YepBooking scrape + persist."""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone

import httpx

from app.db import supabase_availability as db
from app.schemas.courts import (
    AvailabilityBatchResponse,
    AvailabilityDayItem,
    AvailabilityResponse,
)
from app.scrapers.yepbooking import YepBookingScraper, YepBookingSiteConfig
from app.settings import Settings, settings as default_settings

logger = logging.getLogger(__name__)


async def _scrape(
    config: YepBookingSiteConfig,
    target_date: date,
    http_client: httpx.AsyncClient,
) -> AvailabilityResponse:
    scraper = YepBookingScraper(config)
    return await scraper.scrape_availability(http_client, target_date)


def _try_serve_from_supabase_rows(
    rows: list[dict],
    config: YepBookingSiteConfig,
    target_date: date,
    s: Settings,
    now: datetime,
) -> AvailabilityResponse | None:
    """If cached data is sufficient, return it; otherwise None (caller should scrape)."""
    last = db.max_scraped_at(rows)
    max_age = timedelta(seconds=s.court_data_max_age_seconds)
    min_gap = timedelta(seconds=s.court_min_scrape_interval_seconds)

    stale = not rows or last is None or (now - last) > max_age
    interval_blocks = last is not None and (now - last) < min_gap

    if rows:
        logger.info(
            "Supabase read site=%s date=%s row_count=%s stale=%s "
            "min_interval_would_block=%s",
            config.site_key,
            target_date,
            len(rows),
            stale,
            interval_blocks,
        )

    if rows and not stale:
        cached = db.availability_from_rows(
            rows,
            site_key=config.site_key,
            venue_name=config.venue_name,
            venue_timezone=config.timezone,
            session_date=target_date,
            served_stale=False,
        )
        if cached is not None:
            logger.info(
                "Serving from Supabase cache (fresh); no write site=%s date=%s",
                config.site_key,
                target_date,
            )
            return cached

    if rows and stale and interval_blocks:
        cached = db.availability_from_rows(
            rows,
            site_key=config.site_key,
            venue_name=config.venue_name,
            venue_timezone=config.timezone,
            session_date=target_date,
            served_stale=True,
        )
        if cached is not None:
            logger.info(
                "Serving stale Supabase cache (min scrape interval); "
                "no scrape/write site=%s date=%s",
                config.site_key,
                target_date,
            )
            return cached

    return None


async def get_availability(
    config: YepBookingSiteConfig,
    target_date: date,
    http_client: httpx.AsyncClient,
    *,
    force_refresh: bool = False,
    app_settings: Settings | None = None,
) -> AvailabilityResponse:
    s = app_settings or default_settings

    if not s.supabase_enabled:
        logger.info(
            "Scrape-only mode (no Supabase); site=%s date=%s",
            config.site_key,
            target_date,
        )
        return await _scrape(config, target_date, http_client)

    if force_refresh:
        fresh = await _scrape(config, target_date, http_client)
        logger.info(
            "Attempting Supabase persist (force refresh) site=%s date=%s",
            config.site_key,
            target_date,
        )
        try:
            await db.replace_slots_for_day(
                http_client, s, fresh, venue_timezone=config.timezone
            )
            logger.info(
                "Supabase persist succeeded (force refresh) site=%s date=%s",
                config.site_key,
                target_date,
            )
        except (httpx.HTTPError, ValueError) as exc:
            logger.error(
                "Supabase write failed (force refresh) %s %s: %s",
                config.site_key,
                target_date,
                exc,
            )
        return AvailabilityResponse(
            site=fresh.site,
            venue_name=fresh.venue_name,
            date=fresh.date,
            courts=fresh.courts,
            scraped_at=fresh.scraped_at,
            served_stale=False,
        )

    rows: list[dict] = []
    try:
        rows = await db.fetch_slots_for_day(
            http_client, s, config.site_key, target_date
        )
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning(
            "Supabase read failed for %s %s: %s; falling back to scrape",
            config.site_key,
            target_date,
            exc,
        )

    now = datetime.now(timezone.utc)
    cached = _try_serve_from_supabase_rows(rows, config, target_date, s, now)
    if cached is not None:
        return cached

    fresh = await _scrape(config, target_date, http_client)
    logger.info(
        "Attempting Supabase persist after live scrape site=%s date=%s",
        config.site_key,
        target_date,
    )
    try:
        await db.replace_slots_for_day(
            http_client, s, fresh, venue_timezone=config.timezone
        )
        logger.info(
            "Supabase persist succeeded after live scrape site=%s date=%s",
            config.site_key,
            target_date,
        )
    except (httpx.HTTPError, ValueError) as exc:
        logger.error(
            "Supabase write failed for %s %s: %s",
            config.site_key,
            target_date,
            exc,
        )
    return AvailabilityResponse(
        site=fresh.site,
        venue_name=fresh.venue_name,
        date=fresh.date,
        courts=fresh.courts,
        scraped_at=fresh.scraped_at,
        served_stale=False,
    )


def _scrape_error_message(config: YepBookingSiteConfig, exc: BaseException) -> str:
    if isinstance(exc, httpx.HTTPStatusError):
        return f"Upstream error: {exc.response.status_code}"
    if isinstance(exc, httpx.RequestError):
        return f"Failed to reach {config.site_key}: {exc}"
    return str(exc)


async def get_availability_batch(
    config: YepBookingSiteConfig,
    dates: list[date],
    http_client: httpx.AsyncClient,
    *,
    app_settings: Settings | None = None,
) -> AvailabilityBatchResponse:
    s = app_settings or default_settings
    sorted_dates = sorted(set(dates))
    now = datetime.now(timezone.utc)

    if not s.supabase_enabled:
        days: list[AvailabilityDayItem] = []
        for d in sorted_dates:
            try:
                fresh = await _scrape(config, d, http_client)
                days.append(
                    AvailabilityDayItem(date=d, ok=True, data=fresh, error=None)
                )
            except (httpx.HTTPStatusError, httpx.RequestError) as exc:
                days.append(
                    AvailabilityDayItem(
                        date=d,
                        ok=False,
                        data=None,
                        error=_scrape_error_message(config, exc),
                    )
                )
        return AvailabilityBatchResponse(
            site=config.site_key,
            venue_name=config.venue_name,
            days=days,
        )

    grouped: dict[date, list[dict]] = {d: [] for d in sorted_dates}
    try:
        grouped = await db.fetch_slots_for_site_dates(
            http_client, s, config.site_key, sorted_dates
        )
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning(
            "Supabase batch read failed for %s: %s; treating days as uncached",
            config.site_key,
            exc,
        )

    need_scrape: list[date] = []
    resolved: dict[date, AvailabilityDayItem] = {}

    for d in sorted_dates:
        rows = grouped.get(d, [])
        cached = _try_serve_from_supabase_rows(rows, config, d, s, now)
        if cached is not None:
            resolved[d] = AvailabilityDayItem(
                date=d, ok=True, data=cached, error=None
            )
        else:
            need_scrape.append(d)

    fresh_by_date: dict[date, AvailabilityResponse] = {}
    for d in need_scrape:
        try:
            fresh = await _scrape(config, d, http_client)
            fresh_by_date[d] = fresh
        except (httpx.HTTPStatusError, httpx.RequestError) as exc:
            resolved[d] = AvailabilityDayItem(
                date=d,
                ok=False,
                data=None,
                error=_scrape_error_message(config, exc),
            )

    if fresh_by_date:
        snapshots = [fresh_by_date[d] for d in need_scrape if d in fresh_by_date]
        logger.info(
            "Attempting Supabase batch persist after live scrapes site=%s dates=%s",
            config.site_key,
            [d.isoformat() for d in fresh_by_date],
        )
        try:
            await db.replace_slots_many_days(
                http_client,
                s,
                snapshots,
                venue_timezone=config.timezone,
            )
            logger.info(
                "Supabase batch persist succeeded site=%s count=%s",
                config.site_key,
                len(snapshots),
            )
        except (httpx.HTTPError, ValueError) as exc:
            logger.error(
                "Supabase batch write failed for %s: %s",
                config.site_key,
                exc,
            )
        for d, fresh in fresh_by_date.items():
            resolved[d] = AvailabilityDayItem(
                date=d, ok=True, data=fresh, error=None
            )

    days_out = [resolved[d] for d in sorted_dates]
    return AvailabilityBatchResponse(
        site=config.site_key,
        venue_name=config.venue_name,
        days=days_out,
    )
