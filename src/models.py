"""Data models for LootPing."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class Deal:
    """Represents a game deal or giveaway item."""

    id: str
    title: str
    worth: str
    platforms: str
    url: str
    image_url: Optional[str] = None
    end_date: Optional[str] = None
    source: str = "gamerpower"
    deal_type: str = "Game"
    description: Optional[str] = None

    def __post_init__(self) -> None:
        # Standardize strings
        self.id = str(self.id).strip()
        self.title = self.title.strip() if self.title else "Unknown Title"
        self.worth = self.worth.strip() if self.worth else "N/A"
        self.platforms = self.platforms.strip() if self.platforms else "Various Platforms"
        self.url = self.url.strip() if self.url else ""
        if self.image_url:
            self.image_url = self.image_url.strip()
        if self.end_date:
            self.end_date = self.end_date.strip()
        if self.deal_type:
            self.deal_type = self.deal_type.strip().capitalize()

    def matches_platforms(self, allowed: list[str]) -> bool:
        """
        Checks if the deal belongs to any of the allowed platforms/stores.
        Returns True if allowed list is empty (no filtering) or if any keyword matches.
        """
        if not allowed:
            return True
        target_text = f"{self.platforms} {self.title} {self.url} {self.source}".lower()
        return any(keyword.lower() in target_text for keyword in allowed)


@dataclass
class DispatchResult:
    """Result of dispatching deals to a notification channel."""

    channel: str
    success: bool
    items_sent: int
    error_message: Optional[str] = None
