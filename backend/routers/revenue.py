from fastapi import APIRouter, Depends, HTTPException
from google.cloud import bigquery
from auth import verify_api_key
from datetime import datetime
import logging

router = APIRouter()
client = bigquery.Client()
logger = logging.getLogger(__name__)

@router.get("/latest")
async def revenue_latest(api_key: str = Depends(verify_api_key)):
    """
    Get the latest revenue metrics snapshot from BigQuery.
    Returns all fields from the most recent snapshot.
    """
    try:
        query = """
            SELECT * 
            FROM `outstaffer-app-prod.dashboard_metrics.monthly_subscription_snapshot`
            WHERE snapshot_date = (
                SELECT MAX(snapshot_date) 
                FROM `outstaffer-app-prod.dashboard_metrics.monthly_subscription_snapshot`
            )
        """
        query_job = client.query(query)
        results = query_job.result()

        # Convert to dict and handle the first row
        rows = list(results)
        if not rows:
            return {"error": "No data found"}

        # Convert the first row to a dict (there should only be one row for latest date)
        result_dict = dict(rows[0])

        # Convert date objects to ISO format strings for JSON serialization
        for key, value in result_dict.items():
            if isinstance(value, datetime):
                result_dict[key] = value.isoformat()

        return result_dict

    except Exception as e:
        logger.error(f"Error fetching latest revenue metrics: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@router.get("/trend")
async def revenue_trend(months: int = 6, api_key: str = Depends(verify_api_key)):
    """
    Get MRR trend data for the last X months (default 6).
    Returns month and total_mrr for charting.
    """
    try:
        query = f"""
            SELECT 
                snapshot_date,
                total_mrr
            FROM `outstaffer-app-prod.dashboard_metrics.monthly_subscription_snapshot`
            WHERE snapshot_date >= DATE_SUB(
                (SELECT MAX(snapshot_date) FROM `outstaffer-app-prod.dashboard_metrics.monthly_subscription_snapshot`),
                INTERVAL {months} MONTH
            )
            ORDER BY snapshot_date
        """
        query_job = client.query(query)
        results = query_job.result()

        trend_data = []
        for row in results:
            trend_data.append({
                "month": row.snapshot_date.strftime("%b %Y"),  # Format as "Jan 2025"
                "value": float(row.total_mrr),
                "date": row.snapshot_date.isoformat()
            })

        return trend_data

    except Exception as e:
        logger.error(f"Error fetching revenue trend: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@router.get("/subscription-trend")
async def subscription_trend(months: int = 6, api_key: str = Depends(verify_api_key)):
    """
    Get subscription count trend for the last X months (default 6).
    Returns month and total_active_subscriptions for charting.
    """
    try:
        query = f"""
            SELECT 
                snapshot_date,
                total_active_subscriptions
            FROM `outstaffer-app-prod.dashboard_metrics.monthly_subscription_snapshot`
            WHERE snapshot_date >= DATE_SUB(
                (SELECT MAX(snapshot_date) FROM `outstaffer-app-prod.dashboard_metrics.monthly_subscription_snapshot`),
                INTERVAL {months} MONTH
            )
            ORDER BY snapshot_date
        """
        query_job = client.query(query)
        results = query_job.result()

        trend_data = []
        for row in results:
            trend_data.append({
                "month": row.snapshot_date.strftime("%b %Y"),  # Format as "Jan 2025"
                "value": int(row.total_active_subscriptions),
                "date": row.snapshot_date.isoformat()
            })

        return trend_data

    except Exception as e:
        logger.error(f"Error fetching subscription trend: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")