"""
Telegram message formatting for articles.
"""


def format_message(article: dict) -> str:
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
