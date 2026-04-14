"""
RSS feed scraping and article collection logic.
"""

import re
import hashlib
import logging
import feedparser

from config import MIN_SCORE
from sources import SOURCES
from scoring import score_article, recency_bonus, is_within_age_limit

log = logging.getLogger(__name__)


def article_id(url: str) -> str:
    """Generate a unique ID for an article based on its URL."""
    return hashlib.sha256(url.encode()).hexdigest()[:16]


def scrape_feed(name: str, url: str, emoji: str) -> list[dict]:
    """Parse a single RSS feed; score and return article dicts."""
    articles = []
    try:
        feed = feedparser.parse(url)
        for entry in feed.entries:
            link      = getattr(entry, "link",    "").strip()
            title     = getattr(entry, "title",   "No title").strip()
            summary   = getattr(entry, "summary", "").strip()
            published = getattr(entry, "published", "")

            if not link:
                continue

            # Filter out articles older than MAX_AGE_HOURS
            if not is_within_age_limit(published):
                continue

            # Strip HTML tags from summary
            summary = re.sub(r"<[^>]+>", "", summary)
            summary = summary[:400] + ("…" if len(summary) > 400 else "")

            score, category = score_article(title, summary)
            score += recency_bonus(published)

            articles.append({
                "id":        article_id(link),
                "source":    name,
                "emoji":     emoji,
                "title":     title,
                "summary":   summary,
                "url":       link,
                "published": published,
                "score":     score,
                "category":  category,
            })

    except Exception as e:
        log.warning("Failed to parse feed '%s': %s", name, e)
    return articles


def scrape_all() -> list[dict]:
    """Scrape every source; filter by MIN_SCORE; sort by score desc."""
    all_articles = []
    for name, url, emoji in SOURCES:
        arts = scrape_feed(name, url, emoji)
        log.info("  [%s] %d articles fetched", name, len(arts))
        all_articles.extend(arts)

    # Keep only relevant articles
    relevant = [a for a in all_articles if a["score"] >= MIN_SCORE]
    relevant.sort(key=lambda a: a["score"], reverse=True)

    log.info(
        "Relevance filter: %d total → %d relevant (score ≥ %d)",
        len(all_articles), len(relevant), MIN_SCORE,
    )
    return relevant
