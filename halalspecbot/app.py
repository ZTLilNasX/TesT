"""HalalSpecBot Streamlit dashboard.

Run with:  streamlit run halalspecbot/app.py
"""

import os
import sys
import time
from datetime import datetime

# Make `halalspecbot` importable when run as `streamlit run halalspecbot/app.py`
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from halalspecbot import config, database, watchlist_manager
from halalspecbot.alerts import alert_classification_change, send_alert
from halalspecbot.models import AnalysisResult
from halalspecbot.pipeline import run_full_analysis
from halalspecbot.scanner import run_watchlist_scan
from halalspecbot.discovery import discover_candidates
from halalspecbot.utils import (
    classification_color,
    classification_emoji,
    format_large_number,
    format_percentage,
    format_price,
    parse_tickers,
)

st.set_page_config(page_title="HalalSpecBot", page_icon="🕌", layout="wide")

# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------

if "analysis_results" not in st.session_state:
    st.session_state["analysis_results"] = {}
if "alert_feed" not in st.session_state:
    st.session_state["alert_feed"] = []
if "last_scan" not in st.session_state:
    st.session_state["last_scan"] = None
if "scan_results" not in st.session_state:
    st.session_state["scan_results"] = []
if "discovery_hits" not in st.session_state:
    st.session_state["discovery_hits"] = []
if "discovery_results" not in st.session_state:
    st.session_state["discovery_results"] = []
if "last_discovery" not in st.session_state:
    st.session_state["last_discovery"] = None
if "discovery_seen_buys" not in st.session_state:
    st.session_state["discovery_seen_buys"] = set()

database.init_db()

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------

st.title("HalalSpecBot – Shariah-Compliant Stock Speculation Research Bot")
st.warning(f"⚠️ {config.APP_WARNING}")

# ---------------------------------------------------------------------------
# Sidebar — inputs and auto-scan controls
# ---------------------------------------------------------------------------

with st.sidebar:
    st.header("Analyze Stocks")
    tickers_input = st.text_area(
        "Tickers (comma or space separated)",
        placeholder="e.g. MSFT, NVDA, 2222.SR",
        height=90,
    )
    catalyst_notes = st.text_area(
        "Catalyst notes (optional)",
        placeholder="e.g. New AI product launch expected next quarter…",
        height=90,
    )
    run_clicked = st.button("▶ Run Analysis", type="primary", use_container_width=True)

    st.divider()
    st.header("Continuous Scanner")
    st.caption(
        "Keeps re-checking every tracked ticker for the next halal speculative setup."
    )
    auto_scan = st.selectbox(
        "Auto-scan interval",
        ["Manual only", "Every 15 min", "Every 30 min", "Every 60 min"],
    )
    scan_now = st.button("🔄 Scan Watchlist Now", use_container_width=True)

    if st.session_state["last_scan"]:
        st.caption(f"Last scan: {st.session_state['last_scan']}")

    st.divider()
    st.header("🚀 Market Discovery")
    st.caption(
        "Scans a broad universe for high-momentum halal candidates. "
        "Momentum is not a prediction — fast movers are high risk."
    )
    use_custom_universe = st.checkbox("Use my own ticker list", value=False)
    custom_universe = ""
    if use_custom_universe:
        custom_universe = st.text_area(
            "Universe tickers", placeholder="AAPL, NVDA, PLTR, …", height=80
        )
    top_n = st.slider("Deep-analyze top N movers", 5, 40,
                      config.DISCOVERY_DEFAULT_TOP_N, step=5)
    auto_discover = st.selectbox(
        "Auto-discovery interval",
        ["Manual only", "Every 15 min", "Every 30 min", "Every 60 min"],
        key="auto_discover_select",
    )
    discover_now = st.button("🔭 Scan the Market Now", use_container_width=True)
    if st.session_state["last_discovery"]:
        st.caption(f"Last discovery: {st.session_state['last_discovery']}")

    st.divider()
    if st.session_state["alert_feed"]:
        st.header("Alerts")
        for alert in st.session_state["alert_feed"][:10]:
            st.info(f"{alert['time']} — {alert['message']}")

# Auto-refresh timers for the scanner and the discovery scan
_INTERVALS = {"Every 15 min": 15 * 60, "Every 30 min": 30 * 60, "Every 60 min": 60 * 60}
_autorefresh = None
if auto_scan in _INTERVALS or auto_discover in _INTERVALS:
    try:
        from streamlit_autorefresh import st_autorefresh

        _autorefresh = st_autorefresh
    except ImportError:
        st.sidebar.caption(
            "Install `streamlit-autorefresh` for automatic scanning; "
            "use the manual buttons meanwhile."
        )

