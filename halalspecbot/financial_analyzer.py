"""Financial quality scoring (0–100) from free fundamental data."""

from typing import Tuple

from halalspecbot.models import StockData
from halalspecbot.utils import safe_divide


def analyze_financials(stock: StockData) -> Tuple[float, list, list]:
    """Score financial strength.

    Returns (score 0-100, human-readable notes, data warnings).
    Five components, 20 points each. Missing data earns no points and is
    reported as a warning; if too many fields are missing the score is
    capped at 50 so incomplete data never looks like strength.
    """
    notes: list = []
    warnings: list = []
    score = 0.0
    missing = 0

    # --- 1. Profitability (20) ---
    if stock.net_income is None:
        missing += 1
        warnings.append("Net income unknown")
    elif stock.net_income > 0:
        score += 10
        notes.append("Profitable (positive net income)")
    else:
        notes.append("Unprofitable (negative net income)")
    if stock.gross_margin is not None and stock.gross_margin > 0.30:
        score += 5
        notes.append(f"Healthy gross margin ({stock.gross_margin:.0%})")
    if stock.profit_margin is not None and stock.profit_margin > 0.10:
        score += 5
        notes.append(f"Strong profit margin ({stock.profit_margin:.0%})")

    # --- 2. Revenue quality (20) ---
    if stock.revenue is None:
        missing += 1
        warnings.append("Revenue unknown")
    elif stock.revenue > 0:
        score += 5
    if stock.revenue_growth is None:
        warnings.append("Revenue growth unknown")
    else:
        if stock.revenue_growth > 0.10:
            score += 10
            notes.append(f"Revenue growing ({stock.revenue_growth:.0%})")
        if stock.revenue_growth > 0.20:
            score += 5
            notes.append("Revenue growth accelerating (>20%)")
        if stock.revenue_growth < 0:
            notes.append(f"Revenue shrinking ({stock.revenue_growth:.0%})")

    # --- 3. Cash flow (20) ---
    if stock.free_cashflow is None:
        missing += 1
        warnings.append("Free cash flow unknown")
    elif stock.free_cashflow > 0:
        score += 10
        notes.append("Positive free cash flow")
        fcf_margin = safe_divide(stock.free_cashflow, stock.revenue)
        if fcf_margin is not None and fcf_margin > 0.08:
            score += 5
            notes.append(f"Strong FCF margin ({fcf_margin:.0%})")
    else:
        notes.append("Negative free cash flow")
    if stock.operating_cashflow is not None and stock.operating_cashflow > 0:
        score += 5

    # --- 4. Debt / leverage (20) ---
    debt_ratio = safe_divide(stock.total_debt, stock.market_cap)
    if debt_ratio is None:
        debt_ratio = safe_divide(stock.total_debt, stock.total_assets)
    if stock.total_debt == 0:
        debt_ratio = 0.0
    if debt_ratio is None:
        missing += 1
        warnings.append("Debt ratio could not be computed")
    elif debt_ratio < 0.30:
        score += 20
        notes.append(f"Low debt ({debt_ratio:.0%} of market value)")
    elif debt_ratio < 0.50:
        score += 10
        notes.append(f"Moderate debt ({debt_ratio:.0%})")
    else:
        notes.append(f"High debt ({debt_ratio:.0%})")

    # --- 5. Growth consistency (20) ---
    if stock.earnings_growth is None:
        warnings.append("Earnings growth unknown")
    elif stock.earnings_growth > 0.10:
        score += 10
        notes.append(f"Earnings growing ({stock.earnings_growth:.0%})")
    if stock.ebitda is not None and stock.ebitda > 0:
        score += 5
    if (
        stock.revenue_growth is not None
        and stock.earnings_growth is not None
        and stock.revenue_growth > 0
        and stock.earnings_growth > 0
    ):
        score += 5
        notes.append("Revenue and earnings both growing")

    # Cash strength bonus context (informational only)
    cash_to_debt = safe_divide(stock.total_cash, stock.total_debt)
    if cash_to_debt is not None and cash_to_debt > 1:
        notes.append("More cash than debt on the balance sheet")

    # Cap when data is too thin — incomplete data must not look strong.
    if missing > 3:
        score = min(score, 50.0)
        warnings.append("Too many missing fields — financial score capped at 50")

    return min(score, 100.0), notes, warnings
