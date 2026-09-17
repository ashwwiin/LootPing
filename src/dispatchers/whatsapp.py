"""WhatsApp Dispatcher using the CallMeBot Gateway."""

import logging
import urllib.parse
from typing import List, Optional
import requests

from src.config import config
from src.dispatchers.base import BaseDispatcher
from src.models import Deal, DispatchResult

logger = logging.getLogger(__name__)


class WhatsAppDispatcher(BaseDispatcher):
    """Dispatches personal game giveaway notifications to WhatsApp via CallMeBot gateway."""

    GATEWAY_URL = "https://api.callmebot.com/whatsapp.php"

    def __init__(
        self,
        phone: Optional[str] = None,
        apikey: Optional[str] = None,
        timeout: Optional[int] = None,
    ):
        self.phone = phone if phone is not None else config.whatsapp_phone
        self.apikey = apikey if apikey is not None else config.whatsapp_apikey
        self.timeout = timeout if timeout is not None else config.http_timeout

    @property
    def name(self) -> str:
        return "WhatsApp"

    def is_enabled(self) -> bool:
        return bool(
            self.phone
            and self.phone.strip()
            and self.apikey
            and self.apikey.strip()
        )

    def send_deals(self, deals: List[Deal]) -> DispatchResult:
        if not self.is_enabled():
            logger.info("WhatsApp dispatcher is disabled (missing WHATSAPP_PHONE or WHATSAPP_APIKEY).")
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
                last_error = f"Failed to deliver deal {deal.id} to WhatsApp"

        all_success = sent_count == len(deals)
        return DispatchResult(
            channel=self.name,
            success=all_success,
            items_sent=sent_count,
            error_message=last_error if not all_success else None,
        )

    def _format_whatsapp_message(self, deal: Deal) -> str:
        """Formats the deal into WhatsApp markdown format."""
        lines = [
            f"🎁 *FREE GAME ALERT: {deal.title}*",
            "",
            f"💰 *Worth:* ~{deal.worth}~ (100% OFF - FREE)",
            f"🕹 *Platform:* {deal.platforms}",
            f"🏷 *Type:* {deal.deal_type}",
        ]

        if deal.end_date:
            lines.append(f"⏳ *Ends:* {deal.end_date}")

        lines.append("")
        lines.append(f"🔗 *Claim Deal:* {deal.url}")
        lines.append("")
        lines.append(f"_LootPing • {deal.source}_")

        return "\n".join(lines)

    def _send_single_deal(self, deal: Deal) -> bool:
        """Sends a single message via CallMeBot GET API."""
        msg_text = self._format_whatsapp_message(deal)

        params = {
            "phone": self.phone.strip().replace("+", ""),
            "text": msg_text,
            "apikey": self.apikey.strip(),
        }

        try:
            # CallMeBot accepts GET request with urlencoded params
            response = requests.get(
                self.GATEWAY_URL,
                params=params,
                timeout=self.timeout,
            )

            # CallMeBot returns HTTP 200 with HTML message indicating status
            if response.status_code == 200:
                logger.info("WhatsApp: Dispatched alert for '%s'", deal.title)
                return True

            logger.warning(
                "WhatsApp (CallMeBot) returned HTTP %d: %s",
                response.status_code,
                response.text[:200],
            )
            return False

        except requests.RequestException as e:
            logger.error("WhatsApp network/timeout error for '%s': %s", deal.title, e)
            return False
        except Exception as e:
            logger.error("Unexpected WhatsApp error for '%s': %s", deal.title, e)
            return False
