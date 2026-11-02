"""
Light-weight Bursa Malaysia stock lookup via Yahoo Finance's public chart
endpoint (no API key). Used to attach price/change to the daily business story
when the company is listed.

This is informational only — NOT financial advice.
"""

import requests

import config

YF_CHART = "https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
_HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}


def ticker_for(company_name: str) -> str | None:
    """Best-effort map a company name to a Bursa ticker (substring match)."""
    if not company_name:
        return None
    name = company_name.lower()
    # Longest key first so "genting malaysia" beats "genting".
    for key in sorted(config.BURSA_TICKERS, key=len, reverse=True):
        if key in name:
            return config.BURSA_TICKERS[key]
    return None


def quote(ticker: str) -> dict | None:
    """
    Return {price, currency, change, change_pct} for a ticker, or None.
    """
    if not ticker:
        return None
    try:
        resp = requests.get(
            YF_CHART.format(ticker=ticker), headers=_HEADERS, timeout=20
        )
        if not resp.ok:
            return None
        meta = resp.json()["chart"]["result"][0]["meta"]
    except (requests.RequestException, KeyError, IndexError, ValueError, TypeError):
        return None

    price = meta.get("regularMarketPrice")
    prev = meta.get("chartPreviousClose") or meta.get("previousClose")
    if price is None:
        return None

    change = change_pct = None
    if prev:
        change = price - prev
        change_pct = (change / prev) * 100 if prev else None

    return {
        "price": price,
        "currency": meta.get("currency", "MYR"),
        "change": change,
        "change_pct": change_pct,
    }


def format_quote(company_name: str) -> str:
    """
    Return a short one-line stock summary for the company, or "" if it's not a
    recognised listed company. Always flagged as not financial advice upstream.
    """
    ticker = ticker_for(company_name)
    if not ticker:
        return ""
    q = quote(ticker)
    if not q:
        return ""
    arrow = "▲" if (q["change"] or 0) >= 0 else "▼"
    pct = f"{q['change_pct']:+.2f}%" if q["change_pct"] is not None else ""
    return (f"{q['currency']} {q['price']:.2f} {arrow} {pct} "
            f"(Bursa: {ticker.replace('.KL', '')})")
