"""CheapShark API Ingestion Client for 100% off discounts and giveaways."""

import logging
from typing import List, Optional, Dict
import requests

from src.config import config
from src.ingestion.base import BaseIngester
from src.models import Deal

logger = logging.getLogger(__name__)


class CheapSharkIngester(BaseIngester):
    """Client for querying 100% free deals from CheapShark API v1.4."""

    DEALS_URL = "https://www.cheapshark.com/api/1.0/deals"
    STORES_URL = "https://www.cheapshark.com/api/1.0/stores"
    REDIRECT_URL_TEMPLATE = "https://www.cheapshark.com/redirect?dealID={deal_id}"

    def __init__(self, timeout: Optional[int] = None):
        self.timeout = timeout or config.http_timeout
        self._stores_cache: Dict[str, str] = {}

    def _get_store_name(self, store_id: str) -> str:
        """Resolves CheapShark store ID to store name (e.g. Steam, Epic Games, GOG)."""
        if not self._stores_cache:
            try:
                resp = requests.get(self.STORES_URL, timeout=self.timeout)
                if resp.status_code == 200:
                    for store in resp.json():
                        s_id = str(store.get("storeID"))
                        s_name = store.get("storeName")
                        if s_id and s_name:
                            self._stores_cache[s_id] = s_name
            except Exception as e:
                logger.warning("Failed to fetch CheapShark store list: %s", e)

        return self._stores_cache.get(str(store_id), "PC Store")

    def fetch_deals(self) -> List[Deal]:
        """Fetches active 100% free deals (salePrice == 0.00)."""
        if not config.enable_cheapshark:
            logger.info("CheapShark ingestion is disabled in config.")
            return []

        logger.info("Fetching CheapShark 100% off deals...")
        try:
            params = {
                "upperPrice": 0,
                "sortBy": "Savings",
            }
            response = requests.get(
                self.DEALS_URL,
                params=params,
                timeout=self.timeout,
                headers={"User-Agent": "LootPing/1.0"},
            )

            if response.status_code != 200:
                logger.warning("CheapShark API returned HTTP %d: %s", response.status_code, response.text[:200])
                return []

            data = response.json()
            if not isinstance(data, list):
                return []

            deals: List[Deal] = []
            for item in data:
                deal = self._parse_item(item)
                if deal:
                    deals.append(deal)

            logger.info("Successfully fetched %d deals from CheapShark.", len(deals))
            return deals

        except requests.RequestException as e:
            logger.error("Network error while querying CheapShark API: %s", e)
            return []
        except Exception as e:
            logger.error("Unexpected error during CheapShark ingestion: %s", e)
            return []

    def _parse_item(self, item: dict) -> Optional[Deal]:
        """Parses a CheapShark deal item into a Deal model."""
        try:
            deal_id = item.get("dealID")
            game_id = item.get("gameID")
            unique_id = f"cs_{deal_id}" if deal_id else (f"cs_{game_id}" if game_id else None)
            if not unique_id:
                return None

            title = item.get("title") or item.get("external") or "Free Game"
            normal_price = item.get("normalPrice", "0.00")
            worth = f"${normal_price}" if normal_price != "0.00" else "Free"
            store_id = str(item.get("storeID", "1"))
            store_name = self._get_store_name(store_id)

            url = self.REDIRECT_URL_TEMPLATE.format(deal_id=deal_id) if deal_id else ""
            thumb = item.get("thumb")

            return Deal(
                id=unique_id,
                title=title,
                worth=worth,
                platforms=f"PC ({store_name})",
                url=url,
                image_url=thumb,
                end_date=None,
                source="CheapShark",
                deal_type="Game",
                description=f"100% discount on {store_name}",
            )
        except Exception as e:
            logger.warning("Failed to parse CheapShark item %s: %s", item, e)
            return None
