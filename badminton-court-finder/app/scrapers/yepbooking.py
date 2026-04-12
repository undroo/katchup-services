"""Reusable scraper for any site running the YepBooking platform.

Each venue supplies a `YepBookingSiteConfig`; the scraping and parsing
logic here is shared.
"""

from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass
from datetime import date, datetime, timezone

import httpx
from bs4 import BeautifulSoup, Tag

from app.schemas.courts import (
    AvailabilityResponse,
    CourtAvailability,
    CourtSlot,
    SlotStatus,
)
from app.scrapers.base import BaseScraper
from app.settings import settings

logger = logging.getLogger(__name__)

# Matches "8:00am–9:00am" or "12:00pm–1:00pm" style ranges in title attrs
_TIME_RANGE_RE = re.compile(
    r"(?P<start>\d{1,2}:\d{2}(?:am|pm))\s*.\s*(?P<end>\d{1,2}:\d{2}(?:am|pm))"
)


@dataclass(frozen=True)
class YepBookingSiteConfig:
    """Per-venue configuration for a YepBooking site."""

    site_key: str
    venue_name: str
    base_url: str  # e.g. "https://badmintoncentre-botany.yepbooking.com.au"
    sport_id: int  # id_sport query param
    timezone: str  # e.g. "Australia/Sydney"
    # Some multi-location installs use id_location on ajax.schema.php; NBC uses
    # distinct id_sport values per branch instead (see sites/nbc.py).
    location_id: int | None = None


def _normalize_time(raw: str) -> str:
    """Convert '8:00am' / '12:00pm' to 24-hour 'HH:MM'."""
    return datetime.strptime(raw.strip(), "%I:%M%p").strftime("%H:%M")


def _parse_time_range(title: str) -> tuple[str, str] | None:
    m = _TIME_RANGE_RE.search(title)
    if not m:
        return None
    return _normalize_time(m.group("start")), _normalize_time(m.group("end"))


def _slot_status_from_title(title: str) -> SlotStatus:
    lower = title.lower()
    if "available" in lower:
        return SlotStatus.AVAILABLE
    if "booked" in lower:
        return SlotStatus.BOOKED
    if "past" in lower or "can't book" in lower:
        return SlotStatus.PAST
    return SlotStatus.BOOKED


