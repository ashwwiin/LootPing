"""Main entry point for LootPing pipeline execution."""

import logging
import sys
from typing import List

from src.config import config
from src.dispatchers import DiscordDispatcher, TelegramDispatcher, WhatsAppDispatcher
from src.ingestion import GamerPowerIngester, CheapSharkIngester
from src.models import Deal
from src.storage import StateManager

# Configure root logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("LootPing")


def run_pipeline() -> None:
    """Executes full LootPing check, deduplication, and notification flow."""
    logger.info("==================================================")
    logger.info("Starting LootPing Check Pipeline")
    logger.info("==================================================")

    # 1. Initialize State Manager
    state_manager = StateManager(config.state_file_path)

    # 2. Ingest Deals from Data Sources
    all_deals: List[Deal] = []

    # GamerPower API
    gp_ingester = GamerPowerIngester()
    gp_deals = gp_ingester.fetch_deals()
    all_deals.extend(gp_deals)

    # CheapShark API (if enabled)
    if config.enable_cheapshark:
        cs_ingester = CheapSharkIngester()
        cs_deals = cs_ingester.fetch_deals()
        all_deals.extend(cs_deals)

    logger.info("Total fetched deals from all sources: %d", len(all_deals))

    # 3. Filter by Allowed / Trusted Platforms
    allowed = config.allowed_platforms_list
    if allowed:
        trusted_deals = [d for d in all_deals if d.matches_platforms(allowed)]
        logger.info(
            "Platform filter (%s): Retained %d/%d trusted store deals.",
            ", ".join(allowed),
            len(trusted_deals),
            len(all_deals),
        )
        all_deals = trusted_deals

    # 4. Deduplicate against already alerted deals
    new_deals = state_manager.filter_new_deals(all_deals)

    if not new_deals:
        logger.info("No new un-alerted deals found in this cycle.")
        # Prune old cache entries anyway
        pruned = state_manager.prune_older_than(days=config.state_prune_days)
        if pruned > 0:
            state_manager.save()
        logger.info("Pipeline completed successfully (0 new alerts).")
        return

    logger.info("Found %d NEW deals to dispatch!", len(new_deals))

    # 4. Multi-Channel Notification Dispatch
    dispatchers = [
        DiscordDispatcher(),
        TelegramDispatcher(),
        WhatsAppDispatcher(),
    ]

    active_dispatchers = [d for d in dispatchers if d.is_enabled()]
    if not active_dispatchers:
        logger.warning(
            "No notification channels are configured/enabled! "
            "Please configure DISCORD_WEBHOOK_URL, TELEGRAM_BOT_TOKEN/CHAT_ID, or WHATSAPP credentials."
        )

    for dispatcher in dispatchers:
        if dispatcher.is_enabled():
            logger.info("Dispatching %d deals to %s...", len(new_deals), dispatcher.name)
            res = dispatcher.send_deals(new_deals)
            logger.info(
                "[%s] Sent: %d/%d | Success: %s %s",
                dispatcher.name,
                res.items_sent,
                len(new_deals),
                res.success,
                f"({res.error_message})" if res.error_message else "",
            )

    # 5. Update State & Auto-Prune
    state_manager.record_deals(new_deals)
    state_manager.prune_older_than(days=config.state_prune_days)
    state_manager.save()

    logger.info("==================================================")
    logger.info("LootPing Pipeline successfully executed.")
    logger.info("==================================================")


if __name__ == "__main__":
    run_pipeline()
