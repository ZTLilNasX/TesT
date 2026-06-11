"""Fetch company info and price history from yfinance (free data, MVP).

Design rule: never crash because a field is missing. Every field access
goes through _safe_get, and the whole fetch is wrapped in try/except.
Missing fields are reported back as warnings so the confidence score
can be penalized downstream.
"""

import logging
import math
from datetime import datetime, timedelta
from typing import Optional, Tuple

import pandas as pd

from halalspecbot.models import PriceHistory, StockData

logger = logging.getLogger("halalspecbot.data_fetcher")

# Fields whose absence should be flagged as a data-quality warning.
_CRITICAL_FIELDS = {
    "business_summary": "longBusinessSummary",
    "sector": "sector",
    "industry": "industry",
    "market_cap": "marketCap",
    "price": "currentPrice",
    "total_debt": "totalDebt",
    "total_cash": "totalCash",
    "revenue": "totalRevenue",
    "net_income": "netIncomeToCommon",
    "free_cashflow": "freeCashflow",
}


def _safe_get(info: dict, key: str, fallback=None):
    """Get a value from yfinance info, treating None/NaN as missing."""
    val = info.get(key, fallback)
    if val is None:
        return fallback
    if isinstance(val, float) and math.isnan(val):
        return fallback
    return val


def fetch_stock_data(ticker: str) -> Tuple[Optional[StockData], list]:
    """Fetch fundamentals for one ticker.

    Returns (StockData, warnings). StockData is None only when the ticker
    could not be resolved at all.
    """
    warnings: list = []
    try:
        import yfinance as yf

        info = yf.Ticker(ticker).info or {}
    except Exception as exc:  # network errors, delisted tickers, etc.
        logger.warning("yfinance fetch failed for %s: %s", ticker, exc)
        return None, [f"Data fetch failed for {ticker}: {exc}"]

    # yfinance returns a near-empty dict for unknown tickers
    if not info or info.get("quoteType") is None and len(info) < 5:
        return None, [f"Ticker {ticker} not found or no data available"]

    price = _safe_get(info, "currentPrice", _safe_get(info, "regularMarketPrice"))

    data = StockData(
        ticker=ticker.upper(),
        name=_safe_get(info, "shortName", _safe_get(info, "longName")),
        sector=_safe_get(info, "sector"),
        industry=_safe_get(info, "industry"),
        business_summary=_safe_get(info, "longBusinessSummary"),
        country=_safe_get(info, "country"),
        exchange=_safe_get(info, "exchange"),
        market_cap=_safe_get(info, "marketCap"),
        price=price,
        high_52w=_safe_get(info, "fiftyTwoWeekHigh"),
        low_52w=_safe_get(info, "fiftyTwoWeekLow"),
        total_debt=_safe_get(info, "totalDebt"),
        total_cash=_safe_get(info, "totalCash"),
        total_assets=_safe_get(info, "totalAssets"),
        revenue=_safe_get(info, "totalRevenue"),
        gross_profit=_safe_get(info, "grossProfits"),
        ebitda=_safe_get(info, "ebitda"),
        net_income=_safe_get(info, "netIncomeToCommon"),
        free_cashflow=_safe_get(info, "freeCashflow"),
        operating_cashflow=_safe_get(info, "operatingCashflow"),
        profit_margin=_safe_get(info, "profitMargins"),
        gross_margin=_safe_get(info, "grossMargins"),
        revenue_growth=_safe_get(info, "revenueGrowth"),
        earnings_growth=_safe_get(info, "earningsGrowth"),
        beta=_safe_get(info, "beta"),
        avg_volume=_safe_get(info, "averageVolume"),
        volume=_safe_get(info, "volume"),
    )

    for field_name, yf_key in _CRITICAL_FIELDS.items():
        if getattr(data, field_name, None) is None:
            warnings.append(f"Missing data: {field_name} ({yf_key})")

    return data, warnings


def _add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Add moving averages, RSI, and ATR columns in place."""
    close = df["Close"]
    df["MA20"] = close.rolling(20).mean()
    df["MA50"] = close.rolling(50).mean()
    df["MA200"] = close.rolling(200).mean()

    # RSI 14 (Wilder smoothing approximated with EWM)
    delta = close.diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / 14, min_periods=14).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1 / 14, min_periods=14).mean()
    rs = gain / loss.replace(0, pd.NA)
    df["RSI14"] = 100 - (100 / (1 + rs))

    # ATR 14
    prev_close = close.shift(1)
    tr = pd.concat(
        [
            df["High"] - df["Low"],
            (df["High"] - prev_close).abs(),
            (df["Low"] - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    df["ATR14"] = tr.rolling(14).mean()
    return df


def fetch_price_history(ticker: str) -> PriceHistory:
    """Fetch 1y of daily candles; the 6m frame is a slice of the same data."""
    try:
        import yfinance as yf

        df = yf.Ticker(ticker).history(period="1y", interval="1d")
    except Exception as exc:
        logger.warning("price history fetch failed for %s: %s", ticker, exc)
        return PriceHistory(ticker=ticker)

    if df is None or df.empty:
        return PriceHistory(ticker=ticker)

    df = _add_indicators(df.copy())
    cutoff = datetime.now(tz=df.index.tz) - timedelta(days=182)
    df_6m = df[df.index >= cutoff]
    return PriceHistory(ticker=ticker, df_6m=df_6m, df_1y=df)
