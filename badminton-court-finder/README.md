# Badminton Court Finder

Scrapes badminton court booking websites (starting with YepBooking-based venues) and returns current court availability.

## Supported Sites

Venue keys and display names are also returned by `GET /v1/courts/sites` (recommended for clients).

| Key               | Venue                                           | Platform   |
|-------------------|-------------------------------------------------|------------|
| `abdc_alexandria` | Australia Badminton Development Centre (Alexandria) | YepBooking |
| `botany`          | BadmintonWorx Botany                            | YepBooking |

Additional NBC branches (Silverwater, Seven Hills, Granville, Castle Hill, Alexandria, MQ Park, Olympic Park, Olympic Park Pickleball) use keys `nbc_*` — see `app/scrapers/sites/nbc.py`.

## Quick Start

Requires **Python 3.12+** (see `requires-python` in `pyproject.toml`).

```bash
cd badminton-court-finder
pip install -e .
uvicorn app.main:app --reload --port 8000
```

## Environment Variables

| Variable              | Default | Description                                  |
|-----------------------|---------|----------------------------------------------|
| `REQUEST_TIMEOUT`     | `15.0`  | HTTP request timeout in seconds              |
| `RATE_LIMIT_DELAY`    | `1.0`   | Minimum seconds between requests to one host |
| `MAX_CONNECTIONS`     | `10`    | Connection pool size per host                |
| `CORS_ALLOW_ORIGINS`  | _(empty)_ | Comma-separated browser origins allowed for `GET` (e.g. `http://localhost:5173` for Activity Hub). Empty omits CORS middleware. |

## Endpoints

- `GET /health` — liveness check
- `GET /v1/courts/sites` — list configured site keys, venue names, and timezones
- `GET /v1/courts/availability?site=botany&date=2026-04-14` — court availability for a given site and date (use any key from the table above, e.g. `abdc_alexandria`)

## Frontend integration

Versioned API paths live under **`/v1`**. Use **`GET /v1/courts/sites`** for the canonical list of `site` keys (preferred over hard-coding keys from this README).

### Interactive and machine-readable docs

With the server running (local or deployed), open:

- **`{BASE_URL}/docs`** — Swagger UI (try requests in the browser)
- **`{BASE_URL}/redoc`** — ReDoc reference
- **`{BASE_URL}/openapi.json`** — OpenAPI 3 schema (codegen: e.g. `openapi-typescript`, Orval)

Replace `{BASE_URL}` with your deployment origin (no trailing slash), e.g. `https://your-service.vercel.app`.

### Routes and query parameters

| Method | Path | Notes |
|--------|------|--------|
| `GET` | `/health` | Liveness; returns `{"status":"ok"}` |
| `GET` | `/v1/courts/sites` | JSON: `{ "sites": [ { "key", "venue_name", "timezone" } ] }` |
| `GET` | `/v1/courts/availability` | Query: **`site`** (string, key from `/sites`), **`date`** (`YYYY-MM-DD`) |

Example:

```http
GET /v1/courts/availability?site=botany&date=2026-04-14
```

Response shape matches Pydantic models in `app/schemas/courts.py` (`AvailabilityResponse`, nested `CourtAvailability`, `CourtSlot`; `SlotStatus`: `available` | `booked` | `past`).

### Errors

JSON errors follow FastAPI’s shape: **`{ "detail": ... }`**.

- Application handlers (unknown `site`, upstream scrape failures) typically use a **string** `detail`.
- Invalid query parameters (e.g. bad `date` format) may produce **`detail` as a list** of validation objects. Clients should handle both string and structured `detail`.

### CORS (browser apps)

CORS is enabled only when **`CORS_ALLOW_ORIGINS`** is non-empty. Set it to a comma-separated list of allowed origins (e.g. `https://your-frontend.vercel.app,http://localhost:5173`). Only **`GET`** is allowed.

### Activity Hub (Vite)

The Activity Hub client uses `VITE_BADMINTON_BASE_URL` (no trailing slash; defaults to `/api/badminton` when unset). It calls:

- `{base}/v1/courts/sites`
- `{base}/v1/courts/availability?site=...&date=...`

See `activity-hub/src/api/badminton.ts`.

## Deploying to Vercel

1. Create a Vercel project from this repo and set **Root Directory** to **`badminton-court-finder`** (monorepo).
2. Configure the same environment variables as in [Environment Variables](#environment-variables), especially **`CORS_ALLOW_ORIGINS`** for your production web origin(s).
3. Vercel bundles this app as a single Python function. **`REQUEST_TIMEOUT`** (default `15`) should not exceed your plan’s **function max duration**; align Vercel **`maxDuration`** in `vercel.json` (if present) with your plan limits, or lower `REQUEST_TIMEOUT` so requests fail fast instead of timing out at the platform.
4. Cold starts: the HTTP client is created in the app lifespan; the first request after idle may be slower.

Local preview with the Vercel CLI (from `badminton-court-finder`; requires [Vercel CLI](https://vercel.com/docs/cli) and `vercel login` / linked project):

```bash
vercel dev
# or, without a global install:
npx vercel@latest dev
```

## Adding a New Site

1. Create a config module under `app/scrapers/sites/` (see `botany.py` for the pattern).
2. Register the site key in the `SITE_REGISTRY` inside `app/scrapers/sites/__init__.py`.
