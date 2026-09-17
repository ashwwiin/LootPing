"""Ingestion package for game deals and giveaways."""

from src.ingestion.base import BaseIngester
from src.ingestion.gamerpower import GamerPowerIngester
from src.ingestion.cheapshark import CheapSharkIngester

__all__ = ["BaseIngester", "GamerPowerIngester", "CheapSharkIngester"]
