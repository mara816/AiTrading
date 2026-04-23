"""
tools.py — Alpaca API wrappers and Claude tool schema definitions.

Each tool function wraps an Alpaca SDK call and returns a JSON-serializable dict.
Code-level guardrails are enforced in place_order() to prevent the AI from
exceeding risk limits, regardless of what the prompt says.
"""

import json
from datetime import datetime, timedelta
from typing import Any

from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest, StockLatestQuoteRequest
from alpaca.data.timeframe import TimeFrame
from alpaca.trading.client import TradingClient
from alpaca.trading.enums import OrderSide, OrderType, TimeInForce, QueryOrderStatus
from alpaca.trading.requests import (
    GetOrdersRequest,
    LimitOrderRequest,
    MarketOrderRequest,
    StopLimitOrderRequest,
    StopOrderRequest,
)
from alpaca.trading.models import Clock

import config
from tax_tracker import record_transaction

# --- Clients (initialized once) ---

trading_client = TradingClient(
    api_key=config.ALPACA_API_KEY,
    secret_key=config.ALPACA_SECRET_KEY,
    paper=config.ALPACA_PAPER,
)

data_client = StockHistoricalDataClient(
    api_key=config.ALPACA_API_KEY,
    secret_key=config.ALPACA_SECRET_KEY,
)


# --- Helper ---

