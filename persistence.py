"""
Persistence layer for tracking sent articles.
"""

import json
from config import SENT_DB_PATH


def load_sent() -> set:
    """Load the set of already-sent article IDs from disk."""
    if SENT_DB_PATH.exists():
        try:
            data = json.loads(SENT_DB_PATH.read_text())
            return set(data)
        except Exception:
            pass
    return set()


def save_sent(sent: set) -> None:
    """Save the set of sent article IDs to disk."""
    SENT_DB_PATH.write_text(json.dumps(list(sent), indent=2))
