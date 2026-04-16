"""
Fill Google Places fields on featured_places (after sync_badminton_venues).

Populates address, coordinates, rating, price_level, google_place_id, and preview_image_url
(when the Places Photo API yields a redirect to a public CDN URL).

Requires:
  - SUPABASE_URL, SUPABASE_ANON_KEY (read featured_places; PATCH allowed for anon per RLS).
  - SUPABASE_SERVICE_ROLE_KEY recommended for writes (same as sync script).
  - GOOGLE_MAPS_API_KEY — enable **Places API (New)** and billing on the GCP project.

Environment loads from katchup-services/env/.env when present (see featured_places.settings).
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
from datetime import datetime, timezone
from typing import Any

import httpx

from featured_places.google_places import (
    PlaceEnrichment,
    search_text_first_place,
    text_query_for_venue,
)
from featured_places.repo import (
    fetch_featured_places_for_google_enrichment,
    patch_featured_place_fields,
)
from featured_places.settings import Settings

logger = logging.getLogger(__name__)


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _enrichment_to_patch_body(pe: PlaceEnrichment) -> dict[str, Any]:
    return {
        "google_place_id": pe.google_place_id,
        "address": pe.address,
        "latitude": pe.latitude,
        "longitude": pe.longitude,
        "location": pe.location,
        "rating": pe.rating,
        "price_level": pe.price_level,
        "preview_image_url": pe.preview_image_url,
        "updated_at": _iso_now(),
    }


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    p = argparse.ArgumentParser(
        description=(
            "Text-search Google Places (New) for each featured badminton row missing "
            "google_place_id, then PATCH Supabase."
        )
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Log actions without calling PATCH.",
    )
    p.add_argument(
        "--limit",
        type=int,
        default=0,
        metavar="N",
        help="Process at most N rows (0 = no limit).",
    )
    p.add_argument(
        "--court-site-key",
        default="",
        metavar="KEY",
        help="Only this court site_key (optional).",
    )
    p.add_argument(
        "--force",
        action="store_true",
        help="Include rows that already have google_place_id.",
    )
    p.add_argument(
        "--sleep",
        type=float,
        default=0.25,
        metavar="SEC",
        help="Pause between Google API calls (default 0.25).",
    )
    args = p.parse_args(argv)

    try:
        settings = Settings()
    except Exception as e:
        logger.error("Invalid configuration: %s", e)
        return 1

    if not settings.supabase_enabled:
        logger.error("Set SUPABASE_URL and SUPABASE_ANON_KEY.")
        return 1
    if not settings.google_maps_api_key.strip():
        logger.error("Set GOOGLE_MAPS_API_KEY (see katchup-services/env.example).")
        return 1

    court_key = args.court_site_key.strip() or None

    with httpx.Client(timeout=120.0) as client:
        rows = fetch_featured_places_for_google_enrichment(
            client,
            settings,
            court_site_key=court_key,
            missing_google_only=not args.force,
        )
        if args.limit and args.limit > 0:
            rows = rows[: args.limit]

        logger.info("Candidate rows: %s", len(rows))
        if not rows:
            return 0

        processed = 0
        for row in rows:
            row_id = str(row.get("id") or "")
            name = str(row.get("name") or "")
            extra = row.get("extra") if isinstance(row.get("extra"), dict) else {}
            venue_tz = None
            if isinstance(extra, dict):
                raw_tz = extra.get("venue_timezone")
                if isinstance(raw_tz, str):
                    venue_tz = raw_tz

            tq = text_query_for_venue(name)
            try:
                pe = search_text_first_place(
                    client,
                    settings.google_maps_api_key.strip(),
                    tq,
                    venue_timezone=venue_tz,
                )
            except httpx.HTTPError as e:
                logger.error("Google request failed for id=%s: %s", row_id, e)
                continue

            if pe is None:
                logger.warning("No place for id=%s name=%r", row_id, name)
                processed += 1
                if args.sleep > 0:
                    time.sleep(args.sleep)
                continue

            body = _enrichment_to_patch_body(pe)
            if args.dry_run:
                logger.info("DRY-RUN would PATCH id=%s %s", row_id, body)
            else:
                patch_featured_place_fields(client, settings, row_id, body)
                logger.info(
                    "PATCH id=%s google_place_id=%s preview_image_url=%s",
                    row_id,
                    pe.google_place_id,
                    "set" if pe.preview_image_url else "null",
                )

            processed += 1
            if args.sleep > 0:
                time.sleep(args.sleep)

        logger.info("Done. Processed: %s", processed)
        return 0


if __name__ == "__main__":
    sys.exit(main())
