"""
generate_synthetic_data.py
---------------------------------
Generates a realistic (fully synthetic, no real Nielsen data) panel
operations dataset for the Panel Health & Churn Early-Warning System
portfolio project.

Tables produced (as CSVs in ../data/):
    panelist_demographics.csv
    meter_compliance_logs.csv
    churn_risk_events.csv
    response_rate_daily.csv

Run:
    python generate_synthetic_data.py
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import random

# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------
SEED = 42
random.seed(SEED)
np.random.seed(SEED)

N_PANELISTS = 500
MARKETS = ["Guadalajara", "Monterrey", "CDMX", "Puebla", "Tijuana"]
PANEL_TYPES = ["TAM", "Audio"]
INCOME_BRACKETS = ["A/B", "C+", "C", "C-", "D+"]
AGE_BRACKETS = ["18-24", "25-34", "35-44", "45-54", "55+"]

N_DAYS = 90  # ~3 months of daily logs
START_DATE = datetime(2026, 6, 1)
DATES = [START_DATE + timedelta(days=i) for i in range(N_DAYS)]

OUT_DIR = "../data"

# ---------------------------------------------------------------------------
# 1. panelist_demographics
# ---------------------------------------------------------------------------
def generate_demographics():
    rows = []
    for pid in range(1, N_PANELISTS + 1):
        join_date = START_DATE - timedelta(days=random.randint(30, 900))
        rows.append({
            "panelist_id": pid,
            "market": random.choices(MARKETS, weights=[0.30, 0.20, 0.25, 0.10, 0.15])[0],
            "household_size": np.random.randint(1, 6),
            "age_bracket": random.choice(AGE_BRACKETS),
            "income_bracket": random.choice(INCOME_BRACKETS),
            "join_date": join_date.date().isoformat(),
            "panel_type": random.choices(PANEL_TYPES, weights=[0.7, 0.3])[0],
        })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# 2. meter_compliance_logs
#    - Each panelist gets a baseline compliance probability.
#    - A subset of panelists are seeded as "at risk": their compliance
#      probability decays over the window to simulate a real churn signal.
#    - A small fraction of days are NULL (device offline / no report),
#      which is the pipeline-validation trap taught in Day 1.
# ---------------------------------------------------------------------------
def generate_compliance_logs(demographics):
    at_risk_ids = set(
        np.random.choice(demographics["panelist_id"], size=int(N_PANELISTS * 0.12), replace=False)
    )

    rows = []
    for _, panelist in demographics.iterrows():
        pid = panelist["panelist_id"]
        market = panelist["market"]
        base_p = np.random.uniform(0.85, 0.98)  # healthy baseline compliance

        for day_idx, date in enumerate(DATES):
            p = base_p
            if pid in at_risk_ids:
                # Linear decay over the last 30 days -> simulates a real
                # early-warning pattern an analyst should be able to catch.
                decay_start = N_DAYS - 30
                if day_idx >= decay_start:
                    progress = (day_idx - decay_start) / 30
                    p = base_p - progress * 0.55

            roll = np.random.random()
            if roll < 0.015:
                flag = np.nan  # meter never reported (missing, not non-compliant)
                hours = np.nan
            elif roll < 0.015 + (1 - p):
                flag = 0
                hours = round(np.random.uniform(0, 3), 1)
            else:
                flag = 1
                hours = round(np.random.uniform(6, 16), 1)

            rows.append({
                "panelist_id": pid,
                "date": date.date().isoformat(),
                "market": market,
                "compliance_flag": flag,
                "hours_logged": hours,
            })

    df = pd.DataFrame(rows)
    return df, at_risk_ids


# ---------------------------------------------------------------------------
# 3. churn_risk_events
#    Discrete operational events, weighted higher for at-risk panelists.
# ---------------------------------------------------------------------------
def generate_churn_events(demographics, at_risk_ids):
    event_types = ["complaint", "non_response", "equipment_failure", "panel_fatigue_flag"]
    rows = []
    event_id = 1
    for _, panelist in demographics.iterrows():
        pid = panelist["panelist_id"]
        n_events = np.random.poisson(2.5 if pid in at_risk_ids else 0.4)
        for _ in range(n_events):
            event_date = START_DATE + timedelta(days=random.randint(30, N_DAYS - 1))
            rows.append({
                "event_id": event_id,
                "panelist_id": pid,
                "event_date": event_date.date().isoformat(),
                "event_type": random.choice(event_types),
                "risk_score": round(np.random.uniform(0.5, 1.0) if pid in at_risk_ids
                                     else np.random.uniform(0.05, 0.4), 2),
            })
            event_id += 1
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# 4. response_rate_daily
#    Market-level rollup: expected vs actual responses per day.
# ---------------------------------------------------------------------------
def generate_response_rates(demographics):
    rows = []
    market_sizes = demographics["market"].value_counts().to_dict()
    for market, size in market_sizes.items():
        base_rate = np.random.uniform(0.88, 0.96)
        dip_start = N_DAYS - random.randint(10, 20)
        dip_market = random.random() < 0.4  # some markets get a visible dip
        for day_idx, date in enumerate(DATES):
            rate = base_rate
            if dip_market and day_idx >= dip_start:
                rate -= np.random.uniform(0.05, 0.18)
            expected = size
            actual = int(round(expected * max(rate, 0.4) * np.random.uniform(0.97, 1.02)))
            rows.append({
                "market": market,
                "date": date.date().isoformat(),
                "expected_responses": expected,
                "actual_responses": min(actual, expected),
            })
    return pd.DataFrame(rows)


def main():
    demographics = generate_demographics()
    compliance, at_risk_ids = generate_compliance_logs(demographics)
    churn_events = generate_churn_events(demographics, at_risk_ids)
    response_rates = generate_response_rates(demographics)

    demographics.to_csv(f"{OUT_DIR}/panelist_demographics.csv", index=False)
    compliance.to_csv(f"{OUT_DIR}/meter_compliance_logs.csv", index=False)
    churn_events.to_csv(f"{OUT_DIR}/churn_risk_events.csv", index=False)
    response_rates.to_csv(f"{OUT_DIR}/response_rate_daily.csv", index=False)

    # Save ground-truth at-risk list for validating the detection model later
    pd.DataFrame({"panelist_id": sorted(at_risk_ids)}).to_csv(
        f"{OUT_DIR}/_ground_truth_at_risk.csv", index=False
    )

    print(f"panelist_demographics: {len(demographics)} rows")
    print(f"meter_compliance_logs: {len(compliance)} rows")
    print(f"churn_risk_events:     {len(churn_events)} rows")
    print(f"response_rate_daily:   {len(response_rates)} rows")
    print(f"Seeded at-risk panelists: {len(at_risk_ids)}")


if __name__ == "__main__":
    main()
