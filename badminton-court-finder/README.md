# Badminton Court Finder

Scrapes badminton court booking websites (starting with YepBooking-based venues) and returns current court availability.

## Supported Sites

| Key      | Venue                  | Platform   |
|----------|------------------------|------------|
| `botany` | BadmintonWorx Botany   | YepBooking |

## Quick Start

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

## Endpoints

- `GET /health` — liveness check
- `GET /v1/courts/availability?site=botany&date=2026-04-14` — court availability for a given site and date

## Adding a New Site

1. Create a config module under `app/scrapers/sites/` (see `botany.py` for the pattern).
2. Register the site key in the `SITE_REGISTRY` inside `app/scrapers/sites/__init__.py`.
