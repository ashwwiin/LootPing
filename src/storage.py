"""State management and deduplication engine."""

import json
import logging
import os
import tempfile
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any

from src.models import Deal

logger = logging.getLogger(__name__)


class StateManager:
    """Manages tracking of alerted deal IDs to ensure zero duplicate alerts."""

    def __init__(self, file_path: Path):
        self.file_path = Path(file_path)
        self.deals: Dict[str, Dict[str, Any]] = {}
        self._load()

    def _load(self) -> None:
        """Loads state from JSON file with backward-compatible format parsing."""
        if not self.file_path.exists():
            logger.info("State file not found at %s; starting with empty state.", self.file_path)
            self.deals = {}
            return

        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            if isinstance(data, dict):
                # Standard format: {"version": 1, "deals": {"gp_123": {"title": "...", "timestamp": "..."}}}
                if "deals" in data and isinstance(data["deals"], dict):
                    self.deals = data["deals"]
                else:
                    # Legacy or flat dict: {"gp_123": "timestamp"}
                    self.deals = {}
                    for k, v in data.items():
                        if isinstance(v, dict):
                            self.deals[str(k)] = v
                        else:
                            self.deals[str(k)] = {
                                "title": "Legacy Item",
                                "timestamp": str(v) if isinstance(v, str) else datetime.now(timezone.utc).isoformat()
                            }
            elif isinstance(data, list):
                # Legacy format: ["gp_123", "gp_456"]
                now_str = datetime.now(timezone.utc).isoformat()
                self.deals = {str(item): {"title": "Legacy Item", "timestamp": now_str} for item in data}
            else:
                logger.warning("Unrecognized state file format. Initializing empty state.")
                self.deals = {}

            logger.info("Loaded %d previously alerted deal IDs from %s.", len(self.deals), self.file_path)
        except Exception as e:
            logger.error("Failed to read state file %s: %s. Using empty state.", self.file_path, e)
            self.deals = {}

    def is_alerted(self, deal_id: str) -> bool:
        """Checks if a deal ID has already been alerted."""
        return str(deal_id) in self.deals

    def filter_new_deals(self, deals: List[Deal]) -> List[Deal]:
        """Filters out deals that have already been alerted."""
        new_deals = [d for d in deals if not self.is_alerted(d.id)]
        logger.info("Filtered %d incoming deals down to %d new un-alerted deals.", len(deals), len(new_deals))
        return new_deals

    def record_deals(self, deals: List[Deal]) -> None:
        """Records dispatched deals with the current UTC timestamp."""
        now_str = datetime.now(timezone.utc).isoformat()
        for deal in deals:
            self.deals[str(deal.id)] = {
                "title": deal.title,
                "worth": deal.worth,
                "platforms": deal.platforms,
                "timestamp": now_str,
            }

    def prune_older_than(self, days: int = 90) -> int:
        """
        Prunes alerted deals older than the specified number of days.
        Prevents unbounded growth of the state file (FR-2.4).
        """
        if days <= 0:
            return 0

        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        pruned_keys = []

        for deal_id, meta in self.deals.items():
            ts_str = meta.get("timestamp")
            if not ts_str:
                continue

            try:
                # Handle ISO 8601 parsing
                deal_dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                if deal_dt < cutoff:
                    pruned_keys.append(deal_id)
            except Exception:
                # If date cannot be parsed, keep it to be safe
                continue

        for k in pruned_keys:
            del self.deals[k]

        if pruned_keys:
            logger.info("Pruned %d state entries older than %d days.", len(pruned_keys), days)
        return len(pruned_keys)

    def save(self) -> None:
        """Atomically saves the state dictionary to file."""
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "version": 1,
            "last_updated": datetime.now(timezone.utc).isoformat(),
            "deals": self.deals,
        }

        # Write to temporary file in the same directory, then atomic rename
        temp_fd, temp_path = tempfile.mkstemp(dir=self.file_path.parent, prefix="alerted_ids_", suffix=".tmp")
        try:
            with open(temp_fd, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2, ensure_ascii=False)
            os.replace(temp_path, self.file_path)
            logger.info("State successfully saved to %s (%d total recorded deals).", self.file_path, len(self.deals))
        except Exception as e:
            logger.error("Failed to save state file %s: %s", self.file_path, e)
            if os.path.exists(temp_path):
                os.remove(temp_path)
            raise
