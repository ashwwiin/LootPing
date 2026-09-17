"""Unit tests for state management, deduplication, and 90-day pruning."""

import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pytest
from src.models import Deal
from src.storage import StateManager


@pytest.fixture
def temp_state_file(tmp_path: Path) -> Path:
    state_file = tmp_path / "alerted_ids.json"
    return state_file


def test_state_manager_init_empty(temp_state_file: Path):
    manager = StateManager(temp_state_file)
    assert manager.deals == {}
    assert not manager.is_alerted("gp_123")


def test_state_manager_record_and_filter(temp_state_file: Path):
    manager = StateManager(temp_state_file)

    deal1 = Deal(id="gp_1", title="Game 1", worth="$10", platforms="Steam", url="https://example.com/1")
    deal2 = Deal(id="gp_2", title="Game 2", worth="$20", platforms="Epic", url="https://example.com/2")

    # Both are new
    new_deals = manager.filter_new_deals([deal1, deal2])
    assert len(new_deals) == 2

    # Record deal1 and save
    manager.record_deals([deal1])
    manager.save()

    # Create new manager instance to test persistence
    manager2 = StateManager(temp_state_file)
    assert manager2.is_alerted("gp_1")
    assert not manager2.is_alerted("gp_2")

    filtered = manager2.filter_new_deals([deal1, deal2])
    assert len(filtered) == 1
    assert filtered[0].id == "gp_2"


def test_state_manager_pruning(temp_state_file: Path):
    manager = StateManager(temp_state_file)

    # Add old deal (100 days ago) and recent deal (10 days ago)
    now = datetime.now(timezone.utc)
    old_time = (now - timedelta(days=100)).isoformat()
    recent_time = (now - timedelta(days=10)).isoformat()

    manager.deals = {
        "gp_old": {"title": "Old Game", "timestamp": old_time},
        "gp_recent": {"title": "Recent Game", "timestamp": recent_time},
    }

    pruned = manager.prune_older_than(days=90)
    assert pruned == 1
    assert "gp_old" not in manager.deals
    assert "gp_recent" in manager.deals


def test_state_manager_backward_compatibility(temp_state_file: Path):
    # Test reading legacy list format: ["gp_100", "gp_200"]
    with open(temp_state_file, "w", encoding="utf-8") as f:
        json.dump(["gp_100", "gp_200"], f)

    manager = StateManager(temp_state_file)
    assert manager.is_alerted("gp_100")
    assert manager.is_alerted("gp_200")
    assert not manager.is_alerted("gp_300")


def test_deal_platform_filtering():
    trusted = ["steam", "epic", "xbox", "playstation", "gog", "ubisoft"]

    deal_steam = Deal(id="1", title="Game A", worth="$10", platforms="PC, Steam", url="https://store.steampowered.com/app/1")
    deal_epic = Deal(id="2", title="Game B", worth="$20", platforms="PC, Epic Games Store", url="https://store.epicgames.com/p/b")
    deal_gala = Deal(id="3", title="Indie Game", worth="$5", platforms="PC, DRM-Free", url="https://indiegala.com/game/c")
    deal_itch = Deal(id="4", title="Itch Game", worth="$2", platforms="PC, Itch.io", url="https://itch.io/game/d")

    assert deal_steam.matches_platforms(trusted) is True
    assert deal_epic.matches_platforms(trusted) is True
    assert deal_gala.matches_platforms(trusted) is False
    assert deal_itch.matches_platforms(trusted) is False

    # Empty filter matches everything
    assert deal_gala.matches_platforms([]) is True
