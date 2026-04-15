-- featured_places — run manually in Supabase SQL Editor (or CLI) after reviewing.
-- Aligns core columns with public.activities; adds kind, court_site_key (join to
-- court_availability_slots.site_key), and extra jsonb.
--
-- Run 002_featured_places_rls_policies.sql after this file.
--
-- PostgREST access uses the anon key by default (see 002 RLS). Tighten policies if the anon
-- key is exposed to untrusted clients.

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE public.featured_places (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name text NOT NULL,
  location text,
  address text,
  latitude double precision,
  longitude double precision,
  google_place_id text,
  tags text[] NOT NULL DEFAULT '{}'::text[],
  rating double precision,
  price_level integer,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  kind text NOT NULL CHECK (kind = ANY (ARRAY['badminton_court'::text])),
  court_site_key text UNIQUE,
  extra jsonb NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX featured_places_kind_idx ON public.featured_places (kind);

CREATE INDEX featured_places_court_site_key_idx ON public.featured_places (court_site_key)
WHERE
  court_site_key IS NOT NULL;

COMMENT ON TABLE public.featured_places IS 'Curated locations for the app; badminton rows link to court_availability_slots via court_site_key = site_key.';

COMMENT ON COLUMN public.featured_places.kind IS 'Featured category; extend CHECK in this migration when adding new kinds.';

COMMENT ON COLUMN public.featured_places.court_site_key IS 'For kind=badminton_court, matches court_availability_slots.site_key; one featured row per venue.';

COMMENT ON COLUMN public.featured_places.extra IS 'Open-ended metadata (e.g. venue_timezone) without schema churn.';
