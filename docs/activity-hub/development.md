# Activity Hub — development

## Prerequisites

- Node.js 20+
- Badminton Court Finder running locally (see [Operations — quick start](../badminton-court-finder/operations.md#quick-start)), default `http://127.0.0.1:8000`

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
