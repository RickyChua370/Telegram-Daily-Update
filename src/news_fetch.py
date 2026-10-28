"""
Fetches news via RSS feeds:
  - Malaysian business & finance (The Edge, via Google News RSS scoping)
  - Global AI changes / "AI bubble" (Google News, Hacker News, TechCrunch)

RSS is clean, reliable, and free. Each item is reduced to title/link/summary.
Deduping across feeds is done by URL and by normalised title.
"""

import feedparser

import config


def _normalise_title(title: str) -> str:
    return " ".join((title or "").lower().split())


def _fetch_feed(url: str) -> list:
    items = []
    try:
        parsed = feedparser.parse(url)
    except Exception as e:  # feedparser is very tolerant, but be safe
        print(f"  [warn] failed to parse feed {url}: {e}")
        return items

    for entry in parsed.entries:
        title = getattr(entry, "title", "").strip()
        link = getattr(entry, "link", "").strip()
        summary = getattr(entry, "summary", "") or getattr(entry, "description", "")
        if title and link:
            items.append({
                "title": title,
                "link": link,
                "summary": summary.strip(),
            })
    return items


def _fetch_many(urls: list, limit_per_feed: int = 15) -> list:
    seen_urls = set()
    seen_titles = set()
    combined = []
    for url in urls:
        for item in _fetch_feed(url)[:limit_per_feed]:
            norm = _normalise_title(item["title"])
            if item["link"] in seen_urls or norm in seen_titles:
                continue
            seen_urls.add(item["link"])
            seen_titles.add(norm)
            combined.append(item)
    return combined


def fetch_my_business() -> list:
    """Malaysian business & finance news items (raw, pre-summary)."""
    items = _fetch_many(config.MY_BUSINESS_FEEDS)
    print(f"[news] MY business/finance: {len(items)} raw items")
    return items


def fetch_global_ai() -> list:
    """Global AI news items (raw, pre-summary)."""
    items = _fetch_many(config.GLOBAL_AI_FEEDS)
    print(f"[news] global AI: {len(items)} raw items")
    return items
