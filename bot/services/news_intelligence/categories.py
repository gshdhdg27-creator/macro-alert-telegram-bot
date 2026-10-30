"""News categories for Trading AI News Intelligence."""
from typing import Dict, List

CATEGORIES: Dict[str, dict] = {
    "forex": {
        "id": "forex",
        "emoji": "💱",
        "name_ru": "Forex",
        "name_en": "Forex",
        "color": "blue",
        "keywords": [
            "eur/usd", "gbp/usd", "usd/jpy", "forex", "dollar", "euro", "yen",
            "currency", "fx ", "dxy", "cable", "aussie", "loonie",
        ],
        "assets": ["EURUSD", "GBPUSD", "USDJPY", "DXY"],
    },
    "crypto": {
        "id": "crypto",
        "emoji": "🪙",
        "name_ru": "Crypto",
        "name_en": "Crypto",
        "color": "purple",
        "keywords": [
            "bitcoin", "btc", "ethereum", "eth", "crypto", "binance", "coinbase",
            "altcoin", "defi", "stablecoin", "sec crypto", "etf bitcoin",
        ],
        "assets": ["BTC", "ETH"],
    },
    "gold": {
        "id": "gold",
        "emoji": "🟡",
        "name_ru": "Gold & Commodities",
        "name_en": "Gold & Commodities",
        "color": "gold",
        "keywords": [
            "gold", "xau", "silver", "xag", "brent", "wti", "crude oil", "opec",
            "natural gas", "commodity", "commodities",
        ],
        "assets": ["XAUUSD", "OIL"],
    },
    "stocks": {
        "id": "stocks",
        "emoji": "📈",
        "name_ru": "Stocks",
        "name_en": "Stock Market",
        "color": "teal",
        "keywords": [
            "nasdaq", "s&p", "dow jones", "apple", "tesla", "nvidia", "microsoft",
            "amazon", "ipo", "earnings", "stock market", "wall street",
        ],
        "assets": ["NASDAQ", "SP500", "TSLA", "NVDA"],
    },
    "economic": {
        "id": "economic",
        "emoji": "📊",
        "name_ru": "Economic",
        "name_en": "Economic News",
        "color": "orange",
        "keywords": [
            "cpi", "pce", "gdp", "inflation", "unemployment", "nfp", "nonfarm",
            "payroll", "retail sales", "pmi", "jobless",
        ],
        "assets": ["DXY", "SP500", "XAUUSD"],
    },
    "central_banks": {
        "id": "central_banks",
        "emoji": "🏦",
        "name_ru": "Central Banks",
        "name_en": "Central Banks",
        "color": "navy",
        "keywords": [
            "federal reserve", "fed ", "fomc", "ecb", "bank of england", "boe",
            "bank of japan", "boj", "interest rate", "rate hike", "rate cut",
            "powell", "lagarde", "monetary policy",
        ],
        "assets": ["DXY", "EURUSD", "USDJPY", "XAUUSD"],
    },
    "geopolitics": {
        "id": "geopolitics",
        "emoji": "🌍",
        "name_ru": "Geopolitics",
        "name_en": "Geopolitics",
        "color": "red",
        "keywords": [
            "sanction", "war", "conflict", "trade war", "tariff", "geopolitic",
            "middle east", "nato", "election",
        ],
        "assets": ["OIL", "XAUUSD", "DXY"],
    },
    "whales": {
        "id": "whales",
        "emoji": "🐋",
        "name_ru": "Whales & Institutions",
        "name_en": "Whales & Institutions",
        "color": "cyan",
        "keywords": [
            "whale", "institutional", "etf inflow", "etf outflow", "blackrock",
            "grayscale", "liquidation", "open interest", "large transfer",
        ],
        "assets": ["BTC", "ETH"],
    },
    "technical": {
        "id": "technical",
        "emoji": "📉",
        "name_ru": "Technical",
        "name_en": "Technical Analysis",
        "color": "green",
        "keywords": [
            "support", "resistance", "breakout", "rsi", "macd", "volatility",
            "volume spike", "liquidity",
        ],
        "assets": [],
    },
    "sentiment": {
        "id": "sentiment",
        "emoji": "🌡",
        "name_ru": "Sentiment",
        "name_en": "Market Sentiment",
        "color": "gray",
        "keywords": [
            "fear and greed", "bullish", "bearish", "sentiment", "risk-on",
            "risk-off", "vix",
        ],
        "assets": [],
    },
}

PRIMARY_CATS = [
    "forex", "crypto", "gold", "stocks",
    "economic", "central_banks", "geopolitics", "whales",
]

def category_list_text(lang: str = "ru") -> str:
    lines = []
    for key in PRIMARY_CATS:
        c = CATEGORIES[key]
        name = c["name_ru"] if lang == "ru" else c["name_en"]
        lines.append(f"{c['emoji']} {name}")
    return "\n".join(lines)
