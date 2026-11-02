"""
Telegram Daily Update — entry point.

Run order each morning:
  1. Search Google for Malaysian MNC graduate programmes (hard-capped at 90/day).
  2. Filter/dedupe those into a clean list via Gemini (free tier).
  3. Fetch MY business/finance news (The Edge) + global AI news via RSS.
  4. Summarise news in layman's terms via Gemini.
  5. Drop anything already sent on a previous day ("seen" memory).
  6. Format a single digest and send it to Telegram.
  7. Record what we sent so tomorrow only shows new items.

Everything degrades gracefully: missing keys = that section is skipped or sent
raw, rather than the whole run failing.
"""

import datetime
import traceback

from dotenv import load_dotenv

import config
from src import (jobs_search, news_fetch, llm_filter, seen_store,
                telegram_send, youtube_fetch, stocks, trending_fetch)

load_dotenv()  # load .env for local runs; harmless in GitHub Actions


def _job_key(job: dict) -> str:
    return job.get("link", "")


def _news_key(item: dict) -> str:
    return item.get("link", "")


def _video_key(v: dict) -> str:
    return v.get("link", "")


def build_jobs_section() -> tuple:
    """Return (section_text, new_jobs_list)."""
    raw = jobs_search.gather_jobs()
    cleaned = llm_filter.filter_jobs(raw)
    # Resolve Google News redirect links to real publisher URLs BEFORE the
    # "seen" dedup, so dedup keys are the stable real URLs (and the links we
    # show actually work). We only decode the filtered handful, so it's fast.
    cleaned = jobs_search.resolve_job_links(cleaned)
    new_jobs = seen_store.filter_new(cleaned, _job_key)

    if not new_jobs:
        return ("📋 <b>Graduate Programmes (Malaysia, big MNCs)</b>\n"
                "No new openings found today.\n", [])

    lines = ["📋 <b>Graduate Programmes (Malaysia, big MNCs)</b>"]
    for job in new_jobs:
        company = telegram_send.escape(job["company"])
        title = telegram_send.escape(job["title"]) or "Graduate programme"
        note = telegram_send.escape(job["note"])
        label = f"<b>{company}</b> — {title}" if company else f"<b>{title}</b>"
        lines.append(f"• {label}")
        if note:
            lines.append(f"  <i>{note}</i>")
        lines.append(f"  <a href=\"{job['link']}\">Apply / details</a>")
    lines.append("")
    return ("\n".join(lines), new_jobs)


def build_news_section(title: str, emoji: str, items: list) -> tuple:
    """Return (section_text, new_items_list)."""
    new_items = seen_store.filter_new(items, _news_key)
    if not new_items:
        return (f"{emoji} <b>{title}</b>\nNothing new today.\n", [])

    lines = [f"{emoji} <b>{title}</b>"]
    for it in new_items:
        headline = telegram_send.escape(it["headline"])
        summary = telegram_send.escape(it["summary"])
        lines.append(f"• <a href=\"{it['link']}\">{headline}</a>")
        if summary:
            lines.append(f"  {summary}")
    lines.append("")
    return ("\n".join(lines), new_items)


def build_youtube_section() -> tuple:
    """
    New uploads from tracked creators, each with a Malaysian content-idea.
    Returns (section_text, new_videos_list).
    """
    raw = youtube_fetch.fetch_recent_uploads()
    new_videos = seen_store.filter_new(raw, _video_key)
    if not new_videos:
        return ("📺 <b>Creator Watch — Content Ideas</b>\n"
                "No new uploads from your tracked channels today.\n", [])

    enriched = llm_filter.enrich_youtube(new_videos)

    lines = ["📺 <b>Creator Watch — Content Ideas</b>"]
    for v in enriched:
        handle = telegram_send.escape("@" + v["handle"])
        title = telegram_send.escape(v["title"])
        idea = telegram_send.escape(v.get("idea", ""))
        lines.append(f"• <b>{handle}</b>: <a href=\"{v['link']}\">{title}</a>")
        if idea:
            lines.append(f"  💡 <i>{idea}</i>")
    lines.append("")
    return ("\n".join(lines), enriched)


def build_business_story_section() -> str:
    """Daily Malaysian company story + (if listed) stock data + Reddit chatter."""
    candidates = news_fetch.fetch_business_story_candidates()
    story = llm_filter.business_story(candidates)
    if not story or not story.get("story"):
        return ("📖 <b>Malaysia Business Story of the Day</b>\n"
                "No story today (couldn't generate one).\n")

    company = story["company"]
    headline = telegram_send.escape(story["headline"] or company or "Business Story")
    body = telegram_send.escape(story["story"])

    lines = ["📖 <b>Malaysia Business Story of the Day</b>", f"<b>{headline}</b>", body]

    # Stock data (listed companies only) — explicitly not financial advice.
    stock_line = stocks.format_quote(company)
    if stock_line:
        lines.append(f"📈 {telegram_send.escape(stock_line)}")
        lines.append("<i>Market data for info only — not financial advice.</i>")

    # Reddit discussion links about the company.
    reddit = news_fetch.fetch_reddit_links(company, config.BUSINESS_STORY_REDDIT_LINKS)
    if reddit:
        lines.append("💬 <b>What people are saying:</b>")
        for r in reddit:
            lines.append(f"• <a href=\"{r['link']}\">{telegram_send.escape(r['title'])}</a>")

    if story.get("link"):
        lines.append(f"🔗 <a href=\"{story['link']}\">Source</a>")

    lines.append("")
    return "\n".join(lines)


