from __future__ import annotations

from typing import TYPE_CHECKING

from .botany import BOTANY_CONFIG

if TYPE_CHECKING:
    from app.scrapers.yepbooking import YepBookingSiteConfig

SITE_REGISTRY: dict[str, YepBookingSiteConfig] = {
    "botany": BOTANY_CONFIG,
}

__all__ = ["SITE_REGISTRY", "BOTANY_CONFIG"]
