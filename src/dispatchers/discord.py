"""Discord Webhook Dispatcher with Rich Embed support and Rate Limit Handling."""

import logging
import time
from typing import List, Optional
import requests

from src.config import config
from src.dispatchers.base import BaseDispatcher
from src.models import Deal, DispatchResult

logger = logging.getLogger(__name__)


class DiscordDispatcher(BaseDispatcher):
    """Dispatches freebie game alerts to a Discord channel via Incoming Webhooks."""

    EMBED_COLOR_FREEBIE = 0x2ECC71  # Vibrant green (#2ecc71)

    def __init__(
        self,
        webhook_url: Optional[str] = None,
        role_id: Optional[str] = None,
        timeout: Optional[int] = None,
    ):
        self.webhook_url = webhook_url if webhook_url is not None else config.discord_webhook_url
        self.role_id = role_id if role_id is not None else config.discord_role_id
        self.timeout = timeout if timeout is not None else config.http_timeout

    @property
    def name(self) -> str:
        return "Discord"

    def is_enabled(self) -> bool:
        return bool(self.webhook_url and self.webhook_url.strip())

    def send_deals(self, deals: List[Deal]) -> DispatchResult:
        if not self.is_enabled():
            logger.info("Discord dispatcher is disabled (no DISCORD_WEBHOOK_URL set).")
            return DispatchResult(channel=self.name, success=True, items_sent=0)

        if not deals:
            return DispatchResult(channel=self.name, success=True, items_sent=0)

        sent_count = 0
        last_error = None

        for deal in deals:
            success = self._send_single_deal(deal)
            if success:
                sent_count += 1
            else:
                last_error = f"Failed to deliver deal {deal.id} to Discord"

        all_success = sent_count == len(deals)
        return DispatchResult(
            channel=self.name,
            success=all_success,
            items_sent=sent_count,
            error_message=last_error if not all_success else None,
        )

    def _build_payload(self, deal: Deal) -> dict:
        """Builds Discord Webhook JSON payload with Rich Embed."""
        fields = [
            {"name": "💰 Normal Price", "value": deal.worth, "inline": True},
            {"name": "🕹 Platform", "value": deal.platforms, "inline": True},
            {"name": "🏷 Type", "value": deal.deal_type, "inline": True},
        ]

        if deal.end_date:
            fields.append({"name": "⏳ Expiration", "value": deal.end_date, "inline": True})

        if deal.description:
            # Shorten description if too long
            desc = deal.description[:250] + "..." if len(deal.description) > 250 else deal.description
            fields.append({"name": "📝 Details", "value": desc, "inline": False})

        embed = {
            "title": f"🎁 100% FREE: {deal.title}",
            "url": deal.url,
            "description": f"**[Click here to claim {deal.title}]({deal.url})**\nGrab this limited-time freebie before the offer ends!",
            "color": self.EMBED_COLOR_FREEBIE,
            "fields": fields,
            "footer": {
                "text": f"LootPing • Source: {deal.source}",
            },
        }

        if deal.image_url:
            embed["image"] = {"url": deal.image_url}

        payload: dict = {
            "username": "LootPing",
            "avatar_url": "https://raw.githubusercontent.com/feathericons/feather/master/icons/gift.svg",
            "embeds": [embed],
        }

        if self.role_id:
            role_str = self.role_id.strip()
            if role_str == "@everyone" or role_str == "@here":
                payload["content"] = f"{role_str} 🎮 **New Freebie Alert!**"
            else:
                payload["content"] = f"<@&{role_str}> 🎮 **New Freebie Alert!**"

        return payload

    def _send_single_deal(self, deal: Deal, max_retries: int = 2) -> bool:
        """Sends a single deal to Discord with rate-limit retry logic."""
        payload = self._build_payload(deal)

        for attempt in range(max_retries + 1):
            try:
                response = requests.post(
                    self.webhook_url,
                    json=payload,
                    timeout=self.timeout,
                    headers={"Content-Type": "application/json"},
                )

                if response.status_code in (200, 204):
                    logger.info("Discord: Dispatched alert for '%s'", deal.title)
                    return True

                if response.status_code == 429:
                    retry_after = 1.0
                    try:
                        retry_after = float(response.json().get("retry_after", 1.0))
                    except Exception:
                        retry_after = float(response.headers.get("Retry-After", 1.0))

                    logger.warning("Discord 429 Rate Limit hit. Backing off for %.2fs...", retry_after)
                    time.sleep(retry_after)
                    continue

                logger.error(
                    "Discord webhook error (HTTP %d): %s",
                    response.status_code,
                    response.text[:200],
                )
                return False

            except requests.RequestException as e:
                logger.error("Discord network error on attempt %d: %s", attempt + 1, e)
                if attempt < max_retries:
                    time.sleep(1.0)
                else:
                    return False
            except Exception as e:
                logger.error("Unexpected error dispatching to Discord: %s", e)
                return False

        return False
