# Badminton Court Finder — frontend integration

Versioned API paths live under **`/v1`**. Use **`GET /v1/courts/sites`** for the canonical list of `site` keys (preferred over hard-coding keys from [Operations — supported sites](operations.md#supported-sites)).

## Interactive and machine-readable docs

With the server running (local or deployed), open:

- **`{BASE_URL}/docs`** — Swagger UI (try requests in the browser)
- **`{BASE_URL}/redoc`** — ReDoc reference
- **`{BASE_URL}/openapi.json`** — OpenAPI 3 schema (codegen: e.g. `openapi-typescript`, Orval)

Replace `{BASE_URL}` with your deployment origin (no trailing slash), e.g. `https://your-service.vercel.app`.

## Routes and query parameters

| Method | Path | Notes |
|--------|------|--------|
| `GET` | `/health` | Liveness; returns `{"status":"ok"}` |
| `GET` | `/v1/courts/sites` | JSON: `{ "sites": [ { "key", "venue_name", "timezone" } ] }` |
| `GET` | `/v1/courts/availability` | Query: **`site`** (string, key from `/sites`), **`date`** (`YYYY-MM-DD`) |

Example:

```http
GET /v1/courts/availability?site=botany&date=2026-04-14
```

Response shape matches Pydantic models in [`app/schemas/courts.py`](../../badminton-court-finder/app/schemas/courts.py) (`AvailabilityResponse`, nested `CourtAvailability`, `CourtSlot`; `SlotStatus`: `available` | `booked` | `past`).

## Errors

JSON errors follow FastAPI’s shape: **`{ "detail": ... }`**.

- Application handlers (unknown `site`, upstream scrape failures) typically use a **string** `detail`.
- Invalid query parameters (e.g. bad `date` format) may produce **`detail` as a list** of validation objects. Clients should handle both string and structured `detail`.

## CORS (browser apps)

CORS is enabled only when **`CORS_ALLOW_ORIGINS`** is non-empty. Set it to a comma-separated list of allowed origins (e.g. `https://your-frontend.vercel.app,http://localhost:5173`). Only **`GET`** is allowed.

## Activity Hub (Vite)

The Activity Hub client uses `VITE_BADMINTON_BASE_URL` (no trailing slash; defaults to `/api/badminton` when unset). It calls:

- `{base}/v1/courts/sites`
- `{base}/v1/courts/availability?site=...&date=...`

See [`activity-hub/src/api/badminton.ts`](../../activity-hub/src/api/badminton.ts).
