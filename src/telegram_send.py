"""
Sends the daily digest to your phone via the Telegram Bot API.

Telegram messages are capped at 4096 characters, so we split long digests
into multiple messages automatically. We use HTML parse mode for light
formatting (bold headers, clickable links).
"""

import os
import time
import html
import requests

TELEGRAM_API = "https://api.telegram.org/bot{token}/sendMessage"
MAX_LEN = 4000  # a little under Telegram's 4096 hard limit, for safety


def _get_credentials():
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        raise RuntimeError(
            "Missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID. "
            "Set them in your environment / GitHub Actions secrets."
        )
    return token, chat_id


def _recipient_ids() -> list:
    """
    TELEGRAM_CHAT_ID may be a single id or a comma-separated list, so the same
    bot can deliver to several people (e.g. you + a friend). Whitespace and
    empty entries are ignored.
    """
    _, raw = _get_credentials()
    return [cid.strip() for cid in raw.split(",") if cid.strip()]


def escape(text: str) -> str:
    """Escape text for Telegram HTML parse mode."""
    return html.escape(text or "")


def _split_into_chunks(text: str) -> list:
    """Split a long message on line boundaries so we never cut mid-line."""
    if len(text) <= MAX_LEN:
        return [text]
    chunks, current = [], ""
    for line in text.split("\n"):
        # If a single line is somehow too long, hard-split it.
        while len(line) > MAX_LEN:
            chunks.append(line[:MAX_LEN])
            line = line[MAX_LEN:]
        if len(current) + len(line) + 1 > MAX_LEN:
            chunks.append(current)
            current = line
        else:
            current = f"{current}\n{line}" if current else line
    if current:
        chunks.append(current)
    return chunks


def send_message(text: str) -> None:
    """
    Send one logical message to EVERY configured recipient, splitting into
    multiple chunks if needed.

    Delivery to each recipient is independent: if sending to one person fails
    (e.g. they haven't started the bot yet), we log it and still deliver to the
    others. Raises only if delivery failed for ALL recipients.
    """
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise RuntimeError("Missing TELEGRAM_BOT_TOKEN.")
    url = TELEGRAM_API.format(token=token)

    recipients = _recipient_ids()
    chunks = _split_into_chunks(text)
    any_success = False
    errors = []

    for chat_id in recipients:
        try:
            for chunk in chunks:
                resp = requests.post(
                    url,
                    data={
                        "chat_id": chat_id,
                        "text": chunk,
                        "parse_mode": "HTML",
                        "disable_web_page_preview": "true",
                    },
                    timeout=30,
                )
                if not resp.ok:
                    raise RuntimeError(f"{resp.status_code}: {resp.text}")
                time.sleep(0.4)  # gentle with rate limits
            any_success = True
        except Exception as e:  # noqa: BLE001
            # Don't let one bad recipient block the rest.
            print(f"  [warn] Telegram send to {chat_id} failed: {e}")
            errors.append((chat_id, str(e)))

    if not any_success:
        raise RuntimeError(
            f"Telegram send failed for all recipients: {errors}"
        )
