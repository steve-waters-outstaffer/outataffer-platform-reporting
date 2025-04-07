# snapshot-health-insurance.py
import pandas as pd
from datetime import datetime
from google.cloud import bigquery
import logging
import sys
import argparse
from snapshot_utils import write_snapshot_to_bigquery
from metrics_utils import (
    get_active_contracts,
    get_health_insurance_plans_by_country,
    get_contracts_with_health_insurance_data
)

# Set up argument parser
parser = argparse.ArgumentParser(description='Generate health insurance metrics snapshot')
parser.add_argument('--dry-run', action='store_true', help='Validate without writing data')
args = parser.parse_args()

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s', handlers=[logging.StreamHandler(sys.stdout)])
logger = logging.getLogger('health-insurance-snapshot')

# Initialize BigQuery client
client = bigquery.Client()
table_id = 'outstaffer-app-prod.dashboard_metrics.health_insurance_metrics'
SNAPSHOT_DATE = datetime.now().date()
logger.info(f"Processing health insurance snapshot for: {SNAPSHOT_DATE}")

# Step 1: Get all available health insurance plans by country
available_plans = get_health_insurance_plans_by_country(client)
logger.info(f"Loaded {len(available_plans)} plan-country availability rows")

# Step 2: Get active contracts and enrich with health insurance data
active_contracts = get_active_contracts(SNAPSHOT_DATE)
logger.info(f"Loaded {len(active_contracts)} active contracts")

# Enrich contracts with health insurance data
contracts_with_health = get_contracts_with_health_insurance_data(active_contracts, available_plans, client)
logger.info(f"Enriched {len(contracts_with_health)} contracts with health insurance data")

# Step 3: Count the number of contracts per country to get eligible population
country_totals = contracts_with_health.groupby('country').size().reset_index(name='eligible_population')

# Step 4: Count health plan adoption by country
plan_adoption = contracts_with_health.groupby(
    ['country', 'insurance_plan_id', 'insurance_plan_label']
).size().reset_index(name='uptake_count')

# Merge in country totals to calculate percentages
plan_adoption = plan_adoption.merge(
    country_totals,
    on='country',
    how='left'
)

# Calculate adoption percentage
plan_adoption['uptake_percentage'] = (
        plan_adoption['uptake_count'] / plan_adoption['eligible_population'] * 100
).fillna(0)

# Step 5: Generate complete metrics with zero-uptake plans included
all_combinations = []
multi_country_plans = set(available_plans.groupby('plan_id').filter(lambda x: len(x['country'].unique()) > 1)['plan_id'])

for country in contracts_with_health['country'].unique():
    valid_plans = available_plans[available_plans['country'] == country]
    eligible_pop = country_totals[country_totals['country'] == country]['eligible_population'].iloc[0] if not country_totals[country_totals['country'] == country].empty else 0

    for _, plan in valid_plans.iterrows():
        adoption_data = plan_adoption[
            (plan_adoption['country'] == country) &
            (plan_adoption['insurance_plan_id'] == plan['plan_id'])
            ]
        uptake_count = adoption_data['uptake_count'].iloc[0] if not adoption_data.empty else 0
        uptake_percentage = adoption_data['uptake_percentage'].iloc[0] if not adoption_data.empty else 0

        all_combinations.append({
            'country': country,
            'insurance_plan_id': plan['plan_id'],
            'insurance_plan_key': plan['plan_key'],
            'insurance_plan_label': plan['plan_label'],
            'insurance_plan_description': plan['country_description'],
            'uptake_count': uptake_count,
            'eligible_population': eligible_pop,
            'uptake_percentage': uptake_percentage,
            'is_available': True,
            'is_multi_country': plan['plan_id'] in multi_country_plans  # New field
        })

complete_metrics = pd.DataFrame(all_combinations)

