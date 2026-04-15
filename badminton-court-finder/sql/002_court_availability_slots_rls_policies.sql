-- Idempotent RLS policies for existing projects that ran 001 before policies were added.
-- Run in Supabase SQL Editor when PostgREST returns 401 with "row-level security policy" on writes.
-- Requires table public.court_availability_slots to exist.

DROP POLICY IF EXISTS court_availability_slots_anon_select ON public.court_availability_slots;
DROP POLICY IF EXISTS court_availability_slots_anon_insert ON public.court_availability_slots;
DROP POLICY IF EXISTS court_availability_slots_anon_delete ON public.court_availability_slots;

CREATE POLICY court_availability_slots_anon_select ON public.court_availability_slots
  FOR SELECT TO anon USING (true);

CREATE POLICY court_availability_slots_anon_insert ON public.court_availability_slots
  FOR INSERT TO anon WITH CHECK (true);

CREATE POLICY court_availability_slots_anon_delete ON public.court_availability_slots
  FOR DELETE TO anon USING (true);
