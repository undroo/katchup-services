-- Add preview_image_url for parity with SavedIdeaResponse / app thumbnails.
-- Run in Supabase SQL Editor after 001 (and 002 RLS) if the table already exists.

ALTER TABLE public.featured_places
ADD COLUMN IF NOT EXISTS preview_image_url text;

COMMENT ON COLUMN public.featured_places.preview_image_url IS
  'Thumbnail URL (e.g. Google Places photo CDN after redirect); filled by enrich-featured-places-google.';
