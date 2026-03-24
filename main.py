"""
Intelligent News Bot → Telegram
Scrapes cybersecurity, AI/ML, and computer-science articles from curated
sources, scores each item for relevance, and forwards only the most
interesting ones to Telegram — ranked by score, not by arrival order.
"""

import os
import re
import json
import hashlib
import logging
import asyncio
import feedparser

from datetime import datetime, timezone, timedelta
from pathlib import Path
from dotenv import load_dotenv
from telegram import Bot
from telegram.constants import ParseMode
from telegram.error import TelegramError

# ──────────────────────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────────────────────
load_dotenv()

BOT_TOKEN       = os.getenv("BOT_TOKEN", "")
CHAT_ID         = os.getenv("CHAT_ID", "")
MAX_PER_RUN     = int(os.getenv("MAX_PER_RUN", "10"))        # max articles per cycle
MIN_SCORE       = int(os.getenv("MIN_SCORE", "2"))           # minimum relevance score to send
SENT_DB_PATH    = Path(os.getenv("SENT_DB", "sent_articles.json"))
RECENCY_HOURS   = int(os.getenv("RECENCY_HOURS", "24"))      # prefer articles within this window

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────
# Curated Sources  (only cyber / AI / CS focused)
# ──────────────────────────────────────────────────────────────
SOURCES = [
    # ── Cybersecurity ────────────────────────────────────────────
    ("Krebs on Security",   "https://krebsonsecurity.com/feed/",                        "🔐"),
    ("The Hacker News",     "https://feeds.feedburner.com/TheHackersNews",              "🛡️"),
    ("Bleeping Computer",   "https://www.bleepingcomputer.com/feed/",                   "💻"),
    ("SANS ISC",            "https://isc.sans.edu/rssfeed_full.xml",                    "🔐"),
    ("Dark Reading",        "https://www.darkreading.com/rss.xml",                      "🔐"),
    ("Threatpost",          "https://threatpost.com/feed/",                             "🛡️"),
    ("Schneier on Security","https://www.schneier.com/feed/atom/",                      "🔐"),
    ("r/netsec",            "https://www.reddit.com/r/netsec/.rss",                     "🛡️"),
    ("r/cybersecurity",     "https://www.reddit.com/r/cybersecurity/.rss",              "🔐"),

    # ── AI / ML ──────────────────────────────────────────────────
    ("MIT Tech Review AI",  "https://www.technologyreview.com/topic/artificial-intelligence/feed/", "🤖"),
    ("Google AI Blog",      "https://blog.research.google/feeds/posts/default",         "🤖"),
    ("OpenAI Blog",         "https://openai.com/news/rss.xml",                          "🤖"),
    ("DeepMind Blog",       "https://deepmind.google/blog/rss.xml",                     "🤖"),
    ("Hugging Face Blog",   "https://huggingface.co/blog/feed.xml",                     "🤖"),
    ("r/MachineLearning",   "https://www.reddit.com/r/MachineLearning/.rss",            "🤖"),
    ("r/artificial",        "https://www.reddit.com/r/artificial/.rss",                 "🤖"),
    ("ArXiv CS.AI",         "http://arxiv.org/rss/cs.AI",                              "📄"),
    ("ArXiv CS.LG",         "http://arxiv.org/rss/cs.LG",                              "📄"),
    ("ArXiv CS.CR",         "http://arxiv.org/rss/cs.CR",                              "📄"),

    # ── Computer Science / Software Engineering ───────────────────
    ("Hacker News",         "https://news.ycombinator.com/rss",                         "🟠"),
    ("ACM TechNews",        "https://technews.acm.org/archives.cfm?fo=rss",             "🎓"),
    ("Ars Technica Tech",   "https://feeds.arstechnica.com/arstechnica/technology-lab", "🔬"),
    ("Lobsters",            "https://lobste.rs/rss",                                    "🦞"),
    ("r/compsci",           "https://www.reddit.com/r/compsci/.rss",                    "💻"),
    ("r/programming",       "https://www.reddit.com/r/programming/.rss",                "💻"),
    ("Quanta Magazine",     "https://api.quantamagazine.org/feed/",                     "✨"),
]

# ──────────────────────────────────────────────────────────────
# Relevance Scoring
# ──────────────────────────────────────────────────────────────

# Each entry: (compiled_regex, score_points, category_tag)
_KEYWORD_RULES: list[tuple[re.Pattern, int, str]] = []

