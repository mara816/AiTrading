# AiTrading — AI-Powered Day Trading Bot

An AI-powered day trading bot that uses AI (Claude, ChatGPT, Gemini, or Grok) to analyze markets and execute trades via Alpaca.

## How It Works

1. **Cron** triggers `run.py` every 5 minutes during market hours
2. `run.py` reads `prompt.md` (AI instructions) and `strategy.md` (trading rules)
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
*/5 9-15 * * 1-5 cd /mnt/c/Users/mteu/repos/Personal/AiTrading && /mnt/c/Users/mteu/repos/Personal/AiTrading/venv/bin/python run.py >> logs/cron.log 2>&1
```

### 4b. Schedule with Windows Task Scheduler (alternative)

1. Open Task Scheduler → Create Basic Task
2. Trigger: Daily, repeat every 5 minutes for 7 hours
3. Action: Start a program
   - Program: `C:\Users\mteu\repos\Personal\AiTrading\venv\Scripts\python.exe`
   - Arguments: `run.py`
   - Start in: `C:\Users\mteu\repos\Personal\AiTrading`

## Files

| File | Purpose |
|---|---|
| `prompt.md` | System prompt — defines the AI's role and behavior |
| `strategy.md` | Trading strategy playbook — the rules the AI follows |
| `run.py` | Main orchestrator — connects AI to Alpaca |
| `ai_provider.py` | AI provider abstraction — Claude, ChatGPT, Gemini, Grok |
| `tools.py` | Tool definitions — Alpaca API wrappers with guardrails |
| `config.py` | Configuration — loads API keys and settings |
| `logs/` | Trade logs — timestamped reasoning and actions |

## Customization

- **Switch AI provider**: Change `AI_PROVIDER` and `AI_API_KEY` in `.env`
- **Change model**: Set `AI_MODEL` in `.env` (e.g., `claude-opus-4-20250514`, `gpt-4o`, `gemini-2.5-pro`)
- **Change strategy**: Edit `strategy.md` — takes effect on next run
- **Change AI behavior**: Edit `prompt.md`
- **Change watchlist**: Edit `WATCHLIST` in `config.py`
- **Go live**: Set `ALPACA_PAPER=false` in `.env` (after extensive paper testing!)

## Safety

- **Paper trading by default** — no real money at risk
- **Hard-coded guardrails** in `tools.py`: max 2% per trade, max 3 positions, max 3% daily loss
- All decisions are logged with full reasoning for review
