"""Configuration management for LootPing."""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


def _get_env_trimmed(key: str, default: Optional[str] = None) -> Optional[str]:
    val = os.getenv(key, default)
    if val is not None:
        val = val.strip()
    return val if val else None


@dataclass(frozen=True)
class Config:
    """Application configuration loaded from environment variables."""

    # Discord Settings
    discord_webhook_url: Optional[str] = _get_env_trimmed("DISCORD_WEBHOOK_URL")
    discord_role_id: Optional[str] = _get_env_trimmed("DISCORD_ROLE_ID")

    # Telegram Settings
    telegram_bot_token: Optional[str] = _get_env_trimmed("TELEGRAM_BOT_TOKEN")
    telegram_chat_id: Optional[str] = _get_env_trimmed("TELEGRAM_CHAT_ID")

    # WhatsApp (CallMeBot) Settings
    whatsapp_phone: Optional[str] = _get_env_trimmed("WHATSAPP_PHONE")
    whatsapp_apikey: Optional[str] = _get_env_trimmed("WHATSAPP_APIKEY")

    # Ingestion & State Settings
    giveaway_type: str = (_get_env_trimmed("GIVEAWAY_TYPE") or "game").lower()
    allowed_platforms: str = (_get_env_trimmed("ALLOWED_PLATFORMS") or "steam, epic, gog, xbox, playstation, ubisoft, prime").lower()
    enable_cheapshark: bool = (_get_env_trimmed("ENABLE_CHEAPSHARK") or "true").lower() in ("true", "1", "yes")
    state_file_path: Path = Path(_get_env_trimmed("STATE_FILE_PATH") or "data/alerted_ids.json")
    state_prune_days: int = int(_get_env_trimmed("STATE_PRUNE_DAYS") or "90")

    # Request timeouts in seconds (strictly bounded to 10-15s)
    http_timeout: int = int(_get_env_trimmed("HTTP_TIMEOUT") or "12")

    @property
    def is_discord_enabled(self) -> bool:
        return bool(self.discord_webhook_url and self.discord_webhook_url.strip())

    @property
    def is_telegram_enabled(self) -> bool:
        return bool(
            self.telegram_bot_token
            and self.telegram_bot_token.strip()
            and self.telegram_chat_id
            and self.telegram_chat_id.strip()
        )

    @property
    def is_whatsapp_enabled(self) -> bool:
        return bool(
            self.whatsapp_phone
            and self.whatsapp_phone.strip()
            and self.whatsapp_apikey
            and self.whatsapp_apikey.strip()
        )

    @property
    def allowed_platforms_list(self) -> list[str]:
        if not self.allowed_platforms or self.allowed_platforms == "all":
            return []
        return [p.strip().lower() for p in self.allowed_platforms.split(",") if p.strip()]


# Global singleton instance
config = Config()