def _build_rules() -> None:
    """Compile keyword rules once at startup."""
    raw = [
        # ── High-value cybersecurity terms ──────────────────────────
        (r"\b(zero[- ]?day|0day|cve-\d{4})\b",                    4, "🔐 Security"),
        (r"\b(ransomware|malware|exploit|vulnerability|patch)\b",  3, "🔐 Security"),
        (r"\b(data breach|phishing|apt|threat actor|backdoor)\b",  3, "🔐 Security"),
        (r"\b(cybersecurity|infosec|pentest|red team|ctf)\b",      2, "🔐 Security"),
        (r"\b(supply[- ]chain attack|rce|lpe|privilege escalation)\b", 4, "🔐 Security"),
        (r"\b(firewall|ids|ips|siem|soar|endpoint|edr|xdr)\b",     2, "🔐 Security"),
        (r"\b(encryption|cryptography|tls|ssl|pki|certificate)\b", 2, "🔐 Security"),
        (r"\b(botnet|ddos|c2|command.and.control|stealer)\b",      3, "🔐 Security"),

        # ── High-value AI/ML terms ───────────────────────────────────
        (r"\b(large language model|llm|gpt|chatgpt|gemini|claude)\b", 4, "🤖 AI/ML"),
        (r"\b(neural network|deep learning|machine learning|transformer)\b", 3, "🤖 AI/ML"),
        (r"\b(reinforcement learning|diffusion model|generative ai|gen[- ]?ai)\b", 3, "🤖 AI/ML"),
        (r"\b(artificial intelligence|computer vision|nlp|natural language)\b", 2, "🤖 AI/ML"),
        (r"\b(benchmark|fine[- ]?tun|prompt engineer|rag|retrieval)\b", 2, "🤖 AI/ML"),
        (r"\b(openai|anthropic|deepmind|mistral|stability ai|hugging face)\b", 3, "🤖 AI/ML"),
        (r"\b(autonomous agent|ai safety|alignment|hallucination)\b", 3, "🤖 AI/ML"),
        (r"\b(multimodal|embedding|vector database|semantic search)\b", 2, "🤖 AI/ML"),

        # ── High-value CS / software terms ───────────────────────────
        (r"\b(algorithm|data structure|complexity|proof|theorem)\b", 2, "💻 CS"),
        (r"\b(compiler|operating system|kernel|memory.safe|rust|zig)\b", 2, "💻 CS"),
        (r"\b(distributed system|consensus|blockchain|p2p|protocol)\b", 2, "💻 CS"),
        (r"\b(open[- ]?source|github|arxiv|paper|research|preprint)\b", 1, "💻 CS"),
        (r"\b(programming language|type system|formal verification)\b", 2, "💻 CS"),
        (r"\b(cloud|kubernetes|container|devops|infrastructure)\b",    1, "💻 CS"),
        (r"\b(quantum computing|hardware|chip|semiconductor|cpu|gpu)\b", 2, "💻 CS"),
    ]
    for pattern, score, category in raw:
        _KEYWORD_RULES.append((re.compile(pattern, re.IGNORECASE), score, category))

_build_rules()


def score_article(title: str, summary: str) -> tuple[int, str]:
    """
    Score an article's relevance to cybersecurity / AI-ML / CS topics.
    Returns (total_score, dominant_category_tag).
    Title matches are worth 1.5× (rounded).
    """
    text_title   = title.lower()
    text_summary = summary.lower()

    category_scores: dict[str, float] = {}
    total = 0.0

    for pattern, pts, category in _KEYWORD_RULES:
        title_hits   = len(pattern.findall(text_title))
        summary_hits = len(pattern.findall(text_summary))
        contribution = title_hits * pts * 1.5 + summary_hits * pts
        if contribution > 0:
            total += contribution
            category_scores[category] = category_scores.get(category, 0) + contribution

    dominant = max(category_scores, key=category_scores.get) if category_scores else "💻 CS"
    return int(round(total)), dominant


def recency_bonus(published_str: str) -> int:
    """
    Return +2 if the article was published within RECENCY_HOURS,
    +1 if within 2×RECENCY_HOURS, else 0.
    """
    if not published_str:
        return 0
    try:
        from email.utils import parsedate_to_datetime
        pub = parsedate_to_datetime(published_str)
        if pub.tzinfo is None:
            pub = pub.replace(tzinfo=timezone.utc)
        age = datetime.now(timezone.utc) - pub
        if age <= timedelta(hours=RECENCY_HOURS):
            return 2
        if age <= timedelta(hours=RECENCY_HOURS * 2):
            return 1
    except Exception:
        pass
    return 0


# ──────────────────────────────────────────────────────────────
# Sent-article Persistence
# ──────────────────────────────────────────────────────────────

def load_sent() -> set:
    if SENT_DB_PATH.exists():
        try:
            data = json.loads(SENT_DB_PATH.read_text())
            return set(data)
        except Exception:
            pass
    return set()


def save_sent(sent: set) -> None:
    SENT_DB_PATH.write_text(json.dumps(list(sent), indent=2))


def article_id(url: str) -> str:
    return hashlib.sha256(url.encode()).hexdigest()[:16]


# ──────────────────────────────────────────────────────────────
# Scraping
# ──────────────────────────────────────────────────────────────

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

            # Strip HTML tags from summary
            summary = re.sub(r"<[^>]+>", "", summary)
            summary = summary[:400] + ("…" if len(summary) > 400 else "")

            if not link:
                continue

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


# ──────────────────────────────────────────────────────────────
# Telegram Formatting
# ──────────────────────────────────────────────────────────────

def format_message(article: dict) -> str:
    """Build an intelligently formatted Telegram message (HTML mode)."""
    emoji    = article["emoji"]
    source   = article["source"]
    title    = article["title"]
    summary  = article["summary"]
    url      = article["url"]
    score    = article["score"]
    category = article["category"]

    # Score bar (visual relevance indicator)
    bar_filled = min(score // 3, 8)
    bar = "█" * bar_filled + "░" * (8 - bar_filled)

    msg = (
        f"{emoji} <b>{source}</b>  │  {category}\n"
        f"<b>{title}</b>\n"
    )
    if summary:
        msg += f"\n{summary}\n"
    msg += (
        f"\n🔗 <a href=\"{url}\">Read more</a>"
        f"  │  <i>Relevance: [{bar}] {score}pts</i>"
    )
    return msg


# ──────────────────────────────────────────────────────────────
# Main Loop
# ──────────────────────────────────────────────────────────────

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
    log.info("   Min score      : %d", MIN_SCORE)
    log.info("   Recency window : %dh", RECENCY_HOURS)
    log.info("   Sources        : %d", len(SOURCES))

    await run_once(bot, sent)


if __name__ == "__main__":
    asyncio.run(main())
