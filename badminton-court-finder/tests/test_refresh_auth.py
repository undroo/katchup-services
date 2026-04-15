from __future__ import annotations

from datetime import date, datetime, timezone
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.routers.v1 import courts as courts_router
from app.schemas.courts import AvailabilityResponse, CourtAvailability, CourtSlot, SlotStatus
from app.settings import Settings


@pytest.fixture
def sample_availability():
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


def test_refresh_rejects_without_api_key(monkeypatch, sample_availability):
    monkeypatch.setattr(
        courts_router,
        "settings",
        Settings(
            supabase_url="https://proj.supabase.co",
            supabase_anon_key="k",
            refresh_api_key="expected-secret",
        ),
    )
    monkeypatch.setattr(
        courts_router,
        "get_availability",
        AsyncMock(return_value=sample_availability),
    )
    with TestClient(app) as client:
        r = client.post(
            "/v1/courts/availability/refresh",
            json={"site": "botany", "date": "2026-04-14"},
        )
    assert r.status_code == 401


def test_refresh_accepts_api_key(monkeypatch, sample_availability):
    monkeypatch.setattr(
        courts_router,
        "settings",
        Settings(
            supabase_url="https://proj.supabase.co",
            supabase_anon_key="k",
            refresh_api_key="expected-secret",
        ),
    )
    monkeypatch.setattr(
        courts_router,
        "get_availability",
        AsyncMock(return_value=sample_availability),
    )
    with TestClient(app) as client:
        r = client.post(
            "/v1/courts/availability/refresh",
            json={"site": "botany", "date": "2026-04-14"},
            headers={"X-Refresh-Api-Key": "expected-secret"},
        )
    assert r.status_code == 200
    assert r.json()["site"] == "botany"
