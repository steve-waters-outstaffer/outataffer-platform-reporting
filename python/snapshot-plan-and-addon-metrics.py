# snapshot-plan-and-addon-metrics.py
import pandas as pd
from datetime import datetime
from google.cloud import bigquery
import logging
import sys
import argparse
from snapshot_utils import write_snapshot_to_bigquery

# Set up argument parser
parser = argparse.ArgumentParser(description='Generate plan and add-on metrics snapshot')
parser.add_argument('--dry-run', action='store_true', help='Validate without writing data')
args = parser.parse_args()

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s', handlers=[logging.StreamHandler(sys.stdout)])
logger = logging.getLogger('plan-addon-snapshot')

# Initialize BigQuery client
client = bigquery.Client()
table_id = 'outstaffer-app-prod.dashboard_metrics.plan_addon_adoption'

# Define snapshot date as today
SNAPSHOT_DATE = datetime.now().date()
logger.info(f"Processing snapshot for: {SNAPSHOT_DATE}")

# Load lookup tables and metadata
addons_df = client.query("""
    SELECT id, label, type, meta, isActive FROM `outstaffer-app-prod.firestore_exports.plan_add_ons`
""").to_dataframe()

plans_df = client.query("""
    SELECT id, name FROM `outstaffer-app-prod.firestore_exports.plans` WHERE active = TRUE
""").to_dataframe()

# Core query: pull all valid, started, active contracts
contracts_df = client.query("""
    SELECT
        ec.id AS contract_id,
        ec.plan.type AS plan_id,
        ec.plan.deviceUpgrade AS device_id,
        ec.plan.hardwareAddons AS hardware,
        ec.plan.softwareAddons AS software,
        ec.plan.membershipAddons AS membership,
        ec.employmentLocation.country AS country,
        CAST(ec.role.preferredStartDate AS DATE) AS preferredStartDate
    FROM `outstaffer-app-prod.firestore_exports.employee_contracts` ec
    JOIN `outstaffer-app-prod.firestore_exports.companies` c ON ec.companyId = c.id
    JOIN `outstaffer-app-prod.lookup_tables.contract_status_mapping` cm ON ec.status = cm.contract_status
    WHERE (c.demoCompany IS NULL OR c.demoCompany = FALSE)
      AND (ec.__has_error__ IS NULL OR ec.__has_error__ = FALSE)
      AND cm.mapped_status = 'Active'
      AND ec.role.preferredStartDate IS NOT NULL
      AND CAST(ec.role.preferredStartDate AS DATE) <= CURRENT_DATE()
""").to_dataframe()

logger.info(f"Loaded {len(contracts_df)} active + started contracts")

# Metric aggregation functions
def aggregate_addons(df, col, addon_type):
    extracted = df[["contract_id", col]].dropna()
    if extracted.empty:
        return pd.DataFrame(columns=['addon_id', 'contract_count'])

    exploded = extracted.explode(col)
    exploded = exploded[exploded[col].notnull()]

    def extract_addon_key(x):
        if isinstance(x, dict):
            return x.get('key') or "OTHER"
        return str(x) if x else "OTHER"

    exploded['addon_id'] = exploded[col].apply(extract_addon_key)
    return exploded.groupby('addon_id').contract_id.nunique().reset_index(name='contract_count')

# Begin metric construction
metrics = []

total_contracts = len(contracts_df)
logger.info(f"Total active & started contracts: {total_contracts}")

# Plan distribution (ensure all active plans are included)
plan_counts = contracts_df.groupby('plan_id').contract_id.nunique().reset_index(name='contract_count')
all_plans_df = plans_df.merge(plan_counts, how='left', left_on='id', right_on='plan_id').fillna({'contract_count': 0})
for _, row in all_plans_df.iterrows():
    metrics.append({
        'snapshot_date': SNAPSHOT_DATE,
        'metric_type': 'plan',
        'id': row['id'],
        'label': row['name'],
        'count': int(row['contract_count']),
        'overall_percentage': row['contract_count'] / total_contracts * 100 if total_contracts > 0 else 0,
        'category_percentage': 100.0,
        'contract_count': int(row['contract_count'])
    })

# Country distribution
country_counts = contracts_df.groupby('country').contract_id.nunique().reset_index(name='contract_count')
for _, row in country_counts.iterrows():
    label = row['country'] if pd.notna(row['country']) else "OTHER"
    metrics.append({
        'snapshot_date': SNAPSHOT_DATE,
        'metric_type': 'country',
        'id': label,
        'label': label,
        'count': row['contract_count'],
        'overall_percentage': row['contract_count'] / total_contracts * 100,
        'category_percentage': 100.0,
        'contract_count': row['contract_count']
    })

