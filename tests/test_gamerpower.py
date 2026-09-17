"""Unit tests for GamerPower API ingestion."""

import responses
from src.ingestion.gamerpower import GamerPowerIngester


@responses.activate
def test_gamerpower_fetch_success():
    mock_payload = [
        {
            "id": 1050,
            "title": "Cave Story+",
            "worth": "$14.99",
            "thumbnail": "https://www.gamerpower.com/images/cave-story.jpg",
            "image": "https://www.gamerpower.com/images/cave-story.jpg",
            "description": "Download Cave Story+ for free on Epic Games Store.",
            "instructions": "Click the button to claim.",
            "open_giveaway_url": "https://store.epicgames.com/p/cave-story",
            "published_date": "2026-09-01 10:00:00",
            "type": "Game",
            "platforms": "PC, Epic Games Store",
            "end_date": "2026-09-20 23:59:59",
            "users": 1500,
            "status": "Active",
            "gamerpower_url": "https://www.gamerpower.com/cave-story",
        }
    ]

    responses.add(
        responses.GET,
        "https://www.gamerpower.com/api/giveaways?type=game",
        json=mock_payload,
        status=200,
    )

    ingester = GamerPowerIngester(giveaway_type="game")
    deals = ingester.fetch_deals()

    assert len(deals) == 1
    deal = deals[0]
    assert deal.id == "gp_1050"
    assert deal.title == "Cave Story+"
    assert deal.worth == "$14.99"
    assert deal.platforms == "PC, Epic Games Store"
    assert deal.url == "https://store.epicgames.com/p/cave-story"
    assert deal.source == "GamerPower"
    assert deal.deal_type == "Game"


@responses.activate
def test_gamerpower_empty_or_error_handling():
    responses.add(
        responses.GET,
        "https://www.gamerpower.com/api/giveaways?type=game",
        status=500,
    )

    ingester = GamerPowerIngester(giveaway_type="game")
    deals = ingester.fetch_deals()
    assert deals == []
