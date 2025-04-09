# snapshot-geographic-metrics.py
import pandas as pd
from datetime import datetime
from google.cloud import bigquery
import logging
import sys
import argparse
from snapshot_utils import write_snapshot_to_bigquery
from metrics_utils import (
    get_active_contracts,
    get_offboarding_contracts,
    get_approved_not_started_contracts,
    get_revenue_breakdown,
    get_all_countries
)

# Set up argument parser
parser = argparse.ArgumentParser(description='Generate geographic metrics snapshot')
parser.add_argument('--dry-run', action='store_true', help='Validate without writing data')
args = parser.parse_args()

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s', handlers=[logging.StreamHandler(sys.stdout)])
logger = logging.getLogger('geographic-snapshot')

# Initialize BigQuery client
client = bigquery.Client()
table_id = 'outstaffer-app-prod.dashboard_metrics.geographic_metrics'

# Define snapshot date as today
SNAPSHOT_DATE = datetime.now().date()
logger.info(f"Processing geographic snapshot for: {SNAPSHOT_DATE}")

# Get all countries
countries = get_all_countries()
countries_df = pd.DataFrame(countries)
logger.info(f"Loaded {len(countries_df)} countries")

# Get contract data
active_contracts = get_active_contracts(SNAPSHOT_DATE)
offboarding_contracts = get_offboarding_contracts(SNAPSHOT_DATE)
approved_not_started = get_approved_not_started_contracts(SNAPSHOT_DATE)

# Count by country
active_by_country = active_contracts.groupby('country').size().reset_index(name='count')
offboarding_by_country = offboarding_contracts.groupby('country').size().reset_index(name='count')
not_started_by_country = approved_not_started.groupby('country').size().reset_index(name='count')

# Calculate revenue by country
country_revenue = []
for country in countries_df['countryCode']:
    # Get contracts for this country
    country_active = active_contracts[active_contracts['country'] == country]
    country_offboarding = offboarding_contracts[offboarding_contracts['country'] == country]

    # Combine for revenue calculation (active + offboarding)
    revenue_contracts = pd.concat([country_active, country_offboarding]).drop_duplicates(subset='contract_id')

    # Calculate revenue (returns 0 for empty)
    revenue = get_revenue_breakdown(revenue_contracts, SNAPSHOT_DATE)

    country_revenue.append({
        'country': country,
        'mrr_aud': revenue['total_mrr'],
        'arr_aud': revenue['total_arr']
    })

# Convert to DataFrame
revenue_df = pd.DataFrame(country_revenue)

# Now build row-based metrics collection
metrics = []

# For each country
for _, country_row in countries_df.iterrows():
    country_code = country_row['countryCode']
    country_name = country_row['name']

    # Get active contract count
    active_count = active_by_country[active_by_country['country'] == country_code]['count'].values
    active_count = int(active_count[0]) if len(active_count) > 0 else 0

    # Get offboarding contract count
    offboarding_count = offboarding_by_country[offboarding_by_country['country'] == country_code]['count'].values
    offboarding_count = int(offboarding_count[0]) if len(offboarding_count) > 0 else 0

    # Get approved not started count
    not_started_count = not_started_by_country[not_started_by_country['country'] == country_code]['count'].values
    not_started_count = int(not_started_count[0]) if len(not_started_count) > 0 else 0

    # Get revenue
    country_mrr = revenue_df[revenue_df['country'] == country_code]['mrr_aud'].values
    country_arr = revenue_df[revenue_df['country'] == country_code]['arr_aud'].values
    mrr = float(country_mrr[0]) if len(country_mrr) > 0 else 0.0
    arr = float(country_arr[0]) if len(country_arr) > 0 else 0.0

    # Add active contracts metric
    metrics.append({
        'snapshot_date': SNAPSHOT_DATE,
        'metric_type': 'active_contracts_by_country',
        'id': country_code,
        'label': country_name,
        'count': active_count,
        'value_aud': None,
        'percentage': None
    })

    # Add offboarding contracts metric
    metrics.append({
        'snapshot_date': SNAPSHOT_DATE,
        'metric_type': 'offboarding_contracts_by_country',
        'id': country_code,
        'label': country_name,
        'count': offboarding_count,
        'value_aud': None,
        'percentage': None
    })

    # Add approved not started metric
    metrics.append({
        'snapshot_date': SNAPSHOT_DATE,
        'metric_type': 'approved_not_started_by_country',
        'id': country_code,
        'label': country_name,
        'count': not_started_count,
        'value_aud': None,
        'percentage': None
    })

    # Add MRR metric
    metrics.append({
        'snapshot_date': SNAPSHOT_DATE,
        'metric_type': 'mrr_by_country',
        'id': country_code,
        'label': country_name,
        'count': active_count + offboarding_count,  # Total revenue generating contracts
        'value_aud': mrr,
        'percentage': None
    })

    # Add ARR metric
    metrics.append({
        'snapshot_date': SNAPSHOT_DATE,
        'metric_type': 'arr_by_country',
        'id': country_code,
        'label': country_name,
        'count': active_count + offboarding_count,  # Total revenue generating contracts
        'value_aud': arr,
        'percentage': None
    })

# Convert to DataFrame
metrics_df = pd.DataFrame(metrics)

# Define schema for BigQuery
schema = [
    bigquery.SchemaField("snapshot_date", "DATE"),
    bigquery.SchemaField("metric_type", "STRING"),
    bigquery.SchemaField("id", "STRING"),
    bigquery.SchemaField("label", "STRING"),
    bigquery.SchemaField("count", "INTEGER"),
    bigquery.SchemaField("value_aud", "FLOAT"),
    bigquery.SchemaField("percentage", "FLOAT")
]

# Write to BigQuery
success = write_snapshot_to_bigquery(
    metrics_df=metrics_df,
    table_id=table_id,
    schema=schema,
    dry_run=args.dry_run
)

if not success:
    logger.error("Failed to write geographic metrics to BigQuery")
    sys.exit(1)

# Save locally for reference
metrics_df.to_csv(f"geographic_metrics_{SNAPSHOT_DATE}.csv", index=False)
logger.info(f"Saved metrics to geographic_metrics_{SNAPSHOT_DATE}.csv")
logger.info(f"Generated {len(metrics_df)} metric rows for {len(countries_df)} countries")