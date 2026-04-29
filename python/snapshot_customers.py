# =============================================================================
# snapshot_customers.py
#
# Generates the customer snapshot by querying vw_customer_snapshot
# (in dashboard_views) and writing the result to customer_snapshot.
#
# All heavy lifting -- company joins, industry/size lookups, user counts,
# ARR aggregation, demo/internal filtering -- is done by the SQL view.
# This script is intentionally thin: query, add snapshot_date, write.
#
# Usage:
#   python snapshot_customers.py [--dry-run]
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
SOURCE_VIEW   = f"{PROJECT_ID}.dashboard_views.vw_customer_snapshot"
TARGET_TABLE  = f"{PROJECT_ID}.dashboard_metrics.customer_snapshot"
UNMAPPED_VIEW = f"{PROJECT_ID}.dashboard_views.vw_unmapped_contract_statuses"

# -----------------------------------------------------------------------------
# Logging
# -----------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("customer-snapshot")


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
    """Query the customer snapshot view and return a dataframe."""
    query = f"SELECT * FROM `{SOURCE_VIEW}`"
    logger.info("Querying %s", SOURCE_VIEW)
    df = client.query(query).result().to_dataframe()
    logger.info("Fetched %d metric rows", len(df))
    return df


def prepare_for_bigquery(df: pd.DataFrame, snapshot_date) -> pd.DataFrame:
    """
    Add snapshot_date and coerce columns to match the customer_snapshot schema.
    The schema includes a 'rank' INT64 NULLABLE column (not in revenue schema).
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
        "rank",
    ]
    df = df[expected_columns]

    # Type coercion
    df["snapshot_date"] = pd.to_datetime(df["snapshot_date"]).dt.date
    df["metric_type"]   = df["metric_type"].fillna("").astype(str)
    df["id"]            = df["id"].fillna("").astype(str)
    df["label"]         = df["label"].fillna("").astype(str)

    # Defensive: strip newlines/CRs from string columns. Firestore lookup
    # tables (e.g. company_sizes) sometimes contain trailing \n in label
    # values, which BigQuery's CSV loader treats as a row separator and
    # blows up the load with column-count mismatch. Views should also
    # sanitise at source -- see PATTERN.md "Label sanitisation".
    for col in ("metric_type", "id", "label"):
        df[col] = (
            df[col]
            .str.replace(r"[\r\n]+", " ", regex=True)
            .str.strip()
        )
    # count and rank are INTEGER NULLABLE in BigQuery. snapshot_utils writes via
    # CSV, so we use float here (NaN → empty string in CSV → NULL in BQ).
    # Using pandas nullable Int64 causes pd.NA to serialise as empty in CSV
    # which breaks BigQuery's column count check.
    df["count"]         = pd.to_numeric(df["count"],      errors="coerce")  # float, NaN for NULL
    df["value_aud"]     = pd.to_numeric(df["value_aud"],  errors="coerce")
    df["percentage"]    = pd.to_numeric(df["percentage"], errors="coerce")
    df["rank"]          = pd.to_numeric(df["rank"],       errors="coerce")  # float, NaN for NULL

    return df


# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate customer snapshot from vw_customer_snapshot view."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Validate and save CSV but don't write to BigQuery.",
    )
    args = parser.parse_args()

    snapshot_date = datetime.now().date()
    logger.info("Processing customer snapshot for: %s", snapshot_date)

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

    # Headline numbers
    headlines = metrics_df[
        metrics_df["id"].isin([
            "total_customers", "active_customers", "active_contracts",
            "avg_arr_per_customer", "TOP_10",
        ])
    ]
    for _, row in headlines.iterrows():
        if pd.notna(row["value_aud"]):
            logger.info("  %s = AUD %.2f", row["id"], row["value_aud"])
        elif pd.notna(row["count"]):
            logger.info("  %s = %s", row["id"], row["count"])
        elif pd.notna(row["percentage"]):
            logger.info("  %s = %.1f%%", row["id"], row["percentage"])

    # 5. Schema — matches existing customer_snapshot table
    schema = [
        bigquery.SchemaField("snapshot_date", "DATE"),
        bigquery.SchemaField("metric_type",   "STRING"),
        bigquery.SchemaField("id",            "STRING"),
        bigquery.SchemaField("label",         "STRING"),
        bigquery.SchemaField("count",         "INTEGER"),
        bigquery.SchemaField("value_aud",     "FLOAT64"),
        bigquery.SchemaField("percentage",    "FLOAT"),
        bigquery.SchemaField("rank",          "INTEGER"),
    ]

    # 6. Write to BigQuery
    success = write_snapshot_to_bigquery(
        metrics_df, TARGET_TABLE, schema, dry_run=args.dry_run
    )
    if not success:
        logger.error("Failed to write metrics to BigQuery")
        sys.exit(1)

    # 7. Save local CSV for traceability
    csv_path = f"customer_snapshot_{snapshot_date}.csv"
    metrics_df.to_csv(csv_path, index=False)
    logger.info("Saved local copy to %s", csv_path)


if __name__ == "__main__":
    main()
