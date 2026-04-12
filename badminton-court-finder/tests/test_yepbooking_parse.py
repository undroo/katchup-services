from __future__ import annotations

from dataclasses import replace
from datetime import date
from pathlib import Path

import pytest

from app.schemas.courts import SlotStatus
from app.scrapers.sites.botany import BOTANY_CONFIG
from app.scrapers.yepbooking import YepBookingScraper
from app.scrapers.yepbooking_grid import format_yepbooking_grid

_FIXTURE = Path(__file__).resolve().parent / "fixtures" / "yepbooking_minimal.html"


@pytest.fixture
def minimal_html() -> str:
    return _FIXTURE.read_text(encoding="utf-8")


def test_parse_schema_extracts_courts_slots_and_prices(minimal_html: str) -> None:
    scraper = YepBookingScraper(BOTANY_CONFIG)
    courts, prices = scraper._parse_schema(minimal_html)

    print("\nParsed schema (grid):\n" + format_yepbooking_grid(courts, prices))

    assert prices == {"08:00": "$25", "09:00": "$25"}
    assert len(courts) == 2

    c1, c2 = courts
    assert c1.court_name == "Court 1"
    assert c2.court_name == "Court 2"

    assert [(s.start_time, s.end_time, s.status) for s in c1.slots] == [
        ("08:00", "09:00", SlotStatus.AVAILABLE),
        ("09:00", "10:00", SlotStatus.BOOKED),
    ]
    assert [(s.start_time, s.end_time, s.status) for s in c2.slots] == [
        ("08:00", "09:00", SlotStatus.BOOKED),
        ("09:00", "10:00", SlotStatus.AVAILABLE),
    ]


def test_parse_schema_empty_when_tables_missing() -> None:
    scraper = YepBookingScraper(BOTANY_CONFIG)
    courts, prices = scraper._parse_schema("<html><body></body></html>")
    assert courts == []
    assert prices == {}


def test_schema_params_omits_id_location_when_not_configured() -> None:
    scraper = YepBookingScraper(BOTANY_CONFIG)
    params = scraper._schema_params(date(2026, 4, 12))
    assert "id_location" not in params
    assert params["id_sport"] == "1"
    assert params["day"] == "12"
    assert params["month"] == "4"
    assert params["year"] == "2026"


def test_schema_params_includes_id_location_when_configured() -> None:
    cfg = replace(BOTANY_CONFIG, location_id=15)
    scraper = YepBookingScraper(cfg)
    params = scraper._schema_params(date(2025, 1, 2))
    assert params["id_location"] == "15"
    assert params["id_sport"] == "1"
