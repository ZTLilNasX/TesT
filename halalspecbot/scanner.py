"""Continuous watchlist scanner.

Re-runs the full analysis on every tracked ticker and reports which ones
changed classification, ranked by final opportunity score. The Streamlit
app calls this on a timer (auto-refresh) or via a "Scan Now" button so the
bot keeps hunting for the next halal speculative setup.
"""

import time
from typing import Tuple

from halalspecbot import config, database
from halalspecbot.pipeline import run_full_analysis


def run_watchlist_scan(catalyst_notes: str = "", delay_s: float = 1.0) -> Tuple[list, list]:
    """Re-analyze all watchlist tickers.

    Returns (results sorted by final_score desc, classification change events).
    Each change event is a dict: {ticker, old, new}.
    """
    items = database.get_watchlist_items()
    previous = {item["ticker"]: item["status"] for item in items}

    results = []
    changes = []
    for i, ticker in enumerate(previous):
        if i > 0 and delay_s:
            time.sleep(delay_s)  # be polite to the free data source
        result = run_full_analysis(ticker, catalyst_notes)
        results.append(result)
        old = previous[ticker]
        if result.final_classification != old:
            changes.append(
                {"ticker": ticker, "old": old, "new": result.final_classification}
            )

    # Excluded names sink to the bottom regardless of raw score.
    def sort_key(r):
        excluded = r.final_classification == config.CLASS_NON_COMPLIANT
        return (excluded, -(r.final_score or 0))

    results.sort(key=sort_key)
    return results, changes
