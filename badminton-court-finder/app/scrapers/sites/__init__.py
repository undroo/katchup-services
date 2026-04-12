from __future__ import annotations

from typing import TYPE_CHECKING

from .abdc import ABDC_ALEXANDRIA_CONFIG
from .botany import BOTANY_CONFIG
from .nbc import NBC_SITE_CONFIGS

if TYPE_CHECKING:
    from app.scrapers.yepbooking import YepBookingSiteConfig

SITE_REGISTRY: dict[str, YepBookingSiteConfig] = {
    "abdc_alexandria": ABDC_ALEXANDRIA_CONFIG,
    "botany": BOTANY_CONFIG,
    **{cfg.site_key: cfg for cfg in NBC_SITE_CONFIGS},
}

__all__ = [
    "SITE_REGISTRY",
    "ABDC_ALEXANDRIA_CONFIG",
    "BOTANY_CONFIG",
    "NBC_SITE_CONFIGS",
]
