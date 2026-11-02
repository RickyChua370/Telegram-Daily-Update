"""
Fetches recent uploads from the tracked YouTube channels (config.YOUTUBE_CHANNELS).

Primary method: the official YouTube Data API (set YOUTUBE_API_KEY). It's robust
and the free quota (10,000 units/day) is far more than enough for a few channels.

Fallback method: each channel's free public RSS feed
(https://www.youtube.com/feeds/videos.xml?channel_id=...), which needs no key.

Each returned item:
    {
      "handle": "...", "malaysian": bool,
      "title": "...", "link": "...",
      "published": datetime|None,
    }
"""

import os
import datetime
from datetime import timezone

import requests
import feedparser

import config

YT_API_PLAYLIST_ITEMS = "https://www.googleapis.com/youtube/v3/playlistItems"
YT_RSS = "https://www.youtube.com/feeds/videos.xml?channel_id={cid}"


def _uploads_playlist_id(channel_id: str) -> str:
    """The uploads playlist id is the channel id with 'UC' -> 'UU'."""
    if channel_id.startswith("UC"):
        return "UU" + channel_id[2:]
    return channel_id


def _cutoff():
    return datetime.datetime.now(timezone.utc) - datetime.timedelta(
        days=config.YOUTUBE_LOOKBACK_DAYS
    )


def _fetch_channel_api(channel, api_key: str) -> list:
    """Fetch recent uploads for one channel via the Data API."""
    params = {
        "key": api_key,
        "part": "snippet",
        "playlistId": _uploads_playlist_id(channel["channel_id"]),
        "maxResults": 10,
    }
    try:
        resp = requests.get(YT_API_PLAYLIST_ITEMS, params=params, timeout=30)
    except requests.RequestException as e:
        print(f"  [warn] YT API request failed for @{channel['handle']}: {e}")
        return []
    if not resp.ok:
        print(f"  [warn] YT API {resp.status_code} for @{channel['handle']}: "
              f"{resp.text[:160]}")
        return []

    cutoff = _cutoff()
    items = []
    for it in resp.json().get("items", []):
        sn = it.get("snippet", {})
        vid = sn.get("resourceId", {}).get("videoId")
        title = (sn.get("title") or "").strip()
        published_raw = sn.get("publishedAt")
        if not vid or not title:
            continue
        published = None
        if published_raw:
            try:
                published = datetime.datetime.fromisoformat(
                    published_raw.replace("Z", "+00:00"))
            except ValueError:
                published = None
        if published and published < cutoff:
            continue
        items.append({
            "handle": channel["handle"],
            "malaysian": channel["malaysian"],
            "title": title,
            "link": f"https://www.youtube.com/watch?v={vid}",
            "published": published,
        })
    return items[:config.YOUTUBE_MAX_PER_CHANNEL]


def _fetch_channel_rss(channel) -> list:
    """Fetch recent uploads for one channel via its public RSS feed (no key)."""
    url = YT_RSS.format(cid=channel["channel_id"])
    try:
        parsed = feedparser.parse(url)
    except Exception as e:  # noqa: BLE001
        print(f"  [warn] YT RSS parse failed for @{channel['handle']}: {e}")
        return []

    cutoff = _cutoff()
    items = []
    for e in parsed.entries:
        title = getattr(e, "title", "").strip()
        link = getattr(e, "link", "").strip()
        published = None
        if getattr(e, "published_parsed", None):
            published = datetime.datetime(*e.published_parsed[:6], tzinfo=timezone.utc)
        if not title or not link:
            continue
        if published and published < cutoff:
            continue
        items.append({
            "handle": channel["handle"],
            "malaysian": channel["malaysian"],
            "title": title,
            "link": link,
            "published": published,
        })
    return items[:config.YOUTUBE_MAX_PER_CHANNEL]


def fetch_recent_uploads() -> list:
    """
    Recent uploads across all tracked channels. Uses the Data API if
    YOUTUBE_API_KEY is set, else falls back to public RSS feeds.
    """
    channels = getattr(config, "YOUTUBE_CHANNELS", [])
    if not channels:
        return []

    api_key = os.environ.get("YOUTUBE_API_KEY")
    mode = "Data API" if api_key else "RSS (no key)"
    print(f"[yt] fetching {len(channels)} channel(s) via {mode}")

    all_items = []
    for ch in channels:
        items = (_fetch_channel_api(ch, api_key) if api_key
                 else _fetch_channel_rss(ch))
        all_items.extend(items)

    print(f"[yt] found {len(all_items)} recent upload(s) "
          f"(last {config.YOUTUBE_LOOKBACK_DAYS} days)")
    return all_items
