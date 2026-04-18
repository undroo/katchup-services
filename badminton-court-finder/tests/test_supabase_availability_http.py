from __future__ import annotations

import logging
from datetime import date, datetime, timezone

import httpx
import pytest
import respx

from app.db import supabase_availability as db
from app.schemas.courts import (
    AvailabilityResponse,
    CourtAvailability,
    CourtSlot,
    SlotStatus,
)
from app.settings import Settings


def _settings() -> Settings:
    return Settings(
        supabase_url="https://proj.supabase.co",
        supabase_anon_key="test-key",
    )


@pytest.mark.asyncio
async def test_fetch_slots_for_day_parses_json():
    payload = [
        {
            "site_key": "botany",
            "venue_name": "BadmintonWorx Botany",
            "venue_timezone": "Australia/Sydney",
            "session_date": "2026-04-14",
            "court_name": "Court 1",
            "slot_start": "09:00:00",
            "slot_end": "10:00:00",
            "status": "available",
            "price": None,
            "scraped_at": "2026-04-13T12:00:00Z",
        }
    ]
    with respx.mock:
        route = respx.get(
            "https://proj.supabase.co/rest/v1/court_availability_slots"
        ).mock(return_value=httpx.Response(200, json=payload))
        async with httpx.AsyncClient() as client:
            rows = await db.fetch_slots_for_day(
                client, _settings(), "botany", date(2026, 4, 14)
            )
        assert len(rows) == 1
        assert rows[0]["court_name"] == "Court 1"
        assert route.called


@pytest.mark.asyncio
async def test_replace_slots_for_day_delete_then_post():
    resp = AvailabilityResponse(
        site="botany",
        venue_name="BadmintonWorx Botany",
        date=date(2026, 4, 14),
        courts=[
            CourtAvailability(
                court_name="C1",
                slots=[
                    CourtSlot(
                        start_time="08:00",
                        end_time="09:00",
                        status=SlotStatus.AVAILABLE,
                    )
                ],
            )
        ],
        scraped_at=datetime(2026, 4, 13, 12, 0, 0, tzinfo=timezone.utc),
    )
    with respx.mock:
        del_route = respx.delete(
            "https://proj.supabase.co/rest/v1/court_availability_slots"
        ).mock(return_value=httpx.Response(204))
        post_route = respx.post(
            "https://proj.supabase.co/rest/v1/court_availability_slots"
        ).mock(return_value=httpx.Response(201))
        async with httpx.AsyncClient() as client:
            await db.replace_slots_for_day(
                client, _settings(), resp, venue_timezone="Australia/Sydney"
            )
        assert del_route.called
        assert post_route.called
        posted = post_route.calls.last.request.content.decode()
        assert "Australia/Sydney" in posted
        assert "08:00:00" in posted
        assert "sport:badminton" in posted
        assert "environment:indoors" in posted
        assert "access:private" in posted
        assert "place_type:court" in posted


@pytest.mark.asyncio
async def test_replace_slots_post_failure_logs_response_body(caplog):
    resp = AvailabilityResponse(
        site="botany",
        venue_name="BadmintonWorx Botany",
        date=date(2026, 4, 14),
        courts=[
            CourtAvailability(
                court_name="C1",
                slots=[
                    CourtSlot(
                        start_time="08:00",
                        end_time="09:00",
                        status=SlotStatus.AVAILABLE,
                    )
                ],
            )
        ],
        scraped_at=datetime(2026, 4, 13, 12, 0, 0, tzinfo=timezone.utc),
    )
    with respx.mock:
        respx.delete(
            "https://proj.supabase.co/rest/v1/court_availability_slots"
        ).mock(return_value=httpx.Response(204))
        respx.post(
            "https://proj.supabase.co/rest/v1/court_availability_slots"
        ).mock(
            return_value=httpx.Response(
                403, json={"message": "new row violates row-level security"}
            )
        )
        with caplog.at_level(logging.ERROR, logger="app.db.supabase_availability"):
            async with httpx.AsyncClient() as client:
                with pytest.raises(httpx.HTTPStatusError):
                    await db.replace_slots_for_day(
                        client,
                        _settings(),
                        resp,
                        venue_timezone="Australia/Sydney",
                    )
        assert any(
            "PostgREST POST court_availability_slots failed" in r.message
            and "403" in r.message
            and "row-level security" in r.message
            for r in caplog.records
        )


