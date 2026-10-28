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

import config

GOOGLE_CSE_ENDPOINT = "https://www.googleapis.com/customsearch/v1"


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
        # Bias toward recent results and Malaysia.
        "gl": "my",
        "dateRestrict": "m3",  # last 3 months
    }
    try:
        resp = requests.get(GOOGLE_CSE_ENDPOINT, params=params, timeout=30)
    except requests.RequestException as e:
        print(f"  [warn] search request failed for {query!r}: {e}")
        return []

    if resp.status_code == 429:
        print("  [info] Google search daily free quota reached; stopping early.")
        raise StopIteration  # signal to caller to stop making more calls
    if not resp.ok:
        print(f"  [warn] search returned {resp.status_code} for {query!r}: {resp.text[:200]}")
        return []

    data = resp.json()
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

    print(f"[jobs] used {budget.used} searches, "
          f"found {len(combined)} unique raw results")
    return list(combined.values())