def build_trending_section() -> str:
    """Trending pulse: Google Trends (MY) + Reddit r/malaysia hot posts."""
    gtrends = trending_fetch.fetch_google_trends()
    reddit = trending_fetch.fetch_reddit_hot()

    if not gtrends and not reddit:
        return ("🔥 <b>Trending in Malaysia</b>\nNothing to show today.\n")

    lines = ["🔥 <b>Trending in Malaysia</b>"]
    if gtrends:
        lines.append("🔎 <b>Google searches spiking:</b>")
        terms = ", ".join(telegram_send.escape(t["term"]) for t in gtrends)
        lines.append(terms)
    if reddit:
        lines.append("👥 <b>Hot on r/malaysia:</b>")
        for p in reddit:
            lines.append(f"• <a href=\"{p['link']}\">{telegram_send.escape(p['title'])}</a>")
    lines.append("")
    return "\n".join(lines)


def _send_section(body: str) -> bool:
    """Send one section as its own Telegram message. Returns True on success."""
    today = datetime.date.today().strftime("%A, %d %B %Y")
    header = (f"🗞️ <b>Your Daily Update</b> · {today}\n"
              f"{config.TIMEZONE_LABEL}\n"
              f"{'─' * 20}\n")
    try:
        telegram_send.send_message(header + body.strip())
        return True
    except Exception:
        print("[error] sending section failed:\n" + traceback.format_exc())
        return False


def main() -> None:
    # Each section is sent as its OWN Telegram message so jobs, Malaysian news,
    # and Global AI are visually separate and easy to scroll. We only record an
    # item as "seen" after its message was sent successfully.
    all_new_for_memory = []

    # --- 1) Jobs ---
    try:
        jobs_text, new_jobs = build_jobs_section()
    except Exception:
        print("[error] jobs section failed:\n" + traceback.format_exc())
        jobs_text, new_jobs = (
            "📋 <b>Graduate Programmes</b>\n(error fetching — see logs)\n", [])
    if _send_section(jobs_text):
        all_new_for_memory.append((new_jobs, _job_key))

    # --- 2) Malaysia Business & Finance ---
    try:
        raw_my = news_fetch.fetch_my_business()
        summarised_my = llm_filter.summarise_news(raw_my, "Malaysian business & finance")
        my_text, new_my = build_news_section(
            "Malaysia Business & Finance", "💰", summarised_my)
    except Exception:
        print("[error] MY news section failed:\n" + traceback.format_exc())
        my_text, new_my = (
            "💰 <b>Malaysia Business & Finance</b>\n(error fetching — see logs)\n", [])
    if _send_section(my_text):
        all_new_for_memory.append((new_my, _news_key))

    # --- 3) Global AI Watch ---
    try:
        raw_ai = news_fetch.fetch_global_ai()
        summarised_ai = llm_filter.summarise_news(raw_ai, "global AI")
        ai_text, new_ai = build_news_section(
            "Global AI Watch", "🤖", summarised_ai)
    except Exception:
        print("[error] AI news section failed:\n" + traceback.format_exc())
        ai_text, new_ai = (
            "🤖 <b>Global AI Watch</b>\n(error fetching — see logs)\n", [])
    if _send_section(ai_text):
        all_new_for_memory.append((new_ai, _news_key))

    # --- 4) Malaysia Business Story of the Day ---
    try:
        story_text = build_business_story_section()
    except Exception:
        print("[error] business story section failed:\n" + traceback.format_exc())
        story_text = ("📖 <b>Malaysia Business Story of the Day</b>\n"
                      "(error fetching — see logs)\n")
    _send_section(story_text)

    # --- 5) Trending in Malaysia ---
    try:
        trending_text = build_trending_section()
    except Exception:
        print("[error] trending section failed:\n" + traceback.format_exc())
        trending_text = "🔥 <b>Trending in Malaysia</b>\n(error fetching — see logs)\n"
    _send_section(trending_text)

    # --- 6) Creator Watch (YouTube content ideas) ---
    try:
        yt_text, new_videos = build_youtube_section()
    except Exception:
        print("[error] YouTube section failed:\n" + traceback.format_exc())
        yt_text, new_videos = (
            "📺 <b>Creator Watch — Content Ideas</b>\n(error fetching — see logs)\n", [])
    if _send_section(yt_text):
        all_new_for_memory.append((new_videos, _video_key))

    print("[done] digest messages sent.")

    # --- Remember what we sent (only for sections that sent successfully) ---
    for items, key_fn in all_new_for_memory:
        if items:
            seen_store.mark_seen(items, key_fn)
    print("[done] seen-store updated.")


if __name__ == "__main__":
    main()
