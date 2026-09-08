"""
generate_compliance_drop.py
---------------------------------
Generates a synthetic "daily compliance drop" feed -- the kind of file a
Panel Operations pipeline would receive each morning from the meter
vendor. Unlike Project 1 (which modeled churn over time), this dataset
is deliberately built around ONE specific root cause hidden in the data,
so the RCA pipeline has something concrete to find.

Hidden root cause (for validation -- don't peek until after running the
RCA pipeline): a firmware update pushed to 'Meter_v3' devices in the
'Monterrey' market caused a compliance drop starting 2026-08-25.
Every other market/device combination behaves normally.

Output: ../data/compliance_drop_2026-09-01.csv
Columns: panelist_id, date, market, device_type, tenure_months,
         compliance_flag, hours_logged
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import random

SEED = 7
random.seed(SEED)
np.random.seed(SEED)

MARKETS = ["Guadalajara", "Monterrey", "CDMX", "Puebla", "Tijuana"]
DEVICE_TYPES = ["Meter_v2", "Meter_v3", "Meter_Audio_v1"]
N_PANELISTS = 400
N_DAYS = 21  # 3-week window ending on the report date
REPORT_DATE = datetime(2026, 9, 1)
START_DATE = REPORT_DATE - timedelta(days=N_DAYS - 1)

INCIDENT_MARKET = "Monterrey"
INCIDENT_DEVICE = "Meter_v3"
INCIDENT_START = datetime(2026, 8, 25)

OUT_PATH = "../data/compliance_drop_2026-09-01.csv"


def assign_panelists():
    panelists = []
    for pid in range(1, N_PANELISTS + 1):
        market = random.choices(MARKETS, weights=[0.25, 0.20, 0.25, 0.15, 0.15])[0]
        device = random.choices(DEVICE_TYPES, weights=[0.45, 0.35, 0.20])[0]
        tenure = int(np.random.exponential(scale=18)) + 1  # months, skewed toward newer panelists
        panelists.append({"panelist_id": pid, "market": market,
                           "device_type": device, "tenure_months": tenure})
    return pd.DataFrame(panelists)


def generate_logs(panelists: pd.DataFrame) -> pd.DataFrame:
    rows = []
    dates = [START_DATE + timedelta(days=i) for i in range(N_DAYS)]

    for _, p in panelists.iterrows():
        base_p = np.random.uniform(0.90, 0.98)  # healthy compliance baseline
        is_incident_cohort = (p["market"] == INCIDENT_MARKET and p["device_type"] == INCIDENT_DEVICE)

        for date in dates:
            p_compliant = base_p
            if is_incident_cohort and date >= INCIDENT_START:
                # sharp, sustained drop -- looks like a firmware/config incident,
                # not a gradual churn trend
                p_compliant = base_p - 0.62

            # small amount of background noise everywhere (unrelated single-day misses)
            p_compliant -= np.random.uniform(0, 0.03)

            flag = 1 if np.random.random() < p_compliant else 0
            hours = round(np.random.uniform(6, 15), 1) if flag == 1 else round(np.random.uniform(0, 3), 1)

            rows.append({
                "panelist_id": p["panelist_id"],
                "date": date.date().isoformat(),
                "market": p["market"],
                "device_type": p["device_type"],
                "tenure_months": p["tenure_months"],
                "compliance_flag": flag,
                "hours_logged": hours,
            })

    return pd.DataFrame(rows)


def main():
    panelists = assign_panelists()
    logs = generate_logs(panelists)
    logs.to_csv(OUT_PATH, index=False)
    print(f"Wrote {len(logs)} rows to {OUT_PATH}")
    print(f"Panelists: {len(panelists)} | Date range: {START_DATE.date()} to {REPORT_DATE.date()}")
    print("(Hidden incident cohort exists in the data -- do not print here, "
          "that defeats the point of the RCA exercise.)")


if __name__ == "__main__":
    main()
