# VYX Telegram News Bot

A Telegram bot that collects cybersecurity and software supply chain news from curated RSS feeds, scores each article by relevance, and sends the most important updates to a Telegram chat.

## Features

- Pulls news from multiple trusted security and tech sources
- Filters and ranks articles by keyword relevance
- Adds a recency bonus for fresh content
- Avoids duplicate posts with local tracking
- Sends formatted messages to Telegram

## Requirements

- Python 3.10+
- A Telegram bot token
- A Telegram chat ID

## Installation

1. Clone the repository
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Create a `.env` file in the project root:

```env
BOT_TOKEN=your_telegram_bot_token
CHAT_ID=your_chat_id
MAX_PER_RUN=10
MIN_SCORE=2
RECENCY_HOURS=24
MAX_AGE_HOURS=24
SENT_DB=sent_articles.json
```

## How it works

- The bot reads RSS feeds from sources like Krebs on Security, The Hacker News, Bleeping Computer, and more.
- Each article is scored based on security and supply chain keywords.
- Fresh articles get extra weight.
- Only unseen articles with a high enough score are sent to Telegram.

## Run

```bash
python main.py
```

## Configuration

- `BOT_TOKEN` — Telegram bot token
- `CHAT_ID` — Telegram chat or channel ID
- `MAX_PER_RUN` — maximum articles sent per run
- `MIN_SCORE` — minimum relevance score required
- `RECENCY_HOURS` — time window for recency bonus
- `MAX_AGE_HOURS` — ignore articles older than this
- `SENT_DB` — file used to store sent article IDs

## Notes

- This project is designed to run as a scheduled job or cron task.
- Articles are stored locally in `sent_articles.json` to prevent duplicates.

## License

Add your preferred license here.
