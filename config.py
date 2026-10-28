"""
Central configuration for the Telegram Daily Update bot.

Everything you'll likely want to tweak lives here:
  - which Google searches to run for jobs
  - which news feeds to pull
  - how many searches we're allowed per day (kept below Google's free 100/day)
  - which big MNC employers to prioritise

No secrets live here. API keys/tokens come from environment variables
(see .env.example and the README).
"""

# ---------------------------------------------------------------------------
# SAFETY: hard cap on paid-API usage
# ---------------------------------------------------------------------------
# Google Programmable Search gives 100 free queries/day, then simply STOPS
# (it does not bill you). We cap at 90 to leave a safety buffer so there is
# zero chance of ever touching a paid quota.
MAX_GOOGLE_SEARCHES_PER_DAY = 90

# Number of results to request per search (Google allows up to 10 per call).
RESULTS_PER_SEARCH = 10

# Optional recency filter for Google job searches (e.g. "m3" = last 3 months,
# "y1" = last year). Leave as None to search without a date restriction —
# recommended, since many graduate-programme pages are older but still open.
JOB_DATE_RESTRICT = None

# ---------------------------------------------------------------------------
# JOBS: target big MNC graduate programmes in Malaysia
# ---------------------------------------------------------------------------
# These are the big multinational / large employers hiring graduates in
# Malaysia. The LLM filter will prioritise listings from well-known large
# employers like these. Add/remove freely.
TARGET_COMPANIES = [
    "Shell", "Petronas", "Maybank", "CIMB", "Public Bank", "RHB",
    "Standard Chartered", "HSBC", "Citi", "Nestle", "Unilever",
    "Procter & Gamble", "Intel", "AMD", "Dell", "Dyson", "Micron",
    "Microsoft", "Google", "Deloitte", "PwC", "EY", "KPMG", "Accenture",
    "Sime Darby", "IOI", "Maxis", "Axiata", "Digi", "CelcomDigi",
    "DHL", "BAT", "AirAsia", "Petron", "Top Glove", "Hartalega",
    "Bursa Malaysia", "Khazanah", "TNB", "Telekom Malaysia",
]

# Google search query templates. Keep these broad enough to catch
# "all companies, any industry" but focused on Malaysia + graduate hiring.
# {year} is filled in automatically with the current year.
# NOTE: Google deprecated "Search the entire web" for Programmable Search
# (Jan 2026). Our engine is therefore restricted to the job-board domains
# configured in the engine's control panel (see README). Because the engine
# already limits the domains, these queries do NOT use site: operators.
JOB_SEARCH_QUERIES = [
    'graduate programme Malaysia',
    'graduate trainee Malaysia',
    'management trainee Malaysia',
    'graduate development programme Malaysia',
    'young talent programme Malaysia',
    'fresh graduate programme Kuala Lumpur',
    'graduate scheme Malaysia',
    'graduate programme {year}',
    'management trainee programme {year}',
    'graduate trainee {year} Malaysia',
]

# Company-specific queries are generated automatically from TARGET_COMPANIES
# at runtime (batched to stay within the daily search cap). You can disable
# this if you only want the generic nets above.
ENABLE_COMPANY_SPECIFIC_QUERIES = True

# ---------------------------------------------------------------------------
# NEWS
# ---------------------------------------------------------------------------
# Malaysian business & finance. The Edge is the primary source; we try its
# feed first and fall back to a Google News feed scoped to The Edge.
MY_BUSINESS_FEEDS = [
    # Google News RSS scoped to The Edge Malaysia (reliable, structured).
    "https://news.google.com/rss/search?q=when:1d%20site:theedgemalaysia.com&hl=en-MY&gl=MY&ceid=MY:en",
    # Broader MY business/finance net via Google News.
    "https://news.google.com/rss/search?q=when:1d%20Malaysia%20business%20finance&hl=en-MY&gl=MY&ceid=MY:en",
]

# Global AI changes / "AI bubble" etc.
GLOBAL_AI_FEEDS = [
    "https://news.google.com/rss/search?q=when:1d%20artificial%20intelligence%20AI&hl=en-US&gl=US&ceid=US:en",
    "https://hnrss.org/newest?q=AI+OR+LLM+OR+OpenAI&count=20",
    "https://techcrunch.com/category/artificial-intelligence/feed/",
]

# Max items to show per news section after dedupe/summarise.
MAX_NEWS_ITEMS_PER_SECTION = 5

# Max job listings to show in the digest (after filtering + dedupe).
MAX_JOBS_IN_DIGEST = 15

# ---------------------------------------------------------------------------
# JOBS: free RSS safety net (no API key, no quota)
# ---------------------------------------------------------------------------
# Because Google's free search is now domain-restricted, we add a free RSS
# layer via Google News to keep coverage broad. These need NO API key and
# complement the Programmable Search results. Results from both sources are
# merged and deduped before the LLM filter runs.
JOB_RSS_FEEDS = [
    # --- General Malaysian graduate-programme news/announcements (last 2 weeks) ---
    "https://news.google.com/rss/search?q=when:14d%20graduate%20programme%20Malaysia&hl=en-MY&gl=MY&ceid=MY:en",
    "https://news.google.com/rss/search?q=when:14d%20graduate%20trainee%20Malaysia&hl=en-MY&gl=MY&ceid=MY:en",
    "https://news.google.com/rss/search?q=when:14d%20management%20trainee%20Malaysia&hl=en-MY&gl=MY&ceid=MY:en",
    "https://news.google.com/rss/search?q=when:14d%20fresh%20graduate%20hiring%20Malaysia&hl=en-MY&gl=MY&ceid=MY:en",

    # --- Direct listings from job boards via Google News site: scoping ---
    # These return ACTUAL graduate job postings (title + link), no API key needed.
    # This is what replaces the blocked Google Custom Search for us.
    "https://news.google.com/rss/search?q=site:gradconnection.com%20Malaysia%20graduate&hl=en-MY&gl=MY&ceid=MY:en",
    "https://news.google.com/rss/search?q=site:hiredly.com%20graduate%20trainee&hl=en-MY&gl=MY&ceid=MY:en",
    "https://news.google.com/rss/search?q=site:ricebowl.my%20graduate&hl=en-MY&gl=MY&ceid=MY:en",
]

# Max items taken from EACH job RSS feed (keeps the batch focused and the LLM
# filtering cheap). The direct job-board feeds are high-volume, so this trims
# them to the most recent listings.
JOB_RSS_PER_FEED = 15

# ---------------------------------------------------------------------------
# LLM (Google Gemini free tier)
# ---------------------------------------------------------------------------
# Model used for filtering jobs and summarising news. The free tier covers
# this volume comfortably. If the key is missing, the bot gracefully falls
# back to sending raw (unsummarised, lightly-deduped) results.
# Flash-Lite is the model available on the Gemini free tier (Google narrowed
# the free tier in Oct 2026 so the full Flash/Pro models need a paid plan).
# It's also faster, which avoids the 504 timeouts seen with the full Flash model.
#
# The bot tries these in order and uses the first one your key can access, so
# it keeps working even as Google rotates model availability. Put your
# preferred model first.
GEMINI_MODEL = "gemini-3.5-flash-lite"
GEMINI_MODEL_FALLBACKS = [
    "gemini-3.5-flash-lite",
    "gemini-3.1-flash-lite",
    "gemini-2.5-flash-lite",
    "gemini-2.0-flash-lite",
]

# ---------------------------------------------------------------------------
# Timezone label (purely cosmetic, shown in the digest header)
# ---------------------------------------------------------------------------
TIMEZONE_LABEL = "Malaysia Time (MYT)"
