"""
Intelligent News Bot → Telegram
Scrapes cybersecurity and software supply chain security articles from curated
sources, scores each item for relevance, and forwards only the most
interesting ones to Telegram — ranked by score, not by arrival order.
"""

import logging
import asyncio

from datetime import datetime, timezone
from telegram import Bot
from telegram.constants import ParseMode
from telegram.error import TelegramError

from config import BOT_TOKEN, CHAT_ID, MAX_PER_RUN
from scraper import scrape_all
from formatter import format_message
from persistence import load_sent, save_sent

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)


async def run_once(bot: Bot, sent: set) -> set:
    """One scrape-and-send cycle. Returns the updated sent set."""
    log.info("Starting scrape cycle at %s", datetime.now(timezone.utc).isoformat())
    articles = scrape_all()

    new_articles = [a for a in articles if a["id"] not in sent]
    log.info(
        "Relevant articles: %d | New (unseen): %d | Will send: ≤%d",
        len(articles), len(new_articles), MAX_PER_RUN,
    )

    sent_count = 0
    for article in new_articles:
        if sent_count >= MAX_PER_RUN:
            log.info("Reached MAX_PER_RUN (%d), stopping this cycle.", MAX_PER_RUN)
            break
        try:
            msg = format_message(article)
            await bot.send_message(
                chat_id=CHAT_ID,
                text=msg,
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=False,
            )
            sent.add(article["id"])
            sent_count += 1
            log.info(
                "  ✓ [score=%d] [%s] %s",
                article["score"], article["source"], article["title"][:60],
            )
            await asyncio.sleep(1.2)   # gentle rate-limit between messages
        except TelegramError as e:
            log.error("  ✗ Telegram error for '%s': %s", article["title"][:60], e)
        except Exception as e:
            log.error("  ✗ Unexpected error: %s", e)

    save_sent(sent)
    log.info("Cycle done. Sent %d new articles.", sent_count)
    return sent


async def main() -> None:
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN is not set. Add it to your .env file.")
    if not CHAT_ID:
        raise ValueError("CHAT_ID is not set. Add it to your .env file.")

    bot  = Bot(token=BOT_TOKEN)
    sent = load_sent()

    log.info("🤖 Intelligent News Bot started.")
    log.info("   Chat ID        : %s", CHAT_ID)
    log.info("   Max per run    : %d", MAX_PER_RUN)
    log.info("   Sources        : 14")

    await run_once(bot, sent)


if __name__ == "__main__":
    asyncio.run(main())
