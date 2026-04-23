import os
from dotenv import load_dotenv

load_dotenv()


def _require(key: str) -> str:
    value = os.getenv(key)
    if not value:
        raise EnvironmentError(f"Missing required environment variable: {key}")
    return value


# --- AI Provider Configuration ---
# Supported: "claude", "chatgpt", "gemini", "grok"
AI_PROVIDER = os.getenv("AI_PROVIDER", "claude")
AI_API_KEY = _require("AI_API_KEY")
# Model override (leave empty to use default for provider)
AI_MODEL = os.getenv("AI_MODEL", "")

# --- Alpaca Configuration ---
ALPACA_API_KEY = _require("ALPACA_API_KEY")
ALPACA_SECRET_KEY = _require("ALPACA_SECRET_KEY")
ALPACA_PAPER = os.getenv("ALPACA_PAPER", "true").lower() == "true"

# Trading guardrails (hard limits enforced in code)
MAX_RISK_PER_TRADE_PCT = 2.0      # Max % of equity per trade
MAX_CONCURRENT_POSITIONS = 3       # Max open positions at once
MAX_DAILY_LOSS_PCT = 3.0           # Max daily loss % before stopping
MAX_TOOL_ITERATIONS = 10           # Safety limit on AI tool-use loop

# Watchlist
WATCHLIST = ["QQQ", "SPY"]

# Alpaca base URL
ALPACA_BASE_URL = (
    "https://paper-api.alpaca.markets"
    if ALPACA_PAPER
    else "https://api.alpaca.markets"
)
