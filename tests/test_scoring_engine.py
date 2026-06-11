"""Scoring engine tests — the classification ladder must be strict."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from halalspecbot import config
from halalspecbot.models import ShariahResult, StockData
from halalspecbot.scoring_engine import compute_ethical_score, compute_final


def shariah(classification: str, score: int = 100, haram: bool = False) -> ShariahResult:
    return ShariahResult(classification=classification, score=score, haram_detected=haram)


def test_non_compliant_final_score_is_zero():
    final, spec, conf, cls = compute_final(
        shariah(config.SHARIAH_NON_COMPLIANT, 0, True), 90, 90, 90, 10, []
    )
    assert final == 0.0
    assert cls == config.CLASS_NON_COMPLIANT


def test_scholar_review_never_becomes_buy():
    final, spec, conf, cls = compute_final(
        shariah(config.SHARIAH_REVIEW, 50), 90, 90, 90, 10, []
    )
    assert cls == config.CLASS_REQUIRES_SCHOLAR_REVIEW
    assert cls != config.CLASS_HALAL_SPECULATIVE_BUY


def test_high_score_halal_company_becomes_buy():
    final, spec, conf, cls = compute_final(
        shariah(config.SHARIAH_COMPLIANT), 70, 70, 65, 50, []
    )
    assert cls == config.CLASS_HALAL_SPECULATIVE_BUY
    assert final > 0


def test_high_risk_company_too_risky():
    final, spec, conf, cls = compute_final(
        shariah(config.SHARIAH_COMPLIANT), 90, 90, 90, 80, []
    )
    assert cls == config.CLASS_HALAL_BUT_TOO_RISKY


def test_mediocre_halal_company_goes_to_watchlist():
    final, spec, conf, cls = compute_final(
        shariah(config.SHARIAH_COMPLIANT), 50, 50, 50, 40, []
    )
    assert cls == config.CLASS_HALAL_WATCHLIST


def test_one_weak_leg_blocks_buy():
    # Strong everywhere except catalyst — must not be a buy.
    final, spec, conf, cls = compute_final(
        shariah(config.SHARIAH_COMPLIANT), 80, 80, 30, 40, []
    )
    assert cls == config.CLASS_HALAL_WATCHLIST


def test_weighted_score_formula():
    # fin=80*0.35 + tech=60*0.25 + cat=70*0.20 + (100-40)*0.20 = 28+15+14+12 = 69
    final, spec, conf, cls = compute_final(
        shariah(config.SHARIAH_COMPLIANT), 80, 60, 70, 40, []
    )
    assert abs(final - 69.0) < 0.1


def test_confidence_penalized_for_missing_data():
    warnings = ["w1", "w2", "w3", "w4", "w5"]
    _, _, conf, _ = compute_final(
        shariah(config.SHARIAH_COMPLIANT), 50, 50, 50, 40, warnings
    )
    assert conf == 75.0


def test_confidence_has_floor():
    warnings = [f"w{i}" for i in range(50)]
    _, _, conf, _ = compute_final(
        shariah(config.SHARIAH_COMPLIANT), 50, 50, 50, 40, warnings
    )
    assert conf == config.CONFIDENCE_FLOOR


def test_ethical_score_zero_for_haram():
    stock = StockData(ticker="X", sector="Healthcare")
    score = compute_ethical_score(stock, shariah(config.SHARIAH_NON_COMPLIANT, 0, True))
    assert score == 0.0


def test_ethical_score_high_for_healthcare():
    stock = StockData(ticker="X", sector="Healthcare", industry="Medical Devices")
    score = compute_ethical_score(stock, shariah(config.SHARIAH_COMPLIANT))
    assert score >= 80
