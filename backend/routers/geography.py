# backend/routers/geography.py
from fastapi import APIRouter, Depends, HTTPException
from google.cloud import bigquery
from auth import verify_api_key
from datetime import datetime
import logging

router = APIRouter()
client = bigquery.Client()
logger = logging.getLogger(__name__)

@router.get("/countries")
async def get_countries(api_key: str = Depends(verify_api_key)):
    """
    Get all geographic metrics by country from the latest snapshot.
    Returns a structured object with metrics organized by country.
    """
    try:
        query = """
            SELECT * 
            FROM `outstaffer-app-prod.dashboard_metrics.geographic_metrics`
            WHERE snapshot_date = (
                SELECT MAX(snapshot_date) 
                FROM `outstaffer-app-prod.dashboard_metrics.geographic_metrics`
            )
            ORDER BY id, metric_type
        """
        query_job = client.query(query)
        results = query_job.result()

        # Get the latest snapshot date
        snapshot_date = None

        # Organize data by country
        country_data = {}

        for row in results:
            # Set snapshot date from first row
            if snapshot_date is None:
                snapshot_date = row.snapshot_date.isoformat()

            country_id = row.id

            # Initialize country object if not already present
            if country_id not in country_data:
                country_data[country_id] = {
                    "id": country_id,
                    "name": row.label,
                    "metrics": {}
                }

            # Handle different metric types
            metric_type = row.metric_type
            base_type = metric_type.replace('_by_country', '')

            # Add metric to country object
            country_data[country_id]["metrics"][base_type] = {
                "count": row.count,
                "value_aud": row.value_aud,
                "percentage": row.percentage
            }

        # Convert to list and calculate totals
        countries_list = list(country_data.values())

        # Calculate global totals and percentages
        totals = {
            "active_contracts": 0,
            "offboarding_contracts": 0,
            "approved_not_started": 0,
            "mrr": 0,
            "arr": 0
        }

        for country in countries_list:
            metrics = country["metrics"]

            if "active_contracts" in metrics:
                totals["active_contracts"] += metrics["active_contracts"]["count"] or 0

            if "offboarding_contracts" in metrics:
                totals["offboarding_contracts"] += metrics["offboarding_contracts"]["count"] or 0

            if "approved_not_started" in metrics:
                totals["approved_not_started"] += metrics["approved_not_started"]["count"] or 0

            if "mrr" in metrics and metrics["mrr"]["value_aud"]:
                totals["mrr"] += metrics["mrr"]["value_aud"]

            if "arr" in metrics and metrics["arr"]["value_aud"]:
                totals["arr"] += metrics["arr"]["value_aud"]

        # Add percentage of total to each country
        for country in countries_list:
            metrics = country["metrics"]

            if "active_contracts" in metrics and totals["active_contracts"] > 0:
                metrics["active_contracts"]["percentage"] = (
                    metrics["active_contracts"]["count"] / totals["active_contracts"] * 100
                    if metrics["active_contracts"]["count"] else 0
                )

            if "mrr" in metrics and totals["mrr"] > 0:
                metrics["mrr"]["percentage"] = (
                    metrics["mrr"]["value_aud"] / totals["mrr"] * 100
                    if metrics["mrr"]["value_aud"] else 0
                )

            if "arr" in metrics and totals["arr"] > 0:
                metrics["arr"]["percentage"] = (
                    metrics["arr"]["value_aud"] / totals["arr"] * 100
                    if metrics["arr"]["value_aud"] else 0
                )

        # Sort by active contracts DESC
        countries_list.sort(key=lambda x: x["metrics"].get("active_contracts", {}).get("count", 0)
        if "active_contracts" in x["metrics"] else 0, reverse=True)

        return {
            "snapshot_date": snapshot_date,
            "countries": countries_list,
            "totals": totals
        }

    except Exception as e:
        logger.error(f"Error fetching geographic metrics: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.get("/trend")
async def get_geographic_trend(months: int = 6, api_key: str = Depends(verify_api_key)):
    """
    Get geographic metrics trend data for the last X months.
    Returns trend data for each country by month.
    """
    try:
        query = """
            WITH monthly_snapshots AS (
                SELECT DISTINCT snapshot_date
                FROM `outstaffer-app-prod.dashboard_metrics.geographic_metrics`
                WHERE snapshot_date >= DATE_SUB(
                    (SELECT MAX(snapshot_date) FROM `outstaffer-app-prod.dashboard_metrics.geographic_metrics`),
                    INTERVAL @months MONTH
                )
                ORDER BY snapshot_date DESC
            ),
            
            active_metrics AS (
                SELECT 
                    gm.snapshot_date,
                    gm.id AS country_code,
                    gm.label AS country_name,
                    CAST(gm.count AS INT64) AS active_count
                FROM `outstaffer-app-prod.dashboard_metrics.geographic_metrics` gm
                JOIN monthly_snapshots ms ON gm.snapshot_date = ms.snapshot_date
                WHERE gm.metric_type = 'active_contracts_by_country'
            ),
            
            mrr_metrics AS (
                SELECT 
                    gm.snapshot_date,
                    gm.id AS country_code,
                    CAST(gm.value_aud AS FLOAT64) AS mrr_value
                FROM `outstaffer-app-prod.dashboard_metrics.geographic_metrics` gm
                JOIN monthly_snapshots ms ON gm.snapshot_date = ms.snapshot_date
                WHERE gm.metric_type = 'mrr_by_country'
            )
            
            SELECT
                am.snapshot_date,
                am.country_code,
                am.country_name,
                am.active_count,
                mm.mrr_value
            FROM active_metrics am
            LEFT JOIN mrr_metrics mm
                ON am.snapshot_date = mm.snapshot_date
                AND am.country_code = mm.country_code
            ORDER BY am.snapshot_date DESC, am.active_count DESC
        """

        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("months", "INT64", months)
            ]
        )

        query_job = client.query(query, job_config=job_config)
        results = query_job.result()

        # Organize by country then by date
        trend_data = {}

        for row in results:
            country_code = row.country_code

            if country_code not in trend_data:
                trend_data[country_code] = {
                    "country_code": country_code,
                    "country_name": row.country_name,
                    "data": []
                }

            trend_data[country_code]["data"].append({
                "date": row.snapshot_date.isoformat(),
                "month": row.snapshot_date.strftime("%b %Y"),
                "active_count": row.active_count,
                "mrr_value": row.mrr_value or 0
            })

        # Convert to list and ensure data is sorted by date
        trend_list = list(trend_data.values())
        for country in trend_list:
            country["data"].sort(key=lambda x: x["date"])

        # Sort countries by latest active count
        trend_list.sort(
            key=lambda x: x["data"][-1]["active_count"] if x["data"] else 0,
            reverse=True
        )

        return trend_list

    except Exception as e:
        logger.error(f"Error fetching geographic trend data: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")