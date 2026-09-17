"""Abstract Base Class for Notification Dispatchers."""

import logging
from abc import ABC, abstractmethod
from typing import List
from src.models import Deal, DispatchResult

logger = logging.getLogger(__name__)


class BaseDispatcher(ABC):
    """Abstract base class for all notification dispatch channels."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Name of the notification channel."""
        pass

    @abstractmethod
    def is_enabled(self) -> bool:
        """Returns True if the required credentials/settings for this channel are present."""
        pass

    @abstractmethod
    def send_deals(self, deals: List[Deal]) -> DispatchResult:
        """Sends the given list of deals to the channel."""
        pass
