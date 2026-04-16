"""
Sync featured_places from distinct badminton venues in court_availability_slots.

Writes name, court_site_key, kind, venue_timezone (in extra), and timestamps.
Preview thumbnails (`preview_image_url`) are not available from court_availability_slots; run
`enrich-featured-places-google` after sync to fill Google fields including preview_image_url.

Environment (same as badminton-court-finder; loaded from katchup-services/env/.env when present):
  SUPABASE_URL               — project URL (https://xxx.supabase.co)
  SUPABASE_ANON_KEY          — reads court_availability_slots
  SUPABASE_SERVICE_ROLE_KEY  — recommended for writes: upserts featured_places (bypasses RLS).
                               Supabase → Project Settings → API → service_role (secret).
                               Omit only if you applied sql/002_featured_places_rls_policies.sql
                               and accept anon INSERT/UPDATE on that table. Never ship to clients.
"""

from __future__ import annotations

import argparse
import logging
import sys

import httpx

from featured_places.repo import (
    fetch_distinct_court_venues,
    upsert_featured_places,
    venue_rows_to_featured_payloads,
)
from featured_places.settings import Settings

logger = logging.getLogger(__name__)


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    p = argparse.ArgumentParser(
        description=(
            "Upsert featured_places (badminton_court) from distinct "
            "court_availability_slots venues."
        )
    )
    p.parse_args(argv)
    try:
        settings = Settings()
    except Exception as e:
        logger.error("Invalid configuration: %s", e)
        return 1

    if not settings.supabase_enabled:
        logger.error("Set SUPABASE_URL and SUPABASE_ANON_KEY (see badminton-court-finder env layout).")
        return 1

    if not settings.supabase_service_role_key.strip():
        logger.warning(
            "SUPABASE_SERVICE_ROLE_KEY is unset; upserts use the anon key. "
            "Add service_role from Project Settings → API if you hit RLS errors."
        )

    with httpx.Client(timeout=120.0) as client:
        venues = fetch_distinct_court_venues(client, settings)
        logger.info("Distinct court venues: %s", len(venues))
        rows = venue_rows_to_featured_payloads(venues)
        upsert_featured_places(client, settings, rows)
    return 0


if __name__ == "__main__":
    sys.exit(main())
