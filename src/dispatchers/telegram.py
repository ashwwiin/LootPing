"""Telegram Bot API Dispatcher."""

import html
import logging
import time
from typing import List, Optional
import requests

from src.config import config
from src.dispatchers.base import BaseDispatcher
from src.models import Deal, DispatchResult

logger = logging.getLogger(__name__)


class TelegramDispatcher(BaseDispatcher):
    """Dispatches freebie game alerts to Telegram Channels or Groups."""

    SEND_MESSAGE_URL_TEMPLATE = "https://api.telegram.org/bot{token}/sendMessage"
    SEND_PHOTO_URL_TEMPLATE = "https://api.telegram.org/bot{token}/sendPhoto"

    def __init__(
        self,
        bot_token: Optional[str] = None,
        chat_id: Optional[str] = None,
        timeout: Optional[int] = None,
    ):
        self.bot_token = bot_token if bot_token is not None else config.telegram_bot_token
        self.chat_id = chat_id if chat_id is not None else config.telegram_chat_id
        self.timeout = timeout if timeout is not None else config.http_timeout

    @property
    def name(self) -> str:
        return "Telegram"

    def is_enabled(self) -> bool:
        return bool(
            self.bot_token
            and self.bot_token.strip()
            and self.chat_id
            and self.chat_id.strip()
        )

    def send_deals(self, deals: List[Deal]) -> DispatchResult:
        if not self.is_enabled():
            logger.info("Telegram dispatcher is disabled (missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID).")
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
                last_error = f"Failed to deliver deal {deal.id} to Telegram"

        all_success = sent_count == len(deals)
        return DispatchResult(
            channel=self.name,
            success=all_success,
            items_sent=sent_count,
            error_message=last_error if not all_success else None,
        )

    def _format_html_message(self, deal: Deal) -> str:
        """Formats the deal into clean Telegram HTML."""
        safe_title = html.escape(deal.title)
        safe_worth = html.escape(deal.worth)
        safe_platforms = html.escape(deal.platforms)
        safe_type = html.escape(deal.deal_type)
        safe_url = html.escape(deal.url)

        lines = [
            f"🎁 <b>FREE GAME ALERT: {safe_title}</b>",
            "",
            f"💰 <b>Original Price:</b> <s>{safe_worth}</s> (100% OFF - FREE)",
            f"🕹 <b>Platform:</b> {safe_platforms}",
            f"🏷 <b>Type:</b> {safe_type}",
        ]

        if deal.end_date:
            lines.append(f"⏳ <b>Ends:</b> {html.escape(deal.end_date)}")

        lines.append("")
        lines.append(f'🔗 <b>Claim Deal:</b> <a href="{safe_url}">Click here to claim</a>')
        lines.append("")
        lines.append(f"<i>LootPing • {deal.source}</i>")

        return "\n".join(lines)

    def _send_single_deal(self, deal: Deal, max_retries: int = 2) -> bool:
        """Sends a single deal message or photo to Telegram."""
        text = self._format_html_message(deal)

        # If deal has an image, attempt sendPhoto first, fallback to sendMessage
        if deal.image_url:
            photo_url = self.SEND_PHOTO_URL_TEMPLATE.format(token=self.bot_token)
            payload = {
                "chat_id": self.chat_id,
                "photo": deal.image_url,
                "caption": text,
                "parse_mode": "HTML",
            }
            if self._post_request(photo_url, payload, max_retries):
                logger.info("Telegram: Dispatched photo alert for '%s'", deal.title)
                return True

        # Fallback or default: sendMessage
        msg_url = self.SEND_MESSAGE_URL_TEMPLATE.format(token=self.bot_token)
        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": False,
        }
        success = self._post_request(msg_url, payload, max_retries)
        if success:
            logger.info("Telegram: Dispatched text alert for '%s'", deal.title)
        return success

    def _post_request(self, endpoint: str, payload: dict, max_retries: int) -> bool:
        """Executes POST request to Telegram Bot API with rate-limit handling."""
        for attempt in range(max_retries + 1):
            try:
                resp = requests.post(endpoint, json=payload, timeout=self.timeout)
                if resp.status_code == 200 and resp.json().get("ok") is True:
                    return True

                if resp.status_code == 429:
                    retry_after = resp.json().get("parameters", {}).get("retry_after", 2)
                    logger.warning("Telegram 429 Rate Limit. Sleeping %ds...", retry_after)
                    time.sleep(float(retry_after))
                    continue

                logger.warning("Telegram API error (HTTP %d): %s", resp.status_code, resp.text[:200])
                return False

            except requests.RequestException as e:
                logger.error("Telegram network error on attempt %d: %s", attempt + 1, e)
                if attempt < max_retries:
                    time.sleep(1.0)
                else:
                    return False
            except Exception as e:
                logger.error("Unexpected error dispatching to Telegram: %s", e)
                return False

        return False
