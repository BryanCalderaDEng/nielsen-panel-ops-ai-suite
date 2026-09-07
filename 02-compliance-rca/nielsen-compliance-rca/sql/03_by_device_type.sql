-- 03_by_device_type.sql
-- Purpose: same recent-vs-baseline comparison as 02_by_market.sql, but
-- sliced by device_type instead. Run alongside 02 to see whether the
-- anomaly tracks a market, a device, or the intersection of both.

WITH windowed AS (
    SELECT
        device_type,
        compliance_flag,
        CASE
            WHEN date >= (SELECT date(MAX(date), '-6 days') FROM compliance_drop) THEN 'recent_7d'
            ELSE 'baseline_prior_14d'
        END AS period
    FROM compliance_drop
)
SELECT
    device_type,
    period,
    COUNT(*) AS total_logs,
    ROUND(1.0 * SUM(compliance_flag) / COUNT(*), 3) AS compliance_rate
FROM windowed
GROUP BY device_type, period
ORDER BY device_type, period;
