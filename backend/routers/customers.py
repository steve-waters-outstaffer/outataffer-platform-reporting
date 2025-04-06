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
        query = """
            WITH RankedSnapshots AS (
                SELECT 
                    snapshot_date,
                    count as value,
                    ROW_NUMBER() OVER (
                        PARTITION BY EXTRACT(YEAR FROM snapshot_date), EXTRACT(MONTH FROM snapshot_date) 
                        ORDER BY snapshot_date DESC
                    ) as rn
                FROM `outstaffer-app-prod.dashboard_metrics.customer_snapshot`
                WHERE 
                    snapshot_date >= DATE_SUB(
                        (SELECT MAX(snapshot_date) FROM `outstaffer-app-prod.dashboard_metrics.customer_snapshot`),
                        INTERVAL @months MONTH
                    )
                    AND metric_type = 'active_customers'
            )
            
            SELECT 
                snapshot_date,
                value 
            FROM RankedSnapshots
            WHERE rn = 1
            ORDER BY snapshot_date
        """

        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("months", "INT64", months)
            ]
        )

        query_job = client.query(query, job_config=job_config)
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

# Add these new functions to your existing backend/routers/customers.py file

@router.get("/company-sizes")
async def company_sizes(api_key: str = Depends(verify_api_key)):
    """
    Get company size distribution metrics.
    Returns size distribution data from the most recent snapshot.
    """
    try:
        query = """
            SELECT * 
            FROM `outstaffer-app-prod.dashboard_metrics.customer_snapshot`
            WHERE 
                snapshot_date = (
                    SELECT MAX(snapshot_date) 
                    FROM `outstaffer-app-prod.dashboard_metrics.customer_snapshot`
                )
                AND metric_type IN (
                    'company_size_distribution', 
                    'company_size_arr', 
                    'company_size_avg_arr'
                )
            ORDER BY rank ASC
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
        logger.error(f"Error fetching company size metrics: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.get("/industries-by-count")
async def industries_by_count(limit: int = 10, api_key: str = Depends(verify_api_key)):
    """
    Get top industries by customer count.
    Returns industries ranked by number of customers from the most recent snapshot.
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
                AND metric_type = 'top_industry_by_count'
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
        logger.error(f"Error fetching industries by count: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.get("/industries-by-arr")
async def industries_by_arr(limit: int = 10, api_key: str = Depends(verify_api_key)):
    """
    Get top industries by ARR.
    Returns industries ranked by annual recurring revenue from the most recent snapshot.
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
                AND metric_type = 'top_industry_by_arr'
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
        logger.error(f"Error fetching industries by ARR: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")