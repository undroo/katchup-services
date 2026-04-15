-- RLS for public.featured_places.
-- Requires 001_featured_places.sql to have been applied.
--
-- Anon policies mirror court_availability_slots: scripts and PostgREST use SUPABASE_ANON_KEY.
-- Upserts need SELECT + INSERT + UPDATE. Tighten USING / WITH CHECK for your threat model.
--
-- Idempotent: safe to re-run after changing policies.

ALTER TABLE public.featured_places ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS featured_places_anon_select ON public.featured_places;
DROP POLICY IF EXISTS featured_places_anon_insert ON public.featured_places;
DROP POLICY IF EXISTS featured_places_anon_update ON public.featured_places;

CREATE POLICY featured_places_anon_select ON public.featured_places FOR SELECT TO anon USING (true);

CREATE POLICY featured_places_anon_insert ON public.featured_places FOR INSERT TO anon WITH CHECK (true);

CREATE POLICY featured_places_anon_update ON public.featured_places FOR UPDATE TO anon USING (true)
WITH CHECK (true);
