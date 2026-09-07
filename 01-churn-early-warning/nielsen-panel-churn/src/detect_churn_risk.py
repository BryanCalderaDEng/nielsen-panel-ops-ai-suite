"""
detect_churn_risk.py
---------------------------------
Panel Health & Churn Early-Warning System — Detection Layer.

Reads the synthetic panel tables and produces:
    outputs/panelist_risk_scores.csv   -> per-panelist composite risk score
    outputs/market_anomalies.csv       -> markets with statistically
                                           significant response-rate drops
    outputs/detection_summary.json     -> machine-readable summary consumed
                                           by generate_ai_summary.py

Method notes (what to say in an interview about this):
- Compliance risk: rolling 14-day non-compliance rate vs each panelist's
  own 60-day baseline, flagged when it deviates > 2 std devs (a simple,
  explainable anomaly-detection approach -- no black box).
- Missing-report handling: NULL compliance_flag days are tracked
  SEPARATELY from non-compliant days (per the Day-1 pipeline lesson) and
  folded into risk as "silent churn" signal.
- Event risk: churn_risk_events are weighted and summed per panelist.
- Market-level anomaly: z-score on daily response rate vs trailing
  30-day market mean/std, flags days beyond a 2-sigma band.
"""

import pandas as pd
import numpy as np
import json

DATA_DIR = "../data"
OUT_DIR = "../outputs"

ROLLING_WINDOW = 14
BASELINE_WINDOW = 60
Z_THRESHOLD = 2.0
# Validated against the synthetic ground-truth at-risk cohort:
# thresh=30 -> precision ~0.77, recall ~0.97 (see README for full sweep).
RISK_ALERT_THRESHOLD = 30


def load_data():
    compliance = pd.read_csv(f"{DATA_DIR}/meter_compliance_logs.csv", parse_dates=["date"])
    events = pd.read_csv(f"{DATA_DIR}/churn_risk_events.csv", parse_dates=["event_date"])
    response = pd.read_csv(f"{DATA_DIR}/response_rate_daily.csv", parse_dates=["date"])
    demographics = pd.read_csv(f"{DATA_DIR}/panelist_demographics.csv")
    return compliance, events, response, demographics


def compute_compliance_risk(compliance: pd.DataFrame) -> pd.DataFrame:
    max_date = compliance["date"].max()
    recent_cutoff = max_date - pd.Timedelta(days=ROLLING_WINDOW)
    baseline_cutoff = max_date - pd.Timedelta(days=BASELINE_WINDOW)

    def panelist_stats(g):
        recent = g[g["date"] >= recent_cutoff]
        baseline = g[(g["date"] >= baseline_cutoff) & (g["date"] < recent_cutoff)]

        recent_total = len(recent)
        recent_noncompliant = (recent["compliance_flag"] == 0).sum()
        recent_missing = recent["compliance_flag"].isna().sum()
        recent_rate = recent_noncompliant / recent_total if recent_total else 0

        baseline_total = len(baseline)
        baseline_noncompliant = (baseline["compliance_flag"] == 0).sum()
        baseline_rate = baseline_noncompliant / baseline_total if baseline_total else 0

        # simple deviation signal: how many "std-devs" worse than own baseline
        # (binomial std approximation, guarded against zero baseline)
        p = max(baseline_rate, 0.01)
        n = max(recent_total, 1)
        std = np.sqrt(p * (1 - p) / n)
        z = (recent_rate - baseline_rate) / std if std > 0 else 0

        return pd.Series({
            "recent_noncompliant_days": recent_noncompliant,
            "recent_missing_days": recent_missing,
            "recent_noncompliance_rate": round(recent_rate, 3),
            "baseline_noncompliance_rate": round(baseline_rate, 3),
            "compliance_z_score": round(z, 2),
        })

    stats = compliance.groupby("panelist_id").apply(panelist_stats).reset_index()
    return stats


