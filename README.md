# HalalSpecBot 🕌

**Shariah-Compliant Stock Speculation Research Bot**

HalalSpecBot is a research dashboard for halal stock speculation through **real share
ownership only**. You enter tickers, it fetches free public data, runs a strict Shariah
screen, scores the opportunity across financial / technical / catalyst / risk dimensions,
and classifies the result. A built-in continuous scanner keeps re-checking your tracked
tickers so the next promising halal setup surfaces automatically — with alerts shown
right in the dashboard.

---

## What it does

- ✅ Fetches company data and price history from free sources (yfinance)
- ✅ Runs a strict, conservative Shariah screen (haram keyword + debt checks)
- ✅ Scores financial strength, technical setup, catalysts, risk, and ethical impact
- ✅ Produces one of five final classifications
- ✅ Generates downloadable Markdown research reports
- ✅ Saves everything to a local SQLite database
- ✅ Tracks a watchlist, excluded stocks, and scholar-review stocks
- ✅ **Continuous scanner**: re-analyzes all tracked tickers on a timer and alerts you in the dashboard when a ticker upgrades (e.g., moves to HALAL SPECULATIVE BUY)

## What it does NOT do

- ❌ Execute trades or connect to any broker
- ❌ Auto-buy or auto-sell anything
- ❌ Recommend margin, leverage, short selling, options, futures, or CFDs
- ❌ Encourage gambling-like trading, pump-and-dump, or market manipulation
- ❌ Issue fatwas or guarantee Shariah compliance

## Shariah disclaimer

This tool performs an **automated preliminary screening only**. It is **not a fatwa**.
When data is incomplete or a business is ambiguous, the bot deliberately classifies the
stock as **REQUIRES SCHOLAR REVIEW** instead of assuming permissibility. Always consult
a qualified Islamic scholar before investing. If any non-compliant income exists,
purification of a portion of gains may be required.

## Financial disclaimer

This tool is for research and education only. It is **not financial advice**. Stock
speculation carries a real risk of permanent capital loss. Consult a licensed financial
professional before making decisions, and never invest money you cannot afford to lose.

---

## Installation

```bash
python -m venv venv
```

Windows:
```bat
venv\Scripts\activate
```

Mac/Linux:
```bash
source venv/bin/activate
```

Then:
```bash
pip install -r requirements.txt
```

## How to run

```bash
streamlit run halalspecbot/app.py
```

Or use the helper scripts: `run_app.bat` (Windows) / `./run_app.sh` (Mac/Linux).

## How to enter tickers

Type one or more tickers in the sidebar, separated by commas or spaces
(e.g. `MSFT, NVDA, AMD`), optionally add catalyst notes, then click **Run Analysis**.

## How the continuous scanner works

Every ticker you analyze is added to the tracked list. In the sidebar, pick an
**auto-scan interval** (15/30/60 minutes) or click **Scan Watchlist Now**. Each scan
re-runs the full pipeline on every tracked ticker, ranks them by Final Opportunity
Score in the **Scanner** tab, and fires a dashboard alert whenever a ticker's
classification changes — for example when one upgrades to HALAL SPECULATIVE BUY.
Keep the browser tab open for auto-scanning to run.

## How scores work

| Score | Meaning |
|---|---|
| Shariah Compliance (0–100) | 100 = clean screen, 50 = uncertain, 0 = haram |
| Financial Strength (0–100) | Profitability, growth, cash flow, debt, consistency |
| Technical Setup (0–100) | Trend, momentum, RSI, volume, volatility, extension |
| Catalyst (0–100) | Growth signals, sector tailwinds, your manual notes |
| Risk (0–100) | **Higher = riskier**: volatility, size, debt, losses, missing data |
| Ethical Impact (0–100) | Higher for productive sectors (healthcare, infrastructure…); 0 if haram |
| Final Opportunity (0–100) | Weighted blend: financial 35%, technical 25%, catalyst 20%, inverted risk 20% |
| Confidence (0–100) | Drops 5 points per missing/uncertain data field |

## How classifications work

1. **NON-COMPLIANT – EXCLUDED** — haram business activity detected. Final score forced to 0. No analysis can override this.
2. **REQUIRES SCHOLAR REVIEW** — business or financial data is unclear. Never becomes a buy automatically.
3. **HALAL BUT TOO RISKY** — passes the Shariah screen but risk score is above 75.
4. **HALAL SPECULATIVE BUY** — Shariah passes AND financial ≥ 65 AND technical ≥ 65 AND catalyst ≥ 60 AND risk ≤ 60.
5. **HALAL WATCHLIST** — Shariah passes but the setup isn't strong enough yet.

**Main rule: no Shariah pass = no speculation. Profit never overrides compliance.**

## Alerts

Alerts are shown directly in the dashboard (toast popups plus a persistent alert feed
in the sidebar). No external services are used in this MVP.

## Running the tests

```bash
pytest tests/ -v
```

## Future improvements

- Live news / earnings-calendar catalyst detection
- AAOIFI-standard financial ratio screening from full balance-sheet data
- Pre-screened halal stock universe scanning (find new candidates, not just re-check tracked ones)
- Email / push notifications
- Multi-market support (Tadawul, FTSE Shariah indices)
- Historical back-testing of the scoring model
