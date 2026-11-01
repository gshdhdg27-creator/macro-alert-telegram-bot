# Macro Alert — Production Deployment

## Components

1. **Telegram bot** — `python -m bot.main`
2. **Backend API** — `uvicorn api.app:app --host 0.0.0.0 --port 8000`
3. **Mini App** — Vercel static site, Root Directory = `miniapp`

## Required environment (server)

```
BOT_TOKEN=<telegram bot token>
ADMIN_ID=<your telegram user id>
DATABASE_URL=sqlite+aiosqlite:///./data/bot.db
OPENAI_API_KEY=          # optional
OPENAI_MODEL=gpt-4o-mini
FMP_API_KEY=             # optional
INITDATA_MAX_AGE=3600
```

### CORS (production — no wildcard)

```
CORS_ORIGINS=https://YOUR-VERCEL-APP.vercel.app,https://web.telegram.org
```

Only `https://` origins (plus localhost for local dev). Invalid schemes fail startup.

## Mini App API base

In `miniapp/index.html` set:

```js
window.MACRO_API_BASE = 'https://YOUR-API-HOST';
```

Or inject via a small config script before `js/api.js`.

When `MACRO_API_BASE` is empty, News/Calendar/Settings show an honest **unavailable** state (no client RSS fallback).

## Auth

Mini App sends raw `Telegram.WebApp.initData` as header:

```
X-Telegram-Init-Data: <initData>
```

Never use `initDataUnsafe` for auth.

## Start order

```bash
mkdir -p data
pip install -r requirements.bot.txt
python -m bot.main          # terminal 1 — bot + scheduler
uvicorn api.app:app --host 0.0.0.0 --port 8000   # terminal 2
```

Database migrations run on API/bot `init_db()` (idempotent).

## Health check

```bash
curl https://YOUR-API-HOST/api/health
# {"ok":true,"service":"macro-alert"}
```
