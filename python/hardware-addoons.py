import pandas as pd
from google.cloud import bigquery
import logging
import sys
import numpy as np

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger('hardware-addons-extractor')

# Initialize BigQuery client
client = bigquery.Client()

def main():
    logger.info("Starting hardware add-ons extraction...")

    # Use a query that directly UNNESTs the hardware add-ons
    # This is the key change - do the UNNEST in BigQuery, not in Python
    unnested_query = """
    WITH hardware_addons AS (
        SELECT
            ec.id as contract_id,
            ec.employmentLocation.country as country,
            addon.key as hardware_key,
            IFNULL(addon.quantity, 1) as quantity
        FROM `outstaffer-app-prod.firestore_exports.employee_contracts` ec,
            UNNEST(plan.hardwareAddons) as addon
        JOIN `outstaffer-app-prod.firestore_exports.companies` c
            ON ec.companyId = c.id
        JOIN `outstaffer-app-prod.lookup_tables.contract_status_mapping` cm
            ON ec.status = cm.contract_status
        WHERE (c.demoCompany IS NULL OR c.demoCompany = FALSE)
            AND (ec.__has_error__ IS NULL OR ec.__has_error__ = FALSE)
            AND cm.mapped_status = 'Active'
            AND plan.hardwareAddons IS NOT NULL
            AND ARRAY_LENGTH(plan.hardwareAddons) > 0
    )
    
    SELECT * FROM hardware_addons
    ORDER BY contract_id, hardware_key
    """

    logger.info("Executing query with UNNEST in BigQuery...")
    hardware_addons_df = client.query(unnested_query).to_dataframe()

    # Count results
    total_addons = hardware_addons_df['quantity'].sum()
    unique_addons = hardware_addons_df['hardware_key'].nunique()
    contracts_with_addons = hardware_addons_df['contract_id'].nunique()

    logger.info(f"Found {total_addons} total hardware add-ons across {unique_addons} unique types")
    logger.info(f"Number of contracts with hardware add-ons: {contracts_with_addons}")

    # Summarize by hardware key
    summary = hardware_addons_df.groupby('hardware_key').agg(
        num_contracts=('contract_id', 'nunique'),
        total_quantity=('quantity', 'sum')
    ).reset_index().sort_values('total_quantity', ascending=False)

    logger.info("\nHardware add-ons summary:")
    logger.info(summary)

    # Show distribution by country
    country_summary = hardware_addons_df.groupby(['country', 'hardware_key']).agg(
        num_contracts=('contract_id', 'nunique'),
        total_quantity=('quantity', 'sum')
    ).reset_index().sort_values(['country', 'total_quantity'], ascending=[True, False])

    logger.info("\nHardware add-ons by country:")
    logger.info(country_summary)

    return summary

if __name__ == "__main__":
    main()