"""
app.py
---------------------------------
Interactive Panel Performance Scorecard.

Reads the validated outputs from Project 1 (churn risk scores, market
anomalies) and the underlying panel demographics / response-rate data,
and presents them as an executive-facing Streamlit dashboard.

Run locally:
    streamlit run app.py

Deploy publicly (free): push this repo to GitHub, then connect it at
https://share.streamlit.io (Streamlit Community Cloud), pointing to
this file as the main app file.
"""

import pandas as pd
import numpy as np
import streamlit as st
import plotly.express as px
from datetime import datetime

st.set_page_config(
    page_title="Panel Performance Scorecard",
    page_icon="\U0001F4CA",
    layout="wide",
)

import os
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")


@st.cache_data
def load_data():
    risk = pd.read_csv(f"{DATA_DIR}/panelist_risk_scores.csv")
    demographics = pd.read_csv(f"{DATA_DIR}/panelist_demographics.csv", parse_dates=["join_date"])
    response = pd.read_csv(f"{DATA_DIR}/response_rate_daily.csv", parse_dates=["date"])
    anomalies = pd.read_csv(f"{DATA_DIR}/market_anomalies.csv")

    # tenure in months, computed from join_date relative to the most recent
    # response-rate date in the dataset (keeps the app self-consistent
    # regardless of when it's actually opened)
    as_of = response["date"].max()
    demographics["tenure_months"] = (
        (as_of - demographics["join_date"]).dt.days / 30.44
    ).round(1)

    merged = risk.merge(demographics[["panelist_id", "tenure_months", "income_bracket", "age_bracket"]],
                         on="panelist_id", how="left")
    return merged, demographics, response, anomalies, as_of


risk_df, demo_df, response_df, anomalies_df, as_of_date = load_data()

# ---------------------------------------------------------------------------
# Header + market filter
# ---------------------------------------------------------------------------
st.title("Panel Performance Scorecard")
st.caption(
    f"Synthetic panel data \u2014 as of {as_of_date.date()}. "
    "Built on validated output from the Churn Early-Warning System (Project 1)."
)

markets = sorted(demo_df["market"].unique())
selected_markets = st.sidebar.multiselect("Market", markets, default=markets)
st.sidebar.markdown("---")
st.sidebar.markdown(
    "**About this scorecard**\n\n"
    "All figures trace back to deterministic calculations in the "
    "Project 1 detection pipeline \u2014 this dashboard only visualizes "
    "them, it does not recompute risk scores independently."
)

risk_view = risk_df[risk_df["market"].isin(selected_markets)]
response_view = response_df[response_df["market"].isin(selected_markets)]
anomalies_view = anomalies_df[anomalies_df["market"].isin(selected_markets)]
demo_view = demo_df[demo_df["market"].isin(selected_markets)]

# ---------------------------------------------------------------------------
# KPI row
# ---------------------------------------------------------------------------
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Panelists in view", f"{len(risk_view):,}")

with col2:
    high_risk = (risk_view["composite_risk_score"] >= 30).sum()
    pct = 100 * high_risk / len(risk_view) if len(risk_view) else 0
    st.metric("High-risk panelists", f"{high_risk}", delta=f"{pct:.1f}% of panel", delta_color="inverse")

with col3:
    avg_response = response_view.assign(
        rate=lambda d: d["actual_responses"] / d["expected_responses"]
    )["rate"].mean()
    st.metric("Avg. response rate", f"{avg_response:.1%}" if not np.isnan(avg_response) else "n/a")

with col4:
    st.metric("Market anomaly days flagged", f"{len(anomalies_view)}")

st.markdown("---")

# ---------------------------------------------------------------------------
# Row: response rate trend + tenure distribution
# ---------------------------------------------------------------------------
left, right = st.columns([3, 2])

with left:
    st.subheader("Response rate trend by market")
    trend = response_view.copy()
    trend["response_rate"] = trend["actual_responses"] / trend["expected_responses"]
    fig = px.line(
        trend, x="date", y="response_rate", color="market",
        labels={"response_rate": "Response rate", "date": "Date"},
    )

    # Overlay the exact days flagged in the market-anomaly table as markers,
    # so the visual dip in the trend line and the anomaly table below are
    # visibly the same event, not two disconnected views of the data.
    if len(anomalies_view):
        anomaly_points = anomalies_view.copy()
        anomaly_points["date"] = pd.to_datetime(anomaly_points["date"])
        fig.add_scatter(
            x=anomaly_points["date"],
            y=anomaly_points["response_rate"],
            mode="markers",
            marker=dict(symbol="x", size=10, color="white",
                        line=dict(width=1, color="black")),
            name="Flagged anomaly day",
            hovertemplate="%{x|%b %d}<br>Response rate: %{y:.1%}<br>Flagged as anomaly<extra></extra>",
        )

    fig.update_layout(yaxis_tickformat=".0%", legend_title_text="Market", height=380)
    st.plotly_chart(fig, use_container_width=True)
    if len(anomalies_view):
        st.caption(
            "\u2716 markers show days flagged in the anomaly table below \u2014 "
            "the same event, shown two ways: visually here, and with the "
            "exact z-score in the table."
        )

with right:
    st.subheader("Panelist tenure distribution")
    fig2 = px.histogram(
        demo_view, x="tenure_months", nbins=30,
        labels={"tenure_months": "Tenure (months)"},
    )
    fig2.update_layout(height=380, yaxis_title="Panelists")
    st.plotly_chart(fig2, use_container_width=True)

st.markdown("---")

# ---------------------------------------------------------------------------
# Row: churn risk leaderboard + market anomaly table
# ---------------------------------------------------------------------------
left2, right2 = st.columns([3, 2])

with left2:
    st.subheader("Churn risk leaderboard")
    st.caption("Top at-risk panelists by composite score (from Project 1's detection pipeline).")
    top_risk = risk_view.sort_values("composite_risk_score", ascending=False).head(20)
    st.dataframe(
        top_risk[["panelist_id", "market", "panel_type", "composite_risk_score",
                   "recent_noncompliance_rate", "recent_missing_days", "tenure_months"]],
        use_container_width=True,
        hide_index=True,
    )

with right2:
    st.subheader("Market-level anomaly days")
    st.caption(
        "Days where a market's response rate broke a 2-sigma band vs. its own "
        "30-day trailing average \u2014 the same days marked with \u2716 in the trend chart above."
    )
    if len(anomalies_view):
        st.dataframe(
            anomalies_view.sort_values("date", ascending=False),
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("No anomaly days flagged for the selected market(s).")

st.markdown("---")
st.caption(
    "Data is fully synthetic, generated for portfolio demonstration purposes. "
    "No real Nielsen panel data is used or represented in this dashboard."
)
