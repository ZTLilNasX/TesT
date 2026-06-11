"""Market discovery scanner.

Two-stage design so we can search a large universe without running the full
(slow) analysis on every ticker:

1. Fast momentum pass — one batched price download for the whole universe,
   then a cheap momentum/volume/breakout score per ticker. This finds the
   names *behaving* like they could move sharply.
2. Deep analysis — run the full Shariah + scoring pipeline only on the top
   momentum candidates, so the expensive work is spent where it matters.

Important: a high momentum score is NOT a prediction of a big gain. It only
means the stock has recently moved and traded actively. The strict Shariah
screen and risk scoring still gate every result — explosive-but-dangerous
names are surfaced as HALAL BUT TOO RISKY, not hidden.
"""

import logging
from dataclasses import dataclass
from typing import List, Optional, Tuple

import numpy as np
import pandas as pd

from halalspecbot import config
from halalspecbot.pipeline import run_full_analysis

logger = logging.getLogger("halalspecbot.discovery")


@dataclass
class MomentumHit:
    """Result of the cheap first-pass momentum screen for one ticker."""

    ticker: str
    momentum_score: float          # 0-100, composite of the factors below
    last_price: Optional[float]
    ret_1m: Optional[float]
    ret_3m: Optional[float]
    volume_surge: Optional[float]  # recent vs baseline average volume
    near_high: Optional[float]     # last close / 6-month high (1.0 = at highs)
    volatility: Optional[float]    # daily return std (higher = more explosive/risky)


def _chunked(seq: list, size: int):
    for i in range(0, len(seq), size):
        yield seq[i : i + size]


def _download_prices(tickers: List[str]) -> dict:
    """Batched price download. Returns {ticker: close_series_with_volume_df}."""
    import yfinance as yf

    frames: dict = {}
    for chunk in _chunked(tickers, config.DISCOVERY_DOWNLOAD_CHUNK):
        try:
            data = yf.download(
                chunk,
                period=config.DISCOVERY_PRICE_PERIOD,
                interval="1d",
                group_by="ticker",
                auto_adjust=True,
                threads=True,
                progress=False,
            )
        except Exception as exc:
            logger.warning("batch download failed for %s: %s", chunk, exc)
            continue

        for ticker in chunk:
            try:
                if len(chunk) == 1:
                    df = data
                else:
                    df = data[ticker] if ticker in data.columns.get_level_values(0) else None
                if df is None or df.empty or df["Close"].dropna().empty:
                    continue
                frames[ticker] = df.dropna(how="all")
            except Exception:
                continue
    return frames


def _safe_return(close: pd.Series, days: int) -> Optional[float]:
    c = close.dropna()
    if len(c) <= days or days <= 0:
        return None
    start = float(c.iloc[-days - 1])
    if start == 0:
        return None
    return float(c.iloc[-1]) / start - 1


def _score_momentum(df: pd.DataFrame) -> MomentumHit:
    close = df["Close"].dropna()
    volume = df["Volume"].dropna() if "Volume" in df else pd.Series(dtype=float)

    last_price = float(close.iloc[-1]) if not close.empty else None
    ret_1m = _safe_return(close, 21)
    ret_3m = _safe_return(close, 63)

    volume_surge = None
    if len(volume) >= 60:
        recent = float(volume.iloc[-5:].mean())
        base = float(volume.iloc[-60:].mean())
        if base > 0:
            volume_surge = recent / base

    near_high = None
    if len(close) >= 20:
        period_high = float(close.max())
        if period_high > 0 and last_price is not None:
            near_high = last_price / period_high

    volatility = None
    if len(close) >= 20:
        volatility = float(close.pct_change().dropna().std())

    # Composite momentum score (0-100). Rewards positive momentum, volume
    # expansion, and proximity to highs. Volatility is informational only.
    score = 0.0
    if ret_1m is not None:
        score += float(np.clip(ret_1m * 100, -20, 35))      # up to +35 for a strong month
    if ret_3m is not None:
        score += float(np.clip(ret_3m * 60, -15, 30))       # up to +30 for a strong quarter
    if volume_surge is not None:
        score += float(np.clip((volume_surge - 1) * 25, 0, 20))  # up to +20 on volume surge
    if near_high is not None:
        score += float(np.clip((near_high - 0.7) / 0.3 * 15, 0, 15))  # up to +15 near highs
    score = float(np.clip(score, 0, 100))

    return MomentumHit(
        ticker=df.attrs.get("ticker", ""),
        momentum_score=score,
        last_price=last_price,
        ret_1m=ret_1m,
        ret_3m=ret_3m,
        volume_surge=volume_surge,
        near_high=near_high,
        volatility=volatility,
    )


def fast_momentum_scan(universe: List[str]) -> List[MomentumHit]:
    """Stage 1: cheap momentum ranking across the whole universe."""
    frames = _download_prices(universe)
    hits: List[MomentumHit] = []
    for ticker, df in frames.items():
        df.attrs["ticker"] = ticker
        try:
            hits.append(_score_momentum(df))
        except Exception as exc:
            logger.warning("momentum scoring failed for %s: %s", ticker, exc)
    hits.sort(key=lambda h: h.momentum_score, reverse=True)
    return hits


def discover_candidates(
    universe: Optional[List[str]] = None,
    top_n: int = config.DISCOVERY_DEFAULT_TOP_N,
    catalyst_notes: str = "",
    progress_cb=None,
) -> Tuple[List[MomentumHit], list]:
    """Full discovery run.

    Returns (momentum_hits, analysis_results). analysis_results are the deep
    AnalysisResult objects for the top momentum names, sorted with halal
    candidates first and excluded names last.
    """
    universe = universe or config.DISCOVERY_UNIVERSE
    hits = fast_momentum_scan(universe)
    top = hits[: max(1, top_n)]

    results = []
    for i, hit in enumerate(top):
        if progress_cb:
            progress_cb(i + 1, len(top), hit.ticker)
        try:
            results.append(run_full_analysis(hit.ticker, catalyst_notes))
        except Exception as exc:
            logger.warning("deep analysis failed for %s: %s", hit.ticker, exc)

    def sort_key(r):
        rank = {
            config.CLASS_HALAL_SPECULATIVE_BUY: 0,
            config.CLASS_HALAL_WATCHLIST: 1,
            config.CLASS_HALAL_BUT_TOO_RISKY: 2,
            config.CLASS_REQUIRES_SCHOLAR_REVIEW: 3,
            config.CLASS_NON_COMPLIANT: 4,
        }.get(r.final_classification, 5)
        return (rank, -(r.final_score or 0))

    results.sort(key=sort_key)
    return hits, results
