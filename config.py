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
JOB_SEARCH_QUERIES = [
    '"graduate programme" Malaysia {year} apply',
    '"graduate trainee" Malaysia {year}',
    '"management trainee programme" Malaysia {year}',
    '"graduate development programme" Malaysia {year}',
    '"young talent programme" Malaysia {year}',
    'fresh graduate programme "Kuala Lumpur" {year}',
    'MNC graduate programme Malaysia {year} hiring',
    'multinational graduate trainee Malaysia {year}',
    '"graduate scheme" Malaysia {year} applications open',
    'graduate programme Malaysia {year} site:*.com.my',
    'graduate trainee Malaysia {year} site:linkedin.com/jobs',
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
# LLM (Google Gemini free tier)
# ---------------------------------------------------------------------------
# Model used for filtering jobs and summarising news. The free tier covers
# this volume comfortably. If the key is missing, the bot gracefully falls
# back to sending raw (unsummarised, lightly-deduped) results.
GEMINI_MODEL = "gemini-2.0-flash"

# ---------------------------------------------------------------------------
# Timezone label (purely cosmetic, shown in the digest header)
# ---------------------------------------------------------------------------
TIMEZONE_LABEL = "Malaysia Time (MYT)"
