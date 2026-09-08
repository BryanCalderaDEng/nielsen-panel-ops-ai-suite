# Interactive Panel Performance Scorecard

A Streamlit dashboard that turns the validated output of Project 1
(the Churn Early-Warning System) into an executive-facing tool: KPIs,
response-rate trends, tenure distribution, a churn-risk leaderboard,
and market-level anomaly flags — filterable by market.

> All data in this repo is synthetically generated (see Project 1).
> No real Nielsen panel data is used or represented anywhere in this
> dashboard.

## Why this project is different from Projects 1 and 2

Projects 1 and 2 are pipelines — their value is in the logic, and a
well-documented README is enough to demonstrate that. This project's
entire point is being a tool someone actually **uses**, not just reads
about. So unlike the other two, this one is meant to be **deployed
live**, not just reviewed as code.

## Run it locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

Opens at `http://localhost:8501`.

## Deploy made in streamlit.io

https://nielsen-panel-ops-ai-suite-egblysyb2hwcjxg9d3hgbo.streamlit.app/

## What's in the dashboard

| Section | What it shows | Source |
|---|---|---|
| KPI row | Panelists in view, high-risk count, avg. response rate, anomaly days flagged | Computed from `panelist_risk_scores.csv` and `response_rate_daily.csv` |
| Response rate trend | Daily response rate by market, line chart | `response_rate_daily.csv` |
| Tenure distribution | Histogram of panelist tenure in months | Derived from `panelist_demographics.csv` join dates |
| Churn risk leaderboard | Top 20 panelists by composite risk score | `panelist_risk_scores.csv` (Project 1 output) |
| Market anomaly table | Days a market's response rate broke its own 2-sigma band | `market_anomalies.csv` (Project 1 output) |

A sidebar filter lets you scope the whole dashboard to one or more
markets — every chart and table updates together.

## Design principle: visualize, don't recompute

Every number in this dashboard traces back to a deterministic
calculation that already happened in Project 1's `detect_churn_risk.py`.
This app does **not** re-derive risk scores or re-run anomaly detection
— it reads the validated CSV outputs and visualizes them. That
separation matters operationally: a dashboard that quietly recalculates
its own version of "risk" independently of the documented detection
pipeline is a data-integrity risk in a real ops environment, since two
different numbers for "risk score" could end up circulating.

## Repo structure

```
nielsen-panel-scorecard/
├── data/                # copied from Project 1's validated outputs
│   ├── panelist_risk_scores.csv
│   ├── market_anomalies.csv
│   ├── panelist_demographics.csv
│   └── response_rate_daily.csv
├── app.py
├── requirements.txt
└── README.md
```

## Portfolio status

This completes the 3-project suite:
1. **Churn Early-Warning System** — detection & validation (Python)
2. **Compliance RCA Workflow** — diagnosis & narration (SQL + Claude)
3. **Panel Performance Scorecard** — communication & interactivity (Streamlit) — **this project**