# Step 6: Create country-level summary metrics
country_metrics = contracts_with_health.groupby('country').agg(
    total_with_insurance=('insurance_plan_id', lambda x: x.notna().sum()),
    total_dependents=('dependent_count', lambda x: x[x > 0].sum())
).reset_index()

# Merge with country totals
country_metrics = country_metrics.merge(country_totals, on='country', how='left')

# Calculate coverage percentage
country_metrics['coverage_percentage'] = (
        country_metrics['total_with_insurance'] / country_metrics['eligible_population'] * 100
).fillna(0)

# Calculate dependent percentage
country_metrics['dependent_percentage'] = (
        country_metrics['total_dependents'] / country_metrics['eligible_population'] * 100
).fillna(0)

# Step 7: Begin metrics construction for BigQuery snapshot
metrics = []
for _, row in complete_metrics.iterrows():
    metrics.append({
        'snapshot_date': SNAPSHOT_DATE,
        'metric_type': 'health_insurance_plan_by_country',
        'id': row['insurance_plan_id'],
        'label': f"{row['insurance_plan_label']} ({row['country']})",
        'count': int(row['uptake_count']),
        'overall_percentage': float(row['uptake_percentage']),
        'category_percentage': 100.0,
        'contract_count': int(row['uptake_count']),
        'is_multi_country': row['is_multi_country']  # Add this to schema
    })

# Add country-level metrics
for _, row in country_metrics.iterrows():
    # Total with insurance metrics
    metrics.append({
        'snapshot_date': SNAPSHOT_DATE,
        'metric_type': 'health_insurance_total_by_country',
        'id': row['country'],
        'label': row['country'],
        'count': int(row['total_with_insurance']),
        'overall_percentage': float(row['coverage_percentage']),
        'category_percentage': 100.0,
        'contract_count': int(row['total_with_insurance'])
    })

    # Eligible population metrics
    metrics.append({
        'snapshot_date': SNAPSHOT_DATE,
        'metric_type': 'eligible_contracts_by_country',
        'id': row['country'],
        'label': row['country'],
        'count': int(row['eligible_population']),
        'overall_percentage': 0.0,
        'category_percentage': 0.0,
        'contract_count': int(row['eligible_population'])
    })

    # Dependent metrics - only add if country has dependents
    if row['total_dependents'] > 0:
        metrics.append({
            'snapshot_date': SNAPSHOT_DATE,
            'metric_type': 'health_insurance_dependents_by_country',
            'id': row['country'],
            'label': row['country'],
            'count': int(row['total_dependents']),
            'overall_percentage': float(row['dependent_percentage']),
            'category_percentage': 100.0,
            'contract_count': int(row['eligible_population'])
        })

# Step 8: Create metrics DataFrame
metrics_df = pd.DataFrame(metrics)
logger.info(f"Generated {len(metrics_df)} metrics rows")

# Update schema
schema = [
    bigquery.SchemaField("snapshot_date", "DATE"),
    bigquery.SchemaField("metric_type", "STRING"),
    bigquery.SchemaField("id", "STRING"),
    bigquery.SchemaField("label", "STRING"),
    bigquery.SchemaField("count", "INTEGER"),
    bigquery.SchemaField("overall_percentage", "FLOAT"),
    bigquery.SchemaField("category_percentage", "FLOAT"),
    bigquery.SchemaField("contract_count", "INTEGER"),
    bigquery.SchemaField("is_multi_country", "BOOLEAN")  # New field
]

# Write to BigQuery
success = write_snapshot_to_bigquery(
    metrics_df=metrics_df,
    table_id=table_id,
    schema=schema,
    dry_run=args.dry_run
)

if not success:
    logger.error("Failed to write health insurance metrics to BigQuery")
    sys.exit(1)

# Save to CSV
csv_filename = f"health_insurance_metrics_{SNAPSHOT_DATE}.csv"
metrics_df.to_csv(csv_filename, index=False)
logger.info(f"Saved metrics to {csv_filename}")

print("Health insurance metrics snapshot completed successfully")