if _autorefresh and auto_scan in _INTERVALS:
    _autorefresh(interval=_INTERVALS[auto_scan] * 1000, key="auto_scan_timer")
    if time.time() - st.session_state.get("last_scan_epoch", 0) >= _INTERVALS[auto_scan] - 30:
        scan_now = True

if _autorefresh and auto_discover in _INTERVALS:
    _autorefresh(interval=_INTERVALS[auto_discover] * 1000, key="auto_discover_timer")
    if time.time() - st.session_state.get("last_discovery_epoch", 0) >= _INTERVALS[auto_discover] - 30:
        discover_now = True

# ---------------------------------------------------------------------------
# Run analysis on demand
# ---------------------------------------------------------------------------

if run_clicked:
    tickers = parse_tickers(tickers_input)
    if not tickers:
        st.error("Please enter at least one ticker.")
    for i, ticker in enumerate(tickers):
        if i > 0:
            time.sleep(1)  # gentle on the free data source
        with st.spinner(f"Analyzing {ticker}…"):
            result = run_full_analysis(ticker, catalyst_notes)
        st.session_state["analysis_results"][ticker] = result
        send_alert(
            f"{classification_emoji(result.final_classification)} {ticker}: "
            f"{result.final_classification}"
        )

# Run scanner on demand / timer
if scan_now:
    with st.spinner("Scanning watchlist for new setups…"):
        results, changes = run_watchlist_scan(catalyst_notes)
    st.session_state["scan_results"] = results
    st.session_state["last_scan"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    st.session_state["last_scan_epoch"] = time.time()
    for change in changes:
        alert_classification_change(change["ticker"], change["old"], change["new"])
    for r in results:
        st.session_state["analysis_results"][r.ticker] = r

# Run market discovery on demand / timer
if discover_now:
    universe = None
    if use_custom_universe:
        parsed = parse_tickers(custom_universe)
        universe = parsed or None
    progress = st.progress(0.0, text="Scanning the market…")

    def _cb(done, total, ticker):
        progress.progress(done / total, text=f"Analyzing {ticker} ({done}/{total})…")

    with st.spinner("Ranking momentum across the universe…"):
        hits, results = discover_candidates(
            universe=universe, top_n=top_n, catalyst_notes=catalyst_notes, progress_cb=_cb
        )
    progress.empty()
    st.session_state["discovery_hits"] = hits
    st.session_state["discovery_results"] = results
    st.session_state["last_discovery"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    st.session_state["last_discovery_epoch"] = time.time()
    for r in results:
        st.session_state["analysis_results"][r.ticker] = r
    # Alert only on newly-found halal speculative buys.
    seen = st.session_state["discovery_seen_buys"]
    for r in results:
        if r.final_classification == config.CLASS_HALAL_SPECULATIVE_BUY and r.ticker not in seen:
            seen.add(r.ticker)
            send_alert(f"🚀 Discovery found a HALAL SPECULATIVE BUY: {r.ticker} "
                       f"(score {r.final_score:.0f})")

# ---------------------------------------------------------------------------
# Rendering helpers
# ---------------------------------------------------------------------------


def gauge(title: str, value: float, invert: bool = False) -> go.Figure:
    """Small plotly gauge. invert=True colors high values red (risk)."""
    value = float(value or 0)
    good = value <= 50 if invert else value >= 50
    color = "#2e7d32" if good else "#c62828"
    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=round(value),
            title={"text": title, "font": {"size": 14}},
            gauge={
                "axis": {"range": [0, 100]},
                "bar": {"color": color},
            },
        )
    )
    fig.update_layout(height=160, margin=dict(l=20, r=20, t=40, b=10))
    return fig


