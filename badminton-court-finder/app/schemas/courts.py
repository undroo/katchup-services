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
    # True when data was read from Supabase but exceeded max age and min scrape interval blocked refresh.
    served_stale: Optional[bool] = None


class SiteInfo(BaseModel):
    key: str
    venue_name: str
    timezone: str


class SitesListResponse(BaseModel):
    sites: List[SiteInfo]


class AvailabilityRefreshBody(BaseModel):
    site: str
    date: date


class AvailabilityBatchBody(BaseModel):
    site: str
    dates: List[date]


class AvailabilityDayItem(BaseModel):
    """One calendar day in a batch response."""

    date: date
    ok: bool
    data: Optional[AvailabilityResponse] = None
    error: Optional[str] = None


class AvailabilityBatchResponse(BaseModel):
    site: str
    venue_name: str
    days: List[AvailabilityDayItem]
