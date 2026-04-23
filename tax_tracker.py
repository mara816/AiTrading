"""
tax_tracker.py — Transaction tracking for Danish tax reporting (SKAT).

Tracks every transaction with all fields required by SKAT for:
- Kapitalindkomst (lagerbeskatning) for US ETFs like QQQ, SPY
- Year-end mark-to-market valuations for lagerbeskatning
- Full audit trail with fees, exchange rates, and AI reasoning

Generates CSV exports compatible with SKAT TastSelv reporting.

IMPORTANT TAX NOTES FOR DENMARK:
- QQQ (US46090E1038) and SPY (US78462F1030) are NOT on SKAT's positivliste
- They are taxed as KAPITALINDKOMST with LAGERBESKATNING (mark-to-market)
- This means you owe tax on UNREALIZED gains each year (Dec 31 valuation)
- Losses under lagerbeskatning are also deductible
- Always consult a tax professional for your specific situation
"""

import csv
import json
from datetime import datetime, date
from pathlib import Path
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")
DK = ZoneInfo("Europe/Copenhagen")

SCRIPT_DIR = Path(__file__).parent
TAX_DIR = SCRIPT_DIR / "tax"
TRANSACTIONS_FILE = TAX_DIR / "transactions.csv"
YEAR_END_FILE_TEMPLATE = "year_end_{year}.csv"
DIVIDENDS_FILE = TAX_DIR / "dividends.csv"

# ISIN codes for the default watchlist
ISIN_MAP = {
    "QQQ": "US46090E1038",
    "SPY": "US78462F1030",
}

# CSV column headers for the transactions file
TRANSACTION_HEADERS = [
    "transaction_id",       # Unique ID (Alpaca order ID)
    "date",                 # Trade date (YYYY-MM-DD)
    "time",                 # Trade time (HH:MM:SS ET)
    "symbol",               # Ticker symbol (e.g., QQQ)
    "isin",                 # ISIN code (for SKAT reporting)
    "side",                 # buy or sell
    "quantity",             # Number of shares
    "price_per_share_usd",  # Execution price in USD
    "total_value_usd",      # Total trade value in USD (qty × price)
    "fees_usd",             # Trading fees/commissions in USD
    "order_type",           # market, limit, stop, stop_limit
    "order_status",         # filled, partially_filled, etc.
    "currency",             # Always USD for Alpaca
    "exchange",             # NASDAQ, NYSE, etc.
    "account_equity_usd",   # Account equity at time of trade
    "daily_pnl_usd",        # Daily P&L at time of trade
    "ai_provider",          # Which AI made the decision
    "ai_reasoning",         # Why the AI made this trade (from logs)
    "paper_trade",          # true/false — was this paper trading?
]

YEAR_END_HEADERS = [
    "year",                 # Tax year
    "symbol",               # Ticker symbol
    "isin",                 # ISIN code
    "quantity_held",        # Shares held on Dec 31
    "avg_cost_basis_usd",   # Average purchase price per share
    "total_cost_basis_usd", # Total cost basis
    "market_price_dec31_usd",  # Market price on Dec 31
    "market_value_dec31_usd",  # Total market value on Dec 31
    "unrealized_gain_loss_usd",  # Unrealized gain/loss for the year
    "realized_gain_loss_usd",    # Realized gain/loss from sales during the year
    "total_gain_loss_usd",       # Total (unrealized + realized)
    "tax_type",                  # "kapitalindkomst_lager" for QQQ/SPY
    "currency",                  # USD
    "note",                      # Additional notes
]

DIVIDEND_HEADERS = [
    "date",                 # Payment date
    "symbol",               # Ticker symbol
    "isin",                 # ISIN code
    "gross_amount_usd",     # Gross dividend in USD
    "tax_withheld_usd",     # US withholding tax (typically 15% with W-8BEN)
    "net_amount_usd",       # Net dividend received
    "withholding_rate_pct", # Withholding rate applied
    "currency",             # USD
]


def _ensure_tax_dir():
    """Create the tax directory if it doesn't exist."""
    TAX_DIR.mkdir(exist_ok=True)


