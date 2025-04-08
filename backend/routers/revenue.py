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

        result_dict = {
            "snapshot_date": rows[0].snapshot_date.isoformat()
        }

        for row in rows:
            key = row.id
            if key not in result_dict:
                result_dict[key] = {}

            if row.count is not None:
                result_dict[key]["count"] = row.count
            if row.value_aud is not None:
                result_dict[key]["value_aud"] = float(row.value_aud)
            if row.percentage is not None:
                result_dict[key]["percentage"] = float(row.percentage)

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
