-- court_availability_slots.tags — run manually in Supabase SQL Editor (or CLI) after 001/002.
-- Aligns with badminton-court-finder app/db/venue_tags.py (BADMINTON_COURT_FINDER_VENUE_TAGS).

ALTER TABLE public.court_availability_slots
ADD COLUMN IF NOT EXISTS tags text[] NOT NULL DEFAULT ARRAY[
  'sport:badminton',
  'environment:indoors',
  'access:private',
  'place_type:court'
]::text[];

COMMENT ON COLUMN public.court_availability_slots.tags IS
  'Venue semantics for UI/filtering; keep in sync with app/db/venue_tags.py. '
  'Vocabulary: sport:badminton, environment:indoors, access:private, place_type:court.';