class YepBookingScraper(BaseScraper):
    """Scrapes court availability from a YepBooking-powered venue."""

    def __init__(self, config: YepBookingSiteConfig) -> None:
        self.config = config

    # -- public interface -----------------------------------------------------

    async def scrape_availability(
        self, client: httpx.AsyncClient, target_date: date
    ) -> AvailabilityResponse:
        await self._init_session(client)
        await asyncio.sleep(settings.rate_limit_delay)

        html = await self._fetch_schema(client, target_date)
        courts, prices = self._parse_schema(html)

        if prices:
            for court in courts:
                for slot in court.slots:
                    time_key = slot.start_time
                    if time_key in prices:
                        slot.price = prices[time_key]

        # TODO: persist to database

        return AvailabilityResponse(
            site=self.config.site_key,
            venue_name=self.config.venue_name,
            date=target_date,
            courts=courts,
            scraped_at=datetime.now(timezone.utc),
        )

    # -- private helpers ------------------------------------------------------

    def _headers(self) -> dict[str, str]:
        return {
            "X-Requested-With": "XMLHttpRequest",
            "Referer": f"{self.config.base_url}/",
        }

    async def _init_session(self, client: httpx.AsyncClient) -> None:
        """GET the homepage to establish a PHPSESSID cookie."""
        resp = await client.get(f"{self.config.base_url}/")
        resp.raise_for_status()
        logger.debug("Session initialised for %s", self.config.site_key)

    def _schema_params(self, target_date: date) -> dict[str, str]:
        params: dict[str, str] = {
            "day": str(target_date.day),
            "month": str(target_date.month),
            "year": str(target_date.year),
            "id_sport": str(self.config.sport_id),
            "event": "pageLoad",
            "tab_type": "normal",
            "timetableWidth": "800",
            "schema_fixed_date": "",
            "default_view": "day",
        }
        if self.config.location_id is not None:
            params["id_location"] = str(self.config.location_id)
        return params

    async def _fetch_schema(
        self, client: httpx.AsyncClient, target_date: date
    ) -> str:
        resp = await client.get(
            f"{self.config.base_url}/ajax/ajax.schema.php",
            params=self._schema_params(target_date),
            headers=self._headers(),
        )
        resp.raise_for_status()
        return resp.text

    def _parse_schema(
        self, html: str
    ) -> tuple[list[CourtAvailability], dict[str, str]]:
        soup = BeautifulSoup(html, "lxml")

        lane_table = soup.find("table", class_="schemaLaneTable")
        data_table = soup.find("table", class_="schemaIndividual")
        if not lane_table or not data_table:
            logger.warning("Could not locate schema tables in response")
            return [], {}

        court_names = self._extract_court_names(lane_table)
        time_headers = self._extract_time_headers(data_table)
        prices = self._extract_prices(data_table, time_headers)

        data_rows = [
            tr
            for tr in data_table.find_all("tr", recursive=False)
            if isinstance(tr, Tag)
            and tr.get("class")
            and any(
                c.startswith("trSchemaLane_") for c in tr.get("class", [])
            )
        ]
        # Also check inside thead/tbody
        for container in data_table.find_all(["thead", "tbody"]):
            for tr in container.find_all("tr", recursive=False):
                if isinstance(tr, Tag) and tr.get("class") and any(
                    c.startswith("trSchemaLane_") for c in tr.get("class", [])
                ):
                    if tr not in data_rows:
                        data_rows.append(tr)

        courts: list[CourtAvailability] = []
        for idx, row in enumerate(data_rows):
            court_name = court_names[idx] if idx < len(court_names) else f"Court {idx + 1}"
            slots = self._extract_slots_from_row(row)
            courts.append(CourtAvailability(court_name=court_name, slots=slots))

        return courts, prices

    @staticmethod
    def _extract_court_names(lane_table: Tag) -> list[str]:
        names: list[str] = []
        for tr in lane_table.find_all("tr"):
            if not isinstance(tr, Tag):
                continue
            classes = tr.get("class", [])
            if not any(c.startswith("trSchemaLane_") for c in classes):
                continue
            span = tr.find("span")
            if span:
                names.append(span.get_text(strip=True))
        return names

    @staticmethod
    def _extract_time_headers(data_table: Tag) -> list[str]:
        """Return 24-hour time strings from the header row."""
        times_row = data_table.find("tr", class_="times")
        if not times_row:
            return []
        headers: list[str] = []
        for td in times_row.find_all("td"):
            raw = td.get_text(strip=True)
            if not raw:
                continue
            try:
                headers.append(_normalize_time(raw))
            except ValueError:
                continue
        return headers

    @staticmethod
    def _extract_prices(
        data_table: Tag, time_headers: list[str]
    ) -> dict[str, str]:
        """Map start-time -> price string from the prices row."""
        prices_row = data_table.find("tr", class_="prices")
        if not prices_row:
            return {}
        price_map: dict[str, str] = {}
        cells = [
            td
            for td in prices_row.find_all("td")
            if "empty" not in (td.get("class") or [])
        ]
        for idx, td in enumerate(cells):
            text = td.get_text(strip=True)
            if idx < len(time_headers) and text:
                price_map[time_headers[idx]] = text
        return price_map

    @staticmethod
    def _extract_slots_from_row(row: Tag) -> list[CourtSlot]:
        slots: list[CourtSlot] = []
        for td in row.find_all("td", recursive=False):
            if not isinstance(td, Tag):
                continue
            td_classes = td.get("class") or []
            if "lineNumber" in td_classes:
                continue

            title = td.get("title", "")
            # Booked / past cells: status is on the <td> title
            if title:
                time_range = _parse_time_range(title)
                if time_range:
                    slots.append(
                        CourtSlot(
                            start_time=time_range[0],
                            end_time=time_range[1],
                            status=_slot_status_from_title(title),
                        )
                    )
                continue

            # Available cells: the <a> inside carries the title
            link = td.find("a", title=True)
            if link:
                link_title = link.get("title", "")
                time_range = _parse_time_range(link_title)
                if time_range:
                    slots.append(
                        CourtSlot(
                            start_time=time_range[0],
                            end_time=time_range[1],
                            status=_slot_status_from_title(link_title),
                        )
                    )

        return slots