def score_cards(result: AnalysisResult) -> None:
    color = classification_color(result.final_classification)
    emoji = classification_emoji(result.final_classification)
    st.markdown(
        f"<div style='padding:12px;border-radius:8px;background:{color};color:white;"
        f"font-size:1.2em;font-weight:bold;'>{emoji} Final Classification: "
        f"{result.final_classification}</div>",
        unsafe_allow_html=True,
    )
    st.write("")
    row1 = st.columns(4)
    row1[0].plotly_chart(
        gauge("Shariah Compliance", result.shariah.score if result.shariah else 0),
        use_container_width=True, key=f"g_sh_{result.ticker}",
    )
    row1[1].plotly_chart(
        gauge("Final Opportunity", result.final_score),
        use_container_width=True, key=f"g_fin_{result.ticker}",
    )
    row1[2].plotly_chart(
        gauge("Speculation Quality", result.speculation_score),
        use_container_width=True, key=f"g_spec_{result.ticker}",
    )
    row1[3].plotly_chart(
        gauge("Confidence", result.confidence_score),
        use_container_width=True, key=f"g_conf_{result.ticker}",
    )
    row2 = st.columns(5)
    row2[0].metric("Financial Strength", f"{result.financial_score:.0f}/100")
    row2[1].metric("Technical Setup", f"{result.technical_score:.0f}/100")
    row2[2].metric("Catalyst", f"{result.catalyst_score:.0f}/100")
    row2[3].metric("Risk (lower = safer)", f"{result.risk_score:.0f}/100")
    row2[4].metric("Ethical Impact", f"{result.ethical_score:.0f}/100")


def price_chart(result: AnalysisResult, period: str) -> None:
    ph = result.price_history
    if ph is None or not ph.has_data:
        st.info("No price history available.")
        return
    df = ph.df_6m if period == "6 Months" else ph.df_1y
    if df.empty:
        st.info("No price history available for this period.")
        return
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df.index, y=df["Close"], name="Price",
                             line=dict(color="#1976d2", width=2)))
    for col, color, dash in [("MA20", "orange", "dot"), ("MA50", "red", "dash"),
                             ("MA200", "purple", "longdash")]:
        if col in df and df[col].notna().any():
            fig.add_trace(go.Scatter(x=df.index, y=df[col], name=col,
                                     line=dict(color=color, dash=dash, width=1)))
    if result.invalidation_level:
        fig.add_hline(y=result.invalidation_level, line_dash="dashdot",
                      line_color="#c62828",
                      annotation_text="Invalidation (estimate)")
    fig.update_layout(
        title=f"{result.ticker} — {period} Price",
        xaxis_title="Date", yaxis_title="Price",
        height=420, legend=dict(orientation="h"),
    )
    st.plotly_chart(fig, use_container_width=True, key=f"chart_{result.ticker}_{period}")


def watchlist_table(items: list, key: str, deletable: bool = True) -> None:
    if not items:
        st.info("Nothing here yet.")
        return
    df = pd.DataFrame(items)
    cols = [c for c in ["ticker", "status", "final_score", "risk_score",
                        "confidence_score", "entry_zone", "invalidation_level",
                        "updated_at"] if c in df.columns]
    st.dataframe(df[cols], use_container_width=True, hide_index=True)
    if deletable:
        tickers = [i["ticker"] for i in items]
        col1, col2 = st.columns([3, 1])
        target = col1.selectbox("Remove ticker", tickers, key=f"del_sel_{key}")
        if col2.button("Delete", key=f"del_btn_{key}"):
            watchlist_manager.remove_ticker(target)
            st.success(f"{target} removed.")
            st.rerun()


