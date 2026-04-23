#!/usr/bin/env python3
"""
run.py — Main orchestrator for the AI trading bot.

Reads prompt.md + strategy.md, calls Claude API with Alpaca tools,
handles the tool-use loop, and logs everything.
"""

import fcntl
import json
import os
import sys
from datetime import datetime, date
from pathlib import Path
from zoneinfo import ZoneInfo

import config
from ai_provider import get_provider
from tools import TOOL_SCHEMAS, TOOL_FUNCTIONS, trading_client

# --- Constants ---

SCRIPT_DIR = Path(__file__).parent
PROMPT_FILE = SCRIPT_DIR / "prompt.md"
STRATEGY_FILE = SCRIPT_DIR / "strategy.md"
LOG_DIR = SCRIPT_DIR / "logs"
STATE_FILE = SCRIPT_DIR / "state.json"
LOCK_FILE = SCRIPT_DIR / ".run.lock"

ET = ZoneInfo("America/New_York")


# --- Helpers ---

def get_eastern_time() -> datetime:
    return datetime.now(ET)


def is_market_open() -> bool:
    """Use Alpaca's clock API to determine if the market is open."""
    try:
        clock = trading_client.get_clock()
        return clock.is_open
    except Exception:
        # Fallback to time-based check if API fails
        now = get_eastern_time()
        if now.weekday() >= 5:
            return False
        market_open = now.replace(hour=9, minute=35, second=0, microsecond=0)
        market_close = now.replace(hour=15, minute=45, second=0, microsecond=0)
        return market_open <= now <= market_close


def read_file(path: Path) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def load_state() -> dict:
    """Load persistent state (ORB used today, loss streak, etc.)."""
    if STATE_FILE.exists():
        with open(STATE_FILE, "r") as f:
            state = json.load(f)
        # Reset state if it's a new day
        if state.get("date") != date.today().isoformat():
            return {"date": date.today().isoformat(), "orb_used": False, "consecutive_losses": 0, "trades_today": 0}
        return state
    return {"date": date.today().isoformat(), "orb_used": False, "consecutive_losses": 0, "trades_today": 0}


def save_state(state: dict):
    """Persist state to disk."""
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def setup_logging() -> Path:
    """Create log directory and return today's log file path."""
    LOG_DIR.mkdir(exist_ok=True)
    today = get_eastern_time().strftime("%Y-%m-%d")
    return LOG_DIR / f"{today}.log"


def log(log_file: Path, message: str):
    """Append a timestamped message to the log file and print to stdout."""
    timestamp = get_eastern_time().strftime("%Y-%m-%d %H:%M:%S ET")
    entry = f"[{timestamp}] {message}"
    print(entry)
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(entry + "\n")


def execute_tool(tool_name: str, tool_input: dict) -> tuple[str, bool]:
    """Execute a tool function. Returns (result_json, is_error)."""
    func = TOOL_FUNCTIONS.get(tool_name)
    if not func:
        return json.dumps({"error": f"Unknown tool: {tool_name}"}), True
    try:
        result = func(**tool_input)
        is_error = isinstance(result, dict) and "error" in result
        return json.dumps(result, default=str), is_error
    except Exception as e:
        return json.dumps({"error": f"Tool execution failed: {str(e)}"}), True


# --- Main ---

def run():
    log_file = setup_logging()
    log(log_file, "=" * 60)
    log(log_file, "RUN STARTED")

    # Market hours check via Alpaca clock
    if not is_market_open():
        now = get_eastern_time()
        log(log_file, f"Market is closed ({now.strftime('%H:%M ET, %A')}). Skipping.")
        return

    # Load persistent state
    state = load_state()
    log(log_file, f"State: ORB used={state['orb_used']}, losses={state['consecutive_losses']}, trades={state['trades_today']}")

    # Read prompt and strategy files
    if not PROMPT_FILE.exists():
        log(log_file, f"ERROR: {PROMPT_FILE} not found")
        sys.exit(1)
    if not STRATEGY_FILE.exists():
        log(log_file, f"ERROR: {STRATEGY_FILE} not found")
        sys.exit(1)

    system_prompt = read_file(PROMPT_FILE)
    strategy = read_file(STRATEGY_FILE)

    now = get_eastern_time()
    state_info = (
        f"## Session State\n"
        f"- ORB trade taken today: {'Yes' if state['orb_used'] else 'No'}\n"
        f"- Consecutive losses today: {state['consecutive_losses']}\n"
        f"- Total trades today: {state['trades_today']}\n"
    )

    user_message = (
        f"Current time: {now.strftime('%Y-%m-%d %H:%M:%S ET (%A)')}\n\n"
        f"{state_info}\n"
        f"## Trading Strategy\n\n{strategy}\n\n"
        f"---\n\n"
        f"Analyze the market and execute your strategy. "
        f"Follow the decision framework step by step. "
        f"Watchlist: {', '.join(config.WATCHLIST)}"
    )

    log(log_file, f"Time: {now.strftime('%H:%M:%S ET')}")
    log(log_file, f"Provider: {config.AI_PROVIDER}")
    log(log_file, f"Watchlist: {', '.join(config.WATCHLIST)}")

    # Initialize AI provider
    provider = get_provider()
    log(log_file, f"Model: {config.AI_MODEL}")

    # Track state changes via a wrapper around execute_tool
    def execute_and_track(tool_name, tool_input):
        result_str, is_error = execute_tool(tool_name, tool_input)
        if tool_name == "place_order" and not is_error:
            try:
                result_data = json.loads(result_str)
                if result_data.get("order_placed"):
                    state["trades_today"] += 1
            except json.JSONDecodeError:
                pass
        return result_str, is_error

    # Run the AI conversation with tool use
    provider.chat_with_tools(
        system_prompt=system_prompt,
        user_message=user_message,
        tool_schemas=TOOL_SCHEMAS,
        execute_tool_fn=execute_and_track,
        log_fn=lambda msg: log(log_file, msg),
        max_iterations=config.MAX_TOOL_ITERATIONS,
    )

    # Save updated state
    save_state(state)

    log(log_file, "RUN COMPLETED")
    log(log_file, "=" * 60 + "\n")


if __name__ == "__main__":
    # File-based lock to prevent overlapping cron runs
    lock_fp = open(LOCK_FILE, "w")
    try:
        fcntl.flock(lock_fp, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        print("Another run is already in progress. Exiting.")
        sys.exit(0)

    try:
        run()
    finally:
        fcntl.flock(lock_fp, fcntl.LOCK_UN)
        lock_fp.close()
