# VYX Telegram News Bot

A Telegram bot that collects cybersecurity and software supply chain news from curated RSS feeds, scores each article by relevance, and sends the most important updates to a Telegram chat.

(Developed for my personal use. Runs on GitHub Actions every day at 7 AM and sends me important news/articles from the past 24 hours :))

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

## How It Works

1. **Feed Collection**: The bot reads RSS feeds from multiple trusted security sources (configured in `sources.py`)
2. **Article Parsing**: Extracts title, summary, link, and publication date from each feed entry
3. **Age Filtering**: Discards articles older than `MAX_AGE_HOURS`
4. **Scoring**: Evaluates each article against keyword rules to determine relevance:
   - **🔐 Security**: Cybersecurity-focused keywords (zero-days, exploits, vulnerabilities, etc.)
   - **🔗 Supply Chain**: Software supply chain security keywords (dependencies, SBOM, npm/PyPI, etc.)
5. **Recency Bonus**: Freshly published articles (within `RECENCY_HOURS`) receive extra points
6. **Deduplication**: Checks against `sent_articles.json` to prevent duplicate posts
7. **Ranking & Sending**: Sends top-scoring unseen articles that meet `MIN_SCORE` threshold to Telegram

## Run

```bash
python main.py
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `BOT_TOKEN` | — | **Required.** Telegram bot token (get from BotFather) |
| `CHAT_ID` | — | **Required.** Telegram chat or channel ID where articles are sent |
| `MAX_PER_RUN` | 10 | Maximum number of articles to send per execution cycle |
| `MIN_SCORE` | 2 | Minimum relevance score threshold (0-4 range) |
| `RECENCY_HOURS` | 24 | Time window (hours) for recency bonus points |
| `MAX_AGE_HOURS` | 24 | Hard cutoff: articles older than this are ignored |
| `SENT_DB` | sent_articles.json | File path for tracking sent articles (prevents duplicates) |

### Scoring System

Articles are scored based on keyword matches:

- **4 points**: Zero-day exploits, CVEs, supply chain attacks, major incidents (Codecov, SolarWinds, Log4Shell)
- **3 points**: Ransomware, malware, data breaches, phishing, APTs, backdoors, npm/PyPI/Maven packages
- **2 points**: General cybersecurity/infosec terms, common security tools, supply chain concepts
- **1 point**: License compliance and general open-source topics

**Recency Bonus**: Articles published within `RECENCY_HOURS` receive +1 point boost.

An article is sent only if its final score ≥ `MIN_SCORE`.

## Adding New Sources

To add a new RSS feed source:

1. Open `sources.py`
2. Add a tuple to the `SOURCES` list with the format: `(name, feed_url, emoji)`

```python
SOURCES = [
    # Existing sources...
    ("My Security Blog", "https://example.com/feed.xml", "🔒"),
]
```

## Project Structure

| File | Purpose |
|------|---------|
| `main.py` | Entry point; handles bot initialization and scrape-send cycles |
| `sources.py` | Defines RSS feed sources (name, URL, emoji icon) |
| `scraper.py` | Fetches and parses RSS feeds using `feedparser` |
| `scoring.py` | Keyword-based scoring engine with regex rules |
| `formatter.py` | Formats article data into Telegram-friendly messages |
| `config.py` | Loads environment variables and configuration |
| `persistence.py` | Manages duplicate tracking via `sent_articles.json` |
| `.env` | Environment variables (user-created) |
| `sent_articles.json` | Tracks article IDs already sent (auto-managed) |

## Keyword Categories

### 🔐 Security Keywords
- Zero-day exploits, CVEs, ransomware, malware, data breaches
- Phishing, APT groups, backdoors, vulnerabilities, patches
- Firewalls, IDS/IPS, SIEM, EDR/XDR, encryption, TLS/SSL
- Authentication, authorization, IAM, intrusion detection
- Incident response, forensics, SOC, CSIRT

### 🔗 Supply Chain Keywords
- Dependencies, SBOM, npm, PyPI, Maven, NuGet, package managers
- Dependency confusion, typosquatting, package hijacking
- Notable incidents: Codecov, SolarWinds, Kaseya, Log4J
- Open-source security, code signing, build pipelines, CI/CD
- DevSecOps, container security, Docker, artifact scanning
- Third-party vendor risk, GitHub/GitLab security
- SLSA, in-toto, Sigstore, provenance, attestation

## Advanced Usage

### Adjusting Sensitivity

To be more selective, increase `MIN_SCORE`:
```env
MIN_SCORE=3  # Only high-relevance articles
```

To be more inclusive, decrease `MIN_SCORE`:
```env
MIN_SCORE=1  # Include lower-relevance matches
```

### Controlling Article Age

To catch more articles:
```env
MAX_AGE_HOURS=48  # Accept articles up to 2 days old
```

To be more timely:
```env
MAX_AGE_HOURS=12  # Only very recent articles
```

### Adjusting Recency Preference

Articles published very recently get a scoring boost within this window:
```env
RECENCY_HOURS=12  # Prefer articles from the last 12 hours
```

## Notes

- This project is designed to run as a scheduled job or cron task.
- Articles are stored locally in `sent_articles.json` to prevent duplicate Telegram posts.
- Each article is uniquely identified by the SHA256 hash of its URL.
- Failed feed fetches are logged but don't halt execution.
- Max article summary length is capped at 400 characters with HTML tags stripped.

## License

Add your preferred license here.
