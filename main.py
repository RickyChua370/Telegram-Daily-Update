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
from src import jobs_search, news_fetch, llm_filter, seen_store, telegram_send

load_dotenv()  # load .env for local runs; harmless in GitHub Actions


def _job_key(job: dict) -> str:
    return job.get("link", "")


def _news_key(item: dict) -> str:
    return item.get("link", "")


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

    print("[done] digest messages sent.")

    # --- Remember what we sent (only for sections that sent successfully) ---
    for items, key_fn in all_new_for_memory:
        if items:
            seen_store.mark_seen(items, key_fn)
    print("[done] seen-store updated.")


if __name__ == "__main__":
    main()
