"""GamerPower Giveaways Ingestion Client."""

import logging
from typing import List, Optional
import requests

from src.config import config
from src.ingestion.base import BaseIngester
from src.models import Deal

logger = logging.getLogger(__name__)


class GamerPowerIngester(BaseIngester):
    """Client for the GamerPower Giveaways API v1."""

    BASE_URL = "https://www.gamerpower.com/api/giveaways"

    def __init__(self, giveaway_type: Optional[str] = None, timeout: Optional[int] = None):
        self.giveaway_type = giveaway_type or config.giveaway_type
        self.timeout = timeout or config.http_timeout

    def fetch_deals(self) -> List[Deal]:
        """
        Fetches active giveaways from GamerPower API.
        Filters by giveaway type if configured.
        """
        params = {}
        if self.giveaway_type and self.giveaway_type.lower() != "all":
            params["type"] = self.giveaway_type.lower()

        logger.info("Fetching GamerPower giveaways (type=%s)...", self.giveaway_type)
        try:
            response = requests.get(
                self.BASE_URL,
                params=params,
                timeout=self.timeout,
                headers={"User-Agent": "LootPing/1.0 (https://github.com/lootping)"},
            )

            # GamerPower returns status 200 with an empty list or error dict if no giveaways match
            if response.status_code != 200:
                logger.warning(
                    "GamerPower API returned HTTP %d: %s",
                    response.status_code,
                    response.text[:200],
                )
                return []

            data = response.json()
            if not isinstance(data, list):
                # Could be {"status": 0, "status_message": "No giveaways found"}
                logger.info("GamerPower response is not a list: %s", data)
                return []

            deals: List[Deal] = []
            for item in data:
                deal = self._parse_item(item)
                if deal:
                    deals.append(deal)

            logger.info("Successfully fetched %d deals from GamerPower.", len(deals))
            return deals

        except requests.RequestException as e:
            logger.error("Network error while querying GamerPower API: %s", e)
            return []
        except Exception as e:
            logger.error("Unexpected error during GamerPower ingestion: %s", e)
            return []

    def _parse_item(self, item: dict) -> Optional[Deal]:
        """Parses a single GamerPower raw JSON object into a Deal model."""
        try:
            item_id = item.get("id")
            if not item_id:
                return None

            title = item.get("title", "Untitled Giveaway")
            worth = item.get("worth", "N/A")
            platforms = item.get("platforms", "Various Platforms")
            # Prefer direct store link (open_giveaway_url), fallback to gamerpower_url
            url = item.get("open_giveaway_url") or item.get("gamerpower_url") or ""
            image_url = item.get("image") or item.get("thumbnail")
            end_date = item.get("end_date")
            deal_type = item.get("type", "Game")
            description = item.get("description") or item.get("instructions")

            return Deal(
                id=f"gp_{item_id}",
                title=title,
                worth=worth,
                platforms=platforms,
                url=url,
                image_url=image_url,
                end_date=end_date if end_date != "N/A" else None,
                source="GamerPower",
                deal_type=deal_type,
                description=description,
            )
        except Exception as e:
            logger.warning("Failed to parse GamerPower item %s: %s", item, e)
            return None
