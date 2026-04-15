# Badminton Court Finder — operations

## Supported sites

Venue keys and display names are also returned by `GET /v1/courts/sites` (recommended for clients).

| Key               | Venue                                           | Platform   |
|-------------------|-------------------------------------------------|------------|
| `abdc_alexandria` | Australia Badminton Development Centre (Alexandria) | YepBooking |
| `botany`          | BadmintonWorx Botany                            | YepBooking |

Additional NBC branches (Silverwater, Seven Hills, Granville, Castle Hill, Alexandria, MQ Park, Olympic Park, Olympic Park Pickleball) use keys `nbc_*` — see [`app/scrapers/sites/nbc.py`](../../badminton-court-finder/app/scrapers/sites/nbc.py).

## Quick start

Requires **Python 3.12+** (see `requires-python` in [`pyproject.toml`](../../badminton-court-finder/pyproject.toml)).

```bash
cd badminton-court-finder
pip install -e .
uvicorn app.main:app --reload --port 8000
```

## Environment variables

| Variable              | Default | Description                                  |
|-----------------------|---------|----------------------------------------------|
| `REQUEST_TIMEOUT`     | `15.0`  | HTTP request timeout in seconds              |
| `RATE_LIMIT_DELAY`    | `1.0`   | Minimum seconds between requests to one host |
| `MAX_CONNECTIONS`     | `10`    | Connection pool size per host                |
| `CORS_ALLOW_ORIGINS`  | _(empty)_ | Comma-separated browser origins allowed for `GET` and `POST` (e.g. `http://localhost:5173` for Activity Hub). Empty omits CORS middleware. |
| `SUPABASE_URL`        | _(empty)_ | Supabase project URL (e.g. `https://xxx.supabase.co`). With `SUPABASE_ANON_KEY`, enables DB cache for availability. |
| `SUPABASE_ANON_KEY`   | _(empty)_ | Supabase anon (public) key for PostgREST. Must be set together with `SUPABASE_URL`, or both omitted. Configure RLS policies so `anon` can `SELECT`, `INSERT`, and `DELETE` on `court_availability_slots` as required by this service (see SQL comments in `badminton-court-finder/sql/`). |
| `COURT_DATA_MAX_AGE_SECONDS` | `3600` | If cached rows for `(site, date)` are older than this, a refresh is eligible (live scrape when allowed). |
| `COURT_MIN_SCRAPE_INTERVAL_SECONDS` | `3600` | Minimum time between live scrapes for the same `(site, date)` on normal reads; blocks hammering upstream. Ignored for force refresh. |
| `AVAILABILITY_BATCH_MAX_DATES` | `31` | Maximum number of **distinct** calendar dates allowed per `POST /v1/courts/availability/batch` body. |
| `REFRESH_API_KEY`     | _(empty)_ | If set, `POST /v1/courts/availability/refresh` requires header `X-Refresh-Api-Key` with this value. |

**`site_key` in the database** matches the API `site` query parameter: a stable registry slug (e.g. `botany`), not the venue booking URL. The URL is only on the scraper config (`base_url`).

## Endpoints (summary)

- `GET /health` — liveness check
- `GET /v1/courts/sites` — list configured site keys, venue names, and timezones
- `GET /v1/courts/availability?site=botany&date=2026-04-14` — court availability (served from Supabase when fresh enough and configured; otherwise live scrape, then persist)
- `POST /v1/courts/availability/batch` — JSON body `{"site":"botany","dates":["2026-04-14","2026-04-15"]}`; same read-through cache semantics as GET, one Supabase read for all dates when configured, sequential live scrapes for dates that need refresh, batched Supabase writes after scrapes
- `POST /v1/courts/availability/refresh` — JSON body `{"site":"botany","date":"2026-04-14"}`; always live scrapes and updates Supabase when configured (optional `X-Refresh-Api-Key` if `REFRESH_API_KEY` is set)

For browser clients, OpenAPI docs, and error shapes, see [Frontend integration](frontend.md).

## Adding a new site

1. Create a config module under `app/scrapers/sites/` (see `botany.py` for the pattern).
2. Register the site key in the `SITE_REGISTRY` inside `app/scrapers/sites/__init__.py`.