def _serialize(obj: Any) -> Any:
    """Recursively convert Alpaca model objects to JSON-serializable dicts."""
    if obj is None:
        return None
    if isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, dict):
        return {k: _serialize(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_serialize(i) for i in obj]
    if hasattr(obj, "__dict__"):
        return {k: _serialize(v) for k, v in obj.__dict__.items() if not k.startswith("_")}
    return str(obj)


# --- Tool Functions ---

def get_account() -> dict:
    """Get account info: equity, cash, buying power, daily P&L."""
    account = trading_client.get_account()
    return {
        "equity": str(account.equity),
        "cash": str(account.cash),
        "buying_power": str(account.buying_power),
        "portfolio_value": str(account.portfolio_value),
        "last_equity": str(account.last_equity),
        "daily_pnl": str(float(account.equity) - float(account.last_equity)),
        "daily_pnl_pct": str(
            round(
                (float(account.equity) - float(account.last_equity))
                / float(account.last_equity)
                * 100,
                3,
            )
            if float(account.last_equity) > 0
            else "0"
        ),
        "paper": config.ALPACA_PAPER,
    }


def get_positions() -> dict:
    """Get all open positions with unrealized P&L."""
    positions = trading_client.get_all_positions()
    result = []
    for p in positions:
        result.append({
            "symbol": p.symbol,
            "qty": str(p.qty),
            "side": str(p.side),
            "market_value": str(p.market_value),
            "cost_basis": str(p.cost_basis),
            "unrealized_pl": str(p.unrealized_pl),
            "unrealized_plpc": str(p.unrealized_plpc),
            "current_price": str(p.current_price),
            "avg_entry_price": str(p.avg_entry_price),
        })
    return {"positions": result, "count": len(result)}


def get_bars(symbol: str, timeframe: str = "5Min", limit: int = 50) -> dict:
    """
    Get historical OHLCV bars for a symbol.
    timeframe: '1Min', '5Min', '15Min', '1Hour', '1Day'
    limit: number of bars to return (max 1000)
    """
    tf_map = {
        "1Min": TimeFrame.Minute,
        "5Min": TimeFrame(5, TimeFrame.Minute.unit),
        "15Min": TimeFrame(15, TimeFrame.Minute.unit),
        "1Hour": TimeFrame.Hour,
        "1Day": TimeFrame.Day,
    }
    tf = tf_map.get(timeframe, TimeFrame(5, TimeFrame.Minute.unit))
    limit = min(limit, 1000)

    request = StockBarsRequest(
        symbol_or_symbols=symbol,
        timeframe=tf,
        limit=limit,
    )
    bars = data_client.get_stock_bars(request)

    result = []
    if symbol in bars.data:
        for bar in bars.data[symbol]:
            result.append({
                "timestamp": bar.timestamp.isoformat(),
                "open": float(bar.open),
                "high": float(bar.high),
                "low": float(bar.low),
                "close": float(bar.close),
                "volume": int(bar.volume),
                "vwap": float(bar.vwap) if bar.vwap else None,
            })

    return {"symbol": symbol, "timeframe": timeframe, "bars": result, "count": len(result)}


def get_latest_quote(symbol: str) -> dict:
    """Get the latest bid/ask/last quote for a symbol."""
    request = StockLatestQuoteRequest(symbol_or_symbols=symbol)
    quotes = data_client.get_stock_latest_quote(request)

    if symbol in quotes:
        q = quotes[symbol]
        return {
            "symbol": symbol,
            "bid_price": float(q.bid_price),
            "ask_price": float(q.ask_price),
            "bid_size": int(q.bid_size),
            "ask_size": int(q.ask_size),
            "timestamp": q.timestamp.isoformat(),
        }
    return {"symbol": symbol, "error": "No quote available"}


def get_clock() -> dict:
    """Get market clock: whether market is open, next open/close times."""
    clock = trading_client.get_clock()
    return {
        "is_open": clock.is_open,
        "next_open": clock.next_open.isoformat() if clock.next_open else None,
        "next_close": clock.next_close.isoformat() if clock.next_close else None,
        "timestamp": clock.timestamp.isoformat() if clock.timestamp else None,
    }


def place_order(
    symbol: str,
    qty: float,
    side: str,
    order_type: str = "market",
    time_in_force: str = "day",
    limit_price: float | None = None,
    stop_price: float | None = None,
) -> dict:
    """
    Place a trade order with code-level guardrails.

    side: 'buy' or 'sell'
    order_type: 'market', 'limit', 'stop', 'stop_limit'
    time_in_force: 'day', 'gtc', 'ioc', 'fok'
    """
    # --- GUARDRAILS (enforced in code, not bypassable by the AI) ---

    # 0. Validate inputs
    if qty <= 0:
        return {"error": "GUARDRAIL: qty must be positive.", "order_placed": False}

    # 0b. Enforce watchlist — only trade allowed symbols
    if symbol.upper() not in [s.upper() for s in config.WATCHLIST]:
        return {
            "error": f"GUARDRAIL: {symbol} is not in the watchlist ({', '.join(config.WATCHLIST)}). Trade rejected.",
            "order_placed": False,
        }
    symbol = symbol.upper()

    account = trading_client.get_account()
    equity = float(account.equity)
    last_equity = float(account.last_equity)
    daily_pnl_pct = ((equity - last_equity) / last_equity * 100) if last_equity > 0 else 0

    # 1. Check daily loss limit
    if daily_pnl_pct <= -config.MAX_DAILY_LOSS_PCT:
        return {
            "error": f"GUARDRAIL: Daily loss limit hit ({daily_pnl_pct:.2f}%). No more trades today.",
            "order_placed": False,
        }

    # 2. Check positions
    positions = trading_client.get_all_positions()
    held_symbols = [p.symbol for p in positions]

    if side.lower() == "buy":
        # 2a. Max concurrent positions
        if len(positions) >= config.MAX_CONCURRENT_POSITIONS:
            return {
                "error": f"GUARDRAIL: Max {config.MAX_CONCURRENT_POSITIONS} concurrent positions reached.",
                "order_placed": False,
            }
        # 2b. No duplicate positions on same symbol
        if symbol in held_symbols:
            return {
                "error": f"GUARDRAIL: Already holding a position in {symbol}. Max 1 position per symbol.",
                "order_placed": False,
            }

    if side.lower() == "sell":
        # 2c. Only sell if you actually hold the symbol (prevent naked shorts)
        if symbol not in held_symbols:
            return {
                "error": f"GUARDRAIL: Cannot sell {symbol} — no position held. Naked shorts not allowed.",
                "order_placed": False,
            }

    # 3. Check max risk per trade
    quote = get_latest_quote(symbol)
    if "error" not in quote:
        estimated_cost = qty * quote.get("ask_price", 0)
        max_allowed = equity * (config.MAX_RISK_PER_TRADE_PCT / 100)
        if estimated_cost > max_allowed:
            return {
                "error": f"GUARDRAIL: Order value ${estimated_cost:.2f} exceeds max ${max_allowed:.2f} "
                         f"({config.MAX_RISK_PER_TRADE_PCT}% of ${equity:.2f} equity).",
                "order_placed": False,
            }

    # --- Place the order ---

    side_enum = OrderSide.BUY if side.lower() == "buy" else OrderSide.SELL
    tif_map = {
        "day": TimeInForce.DAY,
        "gtc": TimeInForce.GTC,
        "ioc": TimeInForce.IOC,
        "fok": TimeInForce.FOK,
    }
    tif = tif_map.get(time_in_force.lower(), TimeInForce.DAY)

    order_request: MarketOrderRequest | LimitOrderRequest | StopOrderRequest | StopLimitOrderRequest

    if order_type == "market":
        order_request = MarketOrderRequest(
            symbol=symbol, qty=qty, side=side_enum, time_in_force=tif
        )
    elif order_type == "limit":
        if limit_price is None:
            return {"error": "limit_price required for limit orders", "order_placed": False}
        order_request = LimitOrderRequest(
            symbol=symbol, qty=qty, side=side_enum, time_in_force=tif, limit_price=limit_price
        )
    elif order_type == "stop":
        if stop_price is None:
            return {"error": "stop_price required for stop orders", "order_placed": False}
        order_request = StopOrderRequest(
            symbol=symbol, qty=qty, side=side_enum, time_in_force=tif, stop_price=stop_price
        )
    elif order_type == "stop_limit":
        if limit_price is None or stop_price is None:
            return {"error": "limit_price and stop_price required for stop_limit orders", "order_placed": False}
        order_request = StopLimitOrderRequest(
            symbol=symbol, qty=qty, side=side_enum, time_in_force=tif,
            limit_price=limit_price, stop_price=stop_price
        )
    else:
        return {"error": f"Unknown order type: {order_type}", "order_placed": False}

    order = trading_client.submit_order(order_request)

    # Record transaction for tax reporting (SKAT)
    fill_price = limit_price or (quote.get("ask_price", 0) if "error" not in quote else 0)
    record_transaction(
        order_id=str(order.id),
        symbol=order.symbol,
        side=side.lower(),
        quantity=qty,
        price_per_share=fill_price,
        fees=0.0,  # Alpaca has zero commission for stocks
        order_type=order_type,
        order_status=str(order.status),
        account_equity=equity,
        daily_pnl=equity - last_equity,
        ai_provider=config.AI_PROVIDER,
        paper_trade=config.ALPACA_PAPER,
    )

    return {
        "order_placed": True,
        "order_id": str(order.id),
        "symbol": order.symbol,
        "qty": str(order.qty),
        "side": str(order.side),
        "type": str(order.type),
        "status": str(order.status),
        "time_in_force": str(order.time_in_force),
        "limit_price": str(order.limit_price) if order.limit_price else None,
        "stop_price": str(order.stop_price) if order.stop_price else None,
    }


def get_open_orders() -> dict:
    """Get all open/pending orders."""
    request = GetOrdersRequest(status=QueryOrderStatus.OPEN)
    orders = trading_client.get_orders(request)
    result = []
    for o in orders:
        result.append({
            "order_id": str(o.id),
            "symbol": o.symbol,
            "qty": str(o.qty),
            "side": str(o.side),
            "type": str(o.type),
            "status": str(o.status),
            "limit_price": str(o.limit_price) if o.limit_price else None,
            "stop_price": str(o.stop_price) if o.stop_price else None,
            "created_at": o.created_at.isoformat() if o.created_at else None,
        })
    return {"orders": result, "count": len(result)}


def cancel_order(order_id: str) -> dict:
    """Cancel a pending order by its ID."""
    try:
        trading_client.cancel_order_by_id(order_id)
        return {"cancelled": True, "order_id": order_id}
    except Exception as e:
        return {"cancelled": False, "order_id": order_id, "error": str(e)}


def close_position(symbol: str) -> dict:
    """Close an entire position for a symbol."""
    try:
        # Get position info before closing (for tax tracking)
        positions = get_positions()
        pos_info = None
        if isinstance(positions, list):
            for p in positions:
                if p.get("symbol") == symbol.upper():
                    pos_info = p
                    break

        order = trading_client.close_position(symbol)

        # Record the sell transaction for tax reporting
        if pos_info:
            qty = abs(float(pos_info.get("qty", 0)))
            current_price = float(pos_info.get("current_price", 0))
            try:
                account = trading_client.get_account()
                equity = float(account.equity)
            except Exception:
                equity = 0.0

            record_transaction(
                order_id=str(order.id) if hasattr(order, "id") else "close-" + symbol,
                symbol=symbol.upper(),
                side="sell",
                quantity=qty,
                price_per_share=current_price,
                fees=0.0,
                order_type="market",
                order_status="filled",
                account_equity=equity,
                ai_provider=config.AI_PROVIDER,
                paper_trade=config.ALPACA_PAPER,
            )

        return {
            "closed": True,
            "symbol": symbol,
            "order_id": str(order.id) if hasattr(order, "id") else None,
        }
    except Exception as e:
        return {"closed": False, "symbol": symbol, "error": str(e)}


# --- Claude Tool Schemas ---

TOOL_SCHEMAS = [
    {
        "name": "get_account",
        "description": "Get your trading account info: equity, cash, buying power, and daily P&L. Call this first to understand your current financial position.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "get_positions",
        "description": "Get all currently open positions with unrealized profit/loss. Use this to check what you're currently holding before making new trades.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "get_bars",
        "description": "Get historical OHLCV (Open, High, Low, Close, Volume) price bars for a symbol. Use this for technical analysis — compute VWAP, RSI, moving averages, support/resistance, opening range, etc.",
        "input_schema": {
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "Stock ticker symbol (e.g., 'QQQ', 'SPY')",
                },
                "timeframe": {
                    "type": "string",
                    "enum": ["1Min", "5Min", "15Min", "1Hour", "1Day"],
                    "description": "Bar timeframe. Use '5Min' for intraday scalping analysis.",
                },
                "limit": {
                    "type": "integer",
                    "description": "Number of bars to return (default 50, max 1000). Use more bars for longer-term analysis.",
                },
            },
            "required": ["symbol"],
        },
    },
    {
        "name": "get_latest_quote",
        "description": "Get the latest bid/ask quote for a symbol. Use this for current price checks before placing orders.",
        "input_schema": {
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "Stock ticker symbol (e.g., 'QQQ', 'SPY')",
                },
            },
            "required": ["symbol"],
        },
    },
    {
        "name": "place_order",
        "description": "Place a buy or sell order. ALWAYS explain your reasoning before calling this. Guardrails are enforced: max 2% equity per trade, max 3 positions, max 3% daily loss.",
        "input_schema": {
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "Stock ticker symbol",
                },
                "qty": {
                    "type": "number",
                    "description": "Number of shares to trade",
                },
                "side": {
                    "type": "string",
                    "enum": ["buy", "sell"],
                    "description": "Buy or sell",
                },
                "order_type": {
                    "type": "string",
                    "enum": ["market", "limit", "stop", "stop_limit"],
                    "description": "Order type. Use 'limit' for precise entries, 'stop' or 'stop_limit' for stop losses.",
                },
                "time_in_force": {
                    "type": "string",
                    "enum": ["day", "gtc", "ioc", "fok"],
                    "description": "How long the order stays active. 'day' = expires end of day. 'gtc' = good til cancelled.",
                },
                "limit_price": {
                    "type": "number",
                    "description": "Limit price (required for 'limit' and 'stop_limit' orders)",
                },
                "stop_price": {
                    "type": "number",
                    "description": "Stop trigger price (required for 'stop' and 'stop_limit' orders)",
                },
            },
            "required": ["symbol", "qty", "side"],
        },
    },
    {
        "name": "get_open_orders",
        "description": "Get all currently open/pending orders. Use this to check if you have any orders waiting to be filled.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "cancel_order",
        "description": "Cancel a pending order by its order ID.",
        "input_schema": {
            "type": "object",
            "properties": {
                "order_id": {
                    "type": "string",
                    "description": "The order ID to cancel",
                },
            },
            "required": ["order_id"],
        },
    },
    {
        "name": "get_clock",
        "description": "Get the market clock: whether the market is currently open, and the next open/close times. Use this to verify market hours before trading.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "close_position",
        "description": "Close an entire position for a symbol (sells all shares). Use this when your exit criteria are met or to cut losses.",
        "input_schema": {
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "Stock ticker symbol to close position for",
                },
            },
            "required": ["symbol"],
        },
    },
]

# Map tool names to functions for the orchestrator
TOOL_FUNCTIONS = {
    "get_account": lambda **kwargs: get_account(),
    "get_positions": lambda **kwargs: get_positions(),
    "get_bars": lambda **kwargs: get_bars(**kwargs),
    "get_latest_quote": lambda **kwargs: get_latest_quote(**kwargs),
    "place_order": lambda **kwargs: place_order(**kwargs),
    "get_open_orders": lambda **kwargs: get_open_orders(),
    "cancel_order": lambda **kwargs: cancel_order(**kwargs),
    "close_position": lambda **kwargs: close_position(**kwargs),
    "get_clock": lambda **kwargs: get_clock(),
}
