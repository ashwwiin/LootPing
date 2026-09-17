"""Integration tests for main pipeline execution."""

from pathlib import Path
import responses
from src.storage import StateManager
import main


@responses.activate
def test_pipeline_integration(tmp_path: Path, monkeypatch):
    # Setup temp state file
    test_state = tmp_path / "test_state.json"
    from src.config import Config
    import src.config
    import src.dispatchers.discord
    import src.ingestion.cheapshark

    custom_config = Config(
        state_file_path=test_state,
        discord_webhook_url="https://discord.com/api/webhooks/test",
        enable_cheapshark=True,
    )
    monkeypatch.setattr(src.config, "config", custom_config)
    monkeypatch.setattr(main, "config", custom_config)
    monkeypatch.setattr(src.dispatchers.discord, "config", custom_config)
    monkeypatch.setattr(src.ingestion.cheapshark, "config", custom_config)

    # Mock GamerPower API
    responses.add(
        responses.GET,
        "https://www.gamerpower.com/api/giveaways?type=game",
        json=[
            {
                "id": 888,
                "title": "Pipeline Test Game",
                "worth": "$19.99",
                "platforms": "Steam",
                "open_giveaway_url": "https://store.steampowered.com/app/888",
                "image": "https://example.com/img.jpg",
                "type": "Game",
            }
        ],
        status=200,
    )

    # Mock CheapShark
    responses.add(
        responses.GET,
        "https://www.cheapshark.com/api/1.0/deals?upperPrice=0&sortBy=Savings",
        json=[],
        status=200,
    )

    # Mock Discord Webhook
    responses.add(
        responses.POST,
        "https://www.discord.com/api/webhooks/test",
        status=204,
    )

    # Run pipeline first time
    main.run_pipeline()

    # Verify state was saved
    sm = StateManager(test_state)
    assert sm.is_alerted("gp_888")

    # Run pipeline second time (should find 0 new deals and not post again)
    main.run_pipeline()
