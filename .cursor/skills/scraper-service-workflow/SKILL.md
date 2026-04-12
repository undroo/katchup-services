---
name: scraper-service-workflow
description: Builds or maintains HTTP fetch and HTML parsing flows for Katchup microservices with rate limits, timeouts, and resilient parsing. Use when implementing web scrapers, feed ingestion, or HTML/XML extraction behind FastAPI.
---

# Scraper service workflow

## Planning

1. Identify **allowed targets** (domains, paths) and **robots.txt** obligations.
2. Define **rate limits** (requests per second per host) and **user-agent** policy.
3. Decide **sync vs async**: prefer `httpx.AsyncClient` inside async routes; offload CPU-heavy parsing if needed.

## Implementation checklist

- [ ] Shared HTTP client with timeouts and connection limits (lifespan).
- [ ] Retries with backoff for transient failures; do not retry 4xx except specific cases.
- [ ] Parsing isolated in functions/modules; selectors documented or centralized.
- [ ] Metrics or logs for fetch failures vs parse failures (different causes).
- [ ] No fetching of unvalidated user-supplied URLs without an allowlist (SSRF).

## API surface

Expose results via FastAPI with clear schemas; consider job-style endpoints for long runs (202 + poll, or queue—match what the repo standardizes on later).

## References

Add `reference.md` per target site when selectors and quirks are non-obvious.
