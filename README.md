# AiTrading — AI-Powered Day Trading Bot

An AI-powered day trading bot that uses AI (Claude, ChatGPT, Gemini, or Grok) to analyze markets and execute trades via Alpaca.

## How It Works

1. **Cron** triggers `run.py` every 5 minutes during market hours
2. `run.py` reads `prompts/prompt.md` (AI instructions) and `prompts/strategy.md` (trading rules)
3. The AI analyzes market data using tools (get prices, check positions, etc.)
4. The AI decides whether to trade based on the strategy — or sit out
5. All reasoning and actions are logged to `logs/`

## Supported AI Providers

| Provider | Env Value | Default Model | Est. Daily Cost | Install |
|---|---|---|---|---|
| **Claude** (Anthropic) | `claude` | `claude-sonnet-4-20250514` | $1.50–4.50 | `pip install anthropic` |
| **Gemini** (Google) | `gemini` | `gemini-2.5-flash` | $0.15–0.50 | `pip install google-generativeai` |
| **ChatGPT** (OpenAI) | `chatgpt` | `gpt-4.1` | $1–3 | `pip install openai` |
| **Grok** (xAI) | `grok` | `grok-3` | TBD | `pip install openai` |

## Project Structure

```
AiTrading/
├── run.py                      # Entry point — cron runs this
├── requirements.txt            # Python dependencies
├── .env.example                # Template for API keys
├── aitrading/                  # Core package
│   ├── config.py               # Configuration + centralized paths
│   ├── ai_provider.py          # AI provider abstraction (Claude, ChatGPT, Gemini, Grok)
│   ├── tools.py                # Alpaca API wrappers + code-level guardrails
│   └── tax_tracker.py          # Danish tax tracking for SKAT
├── prompts/                    # AI input files (editable)
│   ├── prompt.md               # System prompt — AI role and behavior
│   └── strategy.md             # Trading strategy playbook
├── docs/                       # Documentation
│   ├── SETUP_GUIDE.md          # Raspberry Pi setup + API key instructions
│   └── TAX_GUIDE.md            # Danish tax guide (SKAT, lagerbeskatning)
├── logs/                       # Trade logs (auto-generated, gitignored)
└── tax/                        # Tax records (auto-generated, gitignored)
```

## Setup

### 1. Install Dependencies

```bash
cd /path/to/AiTrading
python -m venv venv
source venv/bin/activate   # Linux/WSL
# or: venv\Scripts\activate  # Windows
pip install -r requirements.txt

# Install your chosen AI provider SDK:
pip install anthropic              # For Claude
# pip install openai               # For ChatGPT or Grok
# pip install google-generativeai  # For Gemini
```

### 2. Configure API Keys

```bash
cp .env.example .env
# Edit .env with your actual API keys
```

Key settings in `.env`:
```
AI_PROVIDER=claude          # or: chatgpt, gemini, grok
AI_API_KEY=your-key-here    # API key for your chosen provider
AI_MODEL=                   # Leave empty for default, or override
```

You also need:
- **Alpaca API key**: [app.alpaca.markets](https://app.alpaca.markets/) (sign up for paper trading)

### 3. Test Run

```bash
python run.py
```

### 4. Schedule with Cron (WSL/Linux)

```bash
crontab -e
# Add this line (runs every 5 min, weekdays, during market hours 9:35-15:45 ET):
*/5 9-15 * * 1-5 cd /path/to/AiTrading && /path/to/AiTrading/venv/bin/python run.py >> logs/cron.log 2>&1
```

### 4b. Schedule with Windows Task Scheduler (alternative)

1. Open Task Scheduler → Create Basic Task
2. Trigger: Daily, repeat every 5 minutes for 7 hours
3. Action: Start a program
   - Program: `C:\path\to\AiTrading\venv\Scripts\python.exe`
   - Arguments: `run.py`
   - Start in: `C:\path\to\AiTrading`

## Customization

- **Switch AI provider**: Change `AI_PROVIDER` and `AI_API_KEY` in `.env`
- **Change model**: Set `AI_MODEL` in `.env` (e.g., `claude-opus-4-20250514`, `gpt-4o`, `gemini-2.5-pro`)
- **Change strategy**: Edit `prompts/strategy.md` — takes effect on next run
- **Change AI behavior**: Edit `prompts/prompt.md`
- **Change watchlist**: Edit `WATCHLIST` in `aitrading/config.py`
- **Go live**: Set `ALPACA_PAPER=false` in `.env` (after extensive paper testing!)

## Safety

- **Paper trading by default** — no real money at risk
- **Hard-coded guardrails** in `aitrading/tools.py`: max 2% per trade, max 3 positions, max 3% daily loss
- All decisions are logged with full reasoning for review

## 🇩🇰 Danish Tax Reporting (SKAT)

Every trade is automatically recorded to `tax/transactions.csv` for SKAT compliance.

QQQ and SPY are US ETFs **not on SKAT's positivliste** — they are taxed as **kapitalindkomst** with **lagerbeskatning** (mark-to-market annually on unrealized gains).

📖 **Full guide**: [docs/TAX_GUIDE.md](docs/TAX_GUIDE.md)

### Tax Commands

```bash
# View yearly summary + export SKAT-ready CSV
python run.py --tax-report 2026

# Capture Dec 31 positions for lagerbeskatning
python run.py --year-end 2026

# Show tax help
python run.py --tax-help
```

### What's Tracked

- **Every buy/sell**: date, symbol, ISIN, qty, price, fees, order type
- **Year-end valuations**: market value on Dec 31 (for unrealized gains tax)
- **Dividends**: gross amount, US withholding tax, net received
- **SKAT export**: Danish-formatted CSV (Dato, Køb/Salg, ISIN, Kurs, Værdi)

⚠️ Always consult a Danish tax professional (revisor) for your specific situation.
