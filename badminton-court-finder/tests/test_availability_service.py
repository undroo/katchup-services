from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest

from app.schemas.courts import (
    AvailabilityResponse,
    CourtAvailability,
    CourtSlot,
    SlotStatus,
)
from app.scrapers.sites.botany import BOTANY_CONFIG
from app.services import availability_service as svc
from app.settings import Settings


def _utc_iso(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat().replace("+00:00", "Z")


def _row(
    *,
    scraped_at: datetime,
    session_day: date | None = None,
    start: str = "09:00:00",
    end: str = "10:00:00",
) -> dict:
    sd = (session_day or date(2026, 4, 14)).isoformat()
    return {
        "id": "00000000-0000-0000-0000-000000000001",
        "site_key": "botany",
        "venue_name": "BadmintonWorx Botany",
        "venue_timezone": "Australia/Sydney",
        "session_date": sd,
        "court_name": "Court 1",
        "slot_start": start,
        "slot_end": end,
        "status": "available",
        "price": None,
        "scraped_at": _utc_iso(scraped_at),
        "created_at": _utc_iso(scraped_at),
    }


def _fresh_response() -> AvailabilityResponse:
    return AvailabilityResponse(
        site="botany",
        venue_name="BadmintonWorx Botany",
        date=date(2026, 4, 14),
        courts=[
            CourtAvailability(
                court_name="Court A",
                slots=[
                    CourtSlot(
                        start_time="11:00",
                        end_time="12:00",
                        status=SlotStatus.AVAILABLE,
                    )
                ],
            )
        ],
        scraped_at=datetime(2026, 4, 13, 12, 0, 0, tzinfo=timezone.utc),
    )


@pytest.fixture
def http_client():
    import httpx

    return httpx.AsyncClient()


def _settings(**kwargs) -> Settings:
    base = dict(
        supabase_url="https://proj.supabase.co",
        supabase_anon_key="anon-key",
        court_data_max_age_seconds=3600,
        court_min_scrape_interval_seconds=3600,
        refresh_api_key="",
    )
    base.update(kwargs)
    return Settings(**base)


@pytest.mark.asyncio
async def test_cache_hit_fresh_no_scrape(http_client):
    now = datetime.now(timezone.utc)
    rows = [_row(scraped_at=now - timedelta(minutes=5))]
    test_settings = _settings()

    with (
        patch.object(svc.db, "fetch_slots_for_day", new_callable=AsyncMock) as fetch,
        patch.object(svc.db, "replace_slots_for_day", new_callable=AsyncMock) as replace,
        patch.object(svc, "_scrape", new_callable=AsyncMock) as scrape,
    ):
        fetch.return_value = rows
        out = await svc.get_availability(
            BOTANY_CONFIG,
            date(2026, 4, 14),
            http_client,
            app_settings=test_settings,
        )
        scrape.assert_not_awaited()
        replace.assert_not_awaited()
        assert out.site == "botany"
        assert out.served_stale is False
        assert out.courts[0].court_name == "Court 1"


@pytest.mark.asyncio
async def test_stale_but_min_interval_blocks(http_client):
    """max_age < min_gap: data older than max_age but scrape within min_gap is blocked."""
    now = datetime.now(timezone.utc)
    scraped = now - timedelta(minutes=45)
    rows = [_row(scraped_at=scraped)]
    test_settings = _settings(
        court_data_max_age_seconds=30 * 60,
        court_min_scrape_interval_seconds=60 * 60,
    )

    with (
        patch.object(svc.db, "fetch_slots_for_day", new_callable=AsyncMock) as fetch,
        patch.object(svc.db, "replace_slots_for_day", new_callable=AsyncMock) as replace,
        patch.object(svc, "_scrape", new_callable=AsyncMock) as scrape,
    ):
        fetch.return_value = rows
        out = await svc.get_availability(
            BOTANY_CONFIG,
            date(2026, 4, 14),
            http_client,
            app_settings=test_settings,
        )
        scrape.assert_not_awaited()
        replace.assert_not_awaited()
        assert out.served_stale is True


@pytest.mark.asyncio
async def test_stale_triggers_scrape_and_persist(http_client):
    now = datetime.now(timezone.utc)
    scraped = now - timedelta(hours=2)
    rows = [_row(scraped_at=scraped)]
    fresh = _fresh_response()
    test_settings = _settings()

    with (
        patch.object(svc.db, "fetch_slots_for_day", new_callable=AsyncMock) as fetch,
        patch.object(svc.db, "replace_slots_for_day", new_callable=AsyncMock) as replace,
        patch.object(svc, "_scrape", new_callable=AsyncMock) as scrape,
    ):
        fetch.return_value = rows
        scrape.return_value = fresh
        out = await svc.get_availability(
            BOTANY_CONFIG,
            date(2026, 4, 14),
            http_client,
            app_settings=test_settings,
        )
        scrape.assert_awaited_once()
        replace.assert_awaited_once()
        assert out.courts[0].court_name == "Court A"
        assert out.served_stale is False


@pytest.mark.asyncio
async def test_force_refresh_always_scrapes(http_client):
    now = datetime.now(timezone.utc)
    rows = [_row(scraped_at=now - timedelta(minutes=1))]
    fresh = _fresh_response()
    test_settings = _settings()

    with (
        patch.object(svc.db, "fetch_slots_for_day", new_callable=AsyncMock) as fetch,
        patch.object(svc.db, "replace_slots_for_day", new_callable=AsyncMock) as replace,
        patch.object(svc, "_scrape", new_callable=AsyncMock) as scrape,
    ):
        fetch.return_value = rows
        scrape.return_value = fresh
        out = await svc.get_availability(
            BOTANY_CONFIG,
            date(2026, 4, 14),
            http_client,
            force_refresh=True,
            app_settings=test_settings,
        )
        fetch.assert_not_awaited()
        scrape.assert_awaited_once()
        replace.assert_awaited_once()
        assert out.courts[0].court_name == "Court A"


@pytest.mark.asyncio
async def test_supabase_disabled_scrapes_only(http_client):
    test_settings = Settings(
        supabase_url="",
        supabase_anon_key="",
    )
    fresh = _fresh_response()
    with (
        patch.object(svc.db, "fetch_slots_for_day", new_callable=AsyncMock) as fetch,
        patch.object(svc, "_scrape", new_callable=AsyncMock) as scrape,
    ):
        scrape.return_value = fresh
        out = await svc.get_availability(
            BOTANY_CONFIG,
            date(2026, 4, 14),
            http_client,
            app_settings=test_settings,
        )
        fetch.assert_not_awaited()
        scrape.assert_awaited_once()
        assert out == fresh


def _fresh_response_for_date(d: date) -> AvailabilityResponse:
    return AvailabilityResponse(
        site="botany",
        venue_name="BadmintonWorx Botany",
        date=d,
        courts=[
            CourtAvailability(
                court_name="Court A",
                slots=[
                    CourtSlot(
                        start_time="11:00",
                        end_time="12:00",
                        status=SlotStatus.AVAILABLE,
                    )
                ],
            )
        ],
        scraped_at=datetime(2026, 4, 13, 12, 0, 0, tzinfo=timezone.utc),
    )


@pytest.mark.asyncio
async def test_batch_all_supabase_cache_hits_no_scrape(http_client):
    now = datetime.now(timezone.utc)
    d1, d2 = date(2026, 4, 14), date(2026, 4, 15)
    grouped = {
        d1: [_row(scraped_at=now - timedelta(minutes=5), session_day=d1)],
        d2: [_row(scraped_at=now - timedelta(minutes=5), session_day=d2)],
    }
    test_settings = _settings()

    with (
        patch.object(
            svc.db, "fetch_slots_for_site_dates", new_callable=AsyncMock
        ) as fetch_batch,
        patch.object(
            svc.db, "replace_slots_many_days", new_callable=AsyncMock
        ) as replace_many,
        patch.object(svc, "_scrape", new_callable=AsyncMock) as scrape,
    ):
        fetch_batch.return_value = grouped
        out = await svc.get_availability_batch(
            BOTANY_CONFIG,
            [d2, d1, d1],
            http_client,
            app_settings=test_settings,
        )
        fetch_batch.assert_awaited_once()
        scrape.assert_not_awaited()
        replace_many.assert_not_awaited()
        assert len(out.days) == 2
        assert all(day.ok for day in out.days)
        assert [day.date for day in out.days] == [d1, d2]


@pytest.mark.asyncio
async def test_batch_no_supabase_scrapes_each_day(http_client):
    test_settings = Settings(supabase_url="", supabase_anon_key="")
    d1, d2 = date(2026, 4, 14), date(2026, 4, 15)

    async def scrape_side_effect(cfg, target_date, client):
        return _fresh_response_for_date(target_date)

    with patch.object(svc, "_scrape", new_callable=AsyncMock) as scrape:
        scrape.side_effect = scrape_side_effect
        out = await svc.get_availability_batch(
            BOTANY_CONFIG,
            [d1, d2],
            http_client,
            app_settings=test_settings,
        )
        assert scrape.await_count == 2
        assert len(out.days) == 2
        assert all(day.ok for day in out.days)


@pytest.mark.asyncio
async def test_batch_stale_triggers_replace_many_days(http_client):
    now = datetime.now(timezone.utc)
    d1, d2 = date(2026, 4, 14), date(2026, 4, 15)
    stale = now - timedelta(hours=2)
    grouped = {
        d1: [_row(scraped_at=stale, session_day=d1)],
        d2: [_row(scraped_at=stale, session_day=d2)],
    }
    test_settings = _settings()

    async def scrape_side_effect(cfg, target_date, client):
        return _fresh_response_for_date(target_date)

    with (
        patch.object(
            svc.db, "fetch_slots_for_site_dates", new_callable=AsyncMock
        ) as fetch_batch,
        patch.object(
            svc.db, "replace_slots_many_days", new_callable=AsyncMock
        ) as replace_many,
        patch.object(svc, "_scrape", new_callable=AsyncMock) as scrape,
    ):
        fetch_batch.return_value = grouped
        scrape.side_effect = scrape_side_effect
        out = await svc.get_availability_batch(
            BOTANY_CONFIG,
            [d1, d2],
            http_client,
            app_settings=test_settings,
        )
        assert scrape.await_count == 2
        replace_many.assert_awaited_once()
        args, _kwargs = replace_many.call_args
        snapshots = args[2]
        assert len(snapshots) == 2
        assert all(day.ok for day in out.days)


@pytest.mark.asyncio
async def test_batch_one_day_scrape_fails_other_ok(http_client):
    now = datetime.now(timezone.utc)
    d1, d2 = date(2026, 4, 14), date(2026, 4, 15)
    grouped = {
        d1: [_row(scraped_at=now - timedelta(minutes=5), session_day=d1)],
        d2: [],
    }
    test_settings = _settings()
    import httpx

    with (
        patch.object(
            svc.db, "fetch_slots_for_site_dates", new_callable=AsyncMock
        ) as fetch_batch,
        patch.object(
            svc.db, "replace_slots_many_days", new_callable=AsyncMock
        ) as replace_many,
        patch.object(svc, "_scrape", new_callable=AsyncMock) as scrape,
    ):
        fetch_batch.return_value = grouped

        async def scrape_side_effect(cfg, target_date, client):
            if target_date == d2:
                raise httpx.ConnectError("boom")
            return _fresh_response_for_date(target_date)

        scrape.side_effect = scrape_side_effect
        out = await svc.get_availability_batch(
            BOTANY_CONFIG,
            [d1, d2],
            http_client,
            app_settings=test_settings,
        )
        assert scrape.await_count == 1
        assert out.days[0].ok is True
        assert out.days[1].ok is False
        assert out.days[1].error is not None
        replace_many.assert_not_awaited()
