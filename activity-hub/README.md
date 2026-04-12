# Activity Hub

Simple web UI for browsing **sport venue time-slot availability** over the next week. It aggregates data from backend microservices (currently [badminton-court-finder](../badminton-court-finder/)) and shows **how many courts** have at least one **available** slot per time row and date — not individual court names.

**Design:** Visual baseline is the [TapTap Design System](https://www.freefigmatemplates.com/gallery/taptap-design-system) (Figma). There is no npm package; spacing, radii, and neutrals are approximated in Tailwind / `src/index.css`.

## Prerequisites

- Node.js 20+
- Badminton court finder running locally (see that service’s README), default `http://127.0.0.1:8000`

## Quick start

```bash
cd activity-hub
npm install
npm run dev
```

Open the printed local URL (usually `http://localhost:5173`). The Vite dev server proxies `/api/badminton` to the court finder, so you do not need CORS for local development.

## Environment

| Variable | Default (dev) | Description |
|----------|----------------|-------------|
| `VITE_BADMINTON_BASE_URL` | `/api/badminton` | Base URL for the court finder API (no trailing slash). In production, set to the real origin (e.g. `https://courts.example.com`) and configure `CORS_ALLOW_ORIGINS` on the court finder. |

Copy `.env.example` to `.env` if you want to override.

## Production

Build static assets with `npm run build`; serve `dist/` from any static host. Point `VITE_BADMINTON_BASE_URL` at the deployed court-finder URL and set `CORS_ALLOW_ORIGINS` on badminton-court-finder to your Activity Hub origin (comma-separated if multiple).

## Notes

- Dates use the **`Australia/Sydney`** calendar (aligned with configured venues).
- Fetching many locations × 7 days hits the scraper repeatedly; expect slow loads.
