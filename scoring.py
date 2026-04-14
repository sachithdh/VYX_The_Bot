"""
Article scoring logic based on keywords and relevance.
"""

import re
from datetime import datetime, timezone, timedelta

from config import RECENCY_HOURS, MAX_AGE_HOURS


# Each entry: (compiled_regex, score_points, category_tag)
_KEYWORD_RULES: list[tuple[re.Pattern, int, str]] = []


def _build_rules() -> None:
    """Compile keyword rules once at startup."""
    raw = [
        # High-value cybersecurity terms
        (r"\b(zero[- ]?day|0day|cve-\d{4})\b",                    4, "🔐 Security"),
        (r"\b(ransomware|malware|exploit|vulnerability|patch)\b",  3, "🔐 Security"),
        (r"\b(data breach|phishing|apt|threat actor|backdoor)\b",  3, "🔐 Security"),
        (r"\b(cybersecurity|infosec|pentest|red team|ctf)\b",      2, "🔐 Security"),
        (r"\b(supply[- ]chain attack|rce|lpe|privilege escalation)\b", 4, "🔐 Security"),
        (r"\b(firewall|ids|ips|siem|soar|endpoint|edr|xdr)\b",     2, "🔐 Security"),
        (r"\b(encryption|cryptography|tls|ssl|pki|certificate)\b", 2, "🔐 Security"),
        (r"\b(botnet|ddos|c2|command.and.control|stealer)\b",      3, "🔐 Security"),
        (r"\b(authentication|authorization|access.control|iam)\b", 2, "🔐 Security"),
        (r"\b(intrusion|incident.response|forensic|soc|csirt)\b",  2, "🔐 Security"),

        # Software supply chain security
        (r"\b(supply[- ]?chain|software supply chain|dependency)\b", 4, "🔗 Supply Chain"),
        (r"\b(sbom|software bill of materials|dependency tree)\b",   4, "🔗 Supply Chain"),
        (r"\b(npm|pypi|rubygems|maven|nuget|package.manager)\b",     3, "🔗 Supply Chain"),
        (r"\b(dependency.confusion|typosquatting|package.hijack)\b", 4, "🔗 Supply Chain"),
        (r"\b(left[- ]?pad|event[- ]?stream|colors\.js|ua-parser)\b", 3, "🔗 Supply Chain"),
        (r"\b(codecov|solarwinds|kaseya|log4j|log4shell)\b",         4, "🔗 Supply Chain"),
        (r"\b(open[- ]?source.security|oss|maintainer|contributor)\b", 2, "🔗 Supply Chain"),
        (r"\b(code.sign|signature.verif|integrity.check|checksum)\b", 3, "🔗 Supply Chain"),
        (r"\b(build.pipeline|ci[/]cd|devops.security|devsecops)\b",  3, "🔗 Supply Chain"),
        (r"\b(container.security|docker|image.scanning|artifact)\b",  2, "🔗 Supply Chain"),
        (r"\b(github.security|gitlab|repository.security|source.code)\b", 2, "🔗 Supply Chain"),
        (r"\b(third[- ]?party|vendor.risk|upstream|downstream)\b",    2, "🔗 Supply Chain"),
        (r"\b(malicious.package|backdoor.package|trojan.package)\b",  4, "🔗 Supply Chain"),
        (r"\b(npm.audit|pip.audit|dependency.check|snyk|sonatype)\b", 2, "🔗 Supply Chain"),
        (r"\b(slsa|in[- ]?toto|sigstore|provenance|attestation)\b",   3, "🔗 Supply Chain"),
        (r"\b(secure[- ]?software|ssdf|nist|cisa|critical.software)\b", 2, "🔗 Supply Chain"),
        (r"\b(license.compliance|license.risk|gpl|copyleft)\b",       1, "🔗 Supply Chain"),
    ]
    for pattern, score, category in raw:
        _KEYWORD_RULES.append((re.compile(pattern, re.IGNORECASE), score, category))


def score_article(title: str, summary: str) -> tuple[int, str]:
    """
    Score an article's relevance to cybersecurity and software supply chain topics.
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

    dominant = max(category_scores, key=category_scores.get) if category_scores else "🔐 Security"
    return int(round(total)), dominant


def recency_bonus(published_str: str) -> int:
    """
    Return +2 if the article was published within RECENCY_HOURS,
    +1 if within 2xRECENCY_HOURS, else 0.
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


def is_within_age_limit(published_str: str) -> bool:
    """
    Return True if article is within MAX_AGE_HOURS, False otherwise.
    Articles with no publish date are considered valid (True).
    """
    if not published_str:
        return True  # Allow articles without dates
    try:
        from email.utils import parsedate_to_datetime
        pub = parsedate_to_datetime(published_str)
        if pub.tzinfo is None:
            pub = pub.replace(tzinfo=timezone.utc)
        age = datetime.now(timezone.utc) - pub
        return age <= timedelta(hours=MAX_AGE_HOURS)
    except Exception:
        return True  # If we can't parse date, don't filter it out


# Build rules on module import
_build_rules()
