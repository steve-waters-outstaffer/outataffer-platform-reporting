from fastapi import APIRouter, Depends, HTTPException
from google.cloud import bigquery
from auth import verify_api_key
import logging

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
            WHERE snapshot_month = (
                SELECT MAX(snapshot_month)
                FROM `outstaffer-app-prod.dashboard_metrics.requisition_snapshots`
            )
            ORDER BY countryCode
        """
        query_job = client.query(query)
        results = query_job.result()

        snapshot_month = None
        countries = []
        totals = {
            "approved_requisitions": 0,
            "approved_positions": 0,
            "rejected_requisitions": 0,
            "open_positions": 0,
            "mrr": 0,
            "arr": 0,
            "placement_fees": 0,
        }

        for row in results:
            if snapshot_month is None:
                snapshot_month = row.snapshot_month

            country = {
                "id": row.countryCode,
                "name": row.country_name,
                "metrics": {
                    "approved_requisitions": {"count": row.approved_requisitions_count},
                    "approved_positions": {"count": row.approved_positions_count},
                    "rejected_requisitions": {"count": row.rejected_requisitions_count},
                    "open_positions": {"count": row.open_positions_count},
                    "mrr": {"value_aud": float(row.mrr_aud or 0)},
                    "arr": {"value_aud": float(row.arr_aud or 0)},
                    "placement_fees": {"value_aud": float(row.placement_fees_aud or 0)},
                }
            }
            countries.append(country)

            totals["approved_requisitions"] += row.approved_requisitions_count or 0
            totals["approved_positions"] += row.approved_positions_count or 0
            totals["rejected_requisitions"] += row.rejected_requisitions_count or 0
            totals["open_positions"] += row.open_positions_count or 0
            totals["mrr"] += float(row.mrr_aud or 0)
            totals["arr"] += float(row.arr_aud or 0)
            totals["placement_fees"] += float(row.placement_fees_aud or 0)

        return {
            "snapshot_month": snapshot_month,
            "countries": countries,
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
            WITH max_month AS (
                SELECT MAX(PARSE_DATE('%Y-%m', snapshot_month)) AS m
                FROM `outstaffer-app-prod.dashboard_metrics.requisition_snapshots`
            )
            SELECT snapshot_month,
                   SUM(approved_positions_count) AS positions
            FROM `outstaffer-app-prod.dashboard_metrics.requisition_snapshots`, max_month
            WHERE PARSE_DATE('%Y-%m', snapshot_month) >= DATE_SUB(m, INTERVAL @months MONTH)
            GROUP BY snapshot_month
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
                "positions": int(row.positions),
            }
            for row in results
        ]
        return trend
    except Exception as e:
        logger.error(f"Error fetching requisition trend: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
