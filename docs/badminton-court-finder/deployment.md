# Badminton Court Finder — deployment (Vercel)

1. Create a Vercel project from this repo and set **Root Directory** to **`badminton-court-finder`** (monorepo).
2. Configure the same environment variables as in [Operations — environment variables](operations.md#environment-variables), especially **`CORS_ALLOW_ORIGINS`** for your production web origin(s).
3. Vercel bundles this app as a single Python function. **`REQUEST_TIMEOUT`** (default `15`) should not exceed your plan’s **function max duration**; align Vercel **`maxDuration`** in [`vercel.json`](../../badminton-court-finder/vercel.json) (if present) with your plan limits, or lower `REQUEST_TIMEOUT` so requests fail fast instead of timing out at the platform.
4. Cold starts: the HTTP client is created in the app lifespan; the first request after idle may be slower.

## Local preview (Vercel CLI)

From `badminton-court-finder`; requires [Vercel CLI](https://vercel.com/docs/cli) and `vercel login` / linked project:

```bash
vercel dev
# or, without a global install:
npx vercel@latest dev
```
