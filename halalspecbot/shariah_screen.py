"""Strict, conservative Shariah screen.

Rules:
- Any haram keyword match in sector/industry/summary/name => NON-COMPLIANT.
- Missing or unclear business description => REQUIRES SCHOLAR REVIEW.
- High/unknown debt or interest-income exposure is flagged, never ignored.
- The screen never assumes permissibility when data is incomplete.
"""

import re
from typing import Optional

from halalspecbot import config
from halalspecbot.models import ShariahResult, StockData
from halalspecbot.utils import safe_divide


def _keyword_matches(keyword: str, text: str) -> bool:
    """Word-boundary match so 'ham' doesn't hit 'Birmingham'."""
    return re.search(r"\b" + re.escape(keyword) + r"\b", text) is not None


def _scan_haram_keywords(text: str):
    """Return (category, [keywords]) for the first haram category matched."""
    for category, keywords in config.HARAM_KEYWORD_CATEGORIES.items():
        matched = [kw for kw in keywords if _keyword_matches(kw, text)]
        if matched:
            return category, matched
    return None, []


def _scan_review_keywords(text: str) -> list:
    return [kw for kw in config.SCHOLAR_REVIEW_KEYWORDS if _keyword_matches(kw, text)]


def _assess_debt(stock: StockData):
    """Return (debt_ratio, debt_risk_label, note_or_None).

    Uses debt/market_cap first, falls back to debt/assets.
    total_debt == 0 is valid (no debt); None means unknown.
    """
    if stock.total_debt is None:
        return None, "UNKNOWN", "Total debt unknown — debt screen could not be completed."

    if stock.total_debt == 0:
        return 0.0, "LOW", None

    ratio = safe_divide(stock.total_debt, stock.market_cap)
    if ratio is None:
        ratio = safe_divide(stock.total_debt, stock.total_assets)
    if ratio is None:
        return None, "UNKNOWN", (
            "Debt is present but market cap / total assets are unknown — "
            "debt ratio could not be computed."
        )

    if ratio < config.DEBT_RATIO_LOW:
        return ratio, "LOW", None
    if ratio < config.DEBT_RATIO_MODERATE:
        return ratio, "MODERATE", None
    return ratio, "HIGH", (
        f"Debt ratio {ratio:.0%} exceeds the conservative {config.DEBT_RATIO_MODERATE:.0%} "
        "threshold — significant interest-bearing debt exposure."
    )


def screen_shariah(stock: Optional[StockData]) -> ShariahResult:
    """Run the full Shariah screen on one company."""
    # No data at all => scholar review, never assume halal.
    if stock is None:
        return ShariahResult(
            classification=config.SHARIAH_REVIEW,
            score=50,
            uncertainty_notes=[
                "No company data available — Shariah status cannot be determined."
            ],
            purification_notes=(
                "Unknown income sources — purification requirement cannot be assessed. "
                "Scholar review required."
            ),
        )

    scan_text = " ".join(
        filter(
            None,
            [stock.sector, stock.industry, stock.business_summary, stock.name],
        )
    ).lower()

    # ----- Step 1: hard haram keyword screen ------------------------------
    category, matched = _scan_haram_keywords(scan_text)
    if category:
        return ShariahResult(
            classification=config.SHARIAH_NON_COMPLIANT,
            score=0,
            haram_detected=True,
            matched_keywords=matched,
            matched_category=category,
            exclusion_reason=(
                f"Business appears materially involved in a prohibited activity "
                f"({category.replace('_', ' ').title()}). "
                f"Matched keywords: {', '.join(matched)}."
            ),
            debt_risk="N/A",
            interest_income_risk="N/A",
            purification_notes=(
                "Company excluded — purification does not apply because the "
                "investment itself is impermissible."
            ),
        )

    uncertainty: list = []
    review_needed = False

    # ----- Step 2: grey-area keywords -------------------------------------
    review_hits = _scan_review_keywords(scan_text)
    if review_hits:
        review_needed = True
        uncertainty.append(
            "Business touches ambiguous activities requiring scholar judgement: "
            + ", ".join(review_hits)
        )

    # ----- Step 3: missing business data guard -----------------------------
    summary = (stock.business_summary or "").strip()
    if len(summary) < 50:
        review_needed = True
        uncertainty.append(
            "Business description is missing or too short — activities cannot be "
            "verified. Do not assume permissibility."
        )
    if stock.sector is None and stock.industry is None:
        review_needed = True
        uncertainty.append("Sector and industry are both unknown.")

    # ----- Step 4: financial Shariah risk ----------------------------------
    debt_ratio, debt_risk, debt_note = _assess_debt(stock)
    if debt_note:
        uncertainty.append(debt_note)
    if debt_risk in ("HIGH", "UNKNOWN"):
        review_needed = True

    # Interest income is not exposed by free data — always flag uncertainty.
    interest_risk = "UNKNOWN"
    uncertainty.append(
        "Interest income data is not available from free sources — "
        "non-compliant income cannot be ruled out."
    )

    # ----- Step 5: purification note ---------------------------------------
    purification = (
        "Interest income could not be verified. If any non-compliant income exists, "
        "purification of a portion of dividends/gains may be required. "
        "Scholar review recommended."
    )
    if debt_ratio is not None and debt_ratio > config.DEBT_PURIFICATION_NOTE_RATIO:
        purification = (
            f"Debt ratio is {debt_ratio:.0%}. Purification may be required for "
            "income linked to interest-bearing debt, and scholar review is needed."
        )

    if review_needed:
        return ShariahResult(
            classification=config.SHARIAH_REVIEW,
            score=50,
            matched_keywords=review_hits,
            debt_ratio=debt_ratio,
            debt_risk=debt_risk,
            interest_income_risk=interest_risk,
            uncertainty_notes=uncertainty,
            purification_notes=purification,
        )

    return ShariahResult(
        classification=config.SHARIAH_COMPLIANT,
        score=100 if debt_risk == "LOW" else 80,
        debt_ratio=debt_ratio,
        debt_risk=debt_risk,
        interest_income_risk=interest_risk,
        uncertainty_notes=uncertainty,
        purification_notes=purification,
    )
