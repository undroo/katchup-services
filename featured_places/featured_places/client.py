"""Thin PostgREST client for Supabase (same pattern as badminton-court-finder)."""

from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

_BODY_LOG_MAX = 2000


def _log_postgrest_failure(operation: str, response: httpx.Response) -> None:
    text = response.text
    if len(text) > _BODY_LOG_MAX:
        text = text[:_BODY_LOG_MAX] + "..."
    logger.error(
        "PostgREST %s failed: status=%s body=%s",
        operation,
        response.status_code,
        text,
    )


def check_response(operation: str, response: httpx.Response) -> None:
    if not response.is_success:
        _log_postgrest_failure(operation, response)
    response.raise_for_status()


def rest_table_url(supabase_url: str, table: str) -> str:
    return f"{supabase_url.rstrip('/')}/rest/v1/{table}"


def headers_json(
    api_key: str,
    *,
    prefer_minimal: bool = True,
    prefer_representation: bool = False,
    prefer_merge_duplicates: bool = False,
) -> dict[str, str]:
    parts: list[str] = []
    if prefer_merge_duplicates:
        parts.append("resolution=merge-duplicates")
    if prefer_representation:
        parts.append("return=representation")
    if prefer_minimal and not prefer_representation:
        parts.append("return=minimal")
    prefer = ",".join(parts) if parts else "return=minimal"
    return {
        "apikey": api_key,
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Prefer": prefer,
    }


def get_json(
    client: httpx.Client,
    url: str,
    *,
    params: dict[str, str] | None = None,
    headers: dict[str, str],
    operation: str,
) -> list[dict[str, Any]]:
    resp = client.get(url, params=params, headers=headers)
    check_response(operation, resp)
    data = resp.json()
    if not isinstance(data, list):
        return []
    return data


def post_json(
    client: httpx.Client,
    url: str,
    *,
    json: list[dict[str, Any]] | dict[str, Any],
    headers: dict[str, str],
    operation: str,
) -> httpx.Response:
    resp = client.post(url, json=json, headers=headers)
    check_response(operation, resp)
    return resp


def patch_json(
    client: httpx.Client,
    url: str,
    *,
    json: dict[str, Any],
    headers: dict[str, str],
    operation: str,
) -> httpx.Response:
    resp = client.patch(url, json=json, headers=headers)
    check_response(operation, resp)
    return resp
