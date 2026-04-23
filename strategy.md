# Trading Strategy Playbook

## Watchlist

- **QQQ** — Invesco QQQ Trust (tracks NASDAQ-100)
- **SPY** — SPDR S&P 500 ETF Trust (tracks S&P 500)

---

## Market Condition Assessment

Before selecting a strategy, assess the current market condition using 5-minute bars:

### Trending (Directional)
- Price is consistently above or below VWAP
- Recent bars show a clear staircase pattern (higher highs + higher lows, or vice versa)
- Volume is above average on moves in the trend direction
- **→ Use Strategy 2 (Opening Range Breakout) or Strategy 3 (RSI Pullback)**

### Ranging (Mean-Reverting)
- Price oscillates around VWAP, crossing it multiple times
- No clear directional bias
- Upper and lower bounds are visible (support/resistance)
- **→ Use Strategy 1 (VWAP Mean Reversion)**

### Choppy / Unclear
- Erratic price action with large wicks and no pattern
- Volume is low or inconsistent
- Conflicting signals from different indicators
- **→ DO NOT TRADE. Sit out and preserve capital.**

---

## Strategy 1: VWAP Mean Reversion (Ranging Markets)

Use when: Market is ranging, price is oscillating around VWAP.

### Indicators
- **VWAP**: Bars already include VWAP data. This is the anchor.
- **Volume**: Compare current bar volume to 20-bar average volume.

### Entry Rules (Long)
1. Price has dropped **below VWAP** by at least 0.1%
2. Current bar shows a **bullish reversal**: close > open (green candle)
3. Volume on the reversal bar is **≥ 1.3x** the 20-bar average volume
4. **Buy** at market price

### Entry Rules (Short — Sell existing position)
1. Price has risen **above VWAP** by at least 0.1%
2. Current bar shows a **bearish reversal**: close < open (red candle)
3. If holding a long position, **close it**

### Exit Rules
- **Take profit**: When price reaches VWAP + 0.3% (from entry) OR when price crosses above VWAP after being below
- **Stop loss**: 0.2% below entry price — use a stop order immediately after entry
- **Time stop**: Close position if not in profit after 30 minutes (6 bars at 5-min)

---

## Strategy 2: Opening Range Breakout — ORB (Trending Days)

Use when: It's within the first 2 hours of market open and a clear breakout occurs from the opening range.

### Indicators
- **Opening Range**: High and low of the first 3 bars (first 15 minutes: 9:30–9:45 AM ET)
- **Volume**: Compare breakout bar volume to opening range average

### Setup
1. After 9:45 AM ET, mark the **Opening Range High (ORH)** and **Opening Range Low (ORL)** from the first 3 five-minute bars
2. Calculate the **range width** = ORH - ORL

### Entry Rules (Long)
1. A 5-min bar **closes above ORH**
2. Breakout bar volume is **≥ 1.5x** average of the opening range bars
3. **Buy** at market price
4. Immediately set **stop loss** at ORL (or at ORH minus the range width, whichever is tighter)

### Entry Rules (Short — via selling existing position)
1. A 5-min bar **closes below ORL**
2. If holding a long position, **close it immediately**

### Exit Rules
- **Take profit**: At 2x the range width above entry (1:2 risk-reward)
- **Stop loss**: At ORL (for longs) — placed immediately after entry
- **Time stop**: Close by 11:30 AM ET if target not hit
- **One trade only**: Only take the FIRST breakout of the day for this strategy

---

## Strategy 3: RSI Pullback (Oversold Bounces in Uptrends)

Use when: Market is trending up but has a temporary pullback.

### Indicators
- **RSI (14-period)**: Calculate on 5-minute bars
  - RSI = 100 - (100 / (1 + RS)), where RS = avg gain / avg loss over 14 periods
- **50-period EMA**: Exponential moving average of close prices over 50 bars
  - Multiplier = 2 / (50 + 1) = 0.0392
  - EMA = (close - prev_EMA) * multiplier + prev_EMA

### Entry Rules (Long)
1. Price is **above the 50-period EMA** (confirming uptrend)
2. RSI has dropped **below 30** (oversold)
3. RSI now **crosses back above 30** (reversal signal)
4. **Buy** at market price

### Exit Rules
- **Take profit**: When RSI reaches **50** OR price gains 0.5% from entry
- **Stop loss**: At the recent swing low (lowest low of last 5 bars), minimum 0.15% below entry
- **Time stop**: Close if not in profit after 20 minutes (4 bars)

---

## Risk Management Rules (NON-NEGOTIABLE)

These rules override EVERYTHING. Never violate them, even if a trade looks perfect.

### Position Sizing
- **Max risk per trade**: 2% of account equity
- Calculate qty: `max_shares = (equity * 0.02) / entry_price`
- Round down to whole shares

### Portfolio Limits
- **Max 3 concurrent positions** across all symbols
- **Max 1 position per symbol** at a time

### Daily Limits
- **Max daily loss**: 3% of account equity → STOP TRADING for the day
- If daily P&L is negative and you've taken 3 consecutive losses → STOP TRADING

### Stop Losses
- **Every trade MUST have a stop loss** — either via a stop order or manual exit
- Never move a stop loss further away from entry (only tighten)
- Move stop to breakeven once trade is 0.2% in profit

### Time Rules
- Only trade between **9:35 AM and 3:45 PM ET**
- Avoid the first 5 minutes (9:30–9:35) — too volatile
- Avoid the last 15 minutes (3:45–4:00) — closing auction noise
- ORB strategy is only valid before 11:30 AM ET

---

## Decision Framework (Each 5-Minute Run)

```
1. CHECK ACCOUNT → Is daily loss limit hit? → YES → Stop, log "Daily loss limit reached"
2. CHECK POSITIONS → Manage existing positions:
   - Has any stop loss been hit? Close if needed.
   - Is any position at take-profit target? Close it.
   - Should any stop be tightened? Update it.
3. ASSESS MARKET → Fetch 5-min bars for watchlist
   - Determine condition: Trending / Ranging / Choppy
   - If CHOPPY → Log "Market unclear, sitting out" → DONE
4. SELECT STRATEGY →
   - Ranging → VWAP Mean Reversion (Strategy 1)
   - Trending + before 11:30 AM + no ORB trade today → ORB (Strategy 2)
   - Trending + RSI oversold → RSI Pullback (Strategy 3)
5. CHECK ENTRY → Do current conditions match entry rules?
   - NO → Log reasoning → DONE
   - YES → Calculate position size → Place order + stop loss → Log trade
```

---

## Philosophy (Inspired by Fabio Valentini)

> Capital preservation is priority #1. The market will be here tomorrow.

- **Most runs should result in NO TRADE.** That's correct behavior.
- When in doubt, do nothing. The cost of missing a trade is zero. The cost of a bad trade is real.
- The edge comes from patience and selectivity, not from trading frequency.
- Log your reasoning every single run, even when you don't trade — especially when you don't trade.
