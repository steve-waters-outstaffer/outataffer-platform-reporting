from fastapi import APIRouter, Depends, HTTPException
from google.cloud import bigquery
from auth import verify_api_key
from datetime import datetime
import logging

router = APIRouter()
client = bigquery.Client()
logger = logging.getLogger(__name__)

@router.get("/latest")
async def addons_latest(api_key: str = Depends(verify_api_key)):
    """
    Get the latest add-on metrics from BigQuery.
    """
    try:
        query = """
            SELECT * 
            FROM `outstaffer-app-prod.dashboard_metrics.plan_addon_adoption`
            WHERE snapshot_date = (
                SELECT MAX(snapshot_date) 
                FROM `outstaffer-app-prod.dashboard_metrics.plan_addon_adoption`
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
        logger.error(f"Error fetching latest add-on metrics: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")