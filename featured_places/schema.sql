-- WARNING: This schema is for context only and is not meant to be run.
-- Table order and constraints may not be valid for execution.

CREATE TABLE public.activities (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  name character varying NOT NULL,
  location character varying,
  address character varying,
  latitude double precision,
  longitude double precision,
  google_place_id character varying,
  tags ARRAY DEFAULT '{}'::text[],
  rating double precision,
  price_level integer,
  created_at timestamp with time zone DEFAULT now(),
  updated_at timestamp with time zone DEFAULT now(),
  CONSTRAINT activities_pkey PRIMARY KEY (id)
);
CREATE TABLE public.attendees (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  event_id uuid NOT NULL,
  name character varying NOT NULL,
  email character varying NOT NULL,
  mobile character varying,
  status character varying DEFAULT 'invited'::character varying CHECK (status::text = ANY (ARRAY['invited'::character varying, 'confirmed'::character varying, 'declined'::character varying]::text[])),
  invited_by character varying,
  invited_at timestamp with time zone DEFAULT now(),
  responded_at timestamp with time zone,
  created_at timestamp with time zone DEFAULT now(),
  user_id uuid,
  CONSTRAINT attendees_pkey PRIMARY KEY (id),
  CONSTRAINT attendees_event_id_fkey FOREIGN KEY (event_id) REFERENCES public.events(id),
  CONSTRAINT attendees_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id)
);
CREATE TABLE public.availability_exceptions (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL,
  date date NOT NULL,
  start_time character varying NOT NULL,
  end_time character varying NOT NULL,
  name text,
  rule_id uuid,
  created_at timestamp with time zone DEFAULT now(),
  updated_at timestamp with time zone DEFAULT now(),
  slot_type character varying DEFAULT 'free'::character varying CHECK (slot_type::text = ANY (ARRAY['free'::character varying, 'busy'::character varying]::text[])),
  CONSTRAINT availability_exceptions_pkey PRIMARY KEY (id),
  CONSTRAINT availability_exceptions_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id),
  CONSTRAINT availability_exceptions_rule_id_fkey FOREIGN KEY (rule_id) REFERENCES public.availability_patterns(id)
);
CREATE TABLE public.availability_patterns (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL,
  name text NOT NULL,
  start_time character varying NOT NULL,
  end_time character varying NOT NULL,
  recurrence_type character varying NOT NULL CHECK (recurrence_type::text = ANY (ARRAY['once'::character varying, 'daily'::character varying, 'weekly'::character varying, 'custom'::character varying]::text[])),
  days_of_week jsonb DEFAULT '[]'::jsonb,
  start_date date,
  end_date date,
  is_active boolean DEFAULT true,
  slot_type character varying DEFAULT 'free'::character varying CHECK (slot_type::text = ANY (ARRAY['free'::character varying, 'busy'::character varying]::text[])),
  created_at timestamp with time zone DEFAULT now(),
  updated_at timestamp with time zone DEFAULT now(),
  CONSTRAINT availability_patterns_pkey PRIMARY KEY (id),
  CONSTRAINT availability_patterns_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id)
);
CREATE TABLE public.bucket_list_items (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL,
  title character varying NOT NULL,
  description text,
  timeframe character varying,
  location character varying,
  created_at timestamp with time zone DEFAULT now(),
  updated_at timestamp with time zone DEFAULT now(),
  CONSTRAINT bucket_list_items_pkey PRIMARY KEY (id),
  CONSTRAINT bucket_list_items_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id)
);
CREATE TABLE public.chat_messages (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  session_id uuid NOT NULL,
  role character varying NOT NULL CHECK (role::text = ANY (ARRAY['user'::character varying, 'assistant'::character varying, 'system'::character varying]::text[])),
  content text NOT NULL,
  created_at timestamp with time zone DEFAULT now(),
  CONSTRAINT chat_messages_pkey PRIMARY KEY (id),
  CONSTRAINT chat_messages_session_id_fkey FOREIGN KEY (session_id) REFERENCES public.chat_sessions(id)
);
CREATE TABLE public.chat_sessions (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  user_id uuid,
  group_id uuid,
  created_at timestamp with time zone DEFAULT now(),
  updated_at timestamp with time zone DEFAULT now(),
  CONSTRAINT chat_sessions_pkey PRIMARY KEY (id),
  CONSTRAINT chat_sessions_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id),
  CONSTRAINT chat_sessions_group_id_fkey FOREIGN KEY (group_id) REFERENCES public.groups(id)
);
CREATE TABLE public.collection_shares (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  collection_id uuid NOT NULL,
  shared_with_user_id uuid NOT NULL,
  shared_by_user_id uuid NOT NULL,
  permission character varying NOT NULL DEFAULT 'view'::character varying CHECK (permission::text = ANY (ARRAY['view'::character varying, 'edit'::character varying]::text[])),
  created_at timestamp with time zone DEFAULT now(),
  CONSTRAINT collection_shares_pkey PRIMARY KEY (id),
  CONSTRAINT collection_shares_collection_id_fkey FOREIGN KEY (collection_id) REFERENCES public.collections(id),
  CONSTRAINT collection_shares_shared_with_user_id_fkey FOREIGN KEY (shared_with_user_id) REFERENCES public.users(id),
  CONSTRAINT collection_shares_shared_by_user_id_fkey FOREIGN KEY (shared_by_user_id) REFERENCES public.users(id)
);
CREATE TABLE public.collections (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL,
  name text NOT NULL,
  is_default boolean NOT NULL DEFAULT false,
  created_at timestamp with time zone DEFAULT now(),
  CONSTRAINT collections_pkey PRIMARY KEY (id),
  CONSTRAINT collections_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id)
);
CREATE TABLE public.conversation_messages (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  conversation_id uuid NOT NULL,
  sender_id uuid,
  sender_ai_agent character varying,
  content text NOT NULL,
  created_at timestamp with time zone DEFAULT now(),
  edited_at timestamp with time zone,
  guest_sender_id uuid,
  sender_type character varying NOT NULL DEFAULT 'user'::character varying,
  CONSTRAINT conversation_messages_pkey PRIMARY KEY (id),
  CONSTRAINT conversation_messages_conversation_id_fkey FOREIGN KEY (conversation_id) REFERENCES public.conversations(id),
  CONSTRAINT conversation_messages_sender_id_fkey FOREIGN KEY (sender_id) REFERENCES public.users(id),
  CONSTRAINT conversation_messages_guest_sender_id_fkey FOREIGN KEY (guest_sender_id) REFERENCES public.guest_participants(id)
);
CREATE TABLE public.conversation_participants (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  conversation_id uuid NOT NULL,
  user_id uuid,
  ai_agent character varying,
  role character varying DEFAULT 'member'::character varying CHECK (role::text = ANY (ARRAY['admin'::character varying, 'member'::character varying]::text[])),
  last_read_at timestamp with time zone,
  joined_at timestamp with time zone DEFAULT now(),
  guest_participant_id uuid,
  participant_type character varying NOT NULL DEFAULT 'user'::character varying,
  CONSTRAINT conversation_participants_pkey PRIMARY KEY (id),
  CONSTRAINT conversation_participants_conversation_id_fkey FOREIGN KEY (conversation_id) REFERENCES public.conversations(id),
  CONSTRAINT conversation_participants_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id),
  CONSTRAINT conversation_participants_guest_participant_id_fkey FOREIGN KEY (guest_participant_id) REFERENCES public.guest_participants(id)
);
CREATE TABLE public.conversations (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  type character varying NOT NULL CHECK (type::text = ANY (ARRAY['direct'::character varying, 'group'::character varying, 'event'::character varying]::text[])),
  group_id uuid UNIQUE,
  event_id uuid UNIQUE,
  name text,
  created_at timestamp with time zone DEFAULT now(),
  updated_at timestamp with time zone DEFAULT now(),
  CONSTRAINT conversations_pkey PRIMARY KEY (id),
  CONSTRAINT conversations_group_id_fkey FOREIGN KEY (group_id) REFERENCES public.groups(id),
  CONSTRAINT conversations_event_id_fkey FOREIGN KEY (event_id) REFERENCES public.events(id)
);
CREATE TABLE public.court_availability_slots (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  site_key text NOT NULL,
  venue_name text NOT NULL,
  venue_timezone text NOT NULL DEFAULT 'Australia/Sydney'::text,
  session_date date NOT NULL,
  court_name text NOT NULL,
  slot_start time without time zone NOT NULL,
  slot_end time without time zone NOT NULL,
  status text NOT NULL CHECK (status = ANY (ARRAY['available'::text, 'booked'::text, 'past'::text])),
  price text,
  scraped_at timestamp with time zone NOT NULL DEFAULT now(),
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  CONSTRAINT court_availability_slots_pkey PRIMARY KEY (id)
);
CREATE TABLE public.event_proposed_slot_votes (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  proposed_slot_id uuid NOT NULL,
  voter_user_id uuid,
  voter_guest_id uuid,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  CONSTRAINT event_proposed_slot_votes_pkey PRIMARY KEY (id),
  CONSTRAINT event_proposed_slot_votes_proposed_slot_id_fkey FOREIGN KEY (proposed_slot_id) REFERENCES public.event_proposed_slots(id),
  CONSTRAINT event_proposed_slot_votes_voter_user_id_fkey FOREIGN KEY (voter_user_id) REFERENCES public.users(id),
  CONSTRAINT event_proposed_slot_votes_voter_guest_id_fkey FOREIGN KEY (voter_guest_id) REFERENCES public.guest_participants(id)
);
CREATE TABLE public.event_proposed_slots (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  event_id uuid NOT NULL,
  start_at timestamp with time zone NOT NULL,
  end_at timestamp with time zone NOT NULL,
  created_by_user_id uuid,
  created_by_guest_id uuid,
  label text,
  source character varying,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  CONSTRAINT event_proposed_slots_pkey PRIMARY KEY (id),
  CONSTRAINT event_proposed_slots_event_id_fkey FOREIGN KEY (event_id) REFERENCES public.events(id),
  CONSTRAINT event_proposed_slots_created_by_user_id_fkey FOREIGN KEY (created_by_user_id) REFERENCES public.users(id),
  CONSTRAINT event_proposed_slots_created_by_guest_id_fkey FOREIGN KEY (created_by_guest_id) REFERENCES public.guest_participants(id)
);
CREATE TABLE public.event_share_links (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  event_id uuid NOT NULL,
  token character varying NOT NULL UNIQUE,
  created_by uuid NOT NULL,
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  revoked_at timestamp with time zone,
  CONSTRAINT event_share_links_pkey PRIMARY KEY (id),
  CONSTRAINT event_share_links_event_id_fkey FOREIGN KEY (event_id) REFERENCES public.events(id),
  CONSTRAINT event_share_links_created_by_fkey FOREIGN KEY (created_by) REFERENCES public.users(id)
);
CREATE TABLE public.events (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  title character varying NOT NULL,
  date_time timestamp with time zone NOT NULL,
  location character varying,
  notes text,
  created_by uuid,
  group_id uuid,
  created_at timestamp with time zone DEFAULT now(),
  updated_at timestamp with time zone DEFAULT now(),
  google_calendar_event_id character varying,
  last_synced_at timestamp with time zone,
  sync_source character varying DEFAULT 'website'::character varying CHECK (sync_source::text = ANY (ARRAY['website'::character varying, 'google_calendar'::character varying]::text[])),
  end_time timestamp with time zone,
  location_address text,
  location_lat numeric,
  location_lng numeric,
  location_place_id character varying,
  scheduling_poll_closes_at timestamp with time zone,
  scheduling_poll_mode character varying,
  scheduling_status character varying,
  CONSTRAINT events_pkey PRIMARY KEY (id),
  CONSTRAINT events_created_by_fkey FOREIGN KEY (created_by) REFERENCES public.users(id),
  CONSTRAINT events_group_id_fkey FOREIGN KEY (group_id) REFERENCES public.groups(id)
);
CREATE TABLE public.friends (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL,
  friend_id uuid NOT NULL,
  status character varying DEFAULT 'pending'::character varying CHECK (status::text = ANY (ARRAY['pending'::character varying, 'accepted'::character varying, 'blocked'::character varying]::text[])),
  created_at timestamp with time zone DEFAULT now(),
  updated_at timestamp with time zone DEFAULT now(),
  CONSTRAINT friends_pkey PRIMARY KEY (id),
  CONSTRAINT friends_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id),
  CONSTRAINT friends_friend_id_fkey FOREIGN KEY (friend_id) REFERENCES public.users(id)
);
CREATE TABLE public.group_members (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  group_id uuid NOT NULL,
  user_id uuid NOT NULL,
  role character varying DEFAULT 'member'::character varying CHECK (role::text = ANY (ARRAY['admin'::character varying, 'member'::character varying]::text[])),
  joined_at timestamp with time zone DEFAULT now(),
  CONSTRAINT group_members_pkey PRIMARY KEY (id),
  CONSTRAINT group_members_group_id_fkey FOREIGN KEY (group_id) REFERENCES public.groups(id),
  CONSTRAINT group_members_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id)
);
CREATE TABLE public.groups (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  name character varying NOT NULL,
  description text,
  created_by uuid NOT NULL,
  created_at timestamp with time zone DEFAULT now(),
  updated_at timestamp with time zone DEFAULT now(),
  interests ARRAY DEFAULT '{}'::text[],
  preferences ARRAY DEFAULT '{}'::text[],
  CONSTRAINT groups_pkey PRIMARY KEY (id),
  CONSTRAINT groups_created_by_fkey FOREIGN KEY (created_by) REFERENCES public.users(id)
);
CREATE TABLE public.guest_participants (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  event_id uuid NOT NULL,
  share_link_id uuid NOT NULL,
  display_name character varying NOT NULL,
  session_token character varying NOT NULL UNIQUE,
  rsvp_status character varying NOT NULL DEFAULT 'joined'::character varying,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  last_active_at timestamp with time zone NOT NULL DEFAULT now(),
  CONSTRAINT guest_participants_pkey PRIMARY KEY (id),
  CONSTRAINT guest_participants_event_id_fkey FOREIGN KEY (event_id) REFERENCES public.events(id),
  CONSTRAINT guest_participants_share_link_id_fkey FOREIGN KEY (share_link_id) REFERENCES public.event_share_links(id)
);
CREATE TABLE public.notifications (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL,
  type character varying NOT NULL,
  read_at timestamp with time zone,
  created_at timestamp with time zone DEFAULT now(),
  ref_event_id uuid,
  ref_actor_id uuid,
  extra jsonb DEFAULT '{}'::jsonb,
  CONSTRAINT notifications_pkey PRIMARY KEY (id),
  CONSTRAINT notifications_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id),
  CONSTRAINT notifications_ref_event_id_fkey FOREIGN KEY (ref_event_id) REFERENCES public.events(id),
  CONSTRAINT notifications_ref_actor_id_fkey FOREIGN KEY (ref_actor_id) REFERENCES public.users(id)
);
CREATE TABLE public.recommended_events (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  group_id uuid NOT NULL,
  title character varying NOT NULL,
  suggested_date_time timestamp with time zone,
  location character varying,
  description text,
  confidence_score numeric DEFAULT 0.5 CHECK (confidence_score >= 0.0 AND confidence_score <= 1.0),
  source character varying DEFAULT 'ai'::character varying CHECK (source::text = ANY (ARRAY['ai'::character varying, 'template'::character varying, 'similar_group'::character varying]::text[])),
  created_at timestamp with time zone DEFAULT now(),
  status character varying DEFAULT 'pending'::character varying CHECK (status::text = ANY (ARRAY['pending'::character varying, 'accepted'::character varying, 'dismissed'::character varying]::text[])),
  suggested_end_time timestamp with time zone,
  location_address character varying,
  location_lat numeric,
  location_lng numeric,
  location_place_id character varying,
  CONSTRAINT recommended_events_pkey PRIMARY KEY (id),
  CONSTRAINT recommended_events_group_id_fkey FOREIGN KEY (group_id) REFERENCES public.groups(id)
);
CREATE TABLE public.saved_ideas (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL,
  name text NOT NULL,
  url text,
  source character varying NOT NULL,
  created_at timestamp with time zone DEFAULT now(),
  google_place_id character varying,
  categories ARRAY DEFAULT '{}'::text[],
  tags ARRAY DEFAULT '{}'::text[],
  collection_id uuid NOT NULL,
  text text,
  description text,
  preview_image_url text,
  CONSTRAINT saved_ideas_pkey PRIMARY KEY (id),
  CONSTRAINT saved_ideas_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id),
  CONSTRAINT fk_saved_ideas_collection FOREIGN KEY (collection_id) REFERENCES public.collections(id)
);
CREATE TABLE public.users (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  google_id character varying NOT NULL UNIQUE,
  name character varying NOT NULL,
  email character varying NOT NULL UNIQUE,
  picture character varying,
  created_at timestamp with time zone DEFAULT now(),
  updated_at timestamp with time zone DEFAULT now(),
  last_login timestamp with time zone DEFAULT now(),
  google_calendar_token text,
  calendar_connected_at timestamp with time zone,
  last_calendar_sync timestamp with time zone,
  auto_sync_calendar_on_join boolean DEFAULT false,
  preferences jsonb DEFAULT '{"privacy": {"shareAvailability": true, "shareExactLocation": false}, "socialMood": {"scale": {"low_energy": 1, "very_social": 4, "very_antisocial": 0, "selective_social": 2, "moderately_social": 3}, "current": "moderately_social", "lastUpdated": null}, "socialStyle": {"spontaneity": 0.5, "oneOnOneVsGroup": {"group": 0.5, "oneOnOne": 0.5}, "planningHorizon": "medium_term"}, "timePreferences": {"days": {"weekdays": 0.5, "weekends": 0.8}, "timeSlots": {"evening": 0.8, "morning": 0.5, "afternoon": 0.6, "late_night": 0.3}, "hardConstraints": {"latestEnd": "23:00", "earliestStart": "08:00"}}, "groupPreferences": {"comfortBySize": {"1": 0.5, "10+": 0.3, "2-3": 0.8, "4-6": 0.8, "7-10": 0.5}, "preferredSize": {"max": 8, "min": 2, "ideal": 4}}, "activityPreferences": {"tags": {}, "avoid": []}, "locationPreferences": {"keyLocations": {}, "favouriteAreas": [], "maxTravelTimeMinutes": 45}}'::jsonb,
  CONSTRAINT users_pkey PRIMARY KEY (id)
);
CREATE TABLE public.featured_places (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  name text NOT NULL,
  location text,
  address text,
  latitude double precision,
  longitude double precision,
  google_place_id text,
  tags ARRAY DEFAULT '{}'::text[],
  rating double precision,
  price_level integer,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  updated_at timestamp with time zone NOT NULL DEFAULT now(),
  kind text NOT NULL CHECK (kind = ANY (ARRAY['badminton_court'::text])),
  court_site_key text,
  extra jsonb NOT NULL DEFAULT '{}'::jsonb,
  CONSTRAINT featured_places_pkey PRIMARY KEY (id),
  CONSTRAINT featured_places_court_site_key_key UNIQUE (court_site_key)
);