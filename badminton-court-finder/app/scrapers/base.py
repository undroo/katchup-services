from abc import ABC, abstractmethod
from datetime import date

import httpx

from app.schemas.courts import AvailabilityResponse


class BaseScraper(ABC):
    """Interface that every site scraper must implement."""

    @abstractmethod
    async def scrape_availability(
        self, client: httpx.AsyncClient, target_date: date
    ) -> AvailabilityResponse:
        """Fetch and parse court availability for *target_date*."""
        ...
