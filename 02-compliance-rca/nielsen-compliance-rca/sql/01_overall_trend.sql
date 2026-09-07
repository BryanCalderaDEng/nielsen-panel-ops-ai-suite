-- 01_overall_trend.sql
-- Purpose: baseline check -- has overall panel compliance moved at all,
-- and on what date did it start moving? This is always the first query
-- to run before drilling into any dimension.

SELECT
    date,
    COUNT(*) AS total_logs,
    SUM(compliance_flag) AS compliant_logs,
    ROUND(1.0 * SUM(compliance_flag) / COUNT(*), 3) AS compliance_rate
FROM compliance_drop
GROUP BY date
ORDER BY date;
