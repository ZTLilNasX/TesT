"""Markdown report builder for one analyzed ticker."""

from halalspecbot import config
from halalspecbot.models import AnalysisResult
from halalspecbot.utils import (
    classification_emoji,
    format_large_number,
    format_percentage,
    format_price,
)


def _bullets(items: list, empty_text: str = "None noted.") -> str:
    if not items:
        return f"- {empty_text}"
    return "\n".join(f"- {item}" for item in items)


def generate_report(result: AnalysisResult) -> str:
    """Build the full Markdown research report."""
    sd = result.stock_data
    sh = result.shariah
    emoji = classification_emoji(result.final_classification)

    lines = [
        f"# HalalSpecBot Report: {result.ticker}",
        "",
        f"*Generated: {result.analysis_timestamp}*",
        "",
        "## 1. Executive Summary",
        "",
        f"**{sd.name or result.ticker}** — {sd.sector or 'Sector unknown'} / "
        f"{sd.industry or 'Industry unknown'}." if sd else "Company data unavailable.",
        "",
        f"Final classification: {emoji} **{result.final_classification}** "
        f"(opportunity score {result.final_score:.0f}/100, confidence {result.confidence_score:.0f}/100).",
        "",
        "## 2. Final Classification",
        "",
        f"{emoji} **{result.final_classification}**",
        "",
    ]

    # --- Shariah review ---
    lines += ["## 3. Shariah Review", ""]
    if sh:
        lines += [
            f"- **Status:** {sh.classification}",
            f"- **Shariah compliance score:** {sh.score}/100",
            f"- **Haram activity detected:** {'Yes' if sh.haram_detected else 'No'}",
        ]
        if sh.matched_category:
            lines.append(f"- **Matched category:** {sh.matched_category}")
        if sh.matched_keywords:
            lines.append(f"- **Matched keywords:** {', '.join(sh.matched_keywords)}")
        if sh.exclusion_reason:
            lines.append(f"- **Exclusion reason:** {sh.exclusion_reason}")
        ratio = f"{sh.debt_ratio:.0%}" if sh.debt_ratio is not None else "Unknown"
        lines += [
            f"- **Debt ratio:** {ratio} ({sh.debt_risk} risk)",
            f"- **Interest income risk:** {sh.interest_income_risk}",
            "",
            "**Uncertainty notes:**",
            _bullets(sh.uncertainty_notes),
            "",
            f"**Purification:** {sh.purification_notes or 'No notes.'}",
        ]
    lines.append("")

    # --- Business analysis ---
    lines += ["## 4. Business Analysis", ""]
    if sd:
        summary = sd.business_summary or "_Business summary unavailable — scholar review required._"
        lines += [
            f"- **Company:** {sd.name or 'Unknown'}",
            f"- **Sector / Industry:** {sd.sector or 'Unknown'} / {sd.industry or 'Unknown'}",
            f"- **Country / Exchange:** {sd.country or 'Unknown'} / {sd.exchange or 'Unknown'}",
            f"- **Market cap:** {format_large_number(sd.market_cap)}",
            "",
            summary,
        ]
    lines.append("")

    # --- Financial analysis ---
    lines += ["## 5. Financial Analysis", ""]
    if sd:
        lines += [
            "| Metric | Value |",
            "|---|---|",
            f"| Revenue | {format_large_number(sd.revenue)} |",
            f"| Net income | {format_large_number(sd.net_income)} |",
            f"| Free cash flow | {format_large_number(sd.free_cashflow)} |",
            f"| Total debt | {format_large_number(sd.total_debt)} |",
            f"| Total cash | {format_large_number(sd.total_cash)} |",
            f"| Profit margin | {format_percentage(sd.profit_margin)} |",
            f"| Revenue growth | {format_percentage(sd.revenue_growth)} |",
            f"| Earnings growth | {format_percentage(sd.earnings_growth)} |",
            "",
        ]
    lines += [
        f"**Financial strength score: {result.financial_score:.0f}/100**",
        "",
        _bullets(result.financial_notes),
        "",
    ]

    # --- Technical analysis ---
    lines += [
        "## 6. Technical Analysis",
        "",
        f"**Technical setup score: {result.technical_score:.0f}/100**",
        "",
        _bullets(result.technical_notes),
        "",
    ]

    # --- Catalyst analysis ---
    lines += [
        "## 7. Catalyst Analysis",
        "",
        f"**Catalyst score: {result.catalyst_score:.0f}/100**",
        "",
        _bullets(result.catalyst_factors),
        "",
    ]

    # --- Risk analysis ---
    lines += [
        "## 8. Risk Analysis",
        "",
        f"**Risk score: {result.risk_score:.0f}/100** (0 = very low risk, 100 = very high risk)",
        "",
        _bullets(result.risk_notes),
        "",
        "Permanent capital loss is always possible in speculative stocks. "
        "Position sizing and diversification are the investor's responsibility.",
        "",
    ]

    # --- Scenario table ---
    lines += ["## 9. Scenario Table", ""]
    if result.scenarios:
        lines += [
            "| Scenario | Probability | Target | Move | Horizon | Key assumptions |",
            "|---|---|---|---|---|---|",
        ]
        for s in result.scenarios:
            move = f"{s.move_pct:+.0%}" if s.move_pct is not None else "N/A"
            lines.append(
                f"| {s.label} | {s.probability} | {format_price(s.price_target)} | "
                f"{move} | {s.time_horizon} | {s.assumptions} |"
            )
    else:
        lines.append("_Insufficient data to build scenario estimates._")
    lines.append("")

    # --- Watchlist plan ---
    inval = format_price(result.invalidation_level) if result.invalidation_level else "N/A"
    lines += [
        "## 10. Watchlist Plan",
        "",
        f"- **Entry zone (research estimate only):** {result.entry_zone or 'N/A'}",
        f"- **Invalidation level (research estimate only):** {inval}",
        "- **What would improve the setup:** stronger financial data, confirmed catalyst, "
        "recovery above key moving averages with healthy volume.",
        "- **What would remove it from the watchlist:** Shariah status change, breakdown below "
        "the invalidation level, deteriorating fundamentals, or rising data uncertainty.",
        "",
    ]

    # --- Purification review ---
    lines += [
        "## 11. Purification Review",
        "",
        f"- **Non-compliant income found:** "
        f"{'Yes' if (sh and sh.haram_detected) else 'Not detected, but cannot be ruled out'}",
        "- **Interest income known:** No — not available from free data sources.",
        f"- **Purification note:** {sh.purification_notes if sh else 'Unknown.'}",
        "",
    ]

    # --- Data quality ---
    if result.data_quality_warnings:
        lines += [
            "## Data Quality Warnings",
            "",
            _bullets(result.data_quality_warnings),
            "",
        ]

    # --- Verdict ---
    lines += [
        "## 12. Final Verdict",
        "",
        f"{emoji} **{result.final_classification}** — Final opportunity score "
        f"{result.final_score:.0f}/100.",
        "",
        "## 13. Confidence Score",
        "",
        f"**{result.confidence_score:.0f}/100** — confidence is reduced for every missing or "
        "uncertain data point.",
        "",
        "---",
        "",
        f"> {config.REPORT_DISCLAIMER}",
        "",
    ]

    return "\n".join(lines)
