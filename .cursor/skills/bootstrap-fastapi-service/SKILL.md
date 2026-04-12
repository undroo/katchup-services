---
name: bootstrap-fastapi-service
description: Scaffolds a new Python FastAPI microservice directory in katchup-services with consistent layout and run instructions. Use when adding a new service, splitting a boundary, or bootstrapping `main.py`, routers, and settings for the Katchup backend.
---

# Bootstrap FastAPI service

## Before coding

1. Pick a **service name** (kebab-case directory, e.g. `user-preferences-api`).
2. Confirm **how it is invoked** (HTTP only, worker + API, etc.) and **who calls it** (mobile app, other services).
3. List **required env vars** and **external dependencies** (DB, LLM, third-party HTTP).

## Scaffold checklist

- [ ] Service root: `pyproject.toml` (or `requirements.txt`) with pinned-ish FastAPI/uvicorn stack.
- [ ] `README.md` in the service folder: purpose, env vars, `uvicorn` command, health URL.
- [ ] `app/main.py` (or `main.py`): FastAPI app, `lifespan` if shared clients exist.
- [ ] `app/routers/`: at least one router + `include_router` with a version prefix (e.g. `/v1`).
- [ ] `app/schemas/`: Pydantic models for public JSON.
- [ ] `app/settings.py`: `pydantic-settings` (or equivalent) for configuration.
- [ ] `Dockerfile` (optional but recommended): non-root user, single CMD.

## Conventions

Follow `.cursor/rules/` for this repo: dependency injection, typed handlers, health routes, no secrets in code.

## Optional follow-ups

- OpenAPI tags and descriptions for mobile/client codegen.
- CI job pattern once the repo defines shared workflows.
