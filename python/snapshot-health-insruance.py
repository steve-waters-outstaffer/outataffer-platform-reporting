# snapshot-health-insurance.py
import pandas as pd
from datetime import datetime
from google.cloud import bigquery
import logging
import sys
import argparse
from snapshot_utils import write_snapshot_to_bigquery

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

# Load plan availability view (flattened)
logger.info("Loading health insurance plan availability by country...")
availability_df = client.query("""
    SELECT plan_id, plan_key, plan_label, country, is_enabled
    FROM `outstaffer-app-prod.dashboard_metrics.health_insurnace_country_availability`
    WHERE is_enabled = TRUE
""").to_dataframe()
logger.info(f"Loaded {len(availability_df)} plan-country availability rows")

# Load active contracts
logger.info("Loading active contracts with country and insurance plan...")
contracts_df = client.query("""
    SELECT
        ec.id AS contract_id,
        ec.companyId,
        ec.employmentLocation.country AS country,
        ec.role.preferredStartDate AS start_date,
        ec.status,
        sm.mapped_status,
        ec.benefits.healthInsurance AS insurance_plan,
        ec.benefits.addOns.DEPENDENT AS dependent_count
    FROM `outstaffer-app-prod.firestore_exports.employee_contracts` ec
    JOIN `outstaffer-app-prod.firestore_exports.companies` c ON ec.companyId = c.id
    JOIN `outstaffer-app-prod.lookup_tables.contract_status_mapping` sm ON ec.status = sm.contract_status
    WHERE (c.demoCompany IS NULL OR c.demoCompany = FALSE)
      AND (ec.__has_error__ IS NULL OR ec.__has_error__ = FALSE)
      AND sm.mapped_status = 'Active'
""").to_dataframe()
logger.info(f"Loaded {len(contracts_df)} active contracts")

# Step 2: Convert dates
contracts_df['start_date'] = pd.to_datetime(contracts_df['start_date']).dt.date
snapshot_date = datetime.now().date()

# Step 3: Categorise contracts
contracts_df['contract_category'] = 'active'
contracts_df.loc[contracts_df['status'] == 'OFFBOARDING', 'contract_category'] = 'offboarding'
contracts_df.loc[contracts_df['start_date'] > snapshot_date, 'contract_category'] = 'approved_not_started'

# Filter to include only active and offboarding
contracts_df = contracts_df[contracts_df['contract_category'].isin(['active', 'offboarding'])]

# Step 4: Subsets (if needed downstream)
active_contracts = contracts_df[contracts_df['contract_category'] == 'active']
offboarding_contracts = contracts_df[contracts_df['contract_category'] == 'offboarding']
approved_not_started_contracts = contracts_df[contracts_df['contract_category'] == 'approved_not_started']

# Optional: if you only want to calculate metrics using 'active' + 'offboarding':
revenue_contracts = contracts_df[contracts_df['contract_category'].isin(['active', 'offboarding'])]


# Join contracts to availability to get valid matches
logger.info("Joining contracts to plan availability...")
contracts_df['country'] = contracts_df['country'].fillna('UNKNOWN')
availability_df['country'] = availability_df['country'].fillna('UNKNOWN')

valid_matches = pd.merge(
    contracts_df,
    availability_df,
    left_on=['country', 'insurance_plan'],
    right_on=['country', 'plan_id'],
    how='inner'
)
logger.info(f"Matched {len(valid_matches)} contracts with valid insurance options")

# Get total eligible contracts per country (any contract in a country with at least one valid option)
eligible_contracts = pd.merge(
    contracts_df,
    availability_df[['country']].drop_duplicates(),
    on='country',
    how='inner'
)

# Begin metrics construction
metrics = []

# 1. Plan uptake per country (only where plan is enabled)
plan_country_counts = valid_matches.groupby(['country', 'plan_id', 'plan_label']).contract_id.nunique().reset_index(name='uptake_count')
country_totals = eligible_contracts.groupby('country').contract_id.nunique().reset_index(name='eligible_population')

merged = pd.merge(plan_country_counts, country_totals, on='country', how='left')

for _, row in merged.iterrows():
    metrics.append({
        'snapshot_date': SNAPSHOT_DATE,
        'metric_type': 'health_insurance_plan_by_country',
        'id': row['plan_id'],
        'label': f"{row['plan_label']} ({row['country']})",
        'count': int(row['uptake_count']),
        'overall_percentage': row['uptake_count'] / row['eligible_population'] * 100 if row['eligible_population'] > 0 else 0,
        'category_percentage': 100.0,
        'contract_count': int(row['uptake_count'])
    })

# 2. Total uptake per country
uptake_by_country = valid_matches.groupby('country').contract_id.nunique().reset_index(name='uptake_count')

for _, row in uptake_by_country.iterrows():
    eligible = country_totals[country_totals['country'] == row['country']]['eligible_population'].values[0]
    metrics.append({
        'snapshot_date': SNAPSHOT_DATE,
        'metric_type': 'health_insurance_total_by_country',
        'id': row['country'],
        'label': row['country'],
        'count': int(row['uptake_count']),
        'overall_percentage': row['uptake_count'] / eligible * 100 if eligible > 0 else 0,
        'category_percentage': 100.0,
        'contract_count': int(row['uptake_count'])
    })

# 3. Overall eligible population by country
for _, row in country_totals.iterrows():
    metrics.append({
        'snapshot_date': SNAPSHOT_DATE,
        'metric_type': 'eligible_contracts_by_country',
        'id': row['country'],
        'label': row['country'],
        'count': int(row['eligible_population']),
        'overall_percentage': 0,
        'category_percentage': 0,
        'contract_count': int(row['eligible_population'])
    })

# 4. Total dependents by country for valid contracts (only LOCAL in PH)
valid_matches['dependent_count'] = pd.to_numeric(valid_matches['dependent_count'], errors='coerce').fillna(0)
dependent_filter = valid_matches[(valid_matches['plan_key'] == 'LOCAL') & (valid_matches['country'] == 'PH')]
dependent_summary = dependent_filter.groupby('country').dependent_count.sum().reset_index(name='total_dependents')

for _, row in dependent_summary.iterrows():
    eligible = country_totals[country_totals['country'] == row['country']]['eligible_population'].values[0]
    metrics.append({
        'snapshot_date': SNAPSHOT_DATE,
        'metric_type': 'health_insurance_dependents_by_country',
        'id': row['country'],
        'label': row['country'],
        'count': int(row['total_dependents']),
        'overall_percentage': row['total_dependents'] / eligible * 100 if eligible > 0 else 0,
        'category_percentage': 100.0,
        'contract_count': int(eligible)
    })

# Finalise
metrics_df = pd.DataFrame(metrics)
logger.info(f"Generated {len(metrics_df)} country-segmented health insurance metrics")

# Define schema
schema = [
    bigquery.SchemaField("snapshot_date", "DATE"),
    bigquery.SchemaField("metric_type", "STRING"),
    bigquery.SchemaField("id", "STRING"),
    bigquery.SchemaField("label", "STRING"),
    bigquery.SchemaField("count", "INTEGER"),
    bigquery.SchemaField("overall_percentage", "FLOAT"),
    bigquery.SchemaField("category_percentage", "FLOAT"),
    bigquery.SchemaField("contract_count", "INTEGER")
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