def _file_exists_with_headers(filepath: Path, headers: list[str]) -> bool:
    """Check if a CSV file exists and has the correct headers."""
    if not filepath.exists():
        return False
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            existing_headers = next(reader, None)
            return existing_headers == headers
    except Exception:
        return False


def _ensure_csv(filepath: Path, headers: list[str]):
    """Create a CSV file with headers if it doesn't exist."""
    _ensure_tax_dir()
    if not _file_exists_with_headers(filepath, headers):
        with open(filepath, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(headers)


def record_transaction(
    order_id: str,
    symbol: str,
    side: str,
    quantity: float,
    price_per_share: float,
    fees: float = 0.0,
    order_type: str = "market",
    order_status: str = "filled",
    account_equity: float = 0.0,
    daily_pnl: float = 0.0,
    ai_provider: str = "",
    ai_reasoning: str = "",
    paper_trade: bool = True,
):
    """
    Record a transaction to the tax CSV file.
    Called automatically after every successful order.
    """
    _ensure_csv(TRANSACTIONS_FILE, TRANSACTION_HEADERS)

    now_et = datetime.now(ET)
    isin = ISIN_MAP.get(symbol.upper(), "")
    total_value = quantity * price_per_share

    row = [
        order_id,
        now_et.strftime("%Y-%m-%d"),
        now_et.strftime("%H:%M:%S"),
        symbol.upper(),
        isin,
        side.lower(),
        f"{quantity:.4f}",
        f"{price_per_share:.4f}",
        f"{total_value:.2f}",
        f"{fees:.2f}",
        order_type,
        order_status,
        "USD",
        "",  # exchange — filled later if available
        f"{account_equity:.2f}",
        f"{daily_pnl:.2f}",
        ai_provider,
        ai_reasoning.replace("\n", " ").replace(",", ";")[:500],  # Sanitize for CSV
        str(paper_trade).lower(),
    ]

    with open(TRANSACTIONS_FILE, "a", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(row)


def record_dividend(
    symbol: str,
    gross_amount: float,
    tax_withheld: float,
    payment_date: str | None = None,
):
    """Record a dividend payment for tax reporting."""
    _ensure_csv(DIVIDENDS_FILE, DIVIDEND_HEADERS)

    if payment_date is None:
        payment_date = datetime.now(DK).strftime("%Y-%m-%d")

    isin = ISIN_MAP.get(symbol.upper(), "")
    net_amount = gross_amount - tax_withheld
    rate = (tax_withheld / gross_amount * 100) if gross_amount > 0 else 0

    row = [
        payment_date,
        symbol.upper(),
        isin,
        f"{gross_amount:.2f}",
        f"{tax_withheld:.2f}",
        f"{net_amount:.2f}",
        f"{rate:.1f}",
        "USD",
    ]

    with open(DIVIDENDS_FILE, "a", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(row)


def generate_year_end_report(year: int, positions: list[dict], realized_gains: dict | None = None):
    """
    Generate a year-end mark-to-market report for lagerbeskatning.

    Call this on Dec 31 (or Jan 1) with current positions and their market values.
    This is the key document for SKAT's lagerbeskatning.

    Args:
        year: Tax year (e.g., 2026)
        positions: List of dicts with keys: symbol, qty, avg_entry_price, current_price, market_value, cost_basis
        realized_gains: Optional dict of {symbol: realized_gain_usd} from sales during the year
    """
    filepath = TAX_DIR / YEAR_END_FILE_TEMPLATE.format(year=year)
    _ensure_csv(filepath, YEAR_END_HEADERS)

    if realized_gains is None:
        realized_gains = {}

    rows = []
    for pos in positions:
        symbol = pos.get("symbol", "")
        qty = float(pos.get("qty", 0))
        avg_cost = float(pos.get("avg_entry_price", 0))
        current_price = float(pos.get("current_price", 0))
        cost_basis = qty * avg_cost
        market_value = qty * current_price
        unrealized_gl = market_value - cost_basis
        realized_gl = realized_gains.get(symbol, 0.0)
        total_gl = unrealized_gl + realized_gl

        isin = ISIN_MAP.get(symbol.upper(), "")

        rows.append([
            str(year),
            symbol.upper(),
            isin,
            f"{qty:.4f}",
            f"{avg_cost:.4f}",
            f"{cost_basis:.2f}",
            f"{current_price:.4f}",
            f"{market_value:.2f}",
            f"{unrealized_gl:.2f}",
            f"{realized_gl:.2f}",
            f"{total_gl:.2f}",
            "kapitalindkomst_lager",
            "USD",
            "US ETF — not on SKAT positivliste — lagerbeskatning applies",
        ])

    with open(filepath, "a", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerows(rows)

    return str(filepath)


def get_yearly_summary(year: int) -> dict:
    """
    Calculate a summary of all transactions for a given tax year.
    Useful for verifying your SKAT reporting.
    """
    if not TRANSACTIONS_FILE.exists():
        return {"error": "No transactions recorded yet"}

    buys = []
    sells = []
    total_fees = 0.0

    with open(TRANSACTIONS_FILE, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if not row["date"].startswith(str(year)):
                continue

            total_fees += float(row.get("fees_usd", 0))

            entry = {
                "date": row["date"],
                "symbol": row["symbol"],
                "isin": row["isin"],
                "quantity": float(row["quantity"]),
                "price": float(row["price_per_share_usd"]),
                "total": float(row["total_value_usd"]),
                "paper": row.get("paper_trade", "true") == "true",
            }

            if row["side"] == "buy":
                buys.append(entry)
            elif row["side"] == "sell":
                sells.append(entry)

    # Calculate realized gains per symbol
    realized_by_symbol = {}
    for sell in sells:
        sym = sell["symbol"]
        if sym not in realized_by_symbol:
            realized_by_symbol[sym] = {"total_sold": 0, "total_bought": 0, "qty_sold": 0}
        realized_by_symbol[sym]["total_sold"] += sell["total"]
        realized_by_symbol[sym]["qty_sold"] += sell["quantity"]

    for buy in buys:
        sym = buy["symbol"]
        if sym in realized_by_symbol:
            realized_by_symbol[sym]["total_bought"] += buy["total"]

    return {
        "year": year,
        "total_buys": len(buys),
        "total_sells": len(sells),
        "total_buy_value_usd": sum(b["total"] for b in buys),
        "total_sell_value_usd": sum(s["total"] for s in sells),
        "total_fees_usd": total_fees,
        "realized_by_symbol": realized_by_symbol,
        "has_paper_trades": any(b["paper"] for b in buys + sells),
        "symbols_traded": list(set(b["symbol"] for b in buys + sells)),
    }


def get_transactions_for_skat(year: int) -> str:
    """
    Export all transactions for a tax year in a format suitable for SKAT reporting.
    Returns the path to the generated CSV.
    """
    if not TRANSACTIONS_FILE.exists():
        return "No transactions recorded yet"

    export_path = TAX_DIR / f"skat_export_{year}.csv"

    skat_headers = [
        "Dato",             # Date
        "Type",             # Køb/Salg (Buy/Sell)
        "Symbol",           # Ticker
        "ISIN",             # International Securities ID
        "Antal",            # Quantity
        "Kurs (USD)",       # Price per share
        "Værdi (USD)",      # Total value
        "Gebyrer (USD)",    # Fees
        "Papirhandel",      # Paper trade (Ja/Nej)
    ]

    rows = []
    with open(TRANSACTIONS_FILE, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if not row["date"].startswith(str(year)):
                continue
            rows.append([
                row["date"],
                "Køb" if row["side"] == "buy" else "Salg",
                row["symbol"],
                row["isin"],
                row["quantity"],
                row["price_per_share_usd"],
                row["total_value_usd"],
                row["fees_usd"],
                "Ja" if row.get("paper_trade", "true") == "true" else "Nej",
            ])

    with open(export_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(skat_headers)
        writer.writerows(rows)

    return str(export_path)