def render_result(result: AnalysisResult) -> None:
    sd = result.stock_data
    sh = result.shariah

    score_cards(result)
    st.write("")

    tabs = st.tabs(
        ["Summary", "Shariah Review", "Financial Analysis", "Technical Analysis",
         "Risk Analysis", "Report"]
    )

    with tabs[0]:
        if result.error:
            st.error(result.error)
        if sd:
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Price", format_price(sd.price))
            c2.metric("Market Cap", format_large_number(sd.market_cap))
            c3.metric("52W High", format_price(sd.high_52w))
            c4.metric("52W Low", format_price(sd.low_52w))
            st.subheader(sd.name or result.ticker)
            st.caption(f"{sd.sector or 'Sector unknown'} · {sd.industry or 'Industry unknown'} · "
                       f"{sd.country or 'Country unknown'} · {sd.exchange or ''}")
            st.write(sd.business_summary or "_Business summary unavailable._")
        if result.entry_zone:
            st.info(f"**Entry zone (research estimate):** {result.entry_zone}")
        if result.data_quality_warnings:
            with st.expander(f"⚠️ {len(result.data_quality_warnings)} data quality warnings"):
                for w in result.data_quality_warnings:
                    st.write(f"- {w}")

    with tabs[1]:
        if sh:
            st.metric("Shariah Compliance Score", f"{sh.score}/100")
            st.write(f"**Status:** {sh.classification}")
            if sh.haram_detected:
                st.error(f"**Exclusion reason:** {sh.exclusion_reason}")
                st.write(f"**Category:** {sh.matched_category}")
                st.write(f"**Matched keywords:** {', '.join(sh.matched_keywords)}")
            ratio = f"{sh.debt_ratio:.0%}" if sh.debt_ratio is not None else "Unknown"
            st.write(f"**Debt ratio:** {ratio} — {sh.debt_risk} risk")
            st.write(f"**Interest income risk:** {sh.interest_income_risk}")
            if sh.uncertainty_notes:
                st.subheader("Uncertainty Notes")
                for note in sh.uncertainty_notes:
                    st.write(f"- {note}")
            st.subheader("Purification")
            st.write(sh.purification_notes or "No notes.")

    with tabs[2]:
        st.metric("Financial Strength Score", f"{result.financial_score:.0f}/100")
        if sd:
            fin_df = pd.DataFrame(
                {
                    "Metric": ["Revenue", "Net Income", "Free Cash Flow", "Operating CF",
                               "Total Debt", "Total Cash", "EBITDA", "Profit Margin",
                               "Revenue Growth", "Earnings Growth"],
                    "Value": [
                        format_large_number(sd.revenue),
                        format_large_number(sd.net_income),
                        format_large_number(sd.free_cashflow),
                        format_large_number(sd.operating_cashflow),
                        format_large_number(sd.total_debt),
                        format_large_number(sd.total_cash),
                        format_large_number(sd.ebitda),
                        format_percentage(sd.profit_margin),
                        format_percentage(sd.revenue_growth),
                        format_percentage(sd.earnings_growth),
                    ],
                }
            )
            st.dataframe(fin_df, use_container_width=True, hide_index=True)
        for note in result.financial_notes:
            st.write(f"- {note}")

    with tabs[3]:
        st.metric("Technical Setup Score", f"{result.technical_score:.0f}/100")
        period = st.radio("Chart period", ["6 Months", "1 Year"], horizontal=True,
                          key=f"period_{result.ticker}")
        price_chart(result, period)
        for note in result.technical_notes:
            st.write(f"- {note}")
        if result.invalidation_level:
            st.warning(
                f"Invalidation level (research estimate): "
                f"{format_price(result.invalidation_level)}"
            )

    with tabs[4]:
        st.metric("Risk Score (0 = low, 100 = high)", f"{result.risk_score:.0f}/100")
        for note in result.risk_notes:
            st.write(f"- {note}")
        if result.scenarios:
            st.subheader("Scenario Cases")
            scen_df = pd.DataFrame(
                [
                    {
                        "Scenario": s.label,
                        "Probability": s.probability,
                        "Target": format_price(s.price_target),
                        "Move": f"{s.move_pct:+.0%}" if s.move_pct is not None else "N/A",
                        "Horizon": s.time_horizon,
                        "Assumptions": s.assumptions,
                        "What could go wrong": s.what_could_go_wrong,
                    }
                    for s in result.scenarios
                ]
            )
            st.dataframe(scen_df, use_container_width=True, hide_index=True)

    with tabs[5]:
        st.download_button(
            "⬇ Download Markdown Report",
            result.report_markdown,
            file_name=f"{result.ticker}_halalspecbot_report.md",
            mime="text/markdown",
            key=f"dl_{result.ticker}",
        )
        st.markdown(result.report_markdown)


# ---------------------------------------------------------------------------
# Main layout
# ---------------------------------------------------------------------------

main_tabs = st.tabs(["📊 Analysis", "🚀 Discovery", "🔍 Scanner", "⭐ Watchlist",
                     "🚫 Excluded Stocks", "🟣 Requires Scholar Review"])

with main_tabs[0]:
    results = st.session_state["analysis_results"]
    if not results:
        st.info("Enter tickers in the sidebar and click **Run Analysis** to begin.")
    for ticker, result in results.items():
        with st.expander(
            f"{classification_emoji(result.final_classification)} {ticker} — "
            f"{result.final_classification} (score {result.final_score:.0f})",
            expanded=len(results) == 1,
        ):
            render_result(result)

