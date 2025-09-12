# backend/routers/requisitions.py
from fastapi import APIRouter, Depends, HTTPException
from google.cloud import bigquery
from auth import verify_api_key
import logging
from datetime import datetime

router = APIRouter()
client = bigquery.Client()
logger = logging.getLogger(__name__)

@router.get("/latest")
async def requisitions_latest(api_key: str = Depends(verify_api_key)):
    """Get the latest requisition metrics grouped by country."""
    try:
        query = """
            SELECT *
            FROM `outstaffer-app-prod.dashboard_metrics.requisition_snapshots`
            WHERE snapshot_date = (
                SELECT MAX(snapshot_date)
                FROM `outstaffer-app-prod.dashboard_metrics.requisition_snapshots`
            )
            ORDER BY id, metric_type
        """
        query_job = client.query(query)
        results = query_job.result()

        snapshot_date = None
        countries = {}
        totals = {
            "submitted_requisitions": 0,
            "created_requisitions": 0,
            "approved_requisitions": 0,
            "approved_positions": 0,
            "rejected_requisitions": 0,
            "open_positions": 0,
            "placement_fees_aud": 0.0,
            "avg_salary_aud": 0.0
        }

        # For calculating weighted average salary
        total_approved_reqs_for_avg = 0
        total_salary_sum = 0

        for row in results:
            if snapshot_date is None and row.snapshot_date:
                snapshot_date = row.snapshot_date.isoformat()

            country_id = row.id
            if country_id not in countries:
                countries[country_id] = {
                    "id": country_id,
                    "name": row.label,
                    "metrics": {}
                }

            metric_type = row.metric_type

            # Populate country-specific metrics
            countries[country_id]["metrics"][metric_type] = {
                "count": row.count,
                "value_aud": float(row.value_aud) if row.value_aud is not None else None
            }

            # Aggregate totals - using a safer if/elif structure
            if metric_type in totals:
                if row.count is not None:
                    totals[metric_type] += row.count
                elif row.value_aud is not None and 'avg' not in metric_type:
                    totals[metric_type] += float(row.value_aud)

            # For weighted average calculation
            if metric_type == 'avg_salary_aud' and row.value_aud is not None:
                approved_reqs_in_country = countries[country_id]["metrics"].get("approved_requisitions", {}).get("count", 0)
                if approved_reqs_in_country > 0:
                    total_salary_sum += float(row.value_aud) * approved_reqs_in_country
                    total_approved_reqs_for_avg += approved_reqs_in_country

        # Calculate the final weighted average for the total
        if total_approved_reqs_for_avg > 0:
            totals['avg_salary_aud'] = total_salary_sum / total_approved_reqs_for_avg
        else:
            # If no approved reqs, check if there's a non-zero sum from a single country case
            if totals['avg_salary_aud'] > 0 and total_approved_reqs_for_avg == 0:
                pass # Keep the single value
            else:
                totals['avg_salary_aud'] = 0


        # Convert countries dictionary to a list for the final response
        countries_list = list(countries.values())

        # Format the snapshot date for the 'snapshot_month' key
        snapshot_month_str = ""
        if snapshot_date:
            snapshot_month_str = datetime.fromisoformat(snapshot_date).strftime('%Y-%m')

        return {
            "snapshot_month": snapshot_month_str,
            "countries": countries_list,
            "totals": totals,
        }
    except Exception as e:
        logger.error(f"Error fetching requisition metrics: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.get("/trend")
async def requisition_trend(months: int = 6, api_key: str = Depends(verify_api_key)):
    """Get requisition trend data for the last X months."""
    try:
        query = """
            WITH monthly_data AS (
              SELECT
                DATE_TRUNC(snapshot_date, MONTH) as month_start,
                SUM(count) as total_positions
              FROM `outstaffer-app-prod.dashboard_metrics.requisition_snapshots`
              WHERE metric_type = 'approved_positions'
              GROUP BY month_start
            )
            SELECT
              FORMAT_DATE('%Y-%m', month_start) AS snapshot_month,
              total_positions
            FROM monthly_data
            WHERE month_start >= DATE_SUB(
              (SELECT MAX(snapshot_date) FROM `outstaffer-app-prod.dashboard_metrics.requisition_snapshots`),
              INTERVAL @months MONTH
            )
            ORDER BY snapshot_month
        """
        job_config = bigquery.QueryJobConfig(query_parameters=[
            bigquery.ScalarQueryParameter("months", "INT64", months)
        ])
        query_job = client.query(query, job_config=job_config)
        results = query_job.result()

        trend = [
            {
                "month": row.snapshot_month,
                "positions": int(row.total_positions or 0),
            }
            for row in results
        ]
        return trend
    except Exception as e:
        logger.error(f"Error fetching requisition trend: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")