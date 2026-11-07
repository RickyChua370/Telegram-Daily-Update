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

# ---------------------------------------------------------------------------
# YOUTUBE CREATOR TRACKING (content-idea engine)
# ---------------------------------------------------------------------------
# Tracks new uploads from specific channels so you can brainstorm similar
# content. For NON-Malaysian creators, the bot also suggests a Malaysian-context
# adaptation (e.g. "Documentary on an Australian dairy farm" -> "Do one on
# Farm Fresh in Malaysia") to spark a 1-minute short/reel idea.
#
# Primary fetch uses the YouTube Data API (set YOUTUBE_API_KEY). If no key is
# set, the bot falls back to each channel's free public RSS feed (no key).
#
# Each entry: handle (for display), channel_id, whether it's Malaysian, and a
# "category" that steers the kind of content idea Gemini suggests:
#   "general"    -> general Malaysian-context short/reel adaptation
#   "selfgrowth" -> ideas for a Malaysian FEMALE FRESH GRADUATE doing
#                   self-growth content
# "malaysian": True  -> treat as already-local context
# "malaysian": False -> adapt the idea to a Malaysian context
YOUTUBE_CHANNELS = [
    {"handle": "publicopinionnyc",  "channel_id": "UCGwyQM5eQOTxoeHOZaMwzSg", "malaysian": False, "category": "general"},
    {"handle": "goodyfeedbluecats", "channel_id": "UCt-9qlL7q9JPpPi1uOintfw", "malaysian": False, "category": "general"},
    {"handle": "Moon-Real",         "channel_id": "UCB6P-Iahz6E0qnUdoURNotQ", "malaysian": False, "category": "general"},
    {"handle": "MalaysianPAYGAP",   "channel_id": "UCrhIk2faO1fWjJzEMvkFnww", "malaysian": True,  "category": "general"},
    {"handle": "BBKNetwork",        "channel_id": "UC0SJCeL0QG4BH_KQALjQE-Q", "malaysian": False, "category": "general"},
    {"handle": "ZietInvests",       "channel_id": "UC-h5sZ-O_4KbdzPy6hxYd9g", "malaysian": False, "category": "general"},
    {"handle": "ceocircleclub00",   "channel_id": "UCWgyEfQYKYOxVPr8NOJAsXw", "malaysian": False, "category": "general"},
    {"handle": "FinancialFaiz",     "channel_id": "UCSYUI0C0gG-Kp03GBaO2G9Q", "malaysian": True,  "category": "general"},
    {"handle": "CNAInsider",        "channel_id": "UC_Lnb8ZHqqgLbp-7hltuT9w", "malaysian": False, "category": "general"},
    {"handle": "LiveActionFilms",   "channel_id": "UCvC6KqMFj7ifnd-JH7hYtQA", "malaysian": False, "category": "general"},
    {"handle": "GrantRudow",        "channel_id": "UCdHqdfzdvT7tbAfeQM1gLnQ", "malaysian": False, "category": "general"},
    {"handle": "companyman114",     "channel_id": "UCQMyhrt92_8XM0KgZH6VnRg", "malaysian": False, "category": "general"},
    {"handle": "CNBC",              "channel_id": "UCH5_L3ytGbBziX0CLuYdQ1Q", "malaysian": False, "category": "general"},
    {"handle": "MrMoneyTV",         "channel_id": "UCTj6bkOhFCeGY_c9MSi5ORw", "malaysian": True,  "category": "general"},

    # --- Self-growth creators (ideas tailored for a MY female fresh graduate) ---
    {"handle": "tamkaur",           "channel_id": "UCQaDvRvrLPPROGSV8Y7XowA", "malaysian": False, "category": "selfgrowth"},
    {"handle": "JillzGuerin",       "channel_id": "UCzR9e4gHwY1kOM0nFMcWe0A", "malaysian": False, "category": "selfgrowth"},
    {"handle": "Sisyphus55",        "channel_id": "UCKPZHZzvSPYvqyk-nFS9kDA", "malaysian": False, "category": "selfgrowth"},
    {"handle": "charlottemorabito", "channel_id": "UCy2xYfqVOaMEx3mMGiJrWmg", "malaysian": False, "category": "selfgrowth"},
    {"handle": "nadeenhui",         "channel_id": "UC1tCLwbySvJO7lkSgJAtzsQ", "malaysian": False, "category": "selfgrowth"},
]

