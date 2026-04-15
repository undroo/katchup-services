from __future__ import annotations

from datetime import date, datetime, timezone
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.routers.v1 import courts as courts_router
from app.schemas.courts import (
    AvailabilityBatchResponse,
    AvailabilityDayItem,
    AvailabilityResponse,
    CourtAvailability,
    CourtSlot,
    SlotStatus,
)
from app.settings import Settings


@pytest.fixture
def sample_day():
    return AvailabilityResponse(
        site="botany",
        venue_name="BadmintonWorx Botany",
        date=date(2026, 4, 14),
        courts=[
            CourtAvailability(
                court_name="C1",
                slots=[
                    CourtSlot(
                        start_time="09:00",
                        end_time="10:00",
                        status=SlotStatus.AVAILABLE,
                    )
                ],
            )
        ],
        scraped_at=datetime(2026, 4, 13, 12, 0, 0, tzinfo=timezone.utc),
    )


def test_batch_endpoint_ok(monkeypatch, sample_day):
    monkeypatch.setattr(
        courts_router,
        "settings",
        Settings(
            supabase_url="https://proj.supabase.co",
            supabase_anon_key="k",
            availability_batch_max_dates=31,
        ),
    )
    batch_out = AvailabilityBatchResponse(
        site="botany",
        venue_name="BadmintonWorx Botany",
        days=[
            AvailabilityDayItem(
                date=date(2026, 4, 14),
                ok=True,
                data=sample_day,
                error=None,
            )
        ],
    )
    monkeypatch.setattr(
        courts_router,
        "get_availability_batch",
        AsyncMock(return_value=batch_out),
    )
    with TestClient(app) as client:
        r = client.post(
            "/v1/courts/availability/batch",
            json={"site": "botany", "dates": ["2026-04-14"]},
        )
    assert r.status_code == 200
    body = r.json()
    assert body["site"] == "botany"
    assert len(body["days"]) == 1
    assert body["days"][0]["ok"] is True


def test_batch_rejects_unknown_site(monkeypatch):
    monkeypatch.setattr(
        courts_router,
        "settings",
        Settings(
            supabase_url="https://proj.supabase.co",
            supabase_anon_key="k",
        ),
    )
    with TestClient(app) as client:
        r = client.post(
            "/v1/courts/availability/batch",
            json={"site": "not-a-site", "dates": ["2026-04-14"]},
        )
    assert r.status_code == 400


def test_batch_rejects_empty_dates(monkeypatch):
    monkeypatch.setattr(
        courts_router,
        "settings",
        Settings(
            supabase_url="https://proj.supabase.co",
            supabase_anon_key="k",
        ),
    )
    with TestClient(app) as client:
        r = client.post(
            "/v1/courts/availability/batch",
            json={"site": "botany", "dates": []},
        )
    assert r.status_code == 400


def test_batch_rejects_too_many_dates(monkeypatch):
    monkeypatch.setattr(
        courts_router,
        "settings",
        Settings(
            supabase_url="https://proj.supabase.co",
            supabase_anon_key="k",
            availability_batch_max_dates=2,
        ),
    )
    with TestClient(app) as client:
        r = client.post(
            "/v1/courts/availability/batch",
            json={
                "site": "botany",
                "dates": ["2026-04-14", "2026-04-15", "2026-04-16"],
            },
        )
    assert r.status_code == 400
