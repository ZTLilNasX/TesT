"""Final scoring and classification.

The classification ladder is strict and ordered:
1. Shariah NON-COMPLIANT  => excluded, final score forced to 0.
2. Shariah REQUIRES SCHOLAR REVIEW => never a buy, regardless of scores.
3. Very high risk => HALAL BUT TOO RISKY.
4. All buy thresholds met => HALAL SPECULATIVE BUY.
5. Otherwise => HALAL WATCHLIST.

Profit never overrides Shariah compliance.
"""

from typing import Optional, Tuple

from halalspecbot import config
from halalspecbot.models import ShariahResult, StockData


def compute_ethical_score(stock: Optional[StockData], shariah: ShariahResult) -> float:
    """Ethical impact score 0-100. Haram business is always 0."""
    if shariah.classification == config.SHARIAH_NON_COMPLIANT:
        return 0.0
    if stock is None:
        return float(config.DEFAULT_ETHICAL_SCORE)
    text = " ".join(filter(None, [stock.sector, stock.industry])).lower()
    best = None
    for keyword, value in config.HIGH_IMPACT_SECTORS.items():
        if keyword in text:
            best = max(best or 0, value)
    return float(best if best is not None else config.DEFAULT_ETHICAL_SCORE)


def compute_confidence(data_warnings: list) -> float:
    """100 minus a fixed penalty per missing-data warning, floored at 10."""
    return max(
        config.CONFIDENCE_FLOOR,
        100.0 - len(data_warnings) * config.CONFIDENCE_PENALTY_PER_WARNING,
    )


def _weighted_score(financial: float, technical: float, catalyst: float, risk: float) -> float:
    w = config.SCORE_WEIGHTS
    return (
        financial * w["financial"]
        + technical * w["technical"]
        + catalyst * w["catalyst"]
        + (100.0 - risk) * w["risk"]
    )


def compute_final(
    shariah: ShariahResult,
    financial_score: float,
    technical_score: float,
    catalyst_score: float,
    risk_score: float,
    data_warnings: list,
) -> Tuple[float, float, float, str]:
    """Returns (final_score, speculation_score, confidence, classification)."""
    confidence = compute_confidence(data_warnings)
    t = config.THRESHOLDS

    # 1. Shariah hard stop — no Shariah pass, no speculation.
    if shariah.classification == config.SHARIAH_NON_COMPLIANT:
        return 0.0, 0.0, confidence, config.CLASS_NON_COMPLIANT

    speculation = _weighted_score(financial_score, technical_score, catalyst_score, risk_score)

    # 2. Unclear data => scholar review, never a buy.
    if shariah.classification == config.SHARIAH_REVIEW:
        return speculation, speculation, confidence, config.CLASS_REQUIRES_SCHOLAR_REVIEW

    # 3. Risk gate.
    if risk_score > t["risk_too_high"]:
        return speculation, speculation, confidence, config.CLASS_HALAL_BUT_TOO_RISKY

    # 4. Buy signal — every leg must clear its threshold.
    if (
        financial_score >= t["financial_buy"]
        and technical_score >= t["technical_buy"]
        and catalyst_score >= t["catalyst_buy"]
        and risk_score <= t["risk_buy_max"]
    ):
        return speculation, speculation, confidence, config.CLASS_HALAL_SPECULATIVE_BUY

    # 5. Default.
    return speculation, speculation, confidence, config.CLASS_HALAL_WATCHLIST
