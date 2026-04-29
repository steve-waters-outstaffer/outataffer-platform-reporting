# =============================================================================
# snapshot_geographic.py
#
# Generates the geographic snapshot by querying vw_geographic_snapshot
# (in dashboard_views) and writing the result to geographic_metrics.
#
# All heavy lifting -- lifecycle stage filtering, country name lookup,
# MRR/ARR aggregation, FX conversion, demo filtering -- is done by the
# SQL view. This script is intentionally thin: query, add snapshot_date, write.
#
# Usage:
#   python snapshot_geographic.py [--dry-run]
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

PROJECT_ID    = "outstaffer-app-prod"
SOURCE_VIEW   = f"{PROJECT_ID}.dashboard_views.vw_geographic_snapshot"
TARGET_TABLE  = f"{PROJECT_ID}.dashboard_metrics.geographic_metrics"
UNMAPPED_VIEW = f"{PROJECT_ID}.dashboard_views.vw_unmapped_contract_statuses"

# -----------------------------------------------------------------------------
# Logging
# -----------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("geographic-snapshot")


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------

def warn_if_unmapped_statuses(client: bigquery.Client) -> None:
    """Data quality check — log a warning if any contract statuses are unmapped."""
    query = f"SELECT * FROM `{UNMAPPED_VIEW}`"
    try:
        rows = list(client.query(query).result())
        if rows:
            logger.warning("Found %d unmapped contract status(es):", len(rows))
            for row in rows:
                logger.warning(
                    "  - %s: %d contract(s), first_seen=%s",
                    row.unmapped_status, row.contract_count, row.first_seen,
                )
            logger.warning(
                "Update dashboard_metrics.contract_status_mapping to capture these."
            )
        else:
            logger.info("No unmapped contract statuses. All good.")
    except Exception as e:
        logger.warning("Could not check unmapped statuses: %s", e)


def fetch_metrics(client: bigquery.Client) -> pd.DataFrame:
    """Query the geographic snapshot view and return a dataframe."""
    query = f"SELECT * FROM `{SOURCE_VIEW}`"
    logger.info("Querying %s", SOURCE_VIEW)
    df = client.query(query).result().to_dataframe()
    logger.info("Fetched %d metric rows", len(df))
    return df


def prepare_for_bigquery(df: pd.DataFrame, snapshot_date) -> pd.DataFrame:
    """
    Add snapshot_date and coerce columns to match the geographic_metrics schema.
    Schema matches revenue/customer: snapshot_date, metric_type, id, label,
    count, value_aud, percentage.
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

    # Float for integer-nullable columns (NaN → empty CSV field → NULL in BQ)
    df["snapshot_date"] = pd.to_datetime(df["snapshot_date"]).dt.date
    df["metric_type"]   = df["metric_type"].fillna("").astype(str)
    df["id"]            = df["id"].fillna("").astype(str)
    df["label"]         = df["label"].fillna("").astype(str)
    df["count"]         = pd.to_numeric(df["count"],      errors="coerce")
    df["value_aud"]     = pd.to_numeric(df["value_aud"],  errors="coerce")
    df["percentage"]    = pd.to_numeric(df["percentage"], errors="coerce")

    return df


# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate geographic snapshot from vw_geographic_snapshot view."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Validate and save CSV but don't write to BigQuery.",
    )
    args = parser.parse_args()

    snapshot_date = datetime.now().date()
    logger.info("Processing geographic snapshot for: %s", snapshot_date)

    client = bigquery.Client(project=PROJECT_ID)

    # 1. Data quality check
    warn_if_unmapped_statuses(client)

    # 2. Fetch from view
    metrics_df = fetch_metrics(client)
    if metrics_df.empty:
        logger.error("No metrics returned from %s. Aborting.", SOURCE_VIEW)
        sys.exit(1)

    # 3. Prep for BigQuery
    metrics_df = prepare_for_bigquery(metrics_df, snapshot_date)

    # 4. Log summary
    summary = metrics_df.groupby("metric_type").size().reset_index(name="rows")
    logger.info("Metric breakdown:")
    for _, row in summary.iterrows():
        logger.info("  - %s: %d rows", row["metric_type"], row["rows"])

    # Top 3 countries by active contracts
    top = (
        metrics_df[metrics_df["metric_type"] == "active_contracts_by_country"]
        .sort_values("count", ascending=False)
        .head(3)
    )
    logger.info("Top countries by active contracts:")
    for _, row in top.iterrows():
        logger.info("  %s (%s): %d contracts", row["label"], row["id"], row["count"])

    # Total MRR across all countries
    total_mrr = metrics_df[metrics_df["metric_type"] == "mrr_by_country"]["value_aud"].sum()
    logger.info("Total MRR (all countries): AUD %.2f", total_mrr)

    # 5. Schema — matches existing geographic_metrics table
    schema = [
        bigquery.SchemaField("snapshot_date", "DATE"),
        bigquery.SchemaField("metric_type",   "STRING"),
        bigquery.SchemaField("id",            "STRING"),
        bigquery.SchemaField("label",         "STRING"),
        bigquery.SchemaField("count",         "INTEGER"),
        bigquery.SchemaField("value_aud",     "FLOAT64"),
        bigquery.SchemaField("percentage",    "FLOAT"),
    ]

    # 6. Write to BigQuery
    success = write_snapshot_to_bigquery(
        metrics_df, TARGET_TABLE, schema, dry_run=args.dry_run
    )
    if not success:
        logger.error("Failed to write geographic metrics to BigQuery")
        sys.exit(1)

    # 7. Save local CSV for traceability
    csv_path = f"geographic_snapshot_{snapshot_date}.csv"
    metrics_df.to_csv(csv_path, index=False)
    logger.info("Saved local copy to %s", csv_path)


if __name__ == "__main__":
    main()
