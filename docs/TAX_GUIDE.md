# 🇩🇰 Danish Tax Guide — AI Trading Bot & SKAT

This guide explains how trading US ETFs (QQQ, SPY) through this bot affects your Danish taxes, what you need to report to SKAT, and how the bot's built-in tax tracking helps you stay compliant.

> ⚠️ **Disclaimer**: This guide is for informational purposes only. Always consult a qualified Danish tax professional (revisor) for your specific situation.

---

## Table of Contents

1. [Why This Matters](#1-why-this-matters)
2. [How QQQ and SPY Are Taxed in Denmark](#2-how-qqq-and-spy-are-taxed-in-denmark)
3. [Lagerbeskatning Explained](#3-lagerbeskatning-explained)
4. [What You Must Report to SKAT](#4-what-you-must-report-to-skat)
5. [How the Bot Tracks Everything](#5-how-the-bot-tracks-everything)
6. [Year-End Procedure](#6-year-end-procedure)
7. [Reporting in TastSelv](#7-reporting-in-tastselv)
8. [Dividends and Withholding Tax](#8-dividends-and-withholding-tax)
9. [Important Deadlines](#9-important-deadlines)
10. [Currency Conversion (USD → DKK)](#10-currency-conversion-usd--dkk)
11. [Common Questions](#11-common-questions)

---

## 1. Why This Matters

When you trade US stocks or ETFs through a **foreign broker** (like Alpaca), SKAT does **not** receive automatic reports about your trades. Danish banks report to SKAT automatically — foreign brokers do not.

**You are 100% responsible for reporting all:**
- Purchases (acquisitions)
- Sales (dispositions)
- Year-end portfolio values
- Dividends received
- Foreign tax withheld

Failure to report can result in penalties, back-taxes, and interest.

---

## 2. How QQQ and SPY Are Taxed in Denmark

### The Key Classification

| ETF | ISIN | On SKAT's Positivliste? | Tax Category | Tax Method |
|-----|------|-------------------------|--------------|------------|
| **QQQ** (Invesco Nasdaq 100) | US46090E1038 | ❌ No | Kapitalindkomst | Lagerbeskatning |
| **SPY** (SPDR S&P 500) | US78462F1030 | ❌ No | Kapitalindkomst | Lagerbeskatning |

### What does this mean?

- **Kapitalindkomst** (capital income): Gains are taxed at your marginal income tax rate, typically **37–42%** depending on municipality and total income. This is higher than the 27%/42% rates for "aktieindkomst" (stock income) that applies to shares on the positivliste.

- **Lagerbeskatning** (mark-to-market taxation): You are taxed on gains **every year**, even if you haven't sold. This is different from "realisationsbeskatning" where you're only taxed when you actually sell.

### Why not aktieindkomst?

SKAT maintains a "positivliste" of approved investment funds. ETFs **on** this list get the favorable aktieindkomst rate. QQQ and SPY are US-domiciled ETFs and are **not** on this list.

> **Tip:** If you want favorable tax treatment, consider Irish-domiciled equivalents (e.g., iShares CSPX for S&P 500) — but check the current positivliste first, and note Alpaca may not offer these.

---

## 3. Lagerbeskatning Explained

Under lagerbeskatning, your taxable gain/loss for the year is calculated as:

```
Taxable gain/loss = Value on Dec 31 - Value on Jan 1 (or purchase price if bought during the year)
```

### Example: Full Year Hold

- You buy 10 shares of QQQ on March 1 for $450/share → Cost: $4,500
- Dec 31 price: $500/share → Value: $5,000
- **Taxable gain for the year: $500** (even though you didn't sell)

### Example: Buy and Sell Within the Year

- You buy 10 QQQ at $450, sell at $470 → Realized gain: $200
- You also still hold 5 QQQ bought at $460, Dec 31 price: $480
- **Taxable: $200 (realized) + $100 (unrealized on remaining 5) = $300**

### Example: Loss Year

- Jan 1 value: $5,000 (10 shares at $500)
- Dec 31 value: $4,200 (10 shares at $420)
- **Deductible loss: $800**

Losses under lagerbeskatning are deductible against other kapitalindkomst.

---

## 4. What You Must Report to SKAT

### For Each Security (per ISIN):

| Field | Description | Example |
|-------|-------------|---------|
| **ISIN** | International securities ID | US46090E1038 |
| **Navn** | Security name | Invesco QQQ Trust |
| **Antal primo** | Shares held Jan 1 | 10 |
| **Kursværdi primo (DKK)** | Value Jan 1 in DKK | 31,500 DKK |
| **Køb i året** | Purchases during year | 5 shares for $2,300 |
| **Salg i året** | Sales during year | 3 shares for $1,400 |
| **Antal ultimo** | Shares held Dec 31 | 12 |
| **Kursværdi ultimo (DKK)** | Value Dec 31 in DKK | 40,800 DKK |
| **Gevinst/tab (DKK)** | Gain or loss for the year | 3,200 DKK |

### Additionally:
- **Dividends received** (gross amount, foreign tax withheld)
- **Foreign broker details** (Alpaca Markets LLC)
- **Account currency** (USD — you must convert to DKK)

---

## 5. How the Bot Tracks Everything

The bot automatically records every trade to `tax/transactions.csv`.

### Automatic Tracking (happens on every trade):

Every time the AI places an order or closes a position, a row is written to `tax/transactions.csv` with:

| Column | Description |
|--------|-------------|
| `transaction_id` | Alpaca order ID |
| `date` | Trade date (YYYY-MM-DD) |
| `time` | Trade time (HH:MM:SS ET) |
| `symbol` | Ticker (QQQ, SPY) |
| `isin` | ISIN code for SKAT |
| `side` | buy or sell |
| `quantity` | Number of shares |
| `price_per_share_usd` | Execution price |
| `total_value_usd` | Total trade value |
| `fees_usd` | Commissions/fees |
| `order_type` | market, limit, stop, stop_limit |
| `paper_trade` | true/false |

### CLI Commands:

```bash
# Generate yearly summary + SKAT-formatted CSV
python run.py --tax-report 2026

# Capture Dec 31 positions (mark-to-market snapshot)
python run.py --year-end 2026

# Show tax help
python run.py --tax-help
```

### Generated Files (in `tax/` directory):

| File | Purpose | When Created |
|------|---------|--------------|
| `transactions.csv` | All trades | Automatically on every trade |
| `year_end_YYYY.csv` | Dec 31 portfolio snapshot | When you run `--year-end` |
| `skat_export_YYYY.csv` | Danish-formatted export | When you run `--tax-report` |
| `dividends.csv` | Dividend payments | Manual or automatic if dividends are received |

---

## 6. Year-End Procedure

Every year, before filing your taxes, follow these steps:

### Step 1: Capture Year-End Positions (Dec 31 or early January)

```bash
python run.py --year-end 2026
```

This creates `tax/year_end_2026.csv` with:
- Shares held on Dec 31
- Average cost basis per share
- Market price on Dec 31
- Unrealized gain/loss (the lagerbeskatning amount)

### Step 2: Generate Tax Report

```bash
python run.py --tax-report 2026
```

This gives you a summary and creates `tax/skat_export_2026.csv` with all transactions in Danish format.

### Step 3: Convert to DKK

All amounts are in USD. You must convert to DKK using the exchange rate on each trade date (or use Nationalbanken's annual average rate — ask your revisor).

Nationalbanken exchange rates: [https://www.nationalbanken.dk/valutakurser](https://www.nationalbanken.dk/valutakurser)

### Step 4: Report in TastSelv

See [Section 7](#7-reporting-in-tastselv) below.

---

## 7. Reporting in TastSelv

1. Log in to **[skat.dk](https://skat.dk)** → **TastSelv**
2. Go to your **Årsopgørelse** (annual tax return)
3. Find **Rubrik 346** (kapitalindkomst from foreign securities under lagerbeskatning)
4. Report the net gain or loss for the year in DKK
5. Under **Udenlandske værdipapirer**, add each security:
   - ISIN number
   - Name of security
   - Number of shares (primo and ultimo)
   - Value primo and ultimo
   - Acquisitions and sales during the year

### Important: Report Acquisitions Separately

SKAT requires you to report acquisitions (purchases) for the year. If you don't report acquisitions by **July 1 of the following year**, you cannot deduct losses.

---

## 8. Dividends and Withholding Tax

### US Withholding Tax

US ETFs may pay dividends. As a Danish tax resident, the US withholds tax at the source:

| Scenario | Withholding Rate |
|----------|-----------------|
| With W-8BEN form filed | **15%** (treaty rate) |
| Without W-8BEN | **30%** (default) |

> **Important:** Make sure you file a **W-8BEN form** with Alpaca to get the reduced 15% rate under the US-Denmark tax treaty.

### Reporting Dividends to SKAT

- Report gross dividend in DKK
- Claim credit for US withholding tax paid (to avoid double taxation)
- Denmark and the US have a double taxation treaty — you can offset the 15% US tax against your Danish tax

### Bot Tracking

If dividends are received, record them:
```python
from aitrading.tax_tracker import record_dividend
record_dividend("QQQ", gross_amount=45.00, tax_withheld=6.75)
```

---

## 9. Important Deadlines

| Deadline | What |
|----------|------|
| **December 31** | Run `--year-end` to capture positions for lagerbeskatning |
| **March 1** (approx.) | SKAT opens TastSelv for the previous year |
| **May 1** | Deadline for filing tax return (årsopgørelse) |
| **July 1** | Deadline to report acquisitions (to preserve loss deduction) |

> Dates may vary slightly each year. Check skat.dk for current deadlines.

---

## 10. Currency Conversion (USD → DKK)

All trading is in USD, but SKAT requires DKK amounts.

### Which Exchange Rate to Use?

Ask your revisor, but common approaches:

1. **Transaction date rate**: Use Nationalbanken's rate on the date of each trade
2. **Annual average rate**: Use Nationalbanken's yearly average USD/DKK rate
3. **Year-end rate**: For Dec 31 valuations, use the Dec 31 exchange rate

Nationalbanken publishes daily and annual rates at:
**[https://www.nationalbanken.dk/valutakurser](https://www.nationalbanken.dk/valutakurser)**

> The bot records all amounts in USD. You must convert to DKK yourself (or have your revisor do it). A future update may add automatic DKK conversion.

---

## 11. Common Questions

### Q: Do I pay tax if I only paper trade?

**No.** Paper trades are not real transactions and have no tax implications. The bot marks each trade with `paper_trade: true/false` so you can filter them out.

### Q: What if I lose money?

Losses under lagerbeskatning are deductible against other kapitalindkomst. If your total kapitalindkomst is negative, the tax value of the deduction is lower (~25% vs. 37-42%).

### Q: Can I use FIFO or specific lot identification?

Under lagerbeskatning, the lot identification method doesn't matter the same way it does under realisationsbeskatning. What matters is the total value at year-start vs. year-end (plus any inflows/outflows during the year).

### Q: What if I hold positions over the new year?

That's exactly when lagerbeskatning kicks in. Even though you didn't sell, the difference between the Jan 1 and Dec 31 values is taxable.

### Q: Do I need a Danish revisor (accountant)?

**Strongly recommended**, especially for your first year. A revisor familiar with foreign securities and lagerbeskatning can ensure you report correctly and claim all available deductions.

### Q: What about the 42% rate — is that always applied?

No. Kapitalindkomst is added to your other income. The effective rate depends on your total taxable income and municipality. Typical range is 37-42%.

### Q: Can I switch to ETFs on the positivliste to pay less tax?

Yes — if you buy Irish-domiciled equivalents (like iShares CSPX instead of SPY), they may be on the positivliste and taxed as aktieindkomst (27% on first ~61,000 DKK, 42% above). However:
- Check the current positivliste at [sfrb.dk](https://www.teledata.sfrb.dk/teledata/vis?teledata=PSL)
- Alpaca may not offer these ETFs
- Some positivliste ETFs are still lagerbeskattet — check the specifics

---

## Summary

| Topic | Key Point |
|-------|-----------|
| **Tax type** | Kapitalindkomst (not aktieindkomst) |
| **Tax method** | Lagerbeskatning (yearly mark-to-market) |
| **Tax rate** | 37–42% (marginal income tax) |
| **Reporting** | Self-report via TastSelv (foreign broker) |
| **Auto-tracked** | All buys/sells with ISIN, qty, price, fees |
| **Manual step** | Run `--year-end` on Dec 31, convert USD→DKK |
| **Key deadline** | Report acquisitions by July 1 to preserve loss deductions |
| **Recommended** | Hire a revisor for the first year |