# Only report uploads newer than this many days (the "seen" memory also
# prevents repeats, but this avoids surfacing stale videos on first run).
YOUTUBE_LOOKBACK_DAYS = 3

# Max videos to show per channel per run (keeps the digest tidy).
YOUTUBE_MAX_PER_CHANNEL = 3


# ---------------------------------------------------------------------------
# #1 MALAYSIA BUSINESS STORY OF THE DAY
# ---------------------------------------------------------------------------
# A daily deep-dive on a Malaysian company: how it grew / entered the market /
# collapsed, etc. Gemini picks a company from recent business news (or its own
# knowledge on quiet days) and tells a short, engaging story.
#
# If the company is listed on Bursa Malaysia, we attach live stock data from
# Yahoo Finance (clearly labelled NOT financial advice). We also attach a few
# Reddit discussion links about the company (via Google News site:reddit.com).

# News feeds used to pick the day's company story.
BUSINESS_STORY_FEEDS = [
    "https://news.google.com/rss/search?q=when:3d%20Malaysia%20company%20business%20growth%20OR%20expansion&hl=en-MY&gl=MY&ceid=MY:en",
    "https://news.google.com/rss/search?q=when:3d%20Malaysia%20company%20acquisition%20OR%20IPO%20OR%20restructuring&hl=en-MY&gl=MY&ceid=MY:en",
]

# A small map of well-known Malaysian companies -> Bursa Malaysia ticker
# (Yahoo Finance uses the ".KL" suffix). Used to attach stock data when the
# day's story company is listed. Gemini is also asked for a ticker guess, but
# this map makes the common ones reliable.
BURSA_TICKERS = {
    "maybank": "1155.KL",
    "cimb": "1023.KL",
    "public bank": "1295.KL",
    "rhb": "1066.KL",
    "petronas chemicals": "5183.KL",
    "petronas gas": "6033.KL",
    "tenaga": "5347.KL",
    "tnb": "5347.KL",
    "axiata": "6888.KL",
    "maxis": "6012.KL",
    "celcomdigi": "6947.KL",
    "digi": "6947.KL",
    "sime darby": "4197.KL",
    "ioi": "1961.KL",
    "top glove": "7113.KL",
    "hartalega": "5168.KL",
    "airasia": "5099.KL",
    "capital a": "5099.KL",
    "genting": "3182.KL",
    "genting malaysia": "4715.KL",
    "mr diy": "5296.KL",
    "ql resources": "7084.KL",
    "nestle malaysia": "4707.KL",
    "ppb": "4065.KL",
    "ihh": "5225.KL",
    "press metal": "8869.KL",
    "gamuda": "5398.KL",
    "ytl": "4677.KL",
    "ytl power": "6742.KL",
    "bursa malaysia": "1818.KL",
    "farm fresh": "5306.KL",
    "99 speedmart": "5326.KL",
}

# How many Reddit discussion links to attach to the business story.
BUSINESS_STORY_REDDIT_LINKS = 3

# ---------------------------------------------------------------------------
# #3 TRENDING PULSE (Google Trends MY + Reddit r/malaysia)
# ---------------------------------------------------------------------------
# NOTE: Reddit blocks anonymous search/JSON, but its public "hot" RSS works.
GOOGLE_TRENDS_MY_RSS = "https://trends.google.com/trending/rss?geo=MY"
REDDIT_MALAYSIA_HOT_RSS = "https://www.reddit.com/r/malaysia/hot/.rss?limit=15"

TRENDING_MAX_GOOGLE = 8   # top N Google Trends searches to show
TRENDING_MAX_REDDIT = 6   # top N r/malaysia hot posts to show
