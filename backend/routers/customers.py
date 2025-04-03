# backend/routers/customers.py
from fastapi import APIRouter, Depends, HTTPException
from google.cloud import bigquery
from auth import verify_api_key
from datetime import datetime
import logging

router = APIRouter()
client = bigquery.Client()
logger = logging.getLogger(__name__)

@router.get("/latest")
async def customers_latest(api_key: str = Depends(verify_api_key)):
    """
    Get the latest customer metrics from BigQuery.
    Returns all metrics from the most recent snapshot date.
    """
    try:
        query = """
            SELECT * 
            FROM `outstaffer-app-prod.dashboard_metrics.customer_snapshot`
            WHERE snapshot_date = (
                SELECT MAX(snapshot_date) 
                FROM `outstaffer-app-prod.dashboard_metrics.customer_snapshot`
            )
        """
        query_job = client.query(query)
        results = query_job.result()

        # Convert to list of dicts
        result_list = []
        for row in results:
            row_dict = dict(row)
            # Convert date objects to ISO format
            for key, value in row_dict.items():
                if isinstance(value, datetime):
                    row_dict[key] = value.isoformat()
            result_list.append(row_dict)

        return result_list

    except Exception as e:
        logger.error(f"Error fetching latest customer metrics: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.get("/top-customers")
async def top_customers(limit: int = 10, api_key: str = Depends(verify_api_key)):
    """
    Get the top customers by ARR.
    Returns top N customers ranked by ARR from the most recent snapshot.
    """
    try:
        query = f"""
            SELECT * 
            FROM `outstaffer-app-prod.dashboard_metrics.customer_snapshot`
            WHERE 
                snapshot_date = (
                    SELECT MAX(snapshot_date) 
                    FROM `outstaffer-app-prod.dashboard_metrics.customer_snapshot`
                )
                AND metric_type = 'top_customer_by_arr'
            ORDER BY rank ASC
            LIMIT {limit}
        """
        query_job = client.query(query)
        results = query_job.result()

        # Convert to list of dicts
        result_list = []
        for row in results:
            row_dict = dict(row)
            # Convert date objects to ISO format
            for key, value in row_dict.items():
                if isinstance(value, datetime):
                    row_dict[key] = value.isoformat()
            result_list.append(row_dict)

        return result_list

    except Exception as e:
        logger.error(f"Error fetching top customers: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.get("/trend")
async def customer_trend(months: int = 6, api_key: str = Depends(verify_api_key)):
    """
    Get customer count trend data for the last X months (default 6).
    Returns month and active_customers count for charting.
    """
    try:
        query = f"""
            SELECT 
                snapshot_date,
                count as value
            FROM `outstaffer-app-prod.dashboard_metrics.customer_snapshot`
            WHERE 
                snapshot_date >= DATE_SUB(
                    (SELECT MAX(snapshot_date) FROM `outstaffer-app-prod.dashboard_metrics.customer_snapshot`),
                    INTERVAL {months} MONTH
                )
                AND metric_type = 'active_customers'
            ORDER BY snapshot_date
        """
        query_job = client.query(query)
        results = query_job.result()

        trend_data = []
        for row in results:
            trend_data.append({
                "month": row.snapshot_date.strftime("%b %Y"),  # Format as "Jan 2025"
                "value": int(row.value),
                "date": row.snapshot_date.isoformat()
            })

        return trend_data

    except Exception as e:
        logger.error(f"Error fetching customer trend: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")