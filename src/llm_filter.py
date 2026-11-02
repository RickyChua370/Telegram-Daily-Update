"""
Uses Google Gemini (free tier) to:
  1. Filter + dedupe raw job search results into genuine, currently-open
     Malaysian graduate programmes, prioritising big MNC employers.
  2. Summarise news headlines in plain, layman's-terms English.

If GEMINI_API_KEY is not set, every function falls back gracefully to a
non-AI path (lightly-cleaned raw data) so the bot still works.
"""

import json
import os
import time

import config

try:
    from google import genai
    from google.genai import types as genai_types
    _HAS_GENAI = True
except ImportError:
    _HAS_GENAI = False

# Per-request timeout (ms) so a stalled call can't hang the whole run.
_REQUEST_TIMEOUT_MS = 60_000
# Retry transient errors (e.g. 503 "high demand") a few times with backoff.
_MAX_RETRIES = 3
_RETRY_BACKOFF_SECONDS = 5


def _get_client():
    """Return a configured Gemini client, or None if unavailable."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key or not _HAS_GENAI:
        return None
    return genai.Client(
        api_key=api_key,
        http_options=genai_types.HttpOptions(timeout=_REQUEST_TIMEOUT_MS),
    )


def _model_candidates() -> list:
    """Preferred model first, then any configured fallbacks (deduped)."""
    candidates = [config.GEMINI_MODEL]
    for m in getattr(config, "GEMINI_MODEL_FALLBACKS", []):
        if m not in candidates:
            candidates.append(m)
    return candidates


def _generate(client, prompt: str) -> str:
    """
    Call Gemini and return the response text.

    - If a model is unavailable (404 / not found / no access), try the next
      model in the fallback chain.
    - Retry transient failures (503/overloaded/timeout/429) with backoff.
    - Raises on final failure so callers can fall back to raw output.
    """
    last_err = None
    for model in _model_candidates():
        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                resp = client.models.generate_content(model=model, contents=prompt)
                if model != config.GEMINI_MODEL:
                    print(f"  [llm] using fallback model: {model}")
                return resp.text or ""
            except Exception as e:  # noqa: BLE001 - we inspect the message below
                last_err = e
                msg = str(e).lower()
                unavailable = any(
                    tok in msg
                    for tok in ("404", "not found", "not available",
                                "does not have access", "unsupported")
                )
                transient = any(
                    tok in msg
                    for tok in ("503", "unavailable", "high demand",
                                "overloaded", "timeout", "deadline", "429")
                )
                if unavailable:
                    print(f"  [llm] model {model} unavailable; trying next...")
                    break  # move to next model in the chain
                if transient and attempt < _MAX_RETRIES:
                    wait = _RETRY_BACKOFF_SECONDS * attempt
                    print(f"  [llm] transient error on {model} "
                          f"(attempt {attempt}/{_MAX_RETRIES}), retrying in {wait}s...")
                    time.sleep(wait)
                    continue
                break  # non-transient, non-404 -> try next model (or give up)
    raise last_err


def _extract_json(text: str):
    """Pull a JSON array/object out of an LLM response, tolerating code fences."""
    text = text.strip()
    if text.startswith("```"):
        # strip ```json ... ``` fences
        text = text.split("```", 2)
        text = text[1] if len(text) > 1 else text[0]
        if text.lstrip().lower().startswith("json"):
            text = text.lstrip()[4:]
    text = text.strip().strip("`").strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Try to locate the first [...] block
        start = text.find("[")
        end = text.rfind("]")
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(text[start:end + 1])
            except json.JSONDecodeError:
                return None
    return None


# ---------------------------------------------------------------------------
# Jobs
# ---------------------------------------------------------------------------
def filter_jobs(raw_results: list) -> list:
    """
    Turn noisy search results into clean job entries:
        [{"company": ..., "title": ..., "link": ..., "note": ...}, ...]
    Falls back to lightly-cleaned raw results if the LLM is unavailable.
    """
    if not raw_results:
        return []

    client = _get_client()
    if client is None:
        print("[llm] Gemini not configured; returning lightly-cleaned raw jobs.")
        return [
            {
                "company": "",
                "title": r["title"],
                "link": r["link"],
                "note": r.get("snippet", "")[:160],
            }
            for r in raw_results[:config.MAX_JOBS_IN_DIGEST]
        ]

    # Keep the prompt compact; send only what the model needs.
    compact = [
        {"title": r["title"], "link": r["link"], "snippet": r.get("snippet", "")}
        for r in raw_results
    ]
    priority = ", ".join(config.TARGET_COMPANIES)

    prompt = f"""You are filtering web search results to find REAL, currently-open
graduate programmes / graduate trainee schemes / management trainee programmes
for FRESH GRADUATES based in MALAYSIA.

Rules:
- Keep ONLY genuine graduate-programme job openings based in Malaysia.
- DROP: listicles, blog posts, news articles, outdated postings, generic career
  advice pages, and anything not clearly an open graduate programme in Malaysia.
- Deduplicate: if several links point to the same programme, keep the single best link.
- PRIORITISE large/multinational employers. Examples of priority employers: {priority}.
- Sort results with the biggest / most reputable MNC employers first.
- Return at most {config.MAX_JOBS_IN_DIGEST} items.

Return ONLY a JSON array (no prose, no code fences) of objects with keys:
  "company"  : best-guess employer name (string, "" if unknown)
  "title"    : the programme / role title (string)
  "link"     : the URL (string)
  "note"     : a very short plain-English note, e.g. intake/industry (string, may be "")

