"""
Finds Malaysian graduate programmes via Google Programmable Search.

SAFETY: Google's free tier is 100 queries/day and then simply STOPS returning
results (it does NOT bill you). We additionally enforce a hard cap of
MAX_GOOGLE_SEARCHES_PER_DAY (default 90) in code, so there is zero possibility
of ever exceeding the free quota or touching a paid tier.

Each search returns title + snippet + link. The raw results are intentionally
noisy; the llm_filter module cleans/dedupes them into real, currently-open
Malaysian graduate programmes afterwards.
"""

import os
import datetime
import requests
import feedparser

import config

try:
    from googlenewsdecoder import gnewsdecoder
    _HAS_DECODER = True
except ImportError:
    _HAS_DECODER = False

GOOGLE_CSE_ENDPOINT = "https://www.googleapis.com/customsearch/v1"


def resolve_link(link: str) -> str:
    """
    Google News RSS links are encoded redirect URLs (news.google.com/rss/
    articles/CBMi...) that sometimes show an "invalid web address" notice when
    opened. Decode them to the real publisher URL.

    - Non-Google-News links are returned unchanged.
    - If decoding fails for any reason, we return the original link (so a job
      is never dropped just because its link couldn't be resolved).
    """
    if not link or "news.google.com" not in link:
        return link
    if not _HAS_DECODER:
        return link
    try:
        # interval adds a small delay between Google requests to avoid 429s.
        res = gnewsdecoder(link, interval=1)
        if res and res.get("decoded_url"):
            return res["decoded_url"]
    except Exception as e:  # noqa: BLE001
        print(f"  [warn] link decode failed ({e}); keeping original link")
    return link


def resolve_job_links(jobs: list) -> list:
    """
    Resolve Google News redirect links to real URLs for a list of job dicts
    (each having a 'link' key). Call this AFTER filtering so we only decode the
    handful of jobs that will actually be shown — keeping it fast and avoiding
    rate limits.
    """
    resolved = 0
    for job in jobs:
        original = job.get("link", "")
        real = resolve_link(original)
        if real != original:
            job["link"] = real
            resolved += 1
    if jobs:
        print(f"[jobs] resolved {resolved}/{len(jobs)} redirect link(s) to real URLs")
    return jobs


class SearchBudget:
    """Enforces the per-run hard cap on Google searches."""

    def __init__(self, limit: int):
        self.limit = limit
        self.used = 0

    def can_search(self) -> bool:
        return self.used < self.limit

    def record(self) -> None:
        self.used += 1


def _build_queries() -> list:
    """Construct the full list of search query strings."""
    year = datetime.date.today().year
    queries = [q.format(year=year) for q in config.JOB_SEARCH_QUERIES]

    if config.ENABLE_COMPANY_SPECIFIC_QUERIES:
        # Batch companies a few at a time with OR to conserve the search budget.
        companies = config.TARGET_COMPANIES
        batch_size = 4
        for i in range(0, len(companies), batch_size):
            batch = companies[i:i + batch_size]
            or_clause = " OR ".join(f'"{c}"' for c in batch)
            queries.append(f"({or_clause}) graduate programme Malaysia {year}")

    return queries


