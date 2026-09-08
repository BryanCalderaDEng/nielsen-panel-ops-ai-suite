-- 02_by_market.sql
-- Purpose: isolate WHICH market is driving the overall movement seen in
-- 01_overall_trend.sql, by comparing the most recent 7 days against the
-- prior 14-day baseline for each market.

WITH windowed AS (
    SELECT
        market,
        compliance_flag,
        CASE
            WHEN date >= (SELECT date(MAX(date), '-6 days') FROM compliance_drop) THEN 'recent_7d'
            ELSE 'baseline_prior_14d'
        END AS period
    FROM compliance_drop
)
SELECT
    market,
    period,
    COUNT(*) AS total_logs,
    ROUND(1.0 * SUM(compliance_flag) / COUNT(*), 3) AS compliance_rate
FROM windowed
GROUP BY market, period
ORDER BY market, period;
