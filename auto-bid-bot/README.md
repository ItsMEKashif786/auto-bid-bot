# Auto Bidding Bot

Detects posts on LinkedIn and X (Twitter) where people are looking for freelancers/developers, generates a personalized bid comment with AI (Groq, OpenRouter fallback), and posts it. Uses Playwright for browser automation, SQLite for deduplication, and n8n for scheduling.

## Project structure

```
auto-bid-bot/
├── linkedin_bot.py     # LinkedIn scraping + commenting
├── twitter_bot.py      # X scraping + replying
├── commenter.py        # Groq -> OpenRouter AI bid generator
├── db.py               # SQLite dedupe (data/bids.db)
├── config.py           # Loads .env
├── utils.py            # Logging, delays, screenshots, dry-run log
├── main.py             # Orchestrator
├── requirements.txt
├── .env.example
├── workflow.json       # n8n workflow
├── session/            # Playwright persistent profiles
└── data/               # SQLite DB
```

## Setup

```bash
git clone <repo> auto-bid-bot && cd auto-bid-bot
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
cp .env.example .env   # then fill in keys
python db.py           # initialize SQLite
```

## Environment variables

| Var | Purpose |
|---|---|
| `GROQ_API_KEY` | Primary AI provider |
| `OPENROUTER_API_KEY` | Fallback AI provider |
| `LINKEDIN_EMAIL` / `LINKEDIN_PASSWORD` | LinkedIn login (optional if session reused) |
| `TWITTER_EMAIL` / `TWITTER_PASSWORD` | X login |
| `DRY_RUN` | `true` = don't actually submit (default) |
| `HEADLESS` | `true` = run browser headless |
| `USER_SKILLS` | Your pitch — used in prompt |

## Run

First run interactively (HEADLESS=false) so you can log in once; sessions are persisted under `session/`.

```bash
python main.py --platform linkedin
python main.py --platform twitter
```

## DRY RUN mode

Set `DRY_RUN=true` in `.env` (default).

When enabled, the bot will:

1. Fetch posts and dedupe them.
2. Generate the AI bid comment.
3. Open the post, type the comment into the comment box.
4. **Take a screenshot** (`logs/<platform>_before_submit_<ts>.png`).
5. Print:
   ```
   DRY RUN: Comment ready
     platform: linkedin
     url: ...
     comment: ...
   ```
6. Append a JSON line to `logs/dry_run.log` with timestamp, platform, post_id, generated_comment.
7. **Skip clicking the submit button.**

Set `DRY_RUN=false` to enable real posting.

Typical terminal output:

```
[INFO] Post fetched: urn:li:activity:123
[INFO] Comment generated
[DRY RUN] Ready to submit
[INFO] Saved to database
```

## Safety limits

- LinkedIn: 10–15 comments/day (max 5 per run)
- X: 5–10 replies/day (max 5 per run)
- Random 3–8s delays between actions, 8–20s between posts
- Human-style typing (per-character delay)

## n8n setup

1. Install n8n (`npx n8n`) and open http://localhost:5678.
2. Settings → Import workflow → load `workflow.json`.
3. Edit the two **Execute Command** nodes so the path matches where you cloned the repo.
4. Cron: `0 9-18/2 * * 1-5` → every 2 hours, 9 AM–6 PM, Mon–Fri.
5. (Optional) Enable the Google Sheets node and set a sheet ID for log backup.
6. Activate the workflow.

## Logs

- `logs/bot.log` — rotating runtime log
- `logs/dry_run.log` — JSON lines of dry-run generations
- `logs/*_before_submit_*.png` — pre-submit screenshots
