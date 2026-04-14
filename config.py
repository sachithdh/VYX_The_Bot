"""
Configuration and environment variables
"""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Telegram Bot credentials
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
CHAT_ID = os.getenv("CHAT_ID", "")

# Scraping behavior
MAX_PER_RUN = int(os.getenv("MAX_PER_RUN", "10"))          # max articles per cycle
MIN_SCORE = int(os.getenv("MIN_SCORE", "2"))               # minimum relevance score to send
RECENCY_HOURS = int(os.getenv("RECENCY_HOURS", "24"))      # prefer articles within this window
MAX_AGE_HOURS = int(os.getenv("MAX_AGE_HOURS", "24"))      # hard cutoff: ignore articles older than this

# Database
SENT_DB_PATH = Path(os.getenv("SENT_DB", "sent_articles.json"))