# Device usage
all_devices_df = addons_df[addons_df['type'] == 'DEVICE'][['id', 'label']].rename(columns={'id': 'device_id', 'label': 'device_label'})
device_counts = contracts_df[contracts_df['device_id'].notnull()].groupby('device_id').contract_id.nunique().reset_index(name='contract_count')
device_counts['device_id'] = device_counts['device_id'].fillna("OTHER")
complete_device_data = all_devices_df.merge(device_counts, how='left', on='device_id').fillna({'device_label': 'OTHER', 'contract_count': 0})
total_devices = complete_device_data.contract_count.sum()
for _, row in complete_device_data.iterrows():
    metrics.append({
        'snapshot_date': SNAPSHOT_DATE,
        'metric_type': 'device',
        'id': row['device_id'],
        'label': row['device_label'],
        'count': int(row['contract_count']),
        'overall_percentage': row['contract_count'] / total_contracts * 100 if total_contracts > 0 else 0,
        'category_percentage': row['contract_count'] / total_devices * 100 if total_devices > 0 else 0,
        'contract_count': int(row['contract_count'])
    })

# Add-on metrics
for addon_type, col in [('hardware_addon', 'hardware'), ('software_addon', 'software'), ('membership_addon', 'membership')]:
    raw_type = addon_type.replace('_addon', '').upper()
    relevant_addons = addons_df[addons_df['type'] == raw_type][['id', 'label']].rename(columns={'id': 'addon_id', 'label': 'addon_label'})
    addon_counts = aggregate_addons(contracts_df, col, addon_type)
    complete_addon_data = relevant_addons.merge(addon_counts, how='left', on='addon_id').fillna({'addon_label': 'OTHER', 'contract_count': 0})
    total_addon_contracts = complete_addon_data.contract_count.sum()
    for _, row in complete_addon_data.iterrows():
        metrics.append({
            'snapshot_date': SNAPSHOT_DATE,
            'metric_type': addon_type,
            'id': row['addon_id'],
            'label': row['addon_label'],
            'count': int(row['contract_count']),
            'overall_percentage': row['contract_count'] / total_contracts * 100 if total_contracts > 0 else 0,
            'category_percentage': row['contract_count'] / total_addon_contracts * 100 if total_addon_contracts > 0 else 0,
            'contract_count': int(row['contract_count'])
        })

# OS breakdown from device meta
device_meta = addons_df[addons_df['type'] == 'DEVICE'][['id', 'label', 'meta']]
os_map = []
for _, row in device_meta.iterrows():
    os_type = "UNKNOWN"
    meta_os = row['meta'].get('operatingSystem') if isinstance(row['meta'], dict) else None
    if meta_os:
        os_type = meta_os
    elif row['label']:
        label = row['label'].lower()
        if 'windows' in label or 'win' in label:
            os_type = 'Windows'
        elif 'mac' in label or 'apple' in label:
            os_type = 'MacOS'
    os_map.append({"device_id": row['id'], "os_type": os_type})

os_df = pd.DataFrame(os_map)
os_usage = contracts_df[contracts_df['device_id'].notnull()].groupby('device_id').contract_id.nunique().reset_index(name='count')
os_summary = os_df.merge(os_usage, how='left', on='device_id').fillna({'os_type': 'OTHER', 'count': 0})
os_totals = os_summary.groupby('os_type').agg({'count': 'sum'}).reset_index()
total_devices = os_totals['count'].sum()

for _, row in os_totals.iterrows():
    metrics.append({
        'snapshot_date': SNAPSHOT_DATE,
        'metric_type': 'os_choice',
        'id': row['os_type'].upper().replace(' ', '_'),
        'label': row['os_type'],
        'count': int(row['count']),
        'overall_percentage': row['count'] / total_contracts * 100 if total_contracts > 0 else 0,
        'category_percentage': row['count'] / total_devices * 100 if total_devices > 0 else 0,
        'contract_count': int(row['count'])
    })

# Create metrics DataFrame
metrics_df = pd.DataFrame(metrics)
logger.info(f"Generated {len(metrics_df)} metrics rows")

# Define schema for BigQuery
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

# Write to BigQuery using our utility
success = write_snapshot_to_bigquery(
    metrics_df=metrics_df,
    table_id=table_id,
    schema=schema,
    dry_run=args.dry_run
)

if not success:
    logger.error("Failed to write plan and add-on metrics to BigQuery")
    sys.exit(1)

# Display metric type counts
metrics_by_type = metrics_df.groupby('metric_type').size().reset_index(name='count')
for _, row in metrics_by_type.iterrows():
    logger.info(f"Generated {row['count']} metrics of type '{row['metric_type']}'")

# Create local CSV backup
csv_filename = f"plan_addon_metrics_{SNAPSHOT_DATE}.csv"
metrics_df.to_csv(csv_filename, index=False)
logger.info(f"Saved metrics to {csv_filename}")

print("Plan and Add-on metrics snapshot completed successfully")