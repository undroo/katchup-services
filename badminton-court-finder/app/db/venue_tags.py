"""Canonical venue tags for rows written by badminton-court-finder to Supabase."""

from __future__ import annotations

# Keep in sync with featured_places BADMINTON_COURT_VENUE_TAGS and sql/003_court_availability_slots_tags.sql.
BADMINTON_COURT_FINDER_VENUE_TAGS: tuple[str, ...] = (
    "sport:badminton",
    "environment:indoors",
    "access:private",
    "place_type:court",
)
