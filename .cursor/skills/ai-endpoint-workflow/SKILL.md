---
name: ai-endpoint-workflow
description: Implements or refactors FastAPI endpoints that call LLMs or embedding APIs for Katchup, with provider abstraction, timeouts, and structured outputs. Use when building AI analysis, summarization, classification, or enrichment features.
---

# AI endpoint workflow

## Design

1. Define the **contract** the mobile app needs: Pydantic response model + stable field names.
2. Place provider SDK / HTTP calls in a dedicated module (e.g. `app/ai/client.py`, `app/ai/prompts.py`).
3. Route handler: validate input → call adapter → map to response model; **no** raw dict passthrough.

## Implementation checklist

- [ ] Input limits (max characters / tokens) enforced server-side.
- [ ] Timeouts and bounded retries on provider calls.
- [ ] Errors mapped to HTTP (503/502) with safe `detail` (no provider stack traces to clients).
- [ ] Logging: request id + model id; **no** prompts or PII in default logs.
- [ ] Tests: mock adapter; assert schema and error paths.

## Structured output

Prefer parsing model output into a Pydantic model; if using JSON-from-model, validate and repair or fail explicitly.

## References

Extend with `reference.md` (model names, pricing notes) when this service stabilizes.
