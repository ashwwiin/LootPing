"""Unit tests for Discord, Telegram, and WhatsApp notification dispatchers."""

import json
import urllib.parse
import responses
from src.dispatchers import DiscordDispatcher, TelegramDispatcher, WhatsAppDispatcher
from src.models import Deal


def sample_deal() -> Deal:
    return Deal(
        id="gp_999",
        title="Epic Space Game",
        worth="$29.99",
        platforms="PC, Steam",
        url="https://store.steampowered.com/app/999",
        image_url="https://example.com/cover.jpg",
        end_date="2026-09-30 23:59:59",
        source="GamerPower",
        deal_type="Game",
        description="A great space adventure.",
    )


# ==================== Discord Tests ====================

@responses.activate
def test_discord_dispatcher_success():
    webhook_url = "https://discord.com/api/webhooks/123/abc"
    responses.add(responses.POST, webhook_url, status=204)

    dispatcher = DiscordDispatcher(webhook_url=webhook_url, role_id="123456789")
    deal = sample_deal()
    result = dispatcher.send_deals([deal])

    assert result.success is True
    assert result.items_sent == 1
    assert len(responses.calls) == 1

    payload = json.loads(responses.calls[0].request.body)
    assert "<@&123456789>" in payload.get("content", "")
    assert len(payload["embeds"]) == 1
    embed = payload["embeds"][0]
    assert "Epic Space Game" in embed["title"]
    assert embed["url"] == deal.url
    assert embed["image"]["url"] == deal.image_url


def test_discord_dispatcher_disabled():
    dispatcher = DiscordDispatcher(webhook_url="")
    assert not dispatcher.is_enabled()
    res = dispatcher.send_deals([sample_deal()])
    assert res.success is True
    assert res.items_sent == 0


# ==================== Telegram Tests ====================

@responses.activate
def test_telegram_dispatcher_photo_and_text():
    token = "123456:ABC-DEF"
    chat_id = "@lootping_alerts"

    # Mock sendPhoto endpoint success
    responses.add(
        responses.POST,
        f"https://api.telegram.org/bot{token}/sendPhoto",
        json={"ok": True, "result": {"message_id": 1}},
        status=200,
    )

    dispatcher = TelegramDispatcher(bot_token=token, chat_id=chat_id)
    deal = sample_deal()
    result = dispatcher.send_deals([deal])

    assert result.success is True
    assert result.items_sent == 1
    assert len(responses.calls) == 1

    body = json.loads(responses.calls[0].request.body)
    assert body["chat_id"] == chat_id
    assert body["photo"] == deal.image_url
    assert "Epic Space Game" in body["caption"]


@responses.activate
def test_telegram_dispatcher_text_only_fallback():
    token = "123456:ABC-DEF"
    chat_id = "@lootping_alerts"

    deal_no_img = Deal(
        id="gp_1001",
        title="Indie Puzzle",
        worth="$9.99",
        platforms="GOG",
        url="https://gog.com/game/puzzle",
    )

    responses.add(
        responses.POST,
        f"https://api.telegram.org/bot{token}/sendMessage",
        json={"ok": True, "result": {"message_id": 2}},
        status=200,
    )

    dispatcher = TelegramDispatcher(bot_token=token, chat_id=chat_id)
    result = dispatcher.send_deals([deal_no_img])

    assert result.success is True
    assert result.items_sent == 1
    body = json.loads(responses.calls[0].request.body)
    assert body["chat_id"] == chat_id
    assert "Indie Puzzle" in body["text"]


# ==================== WhatsApp Tests ====================

@responses.activate
def test_whatsapp_dispatcher_success():
    phone = "1234567890"
    apikey = "secret123"

    responses.add(
        responses.GET,
        "https://api.callmebot.com/whatsapp.php",
        body="Message queued successfully",
        status=200,
    )

    dispatcher = WhatsAppDispatcher(phone=phone, apikey=apikey)
    deal = sample_deal()
    result = dispatcher.send_deals([deal])

    assert result.success is True
    assert result.items_sent == 1
    assert len(responses.calls) == 1

    parsed_url = urllib.parse.urlparse(responses.calls[0].request.url)
    params = urllib.parse.parse_qs(parsed_url.query)
    assert params["phone"][0] == phone
    assert params["apikey"][0] == apikey
    assert "*FREE GAME ALERT: Epic Space Game*" in params["text"][0]
