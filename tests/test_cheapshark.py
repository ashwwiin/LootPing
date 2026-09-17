"""Unit tests for CheapShark API ingestion."""

import responses
from src.ingestion.cheapshark import CheapSharkIngester


@responses.activate
def test_cheapshark_fetch_deals():
    mock_stores = [
        {"storeID": "1", "storeName": "Steam"},
        {"storeID": "25", "storeName": "Epic Games Store"},
    ]
    mock_deals = [
        {
            "internalName": "FREEGAME",
            "title": "Free Game Test",
            "dealID": "deal12345",
            "storeID": "1",
            "gameID": "999",
            "salePrice": "0.00",
            "normalPrice": "19.99",
            "savings": "100.000000",
            "thumb": "https://example.com/thumb.jpg",
        }
    ]

    responses.add(
        responses.GET,
        "https://www.cheapshark.com/api/1.0/stores",
        json=mock_stores,
        status=200,
    )
    responses.add(
        responses.GET,
        "https://www.cheapshark.com/api/1.0/deals?upperPrice=0&sortBy=Savings",
        json=mock_deals,
        status=200,
    )

    ingester = CheapSharkIngester()
    deals = ingester.fetch_deals()

    assert len(deals) == 1
    deal = deals[0]
    assert deal.id == "cs_deal12345"
    assert deal.title == "Free Game Test"
    assert deal.worth == "$19.99"
    assert "Steam" in deal.platforms
    assert deal.source == "CheapShark"
