"""
Fetches a "trending pulse" for Malaysia from two free sources:
  - Google Trends (MY) daily trending searches
  - Reddit r/malaysia "hot" posts (public RSS; Reddit blocks anon search/JSON
    but the hot RSS works)

No API keys needed.
"""

import feedparser

import config


def fetch_google_trends() -> list:
    """Top trending Google searches in Malaysia -> [{'term':..., 'link':...}]."""
    try:
        parsed = feedparser.parse(config.GOOGLE_TRENDS_MY_RSS)
    except Exception as e:  # noqa: BLE001
        print(f"  [warn] Google Trends parse failed: {e}")
        return []
    items = []
    for e in parsed.entries[:config.TRENDING_MAX_GOOGLE]:
        term = getattr(e, "title", "").strip()
        link = getattr(e, "link", "").strip()
        if term:
            items.append({"term": term, "link": link})
    print(f"[trending] Google Trends: {len(items)} term(s)")
    return items


def fetch_reddit_hot() -> list:
    """Hot posts from r/malaysia -> [{'title':..., 'link':...}]."""
    try:
        parsed = feedparser.parse(config.REDDIT_MALAYSIA_HOT_RSS)
    except Exception as e:  # noqa: BLE001
        print(f"  [warn] Reddit r/malaysia parse failed: {e}")
        return []
    items = []
    for e in parsed.entries[:config.TRENDING_MAX_REDDIT]:
        title = getattr(e, "title", "").strip()
        link = getattr(e, "link", "").strip()
        if title:
            items.append({"title": title, "link": link})
    print(f"[trending] Reddit r/malaysia: {len(items)} post(s)")
    return items
