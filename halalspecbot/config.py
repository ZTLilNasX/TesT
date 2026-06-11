"""Central configuration for HalalSpecBot.

This module holds every constant the app uses: haram keyword lists,
scoring weights, classification thresholds, and the database path.
It must never import from other halalspecbot modules.
"""

import os

# ---------------------------------------------------------------------------
# Classification labels (use these constants everywhere — never raw strings)
# ---------------------------------------------------------------------------

CLASS_HALAL_SPECULATIVE_BUY = "HALAL SPECULATIVE BUY"
CLASS_HALAL_WATCHLIST = "HALAL WATCHLIST"
CLASS_HALAL_BUT_TOO_RISKY = "HALAL BUT TOO RISKY"
CLASS_REQUIRES_SCHOLAR_REVIEW = "REQUIRES SCHOLAR REVIEW"
CLASS_NON_COMPLIANT = "NON-COMPLIANT – EXCLUDED"

# Shariah screen-level statuses (before final classification)
SHARIAH_COMPLIANT = "COMPLIANT"
SHARIAH_REVIEW = CLASS_REQUIRES_SCHOLAR_REVIEW
SHARIAH_NON_COMPLIANT = CLASS_NON_COMPLIANT

ALL_CLASSIFICATIONS = [
    CLASS_HALAL_SPECULATIVE_BUY,
    CLASS_HALAL_WATCHLIST,
    CLASS_HALAL_BUT_TOO_RISKY,
    CLASS_REQUIRES_SCHOLAR_REVIEW,
    CLASS_NON_COMPLIANT,
]

# ---------------------------------------------------------------------------
# Haram business keyword categories
# Keywords are matched with word boundaries against sector, industry,
# business summary, and company name (all lowercased).
# A single match in any category => NON-COMPLIANT – EXCLUDED.
# ---------------------------------------------------------------------------

BANKING_RIBA_KEYWORDS = [
    "bank",
    "banking",
    "bancorp",
    "bancshares",
    "credit card",
    "consumer finance",
    "mortgage finance",
    "mortgage lending",
    "payday",
    "pawn",
    "lending",
    "lender",
    "interest income",
    "net interest",
    "savings and loan",
    "credit union",
    "usury",
    "riba",
]

GAMBLING_KEYWORDS = [
    "casino",
    "casinos",
    "gambling",
    "betting",
    "sportsbook",
    "lottery",
    "wagering",
    "slot machine",
    "poker",
    "bingo",
    "racetrack",
]

ALCOHOL_TOBACCO_KEYWORDS = [
    "alcohol",
    "alcoholic",
    "beer",
    "wine",
    "winery",
    "brewery",
    "brewing",
    "distillery",
    "distilled",
    "spirits",
    "liquor",
    "tobacco",
    "cigarette",
    "cigarettes",
    "cigar",
    "vape",
    "vaping",
    "e-cigarette",
    "nicotine",
]

ADULT_KEYWORDS = [
    "adult entertainment",
    "pornography",
    "pornographic",
    "sexually explicit",
    "adult content",
    "strip club",
    "escort services",
]

PORK_HARAM_FOOD_KEYWORDS = [
    "pork",
    "swine",
    "bacon",
    "ham products",
    "hog",
    "pig farming",
    "lard",
]

INSURANCE_KEYWORDS = [
    "insurance",
    "insurer",
    "reinsurance",
    "underwriting",
    "annuity",
    "annuities",
]

UNETHICAL_KEYWORDS = [
    "predatory lending",
    "cluster bomb",
    "landmine",
    "fraud scheme",
]

HARAM_KEYWORD_CATEGORIES = {
    "BANKING_RIBA": BANKING_RIBA_KEYWORDS,
    "GAMBLING": GAMBLING_KEYWORDS,
    "ALCOHOL_TOBACCO": ALCOHOL_TOBACCO_KEYWORDS,
    "ADULT_CONTENT": ADULT_KEYWORDS,
    "PORK_HARAM_FOOD": PORK_HARAM_FOOD_KEYWORDS,
    "CONVENTIONAL_INSURANCE": INSURANCE_KEYWORDS,
    "UNETHICAL_BUSINESS": UNETHICAL_KEYWORDS,
}

# Grey-area keywords: ambiguous businesses that need a human scholar's eye.
# A match here => REQUIRES SCHOLAR REVIEW (not automatic exclusion).
SCHOLAR_REVIEW_KEYWORDS = [
    "defense",
    "defence",
    "weapons",
    "firearms",
    "ammunition",
    "aerospace & defense",
    "financial services",
    "fintech",
    "entertainment",
    "media",
    "music",
    "film",
    "streaming",
    "hotel",
    "restaurant",
    "cannabis",
    "marijuana",
]

# ---------------------------------------------------------------------------
# Ethical impact sector scoring (0–100)
# ---------------------------------------------------------------------------

HIGH_IMPACT_SECTORS = {
    "healthcare": 90,
    "education": 90,
    "infrastructure": 85,
    "utilities": 80,
    "industrials": 75,
    "manufacturing": 80,
    "agriculture": 85,
    "consumer defensive": 75,
    "technology": 70,
    "semiconductors": 80,
    "cybersecurity": 75,
    "logistics": 80,
    "clean energy": 90,
    "renewable": 90,
    "basic materials": 65,
    "energy": 60,
    "real estate": 60,
    "communication services": 50,
    "consumer cyclical": 50,
}
DEFAULT_ETHICAL_SCORE = 50

# ---------------------------------------------------------------------------
# Scoring weights and classification thresholds
# ---------------------------------------------------------------------------

