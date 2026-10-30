# Macro Alert — Trading AI News Intelligence

Personal Telegram bot + Mini App for macroeconomic alerts, real economic calendar, and AI-assisted market news.

## Architecture

| Component | Stack | Deploy |
|-----------|--------|--------|
| Telegram bot | Python 3.11+, aiogram 3, APScheduler, SQLAlchemy | VPS / local / any long-running host |
| Mini App | Static HTML/JS (Tailwind, Lightweight Charts) | Vercel (`miniapp/` root) |
| Database | SQLite (aiosqlite) by default | file `data/bot.db` |

**Do not deploy the Python bot on Vercel.** Vercel only hosts the Mini App static files.

## Features

- 10 news categories: Forex, Crypto, Gold, Stocks, Economic, Central Banks, Geopolitics, Whales, Technical, Sentiment
- RSS collector (BBC, CoinDesk, Fed, Reuters, CNBC) — **no invented news**
- Persistent deduplication (`published_news` table)
- Economic calendar from pipatlas / faireconomy (optional FMP key) — **no placeholder events**
- 15-minute pre-alerts for high-impact calendar events
- Mini App: charts for Binance pairs (real WS), FX spot rates, in-app news detail

## Environment variables

Copy `.env.example` → `.env`:

```
BOT_TOKEN=...
ADMIN_ID=...
OPENAI_API_KEY=          # optional, enables stronger analysis
OPENAI_MODEL=gpt-4o-mini
FMP_API_KEY=             # optional calendar
DEFAULT_TIMEZONE=Europe/Moscow
DATABASE_URL=sqlite+aiosqlite:///./data/bot.db
MINIAPP_URL=https://your-app.vercel.app
```

## Run the bot (local / VPS)

```bash
pip install -r requirements.bot.txt
python -m bot.main
```

## Deploy Mini App (Vercel)

1. Root Directory = `miniapp`
2. Framework = Other / static
3. Redeploy after each push to `miniapp/`

## Market data policy

| Asset | Source | Notes |
|-------|--------|-------|
| BTC, ETH | Binance public API + WS | Real candles and live trades |
| EUR/USD, GBP/USD, USD/JPY | exchangerate-api.com | Spot only (no OHLC history free) |
| Gold, indices, oil | — | Shown as **DATA UNAVAILABLE** until a verified free/paid API is configured |

**Simulated candlesticks are not used as live market data.**

## Critical fixes (recent)

1. `formatter.py` syntax: Unicode separator must be a string (`"━" * 18`)
2. News sort: missing dates no longer crash comparisons
3. DB-backed `PublishedNews` dedupe across restarts
4. Calendar: removed static demo CPI/NFP placeholders
5. All 10 categories in PRIMARY_CATS

## Limitations

- Without `OPENAI_API_KEY`, bias uses conservative keyword heuristics (often UNCERTAIN)
- Free FX APIs do not provide full OHLC history
- Gold/index/oil charts need a paid or additional provider
- Bot must run 24/7 on a server for live polling (not serverless)

## License

Private personal use.
