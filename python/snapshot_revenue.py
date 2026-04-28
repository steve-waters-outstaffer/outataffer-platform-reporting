# =============================================================================
# snapshot_revenue.py
#
# Generates the monthly revenue snapshot by querying vw_revenue_snapshot
# (in dashboard_views) and writing the result to monthly_revenue_metrics.
#
# All heavy lifting -- nested field extraction, status mapping, FX conversion,
# demo / internal company filtering -- is done by the SQL views. This script
# is intentionally thin: query, add snapshot_date, write.
#
# Usage:
#   python snapshot_revenue.py [--dry-run]
# =============================================================================

import argparse
import logging
import sys
from datetime import datetime

import pandas as pd
from google.cloud import bigquery

from snapshot_utils import write_snapshot_to_bigquery

# -----------------------------------------------------------------------------
# Config
# -----------------------------------------------------------------------------

PROJECT_ID = "outstaffer-app-prod"
SOURCE_VIEW = f"{PROJECT_ID}.dashboard_views.vw_revenue_snapshot"
UNMAPPED_STATUSES_VIEW = f"{PROJECT_ID}.dashboard_views.vw_unmapped_contract_statuses"
TARGET_TABLE = f"{PROJECT_ID}.dashboard_metrics.monthly_revenue_metrics"

# -----------------------------------------------------------------------------
# Logging
# -----------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("revenue-snapshot")


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------

def warn_if_unmapped_statuses(client: bigquery.Client) -> None:
    """
    Check if any contract statuses exist in the source data without a mapping.
    Logs a warning if so (does not fail) -- this is data quality monitoring,
    not a hard stop. New statuses default to 'Unmapped' in the base view and
    get excluded from Active/Inactive aggregations downstream.
    """
    query = f"SELECT * FROM `{UNMAPPED_STATUSES_VIEW}`"
    try:
        rows = list(client.query(query).result())
        if rows:
            logger.warning(
                "Found %d unmapped contract status(es) in source data:", len(rows)
            )
            for row in rows:
                logger.warning(
                    "  - %s: %d contract(s), %d compan(ies), first_seen=%s",
                    row.unmapped_status,
                    row.contract_count,
                    row.company_count,
                    row.first_seen,
                )
            logger.warning(
                "Update dashboard_metrics.contract_status_mapping to capture these."
            )
        else:
            logger.info("No unmapped contract statuses. All good.")
    except Exception as e:
        # Don't fail the snapshot just because the monitoring view is unhappy
        logger.warning("Could not check unmapped statuses: %s", e)


def fetch_metrics(client: bigquery.Client) -> pd.DataFrame:
    """Query the revenue snapshot view and return a dataframe."""
    query = f"SELECT * FROM `{SOURCE_VIEW}`"
    logger.info("Querying %s", SOURCE_VIEW)
    df = client.query(query).result().to_dataframe()
    logger.info("Fetched %d metric rows", len(df))
    return df


def prepare_for_bigquery(df: pd.DataFrame, snapshot_date) -> pd.DataFrame:
    """
    Add snapshot_date and coerce columns to match the monthly_revenue_metrics
    schema. Output column order matches the BigQuery schema definition below.
    """
    df = df.copy()
    df["snapshot_date"] = snapshot_date

    expected_columns = [
        "snapshot_date",
        "metric_type",
        "id",
        "label",
        "count",
        "value_aud",
        "percentage",
    ]
    df = df[expected_columns]

    # Type coercion for BigQuery compatibility
    df["snapshot_date"] = pd.to_datetime(df["snapshot_date"]).dt.date
    df["metric_type"] = df["metric_type"].fillna("").astype(str)
    df["id"] = df["id"].fillna("").astype(str)
    df["label"] = df["label"].fillna("").astype(str)
    # count is INTEGER and nullable; preserve NULLs (don't fillna(0) -- that's misleading)
    df["count"] = pd.to_numeric(df["count"], errors="coerce").astype("Int64")
    df["value_aud"] = pd.to_numeric(df["value_aud"], errors="coerce")
    df["percentage"] = pd.to_numeric(df["percentage"], errors="coerce")

    return df


# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate monthly revenue snapshot from vw_revenue_snapshot view."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Validate and save CSV but don't write to BigQuery.",
    )
    args = parser.parse_args()

    snapshot_date = datetime.now().date()
    logger.info("Processing revenue snapshot for: %s", snapshot_date)

    client = bigquery.Client(project=PROJECT_ID)

    # 1. Surface any data quality issues before writing
    warn_if_unmapped_statuses(client)

    # 2. Fetch metrics from the view
    metrics_df = fetch_metrics(client)
    if metrics_df.empty:
        logger.error("No metrics returned from %s. Aborting.", SOURCE_VIEW)
        sys.exit(1)

    # 3. Prep dataframe for BigQuery write
    metrics_df = prepare_for_bigquery(metrics_df, snapshot_date)

    # 4. Log a summary so the operator can sanity-check at a glance
    summary = metrics_df.groupby("metric_type").size().reset_index(name="rows")
    logger.info("Metric breakdown:")
    for _, row in summary.iterrows():
        logger.info("  - %s: %d rows", row["metric_type"], row["rows"])

    # Headline numbers (helpful in logs)
    headlines = metrics_df[
        metrics_df["id"].isin(
            [
                "total_mrr",
                "total_mrr_external",
                "total_mrr_internal",
                "total_active",
                "total_active_external",
            ]
        )
    ]
    for _, row in headlines.iterrows():
        if pd.notna(row["value_aud"]):
            logger.info("  %s = AUD %.2f", row["id"], row["value_aud"])
        else:
            logger.info("  %s = %s", row["id"], row["count"])

    # 5. Schema for the target table
    schema = [
        bigquery.SchemaField("snapshot_date", "DATE"),
        bigquery.SchemaField("metric_type", "STRING"),
        bigquery.SchemaField("id", "STRING"),
        bigquery.SchemaField("label", "STRING"),
        bigquery.SchemaField("count", "INTEGER"),
        bigquery.SchemaField("value_aud", "FLOAT64"),
        bigquery.SchemaField("percentage", "FLOAT"),
    ]

    # 6. Write to BigQuery (handles dry-run, backup, and append automatically)
    success = write_snapshot_to_bigquery(
        metrics_df, TARGET_TABLE, schema, dry_run=args.dry_run
    )
    if not success:
        logger.error("Failed to write metrics to BigQuery")
        sys.exit(1)

    # 7. Save local CSV for traceability
    csv_path = f"revenue_snapshot_{snapshot_date}.csv"
    metrics_df.to_csv(csv_path, index=False)
    logger.info("Saved local copy to %s", csv_path)


if __name__ == "__main__":
    main()