SCORE_WEIGHTS = {
    "financial": 0.35,
    "technical": 0.25,
    "catalyst": 0.20,
    "risk": 0.20,  # inverted: (100 - risk_score) is what enters the weighted sum
}

THRESHOLDS = {
    "financial_buy": 65,
    "technical_buy": 65,
    "catalyst_buy": 60,
    "risk_buy_max": 60,   # risk must be <= this for a BUY
    "risk_too_high": 75,  # above this => HALAL BUT TOO RISKY
}

# Shariah financial risk thresholds (debt relative to market cap or assets)
DEBT_RATIO_LOW = 0.30
DEBT_RATIO_MODERATE = 0.50
DEBT_PURIFICATION_NOTE_RATIO = 0.33

CONFIDENCE_PENALTY_PER_WARNING = 5.0
CONFIDENCE_FLOOR = 10.0

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(_PROJECT_ROOT, "data", "halalspecbot.db")

# ---------------------------------------------------------------------------
# Disclaimers (always shown — never remove)
# ---------------------------------------------------------------------------

APP_WARNING = (
    "This bot is for research only. It is not financial advice and not a fatwa. "
    "When Shariah status is uncertain, consult a qualified scholar."
)

REPORT_DISCLAIMER = (
    "This report is for research only. It is not financial advice and not a fatwa. "
    "Consult a qualified scholar and licensed financial professional before making decisions."
)

NO_NEWS_NOTE = "No verified live news catalyst included in MVP."

# ---------------------------------------------------------------------------
# Discovery universe — a broad mixed list of US tickers the market scanner
# searches for high-momentum halal candidates. This is a starting universe,
# not advice; every ticker still passes the strict Shariah screen, and known
# haram names (banks, casinos, etc.) are intentionally included to demonstrate
# that the screen excludes them. Users can paste their own list in the app.
# ---------------------------------------------------------------------------

DISCOVERY_UNIVERSE = [
    # Mega-cap tech & communication
    "AAPL", "MSFT", "GOOGL", "AMZN", "META", "NFLX", "ADBE", "CRM", "ORCL",
    "CSCO", "IBM", "QCOM", "TXN", "INTC", "AMD", "NVDA", "AVGO", "MU", "ASML",
    "AMAT", "LRCX", "KLAC", "MRVL", "ON", "SWKS", "TER", "ENPH", "FSLR",
    # Software / growth / momentum
    "NOW", "SNOW", "PLTR", "DDOG", "NET", "CRWD", "ZS", "PANW", "FTNT", "S",
    "MDB", "TEAM", "SHOP", "SQ", "PYPL", "UBER", "ABNB", "DASH", "RBLX", "U",
    "TTD", "ROKU", "PINS", "SNAP", "SPOT", "TWLO", "OKTA", "DOCU", "ZM", "HUBS",
    "DELL", "HPQ", "WDC", "STX", "ANET", "SMCI", "ARM",
    # Semiconductors / hardware momentum
    "WOLF", "INDI", "AEHR", "NVTS", "QUBT", "RGTI", "IONQ", "LAES",
    # EV / clean energy / battery (volatile)
    "TSLA", "RIVN", "LCID", "NIO", "XPEV", "LI", "CHPT", "PLUG", "BLNK",
    "RUN", "SEDG", "NEE", "BE", "QS", "FCEL",
    # Healthcare / biotech (some explosive small caps)
    "JNJ", "PFE", "MRK", "ABBV", "LLY", "UNH", "TMO", "DHR", "ABT", "AMGN",
    "GILD", "REGN", "VRTX", "MRNA", "BNTX", "ISRG", "DXCM", "ALNY", "SRPT",
    "CRSP", "NTLA", "BEAM", "VKTX", "RXRX", "TEM",
    # Industrials / infrastructure / defense (defense → scholar review)
    "GE", "HON", "CAT", "DE", "BA", "LMT", "RTX", "NOC", "GD", "EMR", "ETN",
    "PH", "ROK", "URI", "PWR", "FAST", "GEV", "VRT",
    # Energy
    "XOM", "CVX", "COP", "SLB", "EOG", "OXY", "DVN", "MPC", "PSX", "FANG",
    "LNG", "CEG", "SMR", "OKLO",
    # Consumer / retail
    "WMT", "COST", "HD", "LOW", "NKE", "MCD", "SBUX", "TGT", "LULU", "CMG",
    "PG", "KO", "PEP", "DIS", "ELF", "DECK", "CAVA", "CELH",
    # Materials / mining (commodity momentum)
    "FCX", "NEM", "ALB", "MP", "CLF", "X", "AA", "SCCO",
    # Financials / banks (expected NON-COMPLIANT — proves the screen works)
    "JPM", "BAC", "WFC", "GS", "MS", "C", "V", "MA", "AXP", "SCHW",
    # Misc high-volatility / meme / momentum names
    "GME", "AMC", "COIN", "HOOD", "SOFI", "AFRM", "DKNG", "CVNA", "UPST",
    "MARA", "RIOT", "CLSK", "HUT", "BTBT",
]

# Discovery scan tuning
DISCOVERY_DEFAULT_TOP_N = 20          # deep-analyze this many top momentum names
DISCOVERY_PRICE_PERIOD = "6mo"        # history window for the fast momentum pass
DISCOVERY_DOWNLOAD_CHUNK = 50         # tickers per batched yfinance download

DISCOVERY_DISCLAIMER = (
    "Discovery finds stocks with high-momentum / breakout characteristics — it does "
    "NOT predict that any stock will rise 100% or 1000%. No tool can. Most fast movers "
    "are extremely risky and can lose most of their value. Treat every result as a "
    "starting point for your own research and scholar review, never as a signal to buy."
)
