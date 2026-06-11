"""Dashboard alerts (Streamlit-only — no external services).

Alerts fire inside the running app via st.toast and are also kept in
session state so the dashboard can show a persistent alert feed.
"""

from datetime import datetime

from halalspecbot import config

_ALERT_TEMPLATES = {
    config.CLASS_HALAL_SPECULATIVE_BUY: "🟢 {ticker} classified as HALAL SPECULATIVE BUY",
    config.CLASS_HALAL_WATCHLIST: "🔵 {ticker} moved to HALAL WATCHLIST",
    config.CLASS_HALAL_BUT_TOO_RISKY: "🟠 {ticker} risk increased — HALAL BUT TOO RISKY",
    config.CLASS_REQUIRES_SCHOLAR_REVIEW: "🟣 {ticker} requires scholar review",
    config.CLASS_NON_COMPLIANT: "🔴 {ticker} excluded as non-compliant",
}


def classification_alert_message(ticker: str, classification: str) -> str:
    template = _ALERT_TEMPLATES.get(classification, "{ticker} classification updated")
    return template.format(ticker=ticker)


def send_alert(message: str) -> None:
    """Show a toast in the dashboard and append to the in-app alert feed."""
    try:
        import streamlit as st

        st.toast(message)
        feed = st.session_state.setdefault("alert_feed", [])
        feed.insert(0, {"time": datetime.now().strftime("%H:%M:%S"), "message": message})
        # keep the feed from growing without bound
        del feed[100:]
    except Exception:
        # Outside Streamlit (tests, scripts) just print.
        print(f"[ALERT] {message}")


def alert_classification_change(ticker: str, old: str, new: str) -> None:
    """Fire an alert when a ticker's classification changes between scans."""
    if old == new:
        return
    send_alert(classification_alert_message(ticker, new))
    if new == config.CLASS_HALAL_SPECULATIVE_BUY:
        send_alert(f"🚨 {ticker} upgraded — review the full report before acting.")
