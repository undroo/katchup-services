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
| `POST` | `/v1/courts/availability/batch` | JSON body: **`site`**, **`dates`** (array of `YYYY-MM-DD`). Dedupes and sorts days server-side. Max distinct dates: `AVAILABILITY_BATCH_MAX_DATES` (default 31). Response: `{ "site", "venue_name", "days": [ { "date", "ok", "data"?, "error"? } ] }` — each day mirrors a single-day `AvailabilityResponse` in `data` when `ok` is true. |

Example (single day):

```http
GET /v1/courts/availability?site=botany&date=2026-04-14
```

Example (batch — preferred for multi-day calendars such as Activity Hub):

```http
POST /v1/courts/availability/batch
Content-Type: application/json

{"site":"botany","dates":["2026-04-14","2026-04-15","2026-04-16"]}
```

Response shape matches Pydantic models in [`app/schemas/courts.py`](../../badminton-court-finder/app/schemas/courts.py) (`AvailabilityResponse`, nested `CourtAvailability`, `CourtSlot`; `SlotStatus`: `available` | `booked` | `past`; batch wrappers `AvailabilityBatchBody` / `AvailabilityBatchResponse` / `AvailabilityDayItem`).

## Errors

JSON errors follow FastAPI’s shape: **`{ "detail": ... }`**.

- Application handlers (unknown `site`, upstream scrape failures) typically use a **string** `detail`.
- Invalid query parameters (e.g. bad `date` format) may produce **`detail` as a list** of validation objects. Clients should handle both string and structured `detail`.

## CORS (browser apps)

CORS is enabled only when **`CORS_ALLOW_ORIGINS`** is non-empty. Set it to a comma-separated list of allowed origins (e.g. `https://your-frontend.vercel.app,http://localhost:5173`). **`GET`** and **`POST`** are allowed (availability batch, force refresh).

## Activity Hub (Vite)

The Activity Hub client uses `VITE_BADMINTON_BASE_URL` (no trailing slash; defaults to `/api/badminton` when unset). It calls:

- `{base}/v1/courts/sites`
- `{base}/v1/courts/availability/batch` with JSON `{ site, dates }` for the rolling calendar

See [`activity-hub/src/api/badminton.ts`](../../activity-hub/src/api/badminton.ts).
