from fastapi import APIRouter, Depends, HTTPException
from google.cloud import bigquery
from auth import verify_api_key
import datetime
import logging

router = APIRouter()
client = bigquery.Client()
logger = logging.getLogger(__name__)

@router.get("/latest")
async def revenue_latest(api_key: str = Depends(verify_api_key)):
    try:
        query = """
            SELECT snapshot_date, metric_type, id, label, count, value_aud, percentage
            FROM `outstaffer-app-prod.dashboard_metrics.monthly_revenue_metrics`
            WHERE snapshot_date = (
                SELECT MAX(snapshot_date)
                FROM `outstaffer-app-prod.dashboard_metrics.monthly_revenue_metrics`
            )
        """
        query_job = client.query(query)
        results = query_job.result()

        rows = list(results)
        if not rows:
            return {"error": "No data found"}

        # Transform rows into a single dict matching the old structure
        result_dict = {"snapshot_date": rows[0].snapshot_date.isoformat()}
        for row in rows:
            key_map = {
                "total_active": "total_active_subscriptions",
                "eor_fees": "eor_fees_mrr",
                "device_fees": "device_fees_mrr",
                "hardware_fees": "hardware_fees_mrr",
                "software_fees": "software_fees_mrr",
                "health_insurance": "health_insurance_mrr",
                "total_mrr": "total_mrr",
                "total_arr": "total_arr",
                "total_customers": "total_customers",
                "approved_not_started": "approved_not_started",
                "offboarding_contracts": "offboarding_contracts",
                "total_contracts": "total_contracts",
                "revenue_generating_contracts": "revenue_generating_contracts",
                "new_subscriptions": "new_subscriptions",
                "churned_subscriptions": "churned_subscriptions",
                "retention_rate": "retention_rate",
                "churn_rate": "churn_rate",
                "placement_fees": "placement_fees",
                "finalisation_fees": "finalisation_fees",
                "one_time_fees": "one_time_fees",
                "total_monthly_revenue": "total_monthly_revenue",
                "new_customers_this_month": "new_customers_this_month",
                "avg_subscription_value": "avg_subscription_value",
                "recurring_revenue_percentage": "recurring_revenue_percentage",
                "one_time_revenue_percentage": "one_time_revenue_percentage",
                "addon_revenue_percentage": "addon_revenue_percentage",
                "avg_days_until_start": "avg_days_until_start",
                "plan_change_rate": "plan_change_rate",
                "laptops_count": "laptops_count",
            }
            key = key_map.get(row.id, row.id)
            if row.count is not None:
                result_dict[key] = row.count
            elif row.value_aud is not None:
                result_dict[key] = row.value_aud
            elif row.percentage is not None:
                result_dict[key] = row.percentage

        return result_dict

    except Exception as e:
        logger.error(f"Error fetching latest revenue metrics: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.get("/trend")
async def revenue_trend(months: int = 6, api_key: str = Depends(verify_api_key)):
    try:
        query = """
            WITH RankedSnapshots AS (
                SELECT 
                    snapshot_date,
                    value_aud AS total_mrr,
                    ROW_NUMBER() OVER (
                        PARTITION BY EXTRACT(YEAR FROM snapshot_date), EXTRACT(MONTH FROM snapshot_date)
                        ORDER BY snapshot_date DESC
                    ) AS rn
                FROM `outstaffer-app-prod.dashboard_metrics.monthly_revenue_metrics`
                WHERE metric_type = 'total_summary' AND id = 'total_mrr'
                AND snapshot_date >= DATE_SUB(
                    (SELECT MAX(snapshot_date) FROM `outstaffer-app-prod.dashboard_metrics.monthly_revenue_metrics`),
                    INTERVAL @months MONTH
                )
            )
            SELECT snapshot_date, total_mrr
            FROM RankedSnapshots
            WHERE rn = 1
            ORDER BY snapshot_date
        """
        job_config = bigquery.QueryJobConfig(
            query_parameters=[bigquery.ScalarQueryParameter("months", "INT64", months)]
        )
        query_job = client.query(query, job_config=job_config)
        results = query_job.result()

        trend_data = [
            {
                "month": row.snapshot_date.strftime("%b %Y"),
                "value": float(row.total_mrr),
                "date": row.snapshot_date.isoformat()
            }
            for row in results
        ]
        return trend_data

    except Exception as e:
        logger.error(f"Error fetching revenue trend: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.get("/subscription-trend")
async def subscription_trend(months: int = 6, api_key: str = Depends(verify_api_key)):
    try:
        query = """
            WITH RankedSnapshots AS (
                SELECT 
                    snapshot_date,
                    count AS total_active_subscriptions,
                    ROW_NUMBER() OVER (
                        PARTITION BY EXTRACT(YEAR FROM snapshot_date), EXTRACT(MONTH FROM snapshot_date)
                        ORDER BY snapshot_date DESC
                    ) AS rn
                FROM `outstaffer-app-prod.dashboard_metrics.monthly_revenue_metrics`
                WHERE metric_type = 'total_active_subscriptions' AND id = 'total_active'
                AND snapshot_date >= DATE_SUB(
                    (SELECT MAX(snapshot_date) FROM `outstaffer-app-prod.dashboard_metrics.monthly_revenue_metrics`),
                    INTERVAL @months MONTH
                )
            )
            SELECT snapshot_date, total_active_subscriptions
            FROM RankedSnapshots
            WHERE rn = 1
            ORDER BY snapshot_date
        """
        job_config = bigquery.QueryJobConfig(
            query_parameters=[bigquery.ScalarQueryParameter("months", "INT64", months)]
        )
        query_job = client.query(query, job_config=job_config)
        results = query_job.result()

        trend_data = [
            {
                "month": row.snapshot_date.strftime("%b %Y"),
                "value": int(row.total_active_subscriptions),
                "date": row.snapshot_date.isoformat()
            }
            for row in results
        ]
        return trend_data

    except Exception as e:
        logger.error(f"Error fetching subscription trend: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.get("/countries")
async def revenue_by_country(months: int = 6, api_key: str = Depends(verify_api_key)):
    """
    Get revenue breakdown by country from the latest snapshot.
    Returns countries sorted by revenue.
    """
    try:
        query = """
            SELECT snapshot_date, id AS country, label AS country_name, count AS active_subscriptions, value_aud AS total_mrr
            FROM `outstaffer-app-prod.dashboard_metrics.monthly_revenue_metrics`
            WHERE metric_type = 'revenue_by_country'
            AND snapshot_date >= DATE_SUB(
                (SELECT MAX(snapshot_date) FROM `outstaffer-app-prod.dashboard_metrics.monthly_revenue_metrics`),
                INTERVAL @months MONTH
            )
            ORDER BY snapshot_date, country
        """
        job_config = bigquery.QueryJobConfig(query_parameters=[
            bigquery.ScalarQueryParameter("months", "INT64", months)
        ])
        query_job = client.query(query, job_config=job_config)
        results = query_job.result()

        country_data = {}
        for row in results:
            country = row.country
            if country not in country_data:
                country_data[country] = {'name': row.country_name, 'trend': []}
            country_data[country]['trend'].append({
                'month': row.snapshot_date.strftime("%b %Y"),
                'active_subscriptions': row.active_subscriptions,
                'total_mrr': float(row.total_mrr or 0),
                'date': row.snapshot_date.isoformat()
            })

        return list(country_data.values())
    except Exception as e:
        logger.error(f"Error fetching country metrics: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
