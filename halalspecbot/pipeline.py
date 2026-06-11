"""Full analysis pipeline for one ticker.

Shared by the Streamlit app and the watchlist scanner so both run the
identical analysis path: fetch → Shariah screen → analyzers → scoring →
report → database.
"""

from datetime import datetime, timezone

from halalspecbot import config, database
from halalspecbot.catalyst_analyzer import analyze_catalysts
from halalspecbot.data_fetcher import fetch_price_history, fetch_stock_data
from halalspecbot.financial_analyzer import analyze_financials
from halalspecbot.models import AnalysisResult
from halalspecbot.report_generator import generate_report
from halalspecbot.risk_analyzer import analyze_risk
from halalspecbot.scoring_engine import compute_confidence, compute_ethical_score, compute_final
from halalspecbot.shariah_screen import screen_shariah
from halalspecbot.technical_analyzer import analyze_technicals


def run_full_analysis(ticker: str, catalyst_notes: str = "") -> AnalysisResult:
    """Run the whole pipeline. Never raises — errors land in result.error."""
    ticker = ticker.upper().strip()
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    stock, warnings = fetch_stock_data(ticker)

    if stock is None:
        # Could not resolve ticker at all — conservative scholar-review result.
        shariah = screen_shariah(None)
        result = AnalysisResult(
            ticker=ticker,
            shariah=shariah,
            final_classification=config.CLASS_REQUIRES_SCHOLAR_REVIEW,
            confidence_score=compute_confidence(warnings + ["No company data"]),
            data_quality_warnings=warnings,
            analysis_timestamp=timestamp,
            error=warnings[0] if warnings else "No data available",
        )
        result.report_markdown = generate_report(result)
        _persist(result)
        return result

    history = fetch_price_history(ticker)
    shariah = screen_shariah(stock)

    # Hard stop: haram business — skip speculation analysis entirely.
    if shariah.classification == config.SHARIAH_NON_COMPLIANT:
        result = AnalysisResult(
            ticker=ticker,
            stock_data=stock,
            price_history=history,
            shariah=shariah,
            final_classification=config.CLASS_NON_COMPLIANT,
            final_score=0.0,
            ethical_score=0.0,
            confidence_score=compute_confidence(warnings),
            data_quality_warnings=warnings,
            analysis_timestamp=timestamp,
        )
        result.report_markdown = generate_report(result)
        _persist(result)
        return result

    financial_score, fin_notes, fin_warnings = analyze_financials(stock)
    warnings = warnings + fin_warnings

    technical_score, tech_notes, entry_zone, invalidation = analyze_technicals(history, stock)
    catalyst_score, catalyst_factors = analyze_catalysts(stock, catalyst_notes)
    risk_score, risk_notes, scenarios = analyze_risk(stock, history, warnings)
    ethical_score = compute_ethical_score(stock, shariah)

    final_score, speculation_score, confidence, classification = compute_final(
        shariah, financial_score, technical_score, catalyst_score, risk_score, warnings
    )

    result = AnalysisResult(
        ticker=ticker,
        stock_data=stock,
        price_history=history,
        shariah=shariah,
        financial_score=financial_score,
        technical_score=technical_score,
        catalyst_score=catalyst_score,
        risk_score=risk_score,
        ethical_score=ethical_score,
        speculation_score=speculation_score,
        final_score=final_score,
        confidence_score=confidence,
        final_classification=classification,
        entry_zone=entry_zone,
        invalidation_level=invalidation,
        scenarios=scenarios,
        catalyst_factors=catalyst_factors,
        financial_notes=fin_notes,
        technical_notes=tech_notes,
        risk_notes=risk_notes,
        data_quality_warnings=warnings,
        analysis_timestamp=timestamp,
    )
    result.report_markdown = generate_report(result)
    _persist(result)
    return result


def _persist(result: AnalysisResult) -> None:
    """Save the analysis and keep the watchlist entry in sync."""
    try:
        database.init_db()
        database.save_analysis(result)
        database.upsert_watchlist_item(
            ticker=result.ticker,
            status=result.final_classification,
            entry_zone=result.entry_zone or "",
            invalidation_level=result.invalidation_level,
        )
    except Exception:
        # Persistence problems must never break the analysis itself.
        import logging

        logging.getLogger("halalspecbot.pipeline").exception("DB save failed")
