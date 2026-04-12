from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel


class SlotStatus(str, Enum):
    AVAILABLE = "available"
    BOOKED = "booked"
    PAST = "past"


class CourtSlot(BaseModel):
    start_time: str
    end_time: str
    status: SlotStatus
    price: Optional[str] = None


class CourtAvailability(BaseModel):
    court_name: str
    slots: List[CourtSlot]


class AvailabilityResponse(BaseModel):
    site: str
    venue_name: str
    date: date
    courts: List[CourtAvailability]
    scraped_at: datetime


class SiteInfo(BaseModel):
    key: str
    venue_name: str
    timezone: str


class SitesListResponse(BaseModel):
    sites: List[SiteInfo]