Search results:
{json.dumps(compact, ensure_ascii=False)}
"""

    try:
        parsed = _extract_json(_generate(client, prompt))
        if isinstance(parsed, list):
            cleaned = []
            for item in parsed[:config.MAX_JOBS_IN_DIGEST]:
                if isinstance(item, dict) and item.get("link"):
                    cleaned.append({
                        "company": str(item.get("company", "")).strip(),
                        "title": str(item.get("title", "")).strip(),
                        "link": str(item.get("link", "")).strip(),
                        "note": str(item.get("note", "")).strip(),
                    })
            print(f"[llm] filtered down to {len(cleaned)} job(s)")
            return cleaned
    except Exception as e:
        print(f"[llm] job filtering failed ({e}); falling back to raw.")

    return [
        {"company": "", "title": r["title"], "link": r["link"],
         "note": r.get("snippet", "")[:160]}
        for r in raw_results[:config.MAX_JOBS_IN_DIGEST]
    ]


# ---------------------------------------------------------------------------
# News
# ---------------------------------------------------------------------------
def summarise_news(items: list, topic_label: str) -> list:
    """
    Return [{"headline": ..., "summary": ..., "link": ...}, ...] where summary
    is a 1-sentence layman's-terms explanation. Falls back to raw titles if the
    LLM is unavailable.
    """
    if not items:
        return []

    items = items[:config.MAX_NEWS_ITEMS_PER_SECTION]
    client = _get_client()
    if client is None:
        print(f"[llm] Gemini not configured; returning raw {topic_label} headlines.")
        return [
            {"headline": it["title"], "summary": "", "link": it["link"]}
            for it in items
        ]

    compact = [{"title": it["title"], "link": it["link"]} for it in items]
    prompt = f"""Summarise these {topic_label} news headlines for a layman
(a smart person who is NOT a finance/tech expert). For each item write ONE short,
clear sentence explaining what happened and why it matters, in plain English.
Avoid jargon; if you must use a term, briefly explain it.

Return ONLY a JSON array (no prose, no code fences) of objects with keys:
  "headline" : a cleaned, concise version of the headline (string)
  "summary"  : your one-sentence plain-English explanation (string)
  "link"     : the original URL, unchanged (string)

Headlines:
{json.dumps(compact, ensure_ascii=False)}
"""

    try:
        parsed = _extract_json(_generate(client, prompt))
        if isinstance(parsed, list):
            out = []
            for item in parsed:
                if isinstance(item, dict) and item.get("link"):
                    out.append({
                        "headline": str(item.get("headline", "")).strip(),
                        "summary": str(item.get("summary", "")).strip(),
                        "link": str(item.get("link", "")).strip(),
                    })
            print(f"[llm] summarised {len(out)} {topic_label} item(s)")
            return out
    except Exception as e:
        print(f"[llm] news summarise failed ({e}); falling back to raw.")

    return [{"headline": it["title"], "summary": "", "link": it["link"]} for it in items]


# ---------------------------------------------------------------------------
# YouTube content-idea engine
# ---------------------------------------------------------------------------
def enrich_youtube(videos: list) -> list:
    """
    For each tracked video, add a short 'idea' field:
      - Non-Malaysian videos  -> a Malaysian-context adaptation idea for a
        ~1-minute short/reel (e.g. "AU dairy farm doc" -> "do one on Farm Fresh").
      - Malaysian videos       -> a brief angle/hook to riff on locally.

    Input items have keys: handle, malaysian, title, link, published.
    Returns the same list with an added 'idea' (str, may be "" on failure).
    Falls back gracefully (idea="") if the LLM is unavailable.
    """
    if not videos:
        return []

    client = _get_client()
    if client is None:
        print("[llm] Gemini not configured; YouTube videos sent without ideas.")
        for v in videos:
            v["idea"] = ""
        return videos

    compact = [
        {
            "i": idx,
            "title": v["title"],
            "malaysian": bool(v.get("malaysian")),
        }
        for idx, v in enumerate(videos)
    ]

    prompt = f"""You help a Malaysian content creator brainstorm short-form video
ideas (1-minute reels/shorts). Below is a list of recently uploaded YouTube videos
they track.

For EACH item, write ONE concrete, punchy content idea the creator could film,
tailored to a MALAYSIAN audience:
- If "malaysian" is false (foreign video): adapt the concept to a Malaysian
  equivalent. Example: a documentary about an Australian dairy farm ->
  "Mini-doc on Farm Fresh's dairy farms in Malaysia". Name a specific Malaysian
  company/place/person where it makes sense.
- If "malaysian" is true: suggest a fresh angle or hook to make a similar local
  short stand out.
Keep each idea to one sentence, specific and actionable (not generic).

Return ONLY a JSON array (no prose, no code fences) of objects:
  "i"    : the item's index (integer, unchanged)
  "idea" : your one-sentence Malaysian content idea (string)

Videos:
{json.dumps(compact, ensure_ascii=False)}
"""

    try:
        parsed = _extract_json(_generate(client, prompt))
        ideas = {}
        if isinstance(parsed, list):
            for item in parsed:
                if isinstance(item, dict) and "i" in item:
                    try:
                        ideas[int(item["i"])] = str(item.get("idea", "")).strip()
                    except (ValueError, TypeError):
                        continue
        for idx, v in enumerate(videos):
            v["idea"] = ideas.get(idx, "")
        n = sum(1 for v in videos if v.get("idea"))
        print(f"[llm] generated {n}/{len(videos)} YouTube content idea(s)")
        return videos
    except Exception as e:  # noqa: BLE001
        print(f"[llm] YouTube idea generation failed ({e}); sending without ideas.")
        for v in videos:
            v["idea"] = ""
        return videos
