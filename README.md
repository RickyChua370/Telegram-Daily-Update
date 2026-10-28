# 🗞️ Telegram Daily Update

A free, zero-server bot that sends you one Telegram message every morning with:

- 📋 **New Malaysian graduate programmes** at big MNCs (any industry), found via
  targeted Google searches and cleaned up by AI.
- 💰 **Malaysia business & finance news** (The Edge), summarised in plain English.
- 🤖 **Global AI news** ("AI bubble", new model releases, etc.), summarised too.

It runs automatically on **GitHub Actions** (free), delivers via a **Telegram bot**
(free), and uses **Google's free tiers** for search and AI summaries. **No credit
card is required for any part of this, and the code is hard-capped so it can never
exceed the free quotas.**

---

## How it works

```
GitHub Actions (daily, 8 AM MYT)
        │
        ▼
     main.py
        ├── jobs_search.py   → free Google-News RSS job feeds (+ optional Google API)
        ├── news_fetch.py    → The Edge + global AI via RSS
        ├── llm_filter.py    → Gemini (free): filter jobs + layman summaries
        ├── seen_store.py    → remembers past items so you only get NEW ones
        └── telegram_send.py → sends the digest to your phone
```

If any API key is missing, that part degrades gracefully (e.g. news is sent as
raw headlines) instead of the whole thing failing.

---

## Setup (about 15 minutes, no credit card)

You need **4 free credentials**. Here's each, step by step.

### 1. Telegram bot token + your chat ID

1. In Telegram, message **[@BotFather](https://t.me/BotFather)** → send `/newbot`
   → follow prompts → it gives you a **bot token** (looks like `12345:ABC...`).
2. Send any message (e.g. "hi") to your new bot so it's allowed to message you.
3. Get your **chat ID**: open this URL in a browser (paste your token in):
   `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates`
   Look for `"chat":{"id":123456789` — that number is your `TELEGRAM_CHAT_ID`.

### 2. Google Programmable Search (the job searches)

> Free tier = **100 queries/day**. Google does **not** bill past that — it just
> stops. This project is additionally capped at **90/day** in code.
>
> ⚠️ **Note (2026):** Google deprecated the "Search the entire web" option. New
> free engines are limited to **≤50 specific domains**. That's fine for us — we
> point the engine at the job boards where Malaysian MNC graduate programmes
> actually appear, and add a free Google-News RSS layer (`JOB_RSS_FEEDS`, no API
> key) to keep coverage broad.

1. Create a search engine at **https://programmablesearchengine.google.com/controlpanel/create**
   → give it a name → to get past the create screen you must add one site
   (e.g. `my.jobstreet.com`) → complete CAPTCHA → **Create**.
2. Open the engine's **Control Panel → "Sites to search"** and add these
   job-board domains (well within the 50-domain free limit):
   ```
   my.jobstreet.com
   malaysia.indeed.com
   my.gradconnection.com
   glassdoor.com
   www.linkedin.com
   jobstreet.com
   www.ricebowl.my
   www.wobb.my
   graduan.com
   www.hiredly.com
   ```
   (Add the careers domains of specific MNCs too if you like — up to 50 total.)
3. Copy the **Search engine ID** (the `cx` value) → this is `GOOGLE_SEARCH_ENGINE_ID`.
4. Get an API key at **https://developers.google.com/custom-search/v1/introduction**
   → click **"Get a Key"** → create/select a project → copy the key →
   this is `GOOGLE_SEARCH_API_KEY`.
   *(You do NOT need to enable billing. If prompted, skip it — 100/day stays free.)*

### 3. Google Gemini API key (the AI summaries/filtering)

> Free tier, **no card needed**. It throttles rather than billing.

1. Go to **https://aistudio.google.com/app/apikey**
2. Click **"Create API key"** → copy it → this is `GEMINI_API_KEY`.

---

## Running it

### Option A — on GitHub (recommended, fully automatic & free)

1. Push this repo to your GitHub account (it's already set up at
   `RickyChua370/Telegram-Daily-Update`).
2. Go to the repo → **Settings → Secrets and variables → Actions → New repository secret**
   and add these five secrets:

   | Secret name | Value |
   |---|---|
   | `TELEGRAM_BOT_TOKEN` | from step 1 |
   | `TELEGRAM_CHAT_ID` | from step 1 |
   | `GOOGLE_SEARCH_API_KEY` | from step 2 |
   | `GOOGLE_SEARCH_ENGINE_ID` | from step 2 |
   | `GEMINI_API_KEY` | from step 3 |

3. Go to the **Actions** tab → enable workflows if prompted → open **"Daily Digest"**
   → click **"Run workflow"** to test immediately.
4. After that, it runs automatically every day at **8 AM Malaysia time**.
   (Change the time by editing the `cron` line in `.github/workflows/daily.yml` —
   remember it's in UTC, so MYT = UTC + 8.)

### Option B — locally on your computer (for testing)

```bash
pip install -r requirements.txt
cp .env.example .env     # then fill in your keys in .env
python main.py
```

---

## Customising

Everything you'll want to tweak is in **`config.py`**:

- `TARGET_COMPANIES` — the big MNCs to prioritise.
- `JOB_SEARCH_QUERIES` — the Google search templates. Add your own!
- `MY_BUSINESS_FEEDS` / `GLOBAL_AI_FEEDS` — news sources.
- `MAX_GOOGLE_SEARCHES_PER_DAY` — the safety cap (default 90).
- `MAX_JOBS_IN_DIGEST`, `MAX_NEWS_ITEMS_PER_SECTION` — how much to show.

---

## Where the jobs come from

The main job source is **free Google-News RSS feeds** (no API key, no quota),
including `site:`-scoped feeds that pull **actual listings** from job boards like
gradconnection, Hiredly and Ricebowl, plus general Malaysian graduate-hiring news.
The Gemini filter then keeps only genuine, currently-open graduate programmes and
drops the news noise.

The Google **Programmable Search** path (`GOOGLE_SEARCH_*` secrets) is still wired
in and merges on top *if* it's available — but it's **optional**. Note that Google
is winding down the free Custom Search JSON API, and some new Google Cloud accounts
hit a `403 "project does not have access"` even with the API enabled (a known
Google-side provisioning restriction). If that happens to you, just leave those two
secrets unset — the free RSS feeds cover the job section on their own.

## Honest limitations

- **Not 100% complete.** Some companies only post graduate programmes on their own
  careers pages (behind forms) or on LinkedIn, which blocks automated access. This
  bot catches the large majority of *publicly searchable* Malaysian graduate
  programmes, but not literally everything.
- **AI filtering isn't perfect.** The occasional non-job link may slip through, or a
  real one may get dropped. Tune `JOB_SEARCH_QUERIES` over time to improve results.
- **The Edge full articles are paywalled**; summaries are based on headlines/snippets
  from public feeds.

---

## Ideas to add later

- 💱 USD/MYR exchange rate + KLSE index
- 🌧️ Daily weather for your city
- ⏰ A deadline tracker for application closing dates
- 🔖 Reply to the bot to "save" a job for later

PRs / tweaks welcome — it's your bot. 🙂
