# 🎮 LootPing - Game Deals & Freebies Notifier

[![LootPing Deal Checker](https://github.com/your-username/lootping/actions/workflows/checker.yml/badge.svg)](https://github.com/your-username/lootping/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

> **Automated, multi-channel notification engine for 100% free game giveaways and deep discounts across Steam, Epic Games Store, GOG, PlayStation, Xbox, and itch.io.** Runs on a **$0 operational cost model** via GitHub Actions.

---

## ⚡ Features

- 🆓 **100% Free Game Detection**: Automatically tracks giveaways from GamerPower and 100% off deals from CheapShark.
- 💬 **Multi-Channel Dispatch**:
  - **Discord**: Rich Embeds with thumbnail images, platform tags, original prices, and optional role pings (`<@&ROLE_ID>` or `@everyone`).
  - **Telegram**: Formatted HTML/Markdown broadcast messages with link previews to public/private channels or groups.
  - **WhatsApp**: Instant personal mobile push notifications via CallMeBot gateway.
- 🛡 **Zero Spam / Deduplication**: Persists alerted deal IDs in repository storage (`data/alerted_ids.json`), preventing duplicate alerts.
- 🧹 **Automatic 90-Day Pruning**: Automatically prunes stale state entries older than 90 days to keep repository storage lean.
- ⚡ **Resilient & Fault-Tolerant**: Isolated channel dispatch ensures that a temporary failure in one service (e.g. CallMeBot rate limiting) does not disrupt others.
- 🚀 **Zero Infrastructure Overhead**: Runs entirely within GitHub Actions scheduled cron runs (`0 * * * *`).

---

## 🏗 System Architecture

```
   ┌─────────────────────────────────────────────────────────────┐
   │                Cron Trigger (GitHub Actions)                │
   │               Schedule: Every 60 min (0 * * * *)            │
   └──────────────────────────────┬──────────────────────────────┘
                                  │
                                  ▼
   ┌─────────────────────────────────────────────────────────────┐
   │                  Ingestion Engine (Python)                  │
   │      - GamerPower Giveaways API                             │
   │      - CheapShark API (Discounts & Price Drops)             │
   └──────────────────────────────┬──────────────────────────────┘
                                  │
                                  ▼
   ┌─────────────────────────────────────────────────────────────┐
   │             Deduplication & State Cache Engine              │
   │       Reads/Updates data/alerted_ids.json in Git Cache      │
   └──────────────────────────────┬──────────────────────────────┘
                                  │ (Filtered New Deals)
         ┌────────────────────────┼────────────────────────┐
         ▼                        ▼                        ▼
┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐
│  WhatsApp Engine │    │  Telegram Engine │    │  Discord Engine  │
│    CallMeBot     │    │  Bot API /sendMsg│    │ Incoming Webhook │
│  (Personal Ping) │    │(Channels/Groups) │    │  (Rich Embeds)   │
└──────────────────┘    └──────────────────┘    └──────────────────┘
```

---

## 🚀 Setup Guide

### 1. Channel Configuration

You can enable **any or all** of the following notification channels. If a channel's secrets are left unconfigured, LootPing will gracefully skip it.

#### 🎮 Discord Channel (Rich Embeds)
1. In your Discord server, go to **Channel Settings** -> **Integrations** -> **Webhooks**.
2. Click **New Webhook**, select the desired channel (e.g., `#free-games`), and copy the **Webhook URL**.
3. *(Optional)* If you want to ping a specific role when a deal arrives, right-click the role in Server Settings -> Roles, select **Copy ID**, and set `DISCORD_ROLE_ID`.

#### ✈️ Telegram Channel / Group
1. Message [@BotFather](https://t.me/BotFather) on Telegram and create a new bot with `/newbot`.
2. Copy the **HTTP API Token** (e.g., `123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ`).
3. Create a public or private Telegram Channel/Group and add your bot as an **Administrator** with permission to post messages.
4. For public channels, use your `@channel_username`. For private channels/groups, get your numeric Chat ID (e.g., `-1001234567890`).

#### 📱 WhatsApp (Personal Ping via CallMeBot)
1. Add the CallMeBot phone number to your phone contacts:
   - Follow instructions on [CallMeBot WhatsApp Setup](https://www.callmebot.com/blog/free-api-whatsapp-messages/).
2. Send the activation message `I allow callmebot to send me messages` to the bot on WhatsApp.
3. CallMeBot will reply with your personal **API Key**.
4. Use your international phone number without `+` or spaces (e.g., `1234567890`) and your API Key.

---

### 2. GitHub Actions Deployment

1. **Fork or Push** this repository to your GitHub account.
2. In your GitHub repository, go to **Settings** -> **Secrets and variables** -> **Actions**.
3. Under **Repository secrets**, click **New repository secret** and add:

| Secret Name | Description | Example |
| :--- | :--- | :--- |
| `DISCORD_WEBHOOK_URL` | Discord Webhook POST URL | `https://discord.com/api/webhooks/...` |
| `DISCORD_ROLE_ID` *(Optional)* | Discord Role ID to mention | `123456789012345678` or `@everyone` |
| `TELEGRAM_BOT_TOKEN` | Telegram Bot Token from BotFather | `123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11` |
| `TELEGRAM_CHAT_ID` | Telegram Channel Username or Chat ID | `@lootping_deals` or `-1001234567890` |
| `WHATSAPP_PHONE` | Phone number with country code (no `+`) | `1234567890` |
| `WHATSAPP_APIKEY` | CallMeBot API Key | `987654` |

4. Enable GitHub Actions Workflow Write Permissions:
   - Go to **Settings** -> **Actions** -> **General**.
   - Under **Workflow permissions**, select **Read and write permissions**.
   - Check **Allow GitHub Actions to create and approve pull requests**.
   - Click **Save**.

5. Trigger a manual run:
   - Go to the **Actions** tab.
   - Select **LootPing Deal Checker** workflow.
   - Click **Run workflow**.

---

### 3. Local Development & Testing

#### Prerequisites
- Python 3.11+
- Git

#### Installation
```bash
# Clone the repository
git clone https://github.com/your-username/lootping.git
cd lootping

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

#### Running Locally
```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your credentials
# Run the pipeline
python main.py
```

#### Running Test Suite
```bash
pytest -v
```

---

## ⚙️ Configuration Reference

| Variable | Default | Description |
| :--- | :--- | :--- |
| `GIVEAWAY_TYPE` | `game` | Filter giveaway type (`game`, `loot`, `beta`, `all`) |
| `ENABLE_CHEAPSHARK` | `true` | Query CheapShark for 100% discounts |
| `STATE_FILE_PATH` | `data/alerted_ids.json` | Path to persistent deduplication cache |
| `STATE_PRUNE_DAYS` | `90` | Number of days before un-alerted records expire |
| `HTTP_TIMEOUT` | `12` | Bounded HTTP request timeout in seconds |

---

## 📄 License

Distributed under the MIT License. See `LICENSE` for more information.
