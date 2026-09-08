# Panel Health & Churn Early-Warning System

A synthetic-data, end-to-end panel-operations pipeline built to demonstrate
the analytical workflow behind Nielsen's Panel Health Monitoring &
Predictive Risk responsibilities: **detect → validate → score → narrate**.

> All data in this repo is synthetically generated (`src/generate_synthetic_data.py`).
> No real Nielsen panel data is used or referenced anywhere in this project.

## Why this project

Panel operations teams need to catch churn signals *before* a panelist
goes dark, not after. This pipeline simulates that: it generates a panel
with a hidden cohort of "at-risk" panelists (compliance decaying over the
last 30 days), then measures whether a rules-based detection model can
actually find them — with the false-positive/false-negative trade-off made
explicit, not hand-waved.

## Pipeline

```
generate_synthetic_data.py   -->  data/*.csv
detect_churn_risk.py         -->  outputs/panelist_risk_scores.csv
                                   outputs/market_anomalies.csv
                                   outputs/detection_summary.json
generate_ai_summary.py       -->  outputs/daily_briefing.txt
```

Run in order:
```bash
cd src
python generate_synthetic_data.py
python detect_churn_risk.py
export ANTHROPIC_API_KEY=your_key_here   # optional — falls back to a placeholder without it
python generate_ai_summary.py
```

## Detection methodology

**Compliance risk** — each panelist's non-compliance rate in the trailing
14 days is compared against their own 60-day baseline. A z-score above a
1.5-std-dev noise floor counts as signal; below that, week-to-week
randomness in a 14-day sample produces too many false alarms to be
operationally useful.

**Missing-report handling** — a `NULL` compliance flag (meter never
reported) is tracked *separately* from a `0` (reported, non-compliant).
Collapsing the two is a real pipeline bug: a dark meter is often the
higher-risk case, and a naive `WHERE compliance_flag = 0` query silently
erases it. See the model validation below for why this split matters.

**Event risk** — operational events (`complaint`, `equipment_failure`,
`panel_fatigue_flag`, etc.) are summed per panelist as a qualitative
signal layered on top of the quantitative compliance trend.

**Composite score** — a weighted, capped 0–100 blend of the three signals
above. Weights and the noise floor were tuned against the seeded
ground-truth cohort (see below) rather than picked arbitrarily.

## Model validation (against synthetic ground truth)

Because the seed data marks which panelists were deliberately made
"at-risk," the detector's precision/recall can be measured directly —
something worth being able to speak to in an interview, since Nielsen's
JD explicitly calls out predictive risk work:

| Alert threshold | Panelists flagged | Precision | Recall |
|---|---|---|---|
| 10 | 128 | 0.45 | 0.97 |
| 20 | 111 | 0.52 | 0.97 |
| **30 (default)** | **75** | **0.77** | **0.97** |
| 35 | 68 | 0.84 | 0.95 |

**Threshold 30 is the operating point used by default** — it catches 97%
of real at-risk panelists while keeping the false-alarm rate low enough
that an ops team could actually act on the list. This is a deliberate
recall-favoring choice: in churn prevention, a missed at-risk panelist is
usually costlier than an unnecessary follow-up call.

## AI-assisted layer

`generate_ai_summary.py` calls the Claude API to turn the deterministic
JSON output into a short operational briefing a supervisor can read in
under a minute. The LLM is used strictly for **narration**, not
**arithmetic** — every number in the briefing traces back to a
deterministic calculation in `detect_churn_risk.py`. That separation
(compute with code, communicate with an LLM) is the automation pattern
this project is meant to showcase.

## Repo structure

```
nielsen-panel-churn/
├── data/                          # synthetic input tables (generated)
├── src/
│   ├── generate_synthetic_data.py
│   ├── detect_churn_risk.py
│   └── generate_ai_summary.py
├── outputs/                       # detection results + AI briefing (generated)
└── README.md
```

## Next steps for this portfolio

- Project 2: automate a daily compliance-drop RCA using SQL + the Claude API.
- Project 3: wrap `outputs/panelist_risk_scores.csv` and `market_anomalies.csv`
  in an interactive Streamlit scorecard for a non-technical stakeholder view.
