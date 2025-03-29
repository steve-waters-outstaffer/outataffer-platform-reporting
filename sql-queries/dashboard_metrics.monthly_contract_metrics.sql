CREATE OR REPLACE TABLE `outstaffer-app-prod.dashboard_metrics.monthly_contract_metrics`
PARTITION BY DATE_TRUNC(month_date, MONTH)
AS
WITH monthly_data AS (
  SELECT
    DATE_TRUNC(DATE(contract_start_date), MONTH) AS month_date,
    country,
    COUNT(DISTINCT contract_id) AS new_contracts,
    COUNTIF(mapped_status = 'Active') AS active_contracts,
    COUNTIF(mapped_status = 'Inactive') AS inactive_contracts,
    COUNT(DISTINCT companyId) AS unique_companies,
    AVG(days_to_finalize) AS avg_days_to_finalize,
    COUNTIF(securityDepositStatus = 'PAID') AS security_deposits_paid
  FROM `outstaffer-app-prod.dashboard_metrics.base_contracts_view`
  WHERE contract_start_date IS NOT NULL
  GROUP BY month_date, country
)

SELECT
    md.*,
    SUM(md.new_contracts) OVER (
    PARTITION BY md.country
    ORDER BY md.month_date
    ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
  ) AS cumulative_contracts,

  -- Growth metrics
        LAG(md.new_contracts) OVER (
    PARTITION BY md.country
    ORDER BY md.month_date
  ) AS prev_month_new_contracts,

  -- Calculate month-over-month growth rate
        CASE
            WHEN LAG(md.new_contracts) OVER (PARTITION BY md.country ORDER BY md.month_date) > 0
    THEN (md.new_contracts - LAG(md.new_contracts) OVER (PARTITION BY md.country ORDER BY md.month_date))
                / LAG(md.new_contracts) OVER (PARTITION BY md.country ORDER BY md.month_date) * 100
            ELSE NULL
            END AS mom_growth_rate
FROM monthly_data md
ORDER BY md.month_date DESC, md.country