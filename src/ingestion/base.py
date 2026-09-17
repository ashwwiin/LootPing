"""Abstract Base Class for Data Ingestion Clients."""

from abc import ABC, abstractmethod
from typing import List
from src.models import Deal


class BaseIngester(ABC):
    """Base interface for giveaway and deal data sources."""

    @abstractmethod
    def fetch_deals(self) -> List[Deal]:
        """Fetch and normalize deals from the remote source."""
        pass
