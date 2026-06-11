"""Risk scoring (0 = very low risk, 100 = very high risk) and scenario cases.

All scenario estimates use cautious language and never promise returns.
"""

from typing import Optional, Tuple

from halalspecbot.models import PriceHistory, ScenarioEstimate, StockData
from halalspecbot.utils import safe_divide


def analyze_risk(
    stock: StockData, history: Optional[PriceHistory], data_warnings: list
) -> Tuple[float, list, list]:
    """Returns (risk_score 0-100, risk notes, scenario list)."""
    notes: list = []
    risk = 0.0

    # --- 1. Beta / market sensitivity (0-20) ---
    if stock.beta is None:
        risk += 10
        notes.append("Beta unknown — market sensitivity unclear")
    elif stock.beta > 2.0:
        risk += 20
        notes.append(f"Very high beta ({stock.beta:.2f})")
    elif stock.beta > 1.5:
        risk += 14
        notes.append(f"High beta ({stock.beta:.2f})")
    elif stock.beta > 1.0:
        risk += 8

    # --- 2. Volatility (0-20) ---
    atr_pct = None
    if history is not None and not history.df_1y.empty:
        df = history.df_1y
        atr = df["ATR14"].dropna()
        close = df["Close"].dropna()
        if not atr.empty and not close.empty and close.iloc[-1]:
            atr_pct = float(atr.iloc[-1]) / float(close.iloc[-1])
    if atr_pct is None:
        risk += 12
        notes.append("Volatility unknown (no price history)")
    elif atr_pct > 0.07:
        risk += 20
        notes.append(f"Extreme volatility (ATR {atr_pct:.1%} of price)")
    elif atr_pct > 0.04:
        risk += 10
        notes.append(f"Elevated volatility (ATR {atr_pct:.1%})")

    # --- 3. Liquidity / size (0-20) ---
    if stock.market_cap is None:
        risk += 12
        notes.append("Market cap unknown")
    elif stock.market_cap < 300e6:
        risk += 20
        notes.append("Micro-cap — high risk of permanent capital loss")
    elif stock.market_cap < 2e9:
        risk += 12
        notes.append("Small-cap — elevated volatility and liquidity risk")
    elif stock.market_cap < 10e9:
        risk += 5
    if stock.avg_volume is not None and stock.avg_volume < 500_000:
        risk += 5
        notes.append("Thin trading volume")

    # --- 4. Financial fragility (0-25) ---
    if stock.free_cashflow is not None and stock.free_cashflow < 0:
        risk += 10
        notes.append("Negative free cash flow (burning cash)")
    if stock.net_income is not None and stock.net_income < 0:
        risk += 7
        notes.append("Unprofitable")
    debt_ratio = safe_divide(stock.total_debt, stock.market_cap)
    if debt_ratio is not None and debt_ratio > 0.5:
        risk += 8
        notes.append(f"High debt load ({debt_ratio:.0%} of market cap)")

    # --- 5. Data uncertainty (0-15) ---
    missing = len(data_warnings)
    if missing > 0:
        bump = min(15, 3 * missing)
        risk += bump
        notes.append(f"{missing} data fields missing — uncertainty raises risk")

    scenarios = build_scenarios(stock)
    return min(risk, 100.0), notes, scenarios


def build_scenarios(stock: StockData) -> list:
    """Six cautious scenario cases anchored to price and the 52-week range."""
    price = stock.price
    hi = stock.high_52w
    lo = stock.low_52w
    if price is None or hi is None or lo is None:
        return []

    def pct(target: float) -> float:
        return target / price - 1

    caution = "Estimate only — past ranges do not guarantee future prices."

    return [
        ScenarioEstimate(
            label="Extremely Bullish",
            probability="Low",
            price_target=round(hi * 1.5, 2),
            move_pct=pct(hi * 1.5),
            time_horizon="12–24 months",
            assumptions=(
                "Major catalyst lands, growth accelerates well beyond expectations, "
                "and market sentiment is strongly favorable. " + caution
            ),
            what_could_go_wrong="Catalyst fails, sentiment reverses, gains evaporate quickly.",
        ),
        ScenarioEstimate(
            label="Bullish",
            probability="Low–Moderate",
            price_target=round(hi * 1.15, 2),
            move_pct=pct(hi * 1.15),
            time_horizon="6–18 months",
            assumptions="Business executes well and the stock retakes and exceeds its 52-week high. " + caution,
            what_could_go_wrong="Growth slows; the stock stalls below prior highs.",
        ),
        ScenarioEstimate(
            label="Base Case",
            probability="Moderate",
            price_target=round(price * 1.10, 2),
            move_pct=0.10,
            time_horizon="6–12 months",
            assumptions="Business performs roughly in line with current trends. " + caution,
            what_could_go_wrong="Even modest gains depend on stable markets and execution.",
        ),
        ScenarioEstimate(
            label="Bearish",
            probability="Moderate",
            price_target=round(price * 0.80, 2),
            move_pct=-0.20,
            time_horizon="3–12 months",
            assumptions="Earnings disappoint or market conditions deteriorate.",
            what_could_go_wrong="A 20% drawdown is common for speculative names.",
        ),
        ScenarioEstimate(
            label="Extremely Bearish",
            probability="Low–Moderate",
            price_target=round(lo * 0.90, 2),
            move_pct=pct(lo * 0.90),
            time_horizon="6–18 months",
            assumptions="Business deteriorates badly; stock breaks below its 52-week low.",
            what_could_go_wrong="Capital loss could be substantial and slow to recover.",
        ),
        ScenarioEstimate(
            label="Black Swan",
            probability="Very Low",
            price_target=round(lo * 0.50, 2),
            move_pct=pct(lo * 0.50),
            time_horizon="Unpredictable",
            assumptions=(
                "Fraud, delisting, war, systemic crisis, or other extreme events. "
                "Permanent loss of most invested capital is possible."
            ),
            what_could_go_wrong="Total or near-total loss. Never invest money you cannot afford to lose.",
        ),
    ]
