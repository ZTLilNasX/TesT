"""Shariah screen tests — the most important guarantees in the app."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from halalspecbot import config
from halalspecbot.models import StockData
from halalspecbot.shariah_screen import screen_shariah

LONG_SUMMARY_PAD = " The company serves customers worldwide through multiple segments."


def make_stock(**kwargs) -> StockData:
    return StockData(ticker=kwargs.pop("ticker", "TEST"), **kwargs)


def test_bank_is_excluded():
    stock = make_stock(
        name="Example Bancorp",
        sector="Financial Services",
        industry="Banks - Diversified",
        business_summary="A bank providing lending and credit card services." + LONG_SUMMARY_PAD,
    )
    result = screen_shariah(stock)
    assert result.classification == config.SHARIAH_NON_COMPLIANT
    assert result.haram_detected is True
    assert result.matched_category == "BANKING_RIBA"
    assert result.matched_keywords


def test_casino_is_excluded():
    stock = make_stock(
        name="Lucky Resorts",
        sector="Consumer Cyclical",
        industry="Resorts & Casinos",
        business_summary="Operates casino resorts and sports betting platforms." + LONG_SUMMARY_PAD,
    )
    result = screen_shariah(stock)
    assert result.classification == config.SHARIAH_NON_COMPLIANT
    assert result.matched_category in ("GAMBLING", "BANKING_RIBA")


def test_alcohol_company_is_excluded():
    stock = make_stock(
        name="Premium Drinks Co",
        sector="Consumer Defensive",
        industry="Beverages - Wineries & Distilleries",
        business_summary="Produces and distributes wine, beer and spirits globally." + LONG_SUMMARY_PAD,
    )
    result = screen_shariah(stock)
    assert result.classification == config.SHARIAH_NON_COMPLIANT
    assert result.matched_category == "ALCOHOL_TOBACCO"


def test_missing_business_description_requires_review():
    stock = make_stock(sector=None, industry=None, business_summary=None)
    result = screen_shariah(stock)
    assert result.classification == config.SHARIAH_REVIEW
    assert result.uncertainty_notes


def test_none_stock_requires_review():
    result = screen_shariah(None)
    assert result.classification == config.SHARIAH_REVIEW


def test_normal_software_company_not_excluded():
    stock = make_stock(
        name="CloudWorks Inc",
        sector="Technology",
        industry="Software - Application",
        business_summary=(
            "CloudWorks develops productivity software for small businesses, "
            "including project management and invoicing tools." + LONG_SUMMARY_PAD
        ),
        market_cap=5e9,
        total_debt=1e8,
    )
    result = screen_shariah(stock)
    assert result.classification == config.SHARIAH_COMPLIANT
    assert result.haram_detected is False
    assert result.debt_risk == "LOW"


def test_haram_keyword_in_summary_only():
    stock = make_stock(
        name="Diversified Holdings",
        sector="Industrials",
        industry="Conglomerates",
        business_summary="The company also operates an online casino division." + LONG_SUMMARY_PAD,
    )
    result = screen_shariah(stock)
    assert result.classification == config.SHARIAH_NON_COMPLIANT


def test_defense_company_requires_review_not_exclusion():
    stock = make_stock(
        name="AeroSystems",
        sector="Industrials",
        industry="Aerospace & Defense",
        business_summary=(
            "Designs aerospace systems and defense electronics for governments." + LONG_SUMMARY_PAD
        ),
        market_cap=1e10,
        total_debt=1e9,
    )
    result = screen_shariah(stock)
    assert result.classification == config.SHARIAH_REVIEW


def test_high_debt_flagged():
    stock = make_stock(
        name="Heavy Industries",
        sector="Industrials",
        industry="Specialty Industrial Machinery",
        business_summary="Manufactures industrial equipment for construction firms." + LONG_SUMMARY_PAD,
        market_cap=1e9,
        total_debt=6e8,  # 60% of market cap
    )
    result = screen_shariah(stock)
    assert result.debt_risk == "HIGH"
    # High debt forces scholar review under the conservative policy
    assert result.classification == config.SHARIAH_REVIEW
    assert "purification" in (result.purification_notes or "").lower()


def test_zero_debt_is_valid_low_risk():
    stock = make_stock(
        name="Debt Free Corp",
        sector="Technology",
        industry="Software - Infrastructure",
        business_summary="Provides cloud infrastructure software to enterprises." + LONG_SUMMARY_PAD,
        market_cap=2e9,
        total_debt=0,
    )
    result = screen_shariah(stock)
    assert result.debt_risk == "LOW"
    assert result.classification == config.SHARIAH_COMPLIANT


def test_word_boundary_no_false_positive():
    # "Birmingham" must not match "ham"; "embankment" must not match "bank".
    stock = make_stock(
        name="Birmingham Machinery",
        sector="Industrials",
        industry="Farm & Heavy Construction Machinery",
        business_summary=(
            "Builds embankment construction machinery from its Birmingham factory." + LONG_SUMMARY_PAD
        ),
        market_cap=1e9,
        total_debt=1e8,
    )
    result = screen_shariah(stock)
    assert result.classification != config.SHARIAH_NON_COMPLIANT
