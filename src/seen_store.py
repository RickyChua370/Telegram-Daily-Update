"""
Tracks items we've already sent so you only ever get *new* things.

State is stored in a small JSON file (seen.json). In GitHub Actions we persist
this across runs using the actions/cache mechanism (see the workflow), so the
bot "remembers" yesterday's items.

We store a set of stable keys (URLs / normalised identifiers) plus the date
they were first seen, and prune anything older than RETENTION_DAYS so the file
doesn't grow forever.
"""

import json
import os
from datetime import datetime, timedelta, timezone

SEEN_PATH = os.environ.get("SEEN_PATH", "seen.json")
RETENTION_DAYS = 30


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def load_seen() -> dict:
    """Return the seen-store as {key: 'YYYY-MM-DD'}. Empty dict if none/invalid."""
    if not os.path.exists(SEEN_PATH):
        return {}
    try:
        with open(SEEN_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return data
    except (json.JSONDecodeError, OSError):
        pass
    return {}


def _prune(seen: dict) -> dict:
    cutoff = datetime.now(timezone.utc) - timedelta(days=RETENTION_DAYS)
    kept = {}
    for key, date_str in seen.items():
        try:
            seen_date = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            if seen_date >= cutoff:
                kept[key] = date_str
        except (ValueError, TypeError):
            # Keep anything we can't parse rather than silently dropping it.
            kept[key] = _today()
    return kept


def filter_new(items: list, key_fn) -> list:
    """
    Given a list of items and a function that returns a stable key for each,
    return only the items we have NOT seen before. Does not mutate the store.
    """
    seen = load_seen()
    fresh = []
    for item in items:
        key = key_fn(item)
        if key and key not in seen:
            fresh.append(item)
    return fresh


def mark_seen(items: list, key_fn) -> None:
    """Record items as seen (with today's date) and persist + prune."""
    seen = load_seen()
    today = _today()
    for item in items:
        key = key_fn(item)
        if key:
            seen.setdefault(key, today)
    seen = _prune(seen)
    with open(SEEN_PATH, "w", encoding="utf-8") as f:
        json.dump(seen, f, ensure_ascii=False, indent=0)
