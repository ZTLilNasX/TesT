"""Small shared helpers: formatting, safe math, logging."""

import logging
import re
from typing import Optional

from halalspecbot import config


def setup_logging(level: str = "INFO") -> logging.Logger:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    return logging.getLogger("halalspecbot")


def safe_divide(a: Optional[float], b: Optional[float], fallback=None):
    """Return a / b, or fallback when either value is missing or b is 0."""
    if a is None or b is None or b == 0:
        return fallback
    try:
        return a / b
    except (TypeError, ZeroDivisionError):
        return fallback


def format_large_number(n: Optional[float]) -> str:
    """1_500_000 -> '$1.50M'. None -> 'N/A'."""
    if n is None:
        return "N/A"
    sign = "-" if n < 0 else ""
    n = abs(n)
    for divisor, suffix in [(1e12, "T"), (1e9, "B"), (1e6, "M"), (1e3, "K")]:
        if n >= divisor:
            return f"{sign}${n / divisor:.2f}{suffix}"
    return f"{sign}${n:.2f}"


def format_percentage(n: Optional[float]) -> str:
    """0.153 -> '15.3%'. None -> 'N/A'."""
    if n is None:
        return "N/A"
    return f"{n * 100:.1f}%"


def format_price(n: Optional[float]) -> str:
    if n is None:
        return "N/A"
    return f"${n:,.2f}"


def parse_tickers(raw: str) -> list:
    """Split free-text ticker input on commas/whitespace, uppercase, dedupe."""
    tickers = [t.strip().upper() for t in re.split(r"[,\n\s]+", raw or "") if t.strip()]
    seen = set()
    out = []
    for t in tickers:
        if t not in seen:
            seen.add(t)
            out.append(t)
    return out


def classification_color(classification: str) -> str:
    return {
        config.CLASS_HALAL_SPECULATIVE_BUY: "#2e7d32",
        config.CLASS_HALAL_WATCHLIST: "#1565c0",
        config.CLASS_HALAL_BUT_TOO_RISKY: "#ef6c00",
        config.CLASS_REQUIRES_SCHOLAR_REVIEW: "#6a1b9a",
        config.CLASS_NON_COMPLIANT: "#b71c1c",
    }.get(classification, "#555555")


def classification_emoji(classification: str) -> str:
    return {
        config.CLASS_HALAL_SPECULATIVE_BUY: "🟢",
        config.CLASS_HALAL_WATCHLIST: "🔵",
        config.CLASS_HALAL_BUT_TOO_RISKY: "🟠",
        config.CLASS_REQUIRES_SCHOLAR_REVIEW: "🟣",
        config.CLASS_NON_COMPLIANT: "🔴",
    }.get(classification, "⚪")