with main_tabs[1]:
    st.subheader("🚀 Market Discovery — High-Momentum Halal Candidates")
    st.warning(f"⚠️ {config.DISCOVERY_DISCLAIMER}")
    st.caption(
        "Two stages: a fast momentum ranking across the whole universe, then a full "
        "Shariah + opportunity analysis on the top movers. Halal candidates are listed "
        "first; excluded names appear at the bottom so you can see the screen working."
    )

    hits = st.session_state["discovery_hits"]
    disc_results = st.session_state["discovery_results"]

    if not hits and not disc_results:
        st.info(
            "No discovery scan yet. Set options in the sidebar and click "
            "**🔭 Scan the Market Now** (or enable auto-discovery)."
        )
    else:
        if disc_results:
            st.markdown("#### Deep-Analyzed Candidates (ranked)")
            drows = []
            for i, r in enumerate(disc_results):
                hit = next((h for h in hits if h.ticker == r.ticker), None)
                drows.append(
                    {
                        "Rank": i + 1,
                        "Ticker": r.ticker,
                        "Classification": f"{classification_emoji(r.final_classification)} "
                                          f"{r.final_classification}",
                        "Final Score": round(r.final_score),
                        "1M Return": format_percentage(hit.ret_1m) if hit else "N/A",
                        "3M Return": format_percentage(hit.ret_3m) if hit else "N/A",
                        "Momentum": round(hit.momentum_score) if hit else "N/A",
                        "Risk": round(r.risk_score),
                        "Confidence": round(r.confidence_score),
                    }
                )
            st.dataframe(pd.DataFrame(drows), use_container_width=True, hide_index=True)

            buys = [r for r in disc_results
                    if r.final_classification == config.CLASS_HALAL_SPECULATIVE_BUY]
            if buys:
                names = ", ".join(f"{b.ticker} ({b.final_score:.0f})" for b in buys)
                st.success(f"🟢 Halal speculative buy candidates found: {names}. "
                           "Open the Analysis tab for full reports before acting.")
            else:
                st.info("No HALAL SPECULATIVE BUY candidates in this scan — "
                        "the strongest names may be on the watchlist or flagged too risky.")

        with st.expander(f"Full momentum ranking ({len(hits)} tickers scanned)"):
            mrows = [
                {
                    "Ticker": h.ticker,
                    "Momentum": round(h.momentum_score),
                    "Price": format_price(h.last_price),
                    "1M Return": format_percentage(h.ret_1m),
                    "3M Return": format_percentage(h.ret_3m),
                    "Volume Surge": f"{h.volume_surge:.2f}x" if h.volume_surge else "N/A",
                    "Near High": format_percentage(h.near_high) if h.near_high else "N/A",
                }
                for h in hits
            ]
            st.dataframe(pd.DataFrame(mrows), use_container_width=True, hide_index=True)

with main_tabs[2]:
    st.subheader("Continuous Scanner — Best Halal Setups Right Now")
    st.caption(
        "Re-runs the full analysis on every tracked ticker and ranks them by "
        "opportunity score. Enable auto-scan in the sidebar to keep it hunting."
    )
    scan_results = st.session_state["scan_results"]
    if not scan_results:
        st.info("No scan yet. Add tickers via Run Analysis, then click **Scan Watchlist Now**.")
    else:
        rows = [
            {
                "Rank": i + 1,
                "Ticker": r.ticker,
                "Classification": f"{classification_emoji(r.final_classification)} "
                                  f"{r.final_classification}",
                "Final Score": round(r.final_score),
                "Financial": round(r.financial_score),
                "Technical": round(r.technical_score),
                "Catalyst": round(r.catalyst_score),
                "Risk": round(r.risk_score),
                "Confidence": round(r.confidence_score),
                "Entry Zone": r.entry_zone,
            }
            for i, r in enumerate(scan_results)
        ]
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        top = scan_results[0]
        if top.final_classification == config.CLASS_HALAL_SPECULATIVE_BUY:
            st.success(
                f"🟢 Top setup right now: **{top.ticker}** "
                f"(score {top.final_score:.0f}). Review its full report before acting."
            )

with main_tabs[3]:
    st.subheader("Watchlist (Halal Tickers Being Tracked)")
    watchlist_table(watchlist_manager.get_active_watchlist(), key="active")

with main_tabs[4]:
    st.subheader("Excluded Stocks (Non-Compliant)")
    st.caption("These businesses failed the Shariah screen. Profit never overrides compliance.")
    watchlist_table(watchlist_manager.get_excluded(), key="excluded")

with main_tabs[5]:
    st.subheader("Requires Scholar Review")
    st.caption(
        "Business activity or financial data was unclear. Do not assume permissibility — "
        "consult a qualified scholar."
    )
    watchlist_table(watchlist_manager.get_scholar_review(), key="review")

st.divider()
st.caption(config.REPORT_DISCLAIMER)
