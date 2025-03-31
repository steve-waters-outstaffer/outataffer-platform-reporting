# snapshot_utils.py
import pandas as pd
from google.cloud import bigquery
import logging
import sys
from datetime import datetime
import os

# Update the write_snapshot_to_bigquery function in snapshot_utils.py
# Updated write_snapshot_to_bigquery function in snapshot_utils.py
def write_snapshot_to_bigquery(metrics_df, table_id, schema=None, dry_run=False):
    """
    Writes snapshot data to BigQuery with safety measures.

    Args:
        metrics_df: Pandas DataFrame with snapshot metrics
        table_id: Target BigQuery table (project.dataset.table format)
        schema: BigQuery table schema (optional, will be inferred if not provided)
        dry_run: If True, validates but doesn't write data

    Returns:
        True if successful, False otherwise
    """
    logger = logging.getLogger('snapshot-writer')

    try:
        # Check for empty dataframe
        if len(metrics_df) == 0:
            logger.warning(f"Empty DataFrame - no data to write")
            return False

        # Value range validation for numeric columns
        for col in metrics_df.select_dtypes(include=['number']).columns:
            max_val = metrics_df[col].max()
            if max_val > 1e9:  # Adjust threshold as needed
                logger.warning(f"Suspicious high value in {col}: {max_val}")

        # Extract snapshot date for same-day cleanup
        if 'snapshot_date' not in metrics_df.columns:
            logger.error("Missing snapshot_date column in metrics")
            return False

        snapshot_date = metrics_df['snapshot_date'].iloc[0]
        logger.info(f"Processing snapshot for date: {snapshot_date}")

        # Create BigQuery client
        client = bigquery.Client()

        # Check if table exists and create if needed
        try:
            client.get_table(table_id)
            table_exists = True
        except Exception:
            table_exists = False
            logger.info(f"Table {table_id} does not exist yet - will be created")

        if dry_run:
            logger.info(f"DRY RUN: Would have written {len(metrics_df)} records to {table_id}")

            # Save to CSV for inspection in dry run mode
            dry_run_file = f"dry_run_{table_id.split('.')[-1]}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            metrics_df.to_csv(dry_run_file, index=False)
            logger.info(f"Saved dry run data to {dry_run_file} for inspection")
            return True

        # Approach depends on whether the table exists
        if not table_exists:
            # For first run, write the table directly using a CREATE TABLE AS SELECT statement
            # This avoids the Arrow conversion issues
            logger.info("Creating new table from dataframe")

            # Save to temporary CSV
            temp_csv = f"temp_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            metrics_df.to_csv(temp_csv, index=False)

            try:
                # Upload CSV to a temporary table
                dataset_id = table_id.split('.')[1]
                project_id = table_id.split('.')[0]
                table_name = table_id.split('.')[2]
                temp_table_id = f"{project_id}.{dataset_id}.temp_{table_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

                # Define CSV loading job
                job_config = bigquery.LoadJobConfig(
                    schema=schema,
                    skip_leading_rows=1,  # Skip header row
                    source_format=bigquery.SourceFormat.CSV,
                )

                # Load CSV to temp table
                with open(temp_csv, "rb") as source_file:
                    job = client.load_table_from_file(
                        source_file, temp_table_id, job_config=job_config
                    )
                    job.result()  # Wait for the job to complete

                logger.info(f"Loaded CSV to temporary table {temp_table_id}")

                # Now create the target table from the temp table
                create_table_query = f"""
                CREATE OR REPLACE TABLE `{table_id}` AS
                SELECT * FROM `{temp_table_id}`
                """

                create_job = client.query(create_table_query)
                create_job.result()

                # Delete the temp table
                client.delete_table(temp_table_id)

                # Delete temp CSV
                if os.path.exists(temp_csv):
                    os.remove(temp_csv)

                logger.info(f"Successfully created table {table_id} with {len(metrics_df)} records")
                return True

            except Exception as e:
                logger.error(f"Error creating table: {str(e)}", exc_info=True)
                if os.path.exists(temp_csv):
                    os.remove(temp_csv)
                raise
        else:
            # Table exists, do backup and same-day cleanup
            # Backup query
            backup_table = f"{table_id}_backup_{snapshot_date.strftime('%Y%m%d')}"
            backup_query = f"""
            CREATE OR REPLACE TABLE `{backup_table}` AS
            SELECT * FROM `{table_id}` 
            WHERE snapshot_date = '{snapshot_date}'
            """

            # Execute backup
            try:
                backup_job = client.query(backup_query)
                backup_job.result()
                logger.info(f"Backed up existing data for {snapshot_date} to {backup_table}")
            except Exception as e:
                logger.warning(f"Backup failed, but continuing: {str(e)}")

            # Delete existing records for this date
            delete_query = f"""
            DELETE FROM `{table_id}` 
            WHERE snapshot_date = '{snapshot_date}'
            """

            try:
                delete_job = client.query(delete_query)
                delete_job.result()
                logger.info(f"Deleted existing data for {snapshot_date}")
            except Exception as e:
                logger.warning(f"Delete operation failed: {str(e)}")

            # Save to temporary CSV and load via BQ SQL
            temp_csv = f"temp_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            metrics_df.to_csv(temp_csv, index=False)

            try:
                # Define CSV loading job
                job_config = bigquery.LoadJobConfig(
                    schema=schema,
                    skip_leading_rows=1,  # Skip header row
                    source_format=bigquery.SourceFormat.CSV,
                    write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
                )

                # Load CSV to existing table
                with open(temp_csv, "rb") as source_file:
                    job = client.load_table_from_file(
                        source_file, table_id, job_config=job_config
                    )
                    job.result()  # Wait for the job to complete

                # Delete temp CSV
                if os.path.exists(temp_csv):
                    os.remove(temp_csv)

                logger.info(f"Successfully wrote {len(metrics_df)} records to {table_id}")
                return True

            except Exception as e:
                logger.error(f"Error appending to table: {str(e)}", exc_info=True)
                if os.path.exists(temp_csv):
                    os.remove(temp_csv)
                raise

    except Exception as e:
        logger.error(f"Error writing snapshot to BigQuery: {str(e)}", exc_info=True)
        # Save to local file as backup in case of failure
        local_backup = f"failed_snapshot_{table_id.split('.')[-1]}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        metrics_df.to_csv(local_backup, index=False)
        logger.info(f"Saved failed snapshot to {local_backup}")
        return False