-- 05_incident_cohort_daily_trend.sql
-- Purpose: once 04_market_device_crosstab.sql identifies the worst-hit
-- market/device pair, pull its full daily trend to find the EXACT date
-- the drop started -- that date is what you correlate against a
-- deployment log, firmware push, or field-ops change ticket.
--
-- NOTE: :market and :device are placeholders -- the Python runner
-- substitutes them with whatever 04_market_device_crosstab.sql flagged
-- as the worst rate_change, so this query is reusable for any future
-- incident, not hardcoded to this one.

SELECT
    date,
    COUNT(*) AS total_logs,
    SUM(compliance_flag) AS compliant_logs,
    ROUND(1.0 * SUM(compliance_flag) / COUNT(*), 3) AS compliance_rate
FROM compliance_drop
WHERE market = :market
  AND device_type = :device
GROUP BY date
ORDER BY date;
