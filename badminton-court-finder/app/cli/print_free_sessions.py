"""Fetch availability and print court × time grids (YepBooking sites).

Run from the service directory after install:

 pip install -e ".[dev]"
    bcf-free-sessions --site botany

Or:

    python3 -m app.cli.print_free_sessions --site botany --days 7
"""

from __future__ import annotations

import argparse
import asyncio
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import httpx

from app.schemas.courts import CourtAvailability, SlotStatus
from app.scrapers.sites import SITE_REGISTRY
from app.scrapers.yepbooking import YepBookingScraper
from app.scrapers.yepbooking_grid import format_yepbooking_grid
from app.settings import settings


def _today_in_tz(tz_name: str) -> date:
    return datetime.now(ZoneInfo(tz_name)).date()


def _format_day_heading(d: date, tz_name: str) -> str:
    tz = ZoneInfo(tz_name)
    dt = datetime(d.year, d.month, d.day, tzinfo=tz)
    weekday = dt.strftime("%A")
    return f"{d.isoformat()} ({weekday})"


def _count_free_slots(courts: list[CourtAvailability]) -> int:
    return sum(
        1
        for court in courts
        for s in court.slots
        if s.status == SlotStatus.AVAILABLE
    )


def _print_day_grid(
    *,
    tz_name: str,
    target: date,
    courts: list[CourtAvailability],
) -> int:
    """Print availability grid for this day; return count of free slots."""
    heading = _format_day_heading(target, tz_name)
    print(heading)
    if not courts:
        print("(no courts)")
    else:
        print(format_yepbooking_grid(courts, prices=None), end="")
    print()
    return _count_free_slots(courts)


async def _run(site_key: str, num_days: int) -> None:
    config = SITE_REGISTRY.get(site_key)
    if config is None:
        available = ", ".join(sorted(SITE_REGISTRY))
        raise SystemExit(
            f"Unknown site {site_key!r}. Choose one of: {available}"
        )

    today = _today_in_tz(config.timezone)
    scraper = YepBookingScraper(config)

    print(
        f"{config.venue_name} ({site_key}) — "
        f"availability for the next {num_days} day(s), "
        f"timezone {config.timezone}\n"
        f"{'=' * 72}\n"
    )

    total_free = 0
    async with httpx.AsyncClient(
        timeout=httpx.Timeout(settings.request_timeout),
        limits=httpx.Limits(
            max_connections=settings.max_connections,
            max_keepalive_connections=settings.max_connections,
        ),
        follow_redirects=True,
    ) as client:
        for i in range(num_days):
            day = today + timedelta(days=i)
            resp = await scraper.scrape_availability(client, day)
            total_free += _print_day_grid(
                tz_name=config.timezone,
                target=resp.date,
                courts=resp.courts,
            )

    print(f"Total free slots listed: {total_free}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Print badminton court availability grids for upcoming days.",
    )
    parser.add_argument(
        "--site",
        default="botany",
        help="Site key from SITE_REGISTRY (default: botany)",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=7,
        help="Number of consecutive days to check starting today in the venue TZ (default: 7)",
    )
    args = parser.parse_args()
    if args.days < 1:
        raise SystemExit("--days must be at least 1")
    asyncio.run(_run(args.site, args.days))


if __name__ == "__main__":
    main()
