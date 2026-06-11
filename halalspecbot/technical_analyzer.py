"""Technical setup scoring (0–100) plus entry-zone / invalidation estimates.

Technical strength never overrides Shariah compliance — the scoring
engine enforces that gate; this module only measures price behavior.
"""

from typing import Optional, Tuple

from halalspecbot.models import PriceHistory, StockData


def _last(series) -> Optional[float]:
    """Last non-NaN value of a pandas Series, or None."""
    if series is None:
        return None
    s = series.dropna()
    if s.empty:
        return None
    return float(s.iloc[-1])


def analyze_technicals(
    history: PriceHistory, stock: StockData
) -> Tuple[float, list, str, Optional[float]]:
    """Score the chart setup.

    Returns (score 0-100, notes, entry_zone text, invalidation_level).
    """
    notes: list = []
    df = history.df_1y if history else None

    if df is None or df.empty or len(df) < 60:
        return (
            0.0,
            ["Insufficient price history — technical analysis unavailable"],
            "Insufficient price history for an entry estimate.",
            None,
        )

    price = _last(df["Close"])
    ma20 = _last(df["MA20"])
    ma50 = _last(df["MA50"])
    ma200 = _last(df["MA200"])
    rsi = _last(df["RSI14"])
    atr = _last(df["ATR14"])

    score = 0.0

    # --- Trend (25) ---
    if price is not None and ma50 is not None and price > ma50:
        score += 15
        notes.append("Price above 50-day moving average (uptrend)")
    elif ma50 is not None:
        notes.append("Price below 50-day moving average (weak trend)")
    if ma50 is not None and ma200 is not None and ma50 > ma200:
        score += 10
        notes.append("50-day MA above 200-day MA (bullish structure)")

    # --- Momentum (25) ---
    if price is not None and ma20 is not None and price > ma20:
        score += 5
        notes.append("Price above 20-day moving average")
    ret_30 = _period_return(df, 21)
    ret_90 = _period_return(df, 63)
    ret_1y = _period_return(df, len(df) - 1)
    if ret_30 is not None and ret_30 > 0:
        score += 5
        notes.append(f"Positive 30-day return ({ret_30:.1%})")
    if ret_90 is not None and ret_90 > 0:
        score += 5
        notes.append(f"Positive 90-day return ({ret_90:.1%})")
    if rsi is not None:
        if 45 <= rsi <= 70:
            score += 10
            notes.append(f"RSI in healthy zone ({rsi:.0f})")
        elif rsi > 80:
            notes.append(f"RSI extremely overbought ({rsi:.0f}) — extended")
        elif rsi < 30:
            notes.append(f"RSI very weak ({rsi:.0f})")
        else:
            score += 5

    # --- Volume (25) ---
    vol_recent = _last(df["Volume"].rolling(10).mean())
    vol_base = _last(df["Volume"].rolling(60).mean())
    if vol_recent is not None and vol_base is not None and vol_base > 0:
        if vol_recent > vol_base:
            score += 15
            notes.append("Volume trend expanding")
        else:
            score += 5
            notes.append("Volume trend flat or contracting")
    if stock.volume is not None and stock.avg_volume and stock.volume > stock.avg_volume:
        score += 10
        notes.append("Current volume above average")

    # --- Volatility / extension (25) ---
    atr_pct = (atr / price) if (atr is not None and price) else None
    if atr_pct is not None:
        if atr_pct < 0.04:
            score += 15
            notes.append(f"Low volatility (ATR {atr_pct:.1%} of price)")
        elif atr_pct < 0.07:
            score += 8
            notes.append(f"Moderate volatility (ATR {atr_pct:.1%})")
        else:
            notes.append(f"High volatility (ATR {atr_pct:.1%})")
    if stock.high_52w and price is not None:
        dist_high = (stock.high_52w - price) / stock.high_52w
        if dist_high <= 0.10:
            score += 10
            notes.append(f"Within {dist_high:.0%} of 52-week high")
        elif dist_high <= 0.25:
            score += 5
        else:
            notes.append(f"{dist_high:.0%} below 52-week high")

    entry_zone, invalidation = estimate_entry_zone(df, price, ma20, ma50)
    return min(score, 100.0), notes, entry_zone, invalidation


def _period_return(df, days: int) -> Optional[float]:
    closes = df["Close"].dropna()
    if len(closes) <= days or days <= 0:
        return None
    start = float(closes.iloc[-days - 1])
    end = float(closes.iloc[-1])
    if start == 0:
        return None
    return end / start - 1


def estimate_entry_zone(df, price, ma20, ma50) -> Tuple[str, Optional[float]]:
    """Simple, research-only entry-zone and invalidation estimates."""
    if price is None or ma50 is None:
        return "Not enough data for an entry estimate (research only).", None

    if price > ma50:
        lo, hi = sorted([v for v in (ma20, ma50) if v is not None]) if ma20 else (ma50, ma50)
        if ma20 is not None:
            entry = (
                f"Pullback zone near the 20-day MA (~${ma20:.2f}) to the "
                f"50-day MA (~${ma50:.2f}). Research estimate only — not guaranteed."
            )
        else:
            entry = f"Pullback zone near the 50-day MA (~${ma50:.2f}). Research estimate only."
    else:
        entry = (
            f"Wait for recovery above the 50-day MA (~${ma50:.2f}) before considering. "
            "Research estimate only — not guaranteed."
        )

    # Invalidation: the higher (more conservative) of recent swing low or 8% below MA50.
    swing_low = None
    lows = df["Low"].dropna()
    if len(lows) >= 10:
        swing_low = float(lows.iloc[-10:].min())
    candidates = [v for v in (swing_low, ma50 * 0.92) if v is not None]
    invalidation = max(candidates) if candidates else None
    return entry, invalidation
