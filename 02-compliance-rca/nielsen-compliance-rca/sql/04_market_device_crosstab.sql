-- 04_market_device_crosstab.sql
-- Purpose: 02 and 03 tell you a market OR a device looks off, but not
-- whether it's really the INTERSECTION of the two that's the true root
-- cause (a classic RCA trap: two marginal views can each look "slightly
-- off" while masking one sharply-off combination). This query checks
-- every market x device_type pair directly.

WITH windowed AS (
    SELECT
        market,
        device_type,
        compliance_flag,
        CASE
            WHEN date >= (SELECT date(MAX(date), '-6 days') FROM compliance_drop) THEN 'recent_7d'
            ELSE 'baseline_prior_14d'
        END AS period
    FROM compliance_drop
),
agg AS (
    SELECT
        market,
        device_type,
        period,
        COUNT(*) AS total_logs,
        ROUND(1.0 * SUM(compliance_flag) / COUNT(*), 3) AS compliance_rate
    FROM windowed
    GROUP BY market, device_type, period
)
SELECT
    r.market,
    r.device_type,
    b.compliance_rate AS baseline_rate,
    r.compliance_rate AS recent_rate,
    ROUND(r.compliance_rate - b.compliance_rate, 3) AS rate_change
FROM agg r
JOIN agg b
    ON r.market = b.market
   AND r.device_type = b.device_type
   AND r.period = 'recent_7d'
   AND b.period = 'baseline_prior_14d'
ORDER BY rate_change ASC;
