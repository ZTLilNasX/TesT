"""Watchlist views and management built on the database layer."""

from halalspecbot import config, database


def get_full_watchlist() -> list:
    """All tracked tickers with their latest scores merged in."""
    items = database.get_watchlist_items()
    scores = database.get_latest_scores()
    for item in items:
        item.update(
            {
                "final_score": scores.get(item["ticker"], {}).get("final_score"),
                "confidence_score": scores.get(item["ticker"], {}).get("confidence_score"),
                "risk_score": scores.get(item["ticker"], {}).get("risk_score"),
                "financial_score": scores.get(item["ticker"], {}).get("financial_score"),
                "technical_score": scores.get(item["ticker"], {}).get("technical_score"),
                "catalyst_score": scores.get(item["ticker"], {}).get("catalyst_score"),
            }
        )
    return items


def get_active_watchlist() -> list:
    """Halal tickers worth tracking (buys, watchlist, too-risky)."""
    return [
        item
        for item in get_full_watchlist()
        if item["status"]
        in (
            config.CLASS_HALAL_SPECULATIVE_BUY,
            config.CLASS_HALAL_WATCHLIST,
            config.CLASS_HALAL_BUT_TOO_RISKY,
        )
    ]


def get_excluded() -> list:
    return database.get_watchlist_items([config.CLASS_NON_COMPLIANT])


def get_scholar_review() -> list:
    return database.get_watchlist_items([config.CLASS_REQUIRES_SCHOLAR_REVIEW])


def remove_ticker(ticker: str) -> None:
    database.delete_watchlist_item(ticker)
