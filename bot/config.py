from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Telegram
    bot_token: str
    admin_id: int

    # OpenAI
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"

    # Optional data providers
    fmp_api_key: str = ""
    benzinga_api_key: str = ""

    # App
    default_timezone: str = "Europe/Moscow"
    database_url: str = "sqlite+aiosqlite:///./data/bot.db"
    log_level: str = "INFO"

    # Scheduler intervals (seconds)
    calendar_poll_interval: int = 20
    news_poll_interval: int = 45


@lru_cache
def get_settings() -> Settings:
    return Settings()


# ---------------------------------------------------------------------------
# Assets configuration (easy to extend)
# ---------------------------------------------------------------------------

ASSETS = {
    "xauusd": {
        "emoji": "🟡",
        "name_ru": "Золото (XAUUSD)",
        "name_en": "Gold (XAUUSD)",
        "tags": ["XAUUSD", "GOLD", "GOLDEN", "FED", "CPI", "PCE", "DXY", "INFLATION"],
        "keywords": [
            "federal reserve", "fed rate", "interest rate", "powell",
            "cpi", "pce", "inflation", "dollar index", "dxy",
            "safe haven", "gold price", "xau",
        ],
    },
    "nasdaq": {
        "emoji": "📈",
        "name_ru": "NASDAQ 100",
        "name_en": "NASDAQ 100",
        "tags": ["NASDAQ", "NDX", "TECH", "BIGTECH"],
        "keywords": [
            "apple", "aapl", "nvidia", "nvda", "microsoft", "msft",
            "meta", "amazon", "amzn", "google", "googl", "tesla",
            "us10y", "treasury yield", "tech earnings",
        ],
    },
    "sp500": {
        "emoji": "📊",
        "name_ru": "S&P 500",
        "name_en": "S&P 500",
        "tags": ["SPX", "SP500", "S&P", "US MARKET"],
        "keywords": [
            "s&p 500", "spx", "recession", "soft landing",
            "fed", "interest rate", "earnings season",
        ],
    },
    "btc": {
        "emoji": "🪙",
        "name_ru": "Bitcoin (BTC)",
        "name_en": "Bitcoin (BTC)",
        "tags": ["BTC", "BITCOIN", "CRYPTO"],
        "keywords": [
            "bitcoin", "btc", "spot etf", "blackrock ibit", "fidelity fbtc",
            "sec", "miner", "hashrate", "stablecoin", "usdt", "usdc",
            "liquidity", "crypto regulation",
        ],
    },
    "eth": {
        "emoji": "💎",
        "name_ru": "Ethereum (ETH)",
        "name_en": "Ethereum (ETH)",
        "tags": ["ETH", "ETHEREUM"],
        "keywords": [
            "ethereum", "eth", "hard fork", "dencun", "pectra",
            "layer 2", "arbitrum", "optimism", "base", "staking",
            "eth etf", "defi", "tvl",
        ],
    },
    "dxy": {
        "emoji": "💵",
        "name_ru": "DXY (Индекс доллара)",
        "name_en": "DXY (US Dollar Index)",
        "tags": ["DXY", "USD", "DOLLAR"],
        "keywords": [
            "dollar index", "dxy", "powell", "nfp", "nonfarm",
            "jobless claims", "retail sales", "fed",
        ],
    },
    "oil": {
        "emoji": "🛢",
        "name_ru": "Brent / WTI",
        "name_en": "Brent / WTI Oil",
        "tags": ["OIL", "BRENT", "WTI", "CRUDE"],
        "keywords": [
            "opec", "opec+", "brent", "wti", "crude oil",
            "eia", "oil inventory", "middle east", "saudi",
        ],
    },
    "eurusd": {
        "emoji": "💶",
        "name_ru": "EUR/USD",
        "name_en": "EUR/USD",
        "tags": ["EURUSD", "EUR", "EURO"],
        "keywords": [
            "ecb", "lagarde", "eurozone", "euro inflation",
            "pmi", "eur/usd", "euro dollar",
        ],
    },
    "gbpusd": {
        "emoji": "💷",
        "name_ru": "GBP/USD",
        "name_en": "GBP/USD",
        "tags": ["GBPUSD", "GBP", "POUND", "STERLING"],
        "keywords": [
            "bank of england", "boe", "uk inflation", "cpi uk",
            "pound", "sterling", "gbp",
        ],
    },
    "usdjpy": {
        "emoji": "💴",
        "name_ru": "USD/JPY",
        "name_en": "USD/JPY",
        "tags": ["USDJPY", "JPY", "YEN"],
        "keywords": [
            "bank of japan", "boj", "yen intervention",
            "jgb", "japanese bonds", "usd/jpy",
        ],
    },
    "agro": {
        "emoji": "🌾",
        "name_ru": "Agro / Commodities",
        "name_en": "Agro / Commodities",
        "tags": ["AGRO", "WHEAT", "CORN", "SUGAR", "COFFEE"],
        "keywords": [
            "wheat", "corn", "soybean", "sugar", "coffee",
            "usda", "weather", "suez", "panama canal",
            "export duty", "crop report",
        ],
    },
    "tesla": {
        "emoji": "🚗",
        "name_ru": "Tesla & EV",
        "name_en": "Tesla & EV Sector",
        "tags": ["TSLA", "TESLA", "EV"],
        "keywords": [
            "tesla", "tsla", "elon musk", "deliveries",
            "fsd", "autopilot", "lithium", "battery",
            "ev sales", "cybertruck",
        ],
    },
    "ai_tech": {
        "emoji": "🤖",
        "name_ru": "AI & Semiconductors",
        "name_en": "AI & Tech Sector",
        "tags": ["NVDA", "AI", "SEMICONDUCTOR", "CHIPS"],
        "keywords": [
            "nvidia", "nvda", "amd", "tsm", "tsmc",
            "semiconductor", "chip export", "ai investment",
            "data center", "gpu",
        ],
    },
}


def get_asset_keys() -> List[str]:
    return list(ASSETS.keys())
