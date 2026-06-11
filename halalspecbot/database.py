"""SQLite persistence layer for HalalSpecBot."""

import json
import os
import sqlite3
from datetime import datetime, timezone
from typing import Optional

from halalspecbot import config
from halalspecbot.models import AnalysisResult


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_connection(db_path: str = config.DB_PATH) -> sqlite3.Connection:
    """Open a connection. Cheap for SQLite, so callers open per request."""
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: str = config.DB_PATH) -> None:
    """Create all tables if they don't exist."""
    conn = get_connection(db_path)
    try:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS stocks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT UNIQUE NOT NULL,
                company_name TEXT,
                sector TEXT,
                industry TEXT,
                exchange TEXT,
                country TEXT,
                business_summary TEXT,
                last_price REAL,
                market_cap REAL,
                created_at TEXT,
                updated_at TEXT
            );

            CREATE TABLE IF NOT EXISTS shariah_reviews (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT NOT NULL,
                classification TEXT NOT NULL,
                shariah_score INTEGER,
                haram_activity_detected INTEGER,
                matched_keywords TEXT,
                debt_risk TEXT,
                interest_income_risk TEXT,
                uncertainty_notes TEXT,
                purification_notes TEXT,
                created_at TEXT
            );

            CREATE TABLE IF NOT EXISTS stock_scores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT NOT NULL,
                speculation_score REAL,
                catalyst_score REAL,
                financial_score REAL,
                technical_score REAL,
                risk_score REAL,
                ethical_score REAL,
                final_score REAL,
                confidence_score REAL,
                created_at TEXT
            );

            CREATE TABLE IF NOT EXISTS reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT NOT NULL,
                report_markdown TEXT,
                final_verdict TEXT,
                confidence_score REAL,
                created_at TEXT
            );

            CREATE TABLE IF NOT EXISTS watchlist (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT UNIQUE NOT NULL,
                status TEXT NOT NULL,
                entry_zone TEXT,
                invalidation_level REAL,
                notes TEXT,
                created_at TEXT,
                updated_at TEXT
            );
            """
        )
        conn.commit()
    finally:
        conn.close()


def save_analysis(result: AnalysisResult, db_path: str = config.DB_PATH) -> None:
    """Persist a full analysis run: stock info, shariah review, scores, report."""
    conn = get_connection(db_path)
    try:
        now = _now()
        sd = result.stock_data
        if sd is not None:
            conn.execute(
                """
                INSERT INTO stocks (ticker, company_name, sector, industry, exchange,
                                    country, business_summary, last_price, market_cap,
                                    created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(ticker) DO UPDATE SET
                    company_name=excluded.company_name,
                    sector=excluded.sector,
                    industry=excluded.industry,
                    exchange=excluded.exchange,
                    country=excluded.country,
                    business_summary=excluded.business_summary,
                    last_price=excluded.last_price,
                    market_cap=excluded.market_cap,
                    updated_at=excluded.updated_at
                """,
                (
                    result.ticker, sd.name, sd.sector, sd.industry, sd.exchange,
                    sd.country, sd.business_summary, sd.price, sd.market_cap, now, now,
                ),
            )

        sh = result.shariah
        if sh is not None:
            conn.execute(
                """
                INSERT INTO shariah_reviews
                    (ticker, classification, shariah_score, haram_activity_detected,
                     matched_keywords, debt_risk, interest_income_risk,
                     uncertainty_notes, purification_notes, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    result.ticker, sh.classification, sh.score, int(sh.haram_detected),
                    json.dumps(sh.matched_keywords), sh.debt_risk,
                    sh.interest_income_risk, json.dumps(sh.uncertainty_notes),
                    sh.purification_notes, now,
                ),
            )

        conn.execute(
            """
            INSERT INTO stock_scores
                (ticker, speculation_score, catalyst_score, financial_score,
                 technical_score, risk_score, ethical_score, final_score,
                 confidence_score, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                result.ticker, result.speculation_score, result.catalyst_score,
                result.financial_score, result.technical_score, result.risk_score,
                result.ethical_score, result.final_score, result.confidence_score, now,
            ),
        )

        conn.execute(
            """
            INSERT INTO reports (ticker, report_markdown, final_verdict,
                                 confidence_score, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                result.ticker, result.report_markdown,
                result.final_classification, result.confidence_score, now,
            ),
        )
        conn.commit()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Watchlist CRUD
# ---------------------------------------------------------------------------

def upsert_watchlist_item(
    ticker: str,
    status: str,
    entry_zone: str = "",
    invalidation_level: Optional[float] = None,
    notes: str = "",
    db_path: str = config.DB_PATH,
) -> None:
    conn = get_connection(db_path)
    try:
        now = _now()
        conn.execute(
            """
            INSERT INTO watchlist (ticker, status, entry_zone, invalidation_level,
                                   notes, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(ticker) DO UPDATE SET
                status=excluded.status,
                entry_zone=excluded.entry_zone,
                invalidation_level=excluded.invalidation_level,
                notes=excluded.notes,
                updated_at=excluded.updated_at
            """,
            (ticker, status, entry_zone, invalidation_level, notes, now, now),
        )
        conn.commit()
    finally:
        conn.close()


def get_watchlist_items(
    statuses: Optional[list] = None, db_path: str = config.DB_PATH
) -> list:
    """Return watchlist rows as dicts, optionally filtered by status."""
    conn = get_connection(db_path)
    try:
        if statuses:
            placeholders = ",".join("?" for _ in statuses)
            rows = conn.execute(
                f"SELECT * FROM watchlist WHERE status IN ({placeholders}) "
                "ORDER BY updated_at DESC",
                statuses,
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM watchlist ORDER BY updated_at DESC"
            ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def delete_watchlist_item(ticker: str, db_path: str = config.DB_PATH) -> None:
    conn = get_connection(db_path)
    try:
        conn.execute("DELETE FROM watchlist WHERE ticker = ?", (ticker,))
        conn.commit()
    finally:
        conn.close()


def get_latest_scores(db_path: str = config.DB_PATH) -> dict:
    """Map ticker -> most recent stock_scores row (as dict)."""
    conn = get_connection(db_path)
    try:
        rows = conn.execute(
            """
            SELECT s.* FROM stock_scores s
            JOIN (SELECT ticker, MAX(created_at) AS mc FROM stock_scores GROUP BY ticker) m
              ON s.ticker = m.ticker AND s.created_at = m.mc
            """
        ).fetchall()
        return {r["ticker"]: dict(r) for r in rows}
    finally:
        conn.close()


def get_latest_report(ticker: str, db_path: str = config.DB_PATH) -> Optional[dict]:
    conn = get_connection(db_path)
    try:
        row = conn.execute(
            "SELECT * FROM reports WHERE ticker = ? ORDER BY created_at DESC LIMIT 1",
            (ticker,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()
