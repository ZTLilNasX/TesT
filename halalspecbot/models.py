"""Dataclasses shared across HalalSpecBot modules."""

from dataclasses import dataclass, field
from typing import Optional

import pandas as pd


@dataclass
class StockData:
    """Snapshot of company info from the data fetcher.

    Every numeric field defaults to None because free data sources
    (yfinance) frequently omit fields, especially for small caps.
    None always means "unknown" — it is never treated as zero.
    """

    ticker: str
    name: Optional[str] = None
    sector: Optional[str] = None
    industry: Optional[str] = None
    business_summary: Optional[str] = None
    country: Optional[str] = None
    exchange: Optional[str] = None
    market_cap: Optional[float] = None
    price: Optional[float] = None
    high_52w: Optional[float] = None
    low_52w: Optional[float] = None
    total_debt: Optional[float] = None
    total_cash: Optional[float] = None
    total_assets: Optional[float] = None
    revenue: Optional[float] = None
    gross_profit: Optional[float] = None
    ebitda: Optional[float] = None
    net_income: Optional[float] = None
    free_cashflow: Optional[float] = None
    operating_cashflow: Optional[float] = None
    profit_margin: Optional[float] = None
    gross_margin: Optional[float] = None
    revenue_growth: Optional[float] = None
    earnings_growth: Optional[float] = None
    beta: Optional[float] = None
    avg_volume: Optional[float] = None
    volume: Optional[float] = None


@dataclass
class PriceHistory:
    """Daily price history with pre-computed indicator columns."""

    ticker: str
    df_6m: pd.DataFrame = field(default_factory=pd.DataFrame)
    df_1y: pd.DataFrame = field(default_factory=pd.DataFrame)

    @property
    def has_data(self) -> bool:
        return not self.df_1y.empty


@dataclass
class ShariahResult:
    """Outcome of the Shariah screen for one ticker."""

    classification: str  # COMPLIANT | REQUIRES SCHOLAR REVIEW | NON-COMPLIANT – EXCLUDED
    score: int  # 100 = clean, 50 = uncertain, 0 = haram
    haram_detected: bool = False
    matched_keywords: list = field(default_factory=list)
    matched_category: Optional[str] = None
    exclusion_reason: Optional[str] = None
    debt_ratio: Optional[float] = None
    debt_risk: str = "UNKNOWN"  # LOW | MODERATE | HIGH | UNKNOWN
    interest_income_risk: str = "UNKNOWN"
    uncertainty_notes: list = field(default_factory=list)
    purification_notes: Optional[str] = None


@dataclass
class ScenarioEstimate:
    """One row of the six-case scenario table."""

    label: str
    probability: str
    price_target: Optional[float]
    move_pct: Optional[float]
    time_horizon: str
    assumptions: str
    what_could_go_wrong: str


@dataclass
class AnalysisResult:
    """Everything produced by a full analysis run for one ticker."""

    ticker: str
    stock_data: Optional[StockData] = None
    price_history: Optional[PriceHistory] = None
    shariah: Optional[ShariahResult] = None
    financial_score: float = 0.0
    technical_score: float = 0.0
    catalyst_score: float = 0.0
    risk_score: float = 50.0
    ethical_score: float = 0.0
    speculation_score: float = 0.0
    final_score: float = 0.0
    confidence_score: float = 0.0
    final_classification: str = ""
    entry_zone: str = ""
    invalidation_level: Optional[float] = None
    scenarios: list = field(default_factory=list)
    catalyst_factors: list = field(default_factory=list)
    financial_notes: list = field(default_factory=list)
    technical_notes: list = field(default_factory=list)
    risk_notes: list = field(default_factory=list)
    data_quality_warnings: list = field(default_factory=list)
    report_markdown: str = ""
    analysis_timestamp: str = ""
    error: Optional[str] = None
