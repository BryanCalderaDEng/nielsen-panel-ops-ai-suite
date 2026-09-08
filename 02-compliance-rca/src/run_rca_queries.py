"""
run_rca_queries.py
---------------------------------
Executes the diagnostic SQL queries in ../sql/ against panel_ops.db, in
the same order a human analyst would run them by hand:

    1. Is anything wrong at all? (overall trend)
    2. Is it a market? (by market)
    3. Is it a device? (by device type)
    4. Is it actually the INTERSECTION of a market and a device?
       (cross-tab -- this is where the real root cause usually hides)
    5. Drill into the worst-hit combination's daily trend to pinpoint
       the exact date the anomaly started.

Output: ../outputs/rca_evidence.json
    Consumed by generate_rca_report.py to draft the 5-Whys narrative.
"""

import sqlite3
import json

DB_PATH = "../data/panel_ops.db"
SQL_DIR = "../sql"
OUT_PATH = "../outputs/rca_evidence.json"


def run_query(conn, path, params=None):
    with open(path) as f:
        sql = f.read()
    cur = conn.execute(sql, params or {})
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]


def main():
    conn = sqlite3.connect(DB_PATH)

    overall_trend = run_query(conn, f"{SQL_DIR}/01_overall_trend.sql")
    by_market = run_query(conn, f"{SQL_DIR}/02_by_market.sql")
    by_device = run_query(conn, f"{SQL_DIR}/03_by_device_type.sql")
    crosstab = run_query(conn, f"{SQL_DIR}/04_market_device_crosstab.sql")

    # The cross-tab is already sorted by rate_change ascending (query 04),
    # so the first row is the most severe drop -- that's our RCA target.
    worst = crosstab[0]
    incident_trend = run_query(
        conn, f"{SQL_DIR}/05_incident_cohort_daily_trend.sql",
        params={"market": worst["market"], "device": worst["device_type"]},
    )

    # Find the first date in the incident trend where the rate visibly
    # breaks from its own earlier days (simple threshold, not a full
    # changepoint model -- sufficient for a daily ops RCA feed).
    incident_start_date = None
    for i, row in enumerate(incident_trend):
        if i >= 3 and row["compliance_rate"] < 0.75:
            prior_avg = sum(r["compliance_rate"] for r in incident_trend[:i]) / i
            if prior_avg - row["compliance_rate"] > 0.15:
                incident_start_date = row["date"]
                break

    evidence = {
        "overall_trend": overall_trend,
        "by_market": by_market,
        "by_device_type": by_device,
        "market_device_crosstab": crosstab,
        "flagged_cohort": {"market": worst["market"], "device_type": worst["device_type"],
                            "rate_change": worst["rate_change"]},
        "flagged_cohort_daily_trend": incident_trend,
        "estimated_incident_start_date": incident_start_date,
    }

    with open(OUT_PATH, "w") as f:
        json.dump(evidence, f, indent=2)

    print(f"Flagged cohort: {worst['market']} / {worst['device_type']} "
          f"(rate change: {worst['rate_change']})")
    print(f"Estimated incident start date: {incident_start_date}")
    print(f"Wrote evidence bundle to {OUT_PATH}")

    conn.close()


if __name__ == "__main__":
    main()
