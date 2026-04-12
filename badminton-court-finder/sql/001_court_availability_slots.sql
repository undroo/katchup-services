-- court_availability_slots — run manually in Supabase SQL Editor (or CLI).
-- Aligns with badminton-court-finder app/schemas/courts.py (AvailabilityResponse, CourtSlot, SlotStatus).

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE public.court_availability_slots (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  site_key text NOT NULL,
  venue_name text NOT NULL,
  venue_timezone text NOT NULL DEFAULT 'Australia/Sydney',
  session_date date NOT NULL,
  court_name text NOT NULL,
  slot_start time NOT NULL,
  slot_end time NOT NULL,
  status text NOT NULL CHECK (
    status IN ('available', 'booked', 'past')
  ),
  price text,
  scraped_at timestamptz NOT NULL DEFAULT now(),
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT court_availability_slots_slot_identity_uq UNIQUE (
    site_key,
    session_date,
    court_name,
    slot_start,
    slot_end
  )
);

CREATE INDEX court_availability_slots_site_date_idx ON public.court_availability_slots (
  site_key,
  session_date
);

CREATE INDEX court_availability_slots_session_date_idx ON public.court_availability_slots (
  session_date
);

ALTER TABLE public.court_availability_slots ENABLE ROW LEVEL SECURITY;

-- Backend/service role bypasses RLS. If the mobile client reads with the anon key, allow SELECT e.g.:
-- CREATE POLICY court_availability_slots_public_read ON public.court_availability_slots
--   FOR SELECT TO anon, authenticated USING (true);

COMMENT ON TABLE public.court_availability_slots IS 'One row per court time slot with embedded venue fields; maps to AvailabilityResponse + nested CourtSlot in app/schemas/courts.py.';

COMMENT ON COLUMN public.court_availability_slots.site_key IS 'Stable site key (e.g. botany); maps to AvailabilityResponse.site.';

COMMENT ON COLUMN public.court_availability_slots.venue_name IS 'Display name; maps to AvailabilityResponse.venue_name.';

COMMENT ON COLUMN public.court_availability_slots.venue_timezone IS 'IANA timezone for interpreting slot_start/slot_end as local wall clock.';

COMMENT ON COLUMN public.court_availability_slots.session_date IS 'Calendar date of play; maps to AvailabilityResponse.date.';

COMMENT ON COLUMN public.court_availability_slots.court_name IS 'Court label from the venue; maps to CourtAvailability.court_name.';

COMMENT ON COLUMN public.court_availability_slots.slot_start IS 'Start time local to venue_timezone; maps to CourtSlot.start_time.';

COMMENT ON COLUMN public.court_availability_slots.slot_end IS 'End time local to venue_timezone; maps to CourtSlot.end_time.';

COMMENT ON COLUMN public.court_availability_slots.status IS 'available | booked | past; maps to SlotStatus.';

COMMENT ON COLUMN public.court_availability_slots.price IS 'Optional display price string; maps to CourtSlot.price.';

COMMENT ON COLUMN public.court_availability_slots.scraped_at IS 'When this row was last observed or updated from a scrape.';

COMMENT ON COLUMN public.court_availability_slots.created_at IS 'Row insert time.';

-- Example upsert (latest scrape wins on natural key):
-- INSERT INTO public.court_availability_slots (
--   site_key, venue_name, venue_timezone, session_date, court_name,
--   slot_start, slot_end, status, price, scraped_at
-- ) VALUES (...)
-- ON CONFLICT (site_key, session_date, court_name, slot_start, slot_end)
-- DO UPDATE SET
--   status = EXCLUDED.status,
--   price = EXCLUDED.price,
--   venue_name = EXCLUDED.venue_name,
--   venue_timezone = EXCLUDED.venue_timezone,
--   scraped_at = EXCLUDED.scraped_at;
