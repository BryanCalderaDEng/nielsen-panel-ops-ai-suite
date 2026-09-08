# Automated SQL + Claude Workflow for Compliance RCA

An end-to-end Root Cause Analysis pipeline: a synthetic daily compliance
feed is diagnosed with real SQL queries against a SQLite database, and
the findings are turned into a formal 5-Whys RCA report using the
Claude API.

> All data in this repo is synthetically generated
> (`src/generate_compliance_drop.py`). No real Nielsen panel data is
> used or referenced anywhere in this project.

## Why this project

Nielsen's Panel Operations role explicitly calls for "Data Pipelines
Validation & Logic Issue Troubleshooting" and "Root Cause Analysis
(Kaizen/Fishbone/5 Whys + SQL/Python)." This project simulates that
exact workflow on a synthetic incident: a firmware push to a specific
device type in a specific market causes a sharp compliance drop, and
the pipeline has to find it using nothing but the daily data feed —
the same way a real compliance-drop investigation starts.

## Pipeline

```
generate_compliance_drop.py  -->  data/compliance_drop_2026-09-01.csv
load_to_sqlite.py            -->  data/panel_ops.db
run_rca_queries.py           -->  outputs/rca_evidence.json
generate_rca_report.py       -->  outputs/rca_report.md
```

Run in order:
```bash
cd src
python generate_compliance_drop.py
python load_to_sqlite.py
python run_rca_queries.py
export ANTHROPIC_API_KEY=your_key_here   # optional — falls back to a placeholder without it
python generate_rca_report.py
```

## The SQL diagnostic sequence (`sql/`)

The queries are written and run in the order a human analyst would
actually investigate an incident, not just as a random collection of
aggregations:

| # | Query | Question it answers |
|---|---|---|
| 01 | `overall_trend.sql` | Did *anything* change, and when? |
| 02 | `by_market.sql` | Is the anomaly concentrated in one market? |
| 03 | `by_device_type.sql` | Is it concentrated in one device type? |
| 04 | `market_device_crosstab.sql` | Is it actually the **intersection** of a market and a device — the case both 02 and 03 alone would miss? |
| 05 | `incident_cohort_daily_trend.sql` | Once the worst cohort is identified, what exact date did it break? |

Query 04 is the important one methodologically: looking at market and
device type *separately* can each look only mildly off, while the true
signal is concentrated in one specific combination. A real RCA has to
check for that intersection explicitly instead of assuming the two
independent views tell the whole story.

`run_rca_queries.py` chains these automatically — it takes whatever
cohort query 04 flags as most severe and feeds it directly into query
05's parameterized `WHERE` clause, so the same script works for any
future incident, not just this one.

## Validation

The synthetic data generator hides one incident: a compliance drop in
**Monterrey / Meter_v3** starting **2026-08-25**, caused by a simulated
firmware push. This is not revealed to the SQL pipeline in advance.

Running `run_rca_queries.py` against the generated data correctly
identifies:
- **Flagged cohort:** Monterrey / Meter_v3 (rate change: -0.58)
- **Estimated incident start date:** 2026-08-25

This matches the hidden ground truth exactly, which is what makes this
a validated detection pipeline rather than a script that merely runs
without errors.

## AI-assisted layer

`generate_rca_report.py` calls the Claude API to convert the JSON
evidence bundle into a formatted 5-Whys report, structured as:
**Incident Summary → 5 Whys → Recommended Actions**. The prompt
explicitly instructs the model to cite only numbers present in the
evidence and to say so plainly when the data can't support a "why"
any further (e.g., *why* a firmware update caused this specific
failure is a vendor changelog question, not something the compliance
data itself can answer) — an LLM that overreaches past its evidence is
a bigger operational risk than one that admits a boundary.

## Repo structure

```
nielsen-compliance-rca/
├── data/                          # synthetic input + SQLite db (generated)
├── sql/                           # the 5 diagnostic queries, in run order
├── src/
│   ├── generate_compliance_drop.py
│   ├── load_to_sqlite.py
│   ├── run_rca_queries.py
│   └── generate_rca_report.py
├── outputs/                       # evidence bundle + RCA report (generated)
└── README.md
```

## Next steps for this portfolio

- Project 3: wrap the risk scores from Project 1 and the RCA evidence
  pattern from this project into an interactive Streamlit scorecard,
  deployed publicly via Streamlit Community Cloud.
