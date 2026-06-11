"""Catalyst scoring (0–100) from fundamentals, sector tailwinds, and user notes.

The MVP has no live news feed, so this module never invents news. When no
catalyst is detected it says so explicitly.
"""

from typing import Tuple

from halalspecbot import config
from halalspecbot.models import StockData

# Sector / theme tailwind keywords searched in sector, industry, and summary.
TAILWIND_KEYWORDS = [
    "artificial intelligence", "ai ", "semiconductor", "cybersecurity",
    "cloud", "data center", "infrastructure", "healthcare", "medical",
    "renewable", "solar", "energy transition", "electric vehicle",
    "logistics", "automation", "robotics", "saudi", "vision 2030",
]

# Keywords that make user-entered catalyst notes more concrete.
NOTE_SIGNAL_KEYWORDS = [
    "earnings", "contract", "partnership", "approval", "fda", "launch",
    "expansion", "guidance", "backlog", "order", "turnaround", "new product",
]


def analyze_catalysts(stock: StockData, user_notes: str = "") -> Tuple[float, list]:
    """Returns (score 0-100, list of catalyst factor descriptions)."""
    factors: list = []
    score = 0.0

    # --- 1. Earnings growth signal (20) ---
    if stock.earnings_growth is not None:
        if stock.earnings_growth > 0.20:
            score += 20
            factors.append(f"Strong earnings growth ({stock.earnings_growth:.0%})")
        elif stock.earnings_growth > 0.10:
            score += 12
            factors.append(f"Earnings growth ({stock.earnings_growth:.0%})")
        elif stock.earnings_growth > 0:
            score += 5

    # --- 2. Revenue growth signal (20) ---
    if stock.revenue_growth is not None:
        if stock.revenue_growth > 0.15:
            score += 20
            factors.append(f"Revenue acceleration ({stock.revenue_growth:.0%})")
        elif stock.revenue_growth > 0.05:
            score += 12
            factors.append(f"Revenue growth ({stock.revenue_growth:.0%})")
        elif stock.revenue_growth > 0:
            score += 5

    # --- 3. Sector tailwinds (20) ---
    scan_text = " ".join(
        filter(None, [stock.sector, stock.industry, stock.business_summary])
    ).lower()
    tailwinds = [kw.strip() for kw in TAILWIND_KEYWORDS if kw in scan_text]
    if tailwinds:
        score += min(20, 8 + 4 * len(tailwinds))
        factors.append("Sector tailwinds: " + ", ".join(sorted(set(tailwinds))))

    # --- 4. User catalyst notes (20) ---
    notes = (user_notes or "").strip()
    if notes:
        if len(notes.split()) >= 20:
            score += 10
        else:
            score += 5
        hits = [kw for kw in NOTE_SIGNAL_KEYWORDS if kw in notes.lower()]
        if hits:
            score += min(10, 5 * len(hits))
            factors.append("User notes mention: " + ", ".join(hits))
        factors.append(f"Manual catalyst notes provided: “{notes[:200]}”")
    else:
        factors.append("No manual catalyst notes provided.")

    # --- 5. Cash position supporting execution (20) ---
    if stock.total_cash is not None and stock.total_debt is not None:
        if stock.total_cash > stock.total_debt:
            score += 20
            factors.append("Cash exceeds debt — strong position to fund growth")
        elif stock.total_cash > 0:
            score += 8
    elif stock.total_cash is not None and stock.total_cash > 0:
        score += 5

    if not factors or all("No manual" in f for f in factors):
        factors.append("No clear catalyst detected from available data.")

    factors.append(config.NO_NEWS_NOTE)
    return min(score, 100.0), factors