def compute_event_risk(events: pd.DataFrame, all_panelist_ids) -> pd.DataFrame:
    event_risk = events.groupby("panelist_id")["risk_score"].sum().reset_index()
    event_risk = event_risk.rename(columns={"risk_score": "event_risk_sum"})
    full = pd.DataFrame({"panelist_id": all_panelist_ids}).merge(
        event_risk, on="panelist_id", how="left"
    )
    full["event_risk_sum"] = full["event_risk_sum"].fillna(0)
    return full


def compute_market_anomalies(response: pd.DataFrame) -> pd.DataFrame:
    response = response.sort_values(["market", "date"]).copy()
    response["response_rate"] = response["actual_responses"] / response["expected_responses"]

    anomalies = []
    for market, g in response.groupby("market"):
        g = g.reset_index(drop=True)
        g["rolling_mean"] = g["response_rate"].rolling(30, min_periods=10).mean()
        g["rolling_std"] = g["response_rate"].rolling(30, min_periods=10).std()
        g["z_score"] = (g["response_rate"] - g["rolling_mean"]) / g["rolling_std"]
        flagged = g[g["z_score"].abs() >= Z_THRESHOLD]
        for _, row in flagged.iterrows():
            anomalies.append({
                "market": market,
                "date": row["date"].date().isoformat(),
                "response_rate": round(row["response_rate"], 3),
                "rolling_mean": round(row["rolling_mean"], 3),
                "z_score": round(row["z_score"], 2),
            })
    return pd.DataFrame(anomalies)


def compute_composite_risk(compliance_stats, event_risk, demographics):
    merged = demographics.merge(compliance_stats, on="panelist_id", how="left")
    merged = merged.merge(event_risk, on="panelist_id", how="left")
    merged = merged.fillna(0)

    # Composite score: weighted blend, normalized 0-100.
    # Weighting rationale (explain in interview): compliance trend is the
    # leading indicator; missing-report days are a strong silent-churn
    # signal; event risk captures qualitative/operational red flags.
    # Only count a compliance z-score as signal once it clears a noise floor
    # (1.5 std devs) -- below that, week-to-week randomness in a 14-day
    # sample produces too many false positives to be operationally useful.
    signal_z = merged["compliance_z_score"].where(merged["compliance_z_score"] >= 1.5, 0)

    merged["composite_risk_score"] = (
        signal_z * 10
        + merged["recent_missing_days"] * 5
        + merged["event_risk_sum"] * 10
    ).clip(upper=100).round(1)

    merged = merged.sort_values("composite_risk_score", ascending=False)
    return merged[[
        "panelist_id", "market", "panel_type", "composite_risk_score",
        "recent_noncompliance_rate", "baseline_noncompliance_rate",
        "recent_missing_days", "compliance_z_score", "event_risk_sum",
    ]]


def main():
    compliance, events, response, demographics = load_data()

    compliance_stats = compute_compliance_risk(compliance)
    event_risk = compute_event_risk(events, demographics["panelist_id"].unique())
    market_anomalies = compute_market_anomalies(response)
    risk_table = compute_composite_risk(compliance_stats, event_risk, demographics)

    risk_table.to_csv(f"{OUT_DIR}/panelist_risk_scores.csv", index=False)
    market_anomalies.to_csv(f"{OUT_DIR}/market_anomalies.csv", index=False)

    top_risk = risk_table.head(15).to_dict(orient="records")
    summary = {
        "total_panelists": int(len(risk_table)),
        "alert_threshold": RISK_ALERT_THRESHOLD,
        "high_risk_count": int((risk_table["composite_risk_score"] >= RISK_ALERT_THRESHOLD).sum()),
        "top_15_at_risk": top_risk,
        "market_anomaly_count": int(len(market_anomalies)),
        "market_anomalies": market_anomalies.to_dict(orient="records"),
    }
    with open(f"{OUT_DIR}/detection_summary.json", "w") as f:
        json.dump(summary, f, indent=2)

    print(f"High-risk panelists flagged (score >= {RISK_ALERT_THRESHOLD}): {summary['high_risk_count']}")
    print(f"Market-level anomaly days flagged: {summary['market_anomaly_count']}")
    print("Wrote: panelist_risk_scores.csv, market_anomalies.csv, detection_summary.json")


if __name__ == "__main__":
    main()
