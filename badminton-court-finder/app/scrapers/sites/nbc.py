"""NBC Badminton (https://nbc.yepbooking.com.au/) — multiple branches.

YepBooking tab metadata comes from ``GET /ajax/ajax.showTabs.php`` (after a normal
homepage visit). Each branch is exposed as a separate ``id_sport`` value on
``ajax/ajax.schema.php``, not ``id_location``. Values below were captured
2026-04-12.
"""

from __future__ import annotations

from app.scrapers.yepbooking import YepBookingSiteConfig

_NBC_BASE = "https://nbc.yepbooking.com.au"
_TZ = "Australia/Sydney"

NBC_SILVERWATER = YepBookingSiteConfig(
    site_key="nbc_silverwater",
    venue_name="NBC Silverwater",
    base_url=_NBC_BASE,
    sport_id=1,
    timezone=_TZ,
)

NBC_SEVEN_HILLS = YepBookingSiteConfig(
    site_key="nbc_seven_hills",
    venue_name="NBC Seven Hills",
    base_url=_NBC_BASE,
    sport_id=2,
    timezone=_TZ,
)

NBC_GRANVILLE = YepBookingSiteConfig(
    site_key="nbc_granville",
    venue_name="NBC Granville",
    base_url=_NBC_BASE,
    sport_id=4,
    timezone=_TZ,
)

NBC_CASTLE_HILL = YepBookingSiteConfig(
    site_key="nbc_castle_hill",
    venue_name="NBC Castle Hill",
    base_url=_NBC_BASE,
    sport_id=5,
    timezone=_TZ,
)

NBC_ALEXANDRIA = YepBookingSiteConfig(
    site_key="nbc_alexandria",
    venue_name="NBC Alexandria",
    base_url=_NBC_BASE,
    sport_id=6,
    timezone=_TZ,
)

NBC_MQ_PARK = YepBookingSiteConfig(
    site_key="nbc_mq_park",
    venue_name="NBC MQ Park",
    base_url=_NBC_BASE,
    sport_id=7,
    timezone=_TZ,
)

NBC_OLYMPIC_PARK = YepBookingSiteConfig(
    site_key="nbc_olympic_park",
    venue_name="NBC Olympic Park",
    base_url=_NBC_BASE,
    sport_id=8,
    timezone=_TZ,
)

NBC_OLYMPIC_PARK_PICKLEBALL = YepBookingSiteConfig(
    site_key="nbc_olympic_park_pickleball",
    venue_name="NBC Olympic Park (Pickleball)",
    base_url=_NBC_BASE,
    sport_id=9,
    timezone=_TZ,
)

NBC_SITE_CONFIGS: tuple[YepBookingSiteConfig, ...] = (
    NBC_SILVERWATER,
    NBC_SEVEN_HILLS,
    NBC_GRANVILLE,
    NBC_CASTLE_HILL,
    NBC_ALEXANDRIA,
    NBC_MQ_PARK,
    NBC_OLYMPIC_PARK,
    NBC_OLYMPIC_PARK_PICKLEBALL,
)

__all__ = [
    "NBC_ALEXANDRIA",
    "NBC_CASTLE_HILL",
    "NBC_GRANVILLE",
    "NBC_MQ_PARK",
    "NBC_OLYMPIC_PARK",
    "NBC_OLYMPIC_PARK_PICKLEBALL",
    "NBC_SEVEN_HILLS",
    "NBC_SILVERWATER",
    "NBC_SITE_CONFIGS",
]
