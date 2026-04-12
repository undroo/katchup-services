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
| `CORS_ALLOW_ORIGINS`  | _(empty)_ | Comma-separated browser origins allowed for `GET` (e.g. `http://localhost:5173` for Activity Hub). Empty omits CORS middleware. |

## Endpoints (summary)

- `GET /health` — liveness check
- `GET /v1/courts/sites` — list configured site keys, venue names, and timezones
- `GET /v1/courts/availability?site=botany&date=2026-04-14` — court availability for a given site and date (use any key from the table above, e.g. `abdc_alexandria`)

For browser clients, OpenAPI docs, and error shapes, see [Frontend integration](frontend.md).

## Adding a new site

1. Create a config module under `app/scrapers/sites/` (see `botany.py` for the pattern).
2. Register the site key in the `SITE_REGISTRY` inside `app/scrapers/sites/__init__.py`.