@pytest.mark.asyncio
async def test_fetch_slots_for_site_dates_groups_by_day():
    d1, d2 = date(2026, 4, 14), date(2026, 4, 15)
    payload = [
        {
            "site_key": "botany",
            "venue_name": "BadmintonWorx Botany",
            "venue_timezone": "Australia/Sydney",
            "session_date": "2026-04-14",
            "court_name": "Court 1",
            "slot_start": "09:00:00",
            "slot_end": "10:00:00",
            "status": "available",
            "price": None,
            "scraped_at": "2026-04-13T12:00:00Z",
        },
        {
            "site_key": "botany",
            "venue_name": "BadmintonWorx Botany",
            "venue_timezone": "Australia/Sydney",
            "session_date": "2026-04-15",
            "court_name": "Court 2",
            "slot_start": "10:00:00",
            "slot_end": "11:00:00",
            "status": "booked",
            "price": None,
            "scraped_at": "2026-04-13T12:00:00Z",
        },
    ]
    with respx.mock:
        route = respx.get(
            "https://proj.supabase.co/rest/v1/court_availability_slots"
        ).mock(return_value=httpx.Response(200, json=payload))
        async with httpx.AsyncClient() as client:
            grouped = await db.fetch_slots_for_site_dates(
                client, _settings(), "botany", [d2, d1]
            )
        assert route.called
        req = route.calls[0].request
        assert "session_date" in str(req.url)
        assert "in." in str(req.url)
    assert len(grouped[d1]) == 1
    assert grouped[d1][0]["court_name"] == "Court 1"
    assert len(grouped[d2]) == 1
    assert grouped[d2][0]["court_name"] == "Court 2"


@pytest.mark.asyncio
async def test_replace_slots_many_days_delete_in_then_chunked_post():
    d1, d2 = date(2026, 4, 14), date(2026, 4, 15)
    r1 = AvailabilityResponse(
        site="botany",
        venue_name="BadmintonWorx Botany",
        date=d1,
        courts=[
            CourtAvailability(
                court_name="C1",
                slots=[
                    CourtSlot(
                        start_time="08:00",
                        end_time="09:00",
                        status=SlotStatus.AVAILABLE,
                    )
                ],
            )
        ],
        scraped_at=datetime(2026, 4, 13, 12, 0, 0, tzinfo=timezone.utc),
    )
    r2 = AvailabilityResponse(
        site="botany",
        venue_name="BadmintonWorx Botany",
        date=d2,
        courts=[
            CourtAvailability(
                court_name="C2",
                slots=[
                    CourtSlot(
                        start_time="09:00",
                        end_time="10:00",
                        status=SlotStatus.BOOKED,
                    )
                ],
            )
        ],
        scraped_at=datetime(2026, 4, 13, 12, 0, 0, tzinfo=timezone.utc),
    )
    with respx.mock:
        del_route = respx.delete(
            "https://proj.supabase.co/rest/v1/court_availability_slots"
        ).mock(return_value=httpx.Response(204))
        post_route = respx.post(
            "https://proj.supabase.co/rest/v1/court_availability_slots"
        ).mock(return_value=httpx.Response(201))
        async with httpx.AsyncClient() as client:
            await db.replace_slots_many_days(
                client, _settings(), [r1, r2], venue_timezone="Australia/Sydney"
            )
        assert del_route.called
        assert "in." in str(del_route.calls[0].request.url)
        assert post_route.call_count == 1
        posted = post_route.calls.last.request.content.decode()
        assert "2026-04-14" in posted and "2026-04-15" in posted
        assert "sport:badminton" in posted