def _run_single_search(query: str, api_key: str, cx: str) -> list:
    """Run one Google CSE query, returning a list of result dicts."""
    params = {
        "key": api_key,
        "cx": cx,
        "q": query,
        "num": config.RESULTS_PER_SEARCH,
        # Bias toward Malaysia.
        "gl": "my",
    }
    # Optional recency filter (many grad pages are older but still open, so this
    # is off by default — set JOB_DATE_RESTRICT in config to re-enable).
    if getattr(config, "JOB_DATE_RESTRICT", None):
        params["dateRestrict"] = config.JOB_DATE_RESTRICT
    try:
        resp = requests.get(GOOGLE_CSE_ENDPOINT, params=params, timeout=30)
    except requests.RequestException as e:
        print(f"  [warn] search request failed for {query!r}: {e}")
        return []

    if resp.status_code == 429:
        print("  [info] Google search daily free quota reached; stopping early.")
        raise StopIteration  # signal to caller to stop making more calls
    if resp.status_code == 403:
        # Config problem (API not enabled / key-project mismatch). No point
        # hammering the same error 20x — surface it clearly and stop.
        print("  [error] Google search 403 — Custom Search JSON API is not "
              "enabled for this key's project, or the key/engine is misconfigured. "
              "Skipping Google job search (RSS jobs still used).")
        raise StopIteration
    if not resp.ok:
        print(f"  [warn] search returned {resp.status_code} for {query!r}: {resp.text[:200]}")
        return []

    data = resp.json()
    # Diagnostic: Google reports total matches even when it returns few items.
    total = data.get("searchInformation", {}).get("totalResults", "0")
    n_items = len(data.get("items", []))
    print(f"  [search] {query!r} -> total={total}, returned={n_items}")
    results = []
    for item in data.get("items", []):
        results.append({
            "title": item.get("title", "").strip(),
            "link": item.get("link", "").strip(),
            "snippet": item.get("snippet", "").strip(),
            "source_query": query,
        })
    return results


def search_jobs() -> list:
    """
    Run the capped batch of searches and return a combined, URL-deduped list
    of raw result dicts. Returns [] (gracefully) if keys are missing.
    """
    api_key = os.environ.get("GOOGLE_SEARCH_API_KEY")
    cx = os.environ.get("GOOGLE_SEARCH_ENGINE_ID")
    if not api_key or not cx:
        print("[info] Google Search keys not set; skipping job search.")
        return []

    budget = SearchBudget(config.MAX_GOOGLE_SEARCHES_PER_DAY)
    queries = _build_queries()
    print(f"[jobs] running up to {min(len(queries), budget.limit)} searches "
          f"(hard cap {budget.limit}/day)")

    combined = {}
    for query in queries:
        if not budget.can_search():
            print(f"[jobs] hit safety cap of {budget.limit} searches; stopping.")
            break
        budget.record()
        try:
            results = _run_single_search(query, api_key, cx)
        except StopIteration:
            break
        for r in results:
            if r["link"]:
                combined[r["link"]] = r  # dedupe by URL

    print(f"[jobs] Google search used {budget.used} searches, "
          f"found {len(combined)} unique result(s)")
    return list(combined.values())


def search_jobs_rss() -> list:
    """
    Free, no-API-key job source via Google News RSS. Returns the same dict
    shape as the Google search results so the two can be merged seamlessly.

    Each feed contributes only its top-N most recent items (JOB_RSS_PER_FEED)
    so one high-volume feed can't flood the batch, and the total stays small
    enough for the LLM filter to process cheaply.
    """
    per_feed = getattr(config, "JOB_RSS_PER_FEED", 15)
    combined = {}
    for url in config.JOB_RSS_FEEDS:
        try:
            parsed = feedparser.parse(url)
        except Exception as e:
            print(f"  [warn] job RSS parse failed for {url}: {e}")
            continue
        for entry in parsed.entries[:per_feed]:
            link = getattr(entry, "link", "").strip()
            title = getattr(entry, "title", "").strip()
            summary = getattr(entry, "summary", "") or getattr(entry, "description", "")
            if link and title:
                combined[link] = {
                    "title": title,
                    "link": link,
                    "snippet": summary.strip()[:300],
                    "source_query": "rss",
                }
    print(f"[jobs] RSS found {len(combined)} result(s) "
          f"(<= {per_feed}/feed from {len(config.JOB_RSS_FEEDS)} feeds)")
    return list(combined.values())


def gather_jobs() -> list:
    """
    Combine Programmable Search results with the free RSS safety net,
    deduped by URL. This is what main.py calls.
    """
    merged = {}
    for r in search_jobs() + search_jobs_rss():
        if r.get("link"):
            merged[r["link"]] = r
    print(f"[jobs] combined total: {len(merged)} unique raw result(s)")
    return list(merged.values())
