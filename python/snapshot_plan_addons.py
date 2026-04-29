# =============================================================================
# snapshot_plan_addons.py
#
# Generates the plan and add-on adoption snapshot by querying
# vw_plan_addon_snapshot (in dashboard_views) and writing the result to
# plan_addon_adoption.
#
# All heavy lifting -- plan type extraction, addon UNNEST, OS derivation,
# demo/status filtering, label joins -- is done by the SQL view.
# This script is intentionally thin: query, add snapshot_date, write.
#
# Usage:
#   python snapshot_plan_addons.py [--dry-run]
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

PROJECT_ID   = "outstaffer-app-prod"
SOURCE_VIEW  = f"{PROJECT_ID}.dashboard_views.vw_plan_addon_snapshot"
TARGET_TABLE = f"{PROJECT_ID}.dashboard_metrics.plan_addon_adoption"
UNMAPPED_VIEW = f"{PROJECT_ID}.dashboard_views.vw_unmapped_contract_statuses"

# -----------------------------------------------------------------------------
# Logging
# -----------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("plan-addon-snapshot")


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
    """Query the plan/addon snapshot view and return a dataframe."""
    query = f"SELECT * FROM `{SOURCE_VIEW}`"
    logger.info("Querying %s", SOURCE_VIEW)
    df = client.query(query).result().to_dataframe()
    logger.info("Fetched %d metric rows", len(df))
    return df


def prepare_for_bigquery(df: pd.DataFrame, snapshot_date) -> pd.DataFrame:
    """
    Add snapshot_date and coerce columns to match the plan_addon_adoption schema.
    This table has overall_percentage, category_percentage, and contract_count
    in addition to the standard columns.
    """
    df = df.copy()
    df["snapshot_date"] = snapshot_date

    expected_columns = [
        "snapshot_date",
        "metric_type",
        "id",
        "label",
        "count",
        "overall_percentage",
        "category_percentage",
        "contract_count",
    ]
    df = df[expected_columns]

    # Type coercion — use float for integer columns so NaN serialises cleanly
    # to empty string in CSV (snapshot_utils writes via CSV load job)
    df["snapshot_date"]        = pd.to_datetime(df["snapshot_date"]).dt.date
    df["metric_type"]          = df["metric_type"].fillna("").astype(str)
    df["id"]                   = df["id"].fillna("").astype(str)
    df["label"]                = df["label"].fillna("").astype(str)
    df["count"]                = pd.to_numeric(df["count"],                errors="coerce")
    df["overall_percentage"]   = pd.to_numeric(df["overall_percentage"],   errors="coerce")
    df["category_percentage"]  = pd.to_numeric(df["category_percentage"],  errors="coerce")
    df["contract_count"]       = pd.to_numeric(df["contract_count"],       errors="coerce")

    return df


# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate plan/addon snapshot from vw_plan_addon_snapshot view."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Validate and save CSV but don't write to BigQuery.",
    )
    args = parser.parse_args()

    snapshot_date = datetime.now().date()
    logger.info("Processing plan/addon snapshot for: %s", snapshot_date)

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

    # Headline numbers — top item per category
    for metric_type in ["plan", "device", "os_choice", "country"]:
        top = (
            metrics_df[metrics_df["metric_type"] == metric_type]
            .sort_values("contract_count", ascending=False)
            .head(1)
        )
        if not top.empty:
            r = top.iloc[0]
            logger.info(
                "  Top %s: %s (%d contracts, %.1f%% overall)",
                metric_type, r["label"], r["contract_count"], r["overall_percentage"],
            )

    # 5. Schema — matches existing plan_addon_adoption table
    schema = [
        bigquery.SchemaField("snapshot_date",       "DATE"),
        bigquery.SchemaField("metric_type",         "STRING"),
        bigquery.SchemaField("id",                  "STRING"),
        bigquery.SchemaField("label",               "STRING"),
        bigquery.SchemaField("count",               "INTEGER"),
        bigquery.SchemaField("overall_percentage",  "FLOAT"),
        bigquery.SchemaField("category_percentage", "FLOAT"),
        bigquery.SchemaField("contract_count",      "INTEGER"),
    ]

    # 6. Write to BigQuery
    success = write_snapshot_to_bigquery(
        metrics_df, TARGET_TABLE, schema, dry_run=args.dry_run
    )
    if not success:
        logger.error("Failed to write plan/addon metrics to BigQuery")
        sys.exit(1)

    # 7. Save local CSV for traceability
    csv_path = f"plan_addon_snapshot_{snapshot_date}.csv"
    metrics_df.to_csv(csv_path, index=False)
    logger.info("Saved local copy to %s", csv_path)


if __name__ == "__main__":
    main()
