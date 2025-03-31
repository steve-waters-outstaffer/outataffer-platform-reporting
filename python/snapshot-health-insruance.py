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

# Define snapshot date as today
SNAPSHOT_DATE = datetime.now().date()
logger.info(f"Processing health insurance snapshot for: {SNAPSHOT_DATE}")

# Load health insurance options from Firestore exports
logger.info("Loading health insurance options...")
insurance_options_df = client.query("""
    SELECT 
        id, 
        key, 
        label, 
        description,
        STRUCT(
            CASE WHEN countryFieldOverrides.AU.isDisabled IS NOT NULL THEN countryFieldOverrides.AU.isDisabled ELSE FALSE END AS AU,
            CASE WHEN countryFieldOverrides.SG.isDisabled IS NOT NULL THEN countryFieldOverrides.SG.isDisabled ELSE FALSE END AS SG,
            CASE WHEN countryFieldOverrides.TH.isDisabled IS NOT NULL THEN countryFieldOverrides.TH.isDisabled ELSE FALSE END AS TH,
            CASE WHEN countryFieldOverrides.IN.isDisabled IS NOT NULL THEN countryFieldOverrides.IN.isDisabled ELSE FALSE END AS `IN`,
            CASE WHEN countryFieldOverrides.PH.isDisabled IS NOT NULL THEN countryFieldOverrides.PH.isDisabled ELSE FALSE END AS PH,
            CASE WHEN countryFieldOverrides.VN.isDisabled IS NOT NULL THEN countryFieldOverrides.VN.isDisabled ELSE FALSE END AS VN,
            CASE WHEN countryFieldOverrides.MY.isDisabled IS NOT NULL THEN countryFieldOverrides.MY.isDisabled ELSE FALSE END AS MY
        ) AS disabled_in_country
    FROM `outstaffer-app-prod.firestore_exports.health_insurance_options`
    WHERE __has_error__ IS NULL OR __has_error__ = FALSE
""").to_dataframe()

logger.info(f"Loaded {len(insurance_options_df)} health insurance options")

# Load health insurance add-ons (e.g., dependents)
logger.info("Loading health insurance add-ons...")
insurance_addons_df = client.query("""
    SELECT 
        id, 
        label, 
        description,
        maxQuantity,
        CAST(enabled IS NOT NULL AS BOOL) AS is_enabled
    FROM `outstaffer-app-prod.firestore_exports.health_insurance_add_ons`
    WHERE __has_error__ IS NULL OR __has_error__ = FALSE
""").to_dataframe()

logger.info(f"Loaded {len(insurance_addons_df)} health insurance add-ons")

# Load active contracts with health insurance data
logger.info("Loading contracts with health insurance data...")
contracts_df = client.query("""
    SELECT
        ec.id AS contract_id,
        ec.companyId,
        ec.employmentLocation.country AS country,
        ec.benefits.healthInsurance AS insurance_plan,
        -- Health insurance add-ons aren't in the expected field
        -- Just use empty array since they don't exist in the structure
        ARRAY[] AS insurance_addons,
        ec.benefits.addOns.DEPENDENT AS dependent_count,
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

logger.info(f"Loaded {len(contracts_df)} active contracts")

# Define function to extract health insurance add-ons
def aggregate_insurance_addons(df):
    # Check if empty
    if 'insurance_addons' not in df.columns or df['insurance_addons'].isnull().all():
        return pd.DataFrame(columns=['addon_id', 'contract_count'])

    # Extract non-null add-ons
    extracted = df[["contract_id", "insurance_addons"]].dropna(subset=["insurance_addons"])
    if extracted.empty:
        return pd.DataFrame(columns=['addon_id', 'contract_count'])

    # Explode add-ons array
    exploded = extracted.explode('insurance_addons')
    exploded = exploded[exploded['insurance_addons'].notnull()]

    # Extract add-on ID/key
    def extract_addon_key(x):
        if isinstance(x, dict):
            return x.get('key') or x.get('id') or "OTHER"
        return str(x) if x else "OTHER"

    exploded['addon_id'] = exploded['insurance_addons'].apply(extract_addon_key)
    return exploded.groupby('addon_id').contract_id.nunique().reset_index(name='contract_count')

# Begin metrics construction
metrics = []
total_contracts = len(contracts_df)
logger.info(f"Total active contracts for metrics: {total_contracts}")

# Calculate health insurance plan distribution
insurance_counts = contracts_df.groupby('insurance_plan').contract_id.nunique().reset_index(name='contract_count')
all_insurance_plans_df = pd.merge(
    insurance_options_df[['id', 'label']],
    insurance_counts,
    how='left',
    left_on='id',
    right_on='insurance_plan'
).fillna({'contract_count': 0, 'label': 'Unknown'})

# Add metrics for each insurance plan
for _, row in all_insurance_plans_df.iterrows():
    plan_id = row['id']
    plan_label = row['label'] if pd.notna(row['label']) else f"Plan {plan_id}"
    count = int(row['contract_count'])

    metrics.append({
        'snapshot_date': SNAPSHOT_DATE,
        'metric_type': 'health_insurance_plan',
        'id': plan_id,
        'label': plan_label,
        'count': count,
        'overall_percentage': count / total_contracts * 100 if total_contracts > 0 else 0,
        'category_percentage': 100.0,  # Each plan is its own category
        'contract_count': count
    })

# Calculate contracts with any health insurance
has_insurance_count = contracts_df[contracts_df['insurance_plan'].notnull() &
                                   (contracts_df['insurance_plan'] != '')].contract_id.nunique()

metrics.append({
    'snapshot_date': SNAPSHOT_DATE,
    'metric_type': 'has_health_insurance',
    'id': 'HAS_INSURANCE',
    'label': 'Has Health Insurance',
    'count': has_insurance_count,
    'overall_percentage': has_insurance_count / total_contracts * 100 if total_contracts > 0 else 0,
    'category_percentage': 100.0,
    'contract_count': has_insurance_count
})

# Country breakdown for health insurance
insurance_by_country = contracts_df[contracts_df['insurance_plan'].notnull() &
                                    (contracts_df['insurance_plan'] != '')].groupby('country').contract_id.nunique().reset_index(name='contract_count')

for _, row in insurance_by_country.iterrows():
    country = row['country'] if pd.notna(row['country']) else "Unknown"
    count = int(row['contract_count'])

    metrics.append({
        'snapshot_date': SNAPSHOT_DATE,
        'metric_type': 'health_insurance_by_country',
        'id': country,
        'label': country,
        'count': count,
        'overall_percentage': count / total_contracts * 100 if total_contracts > 0 else 0,
        'category_percentage': count / has_insurance_count * 100 if has_insurance_count > 0 else 0,
        'contract_count': count
    })

# Calculate insurance add-ons metrics (like dependents)
insurance_addon_counts = aggregate_insurance_addons(contracts_df)
all_insurance_addons_df = pd.merge(
    insurance_addons_df[['id', 'label']],
    insurance_addon_counts,
    how='left',
    left_on='id',
    right_on='addon_id'
).fillna({'contract_count': 0, 'label': 'Unknown'})

total_addon_contracts = 0
if not insurance_addon_counts.empty:
    total_addon_contracts = insurance_addon_counts['contract_count'].sum()

for _, row in all_insurance_addons_df.iterrows():
    addon_id = row['id']
    addon_label = row['label'] if pd.notna(row['label']) else f"Add-on {addon_id}"
    count = int(row['contract_count'])

    metrics.append({
        'snapshot_date': SNAPSHOT_DATE,
        'metric_type': 'health_insurance_addon',
        'id': addon_id,
        'label': addon_label,
        'count': count,
        'overall_percentage': count / total_contracts * 100 if total_contracts > 0 else 0,
        'category_percentage': count / total_addon_contracts * 100 if total_addon_contracts > 0 else 0,
        'contract_count': count
    })

# Calculate dependent stats from the 'dependent_count' field as well
has_dependents_count = contracts_df[contracts_df['dependent_count'] > 0].contract_id.nunique()
total_dependents = contracts_df['dependent_count'].fillna(0).sum()
avg_dependents = total_dependents / has_dependents_count if has_dependents_count > 0 else 0

metrics.append({
    'snapshot_date': SNAPSHOT_DATE,
    'metric_type': 'health_insurance_dependents',
    'id': 'HAS_DEPENDENTS',
    'label': 'Has Dependents',
    'count': has_dependents_count,
    'overall_percentage': has_dependents_count / total_contracts * 100 if total_contracts > 0 else 0,
    'category_percentage': has_dependents_count / has_insurance_count * 100 if has_insurance_count > 0 else 0,
    'contract_count': has_dependents_count
})

metrics.append({
    'snapshot_date': SNAPSHOT_DATE,
    'metric_type': 'health_insurance_dependents',
    'id': 'TOTAL_DEPENDENTS',
    'label': 'Total Dependents',
    'count': int(total_dependents),
    'overall_percentage': 0,  # Not applicable
    'category_percentage': 0,  # Not applicable
    'contract_count': has_dependents_count
})

metrics.append({
    'snapshot_date': SNAPSHOT_DATE,
    'metric_type': 'health_insurance_dependents',
    'id': 'AVG_DEPENDENTS',
    'label': 'Average Dependents per Contract',
    'count': 0,  # Special case - using the value field instead
    'overall_percentage': 0,  # Not applicable
    'category_percentage': 0,  # Not applicable
    'contract_count': has_dependents_count,
    'value': float(avg_dependents)
})

# Create metrics DataFrame
metrics_df = pd.DataFrame(metrics)
logger.info(f"Generated {len(metrics_df)} health insurance metrics rows")

# Define schema for BigQuery
schema = [
    bigquery.SchemaField("snapshot_date", "DATE"),
    bigquery.SchemaField("metric_type", "STRING"),
    bigquery.SchemaField("id", "STRING"),
    bigquery.SchemaField("label", "STRING"),
    bigquery.SchemaField("count", "INTEGER"),
    bigquery.SchemaField("overall_percentage", "FLOAT"),
    bigquery.SchemaField("category_percentage", "FLOAT"),
    bigquery.SchemaField("contract_count", "INTEGER"),
    bigquery.SchemaField("value", "FLOAT")
]

# Write to BigQuery using our utility
success = write_snapshot_to_bigquery(
    metrics_df=metrics_df,
    table_id=table_id,
    schema=schema,
    dry_run=args.dry_run
)

if not success:
    logger.error("Failed to write health insurance metrics to BigQuery")
    sys.exit(1)

# Write to CSV
csv_filename = f"health_insurance_metrics_{SNAPSHOT_DATE}.csv"
metrics_df.to_csv(csv_filename, index=False)
logger.info(f"Saved metrics to {csv_filename}")

# Display key metrics summary
plans_summary = metrics_df[metrics_df['metric_type'] == 'health_insurance_plan'].sort_values('count', ascending=False)
logger.info("\nHealth Insurance Plan Adoption Summary:")
for _, row in plans_summary.iterrows():
    logger.info(f"  {row['label']}: {row['count']} contracts ({row['overall_percentage']:.1f}%)")

logger.info(f"\nContracts with health insurance: {has_insurance_count} ({has_insurance_count/total_contracts*100:.1f}% of all contracts)")
logger.info(f"Contracts with dependents: {has_dependents_count} ({has_dependents_count/has_insurance_count*100:.1f}% of insured contracts)")
logger.info(f"Total dependents: {total_dependents}")
logger.info(f"Average dependents per contract with dependents: {avg_dependents:.2f}")

print("Health insurance metrics snapshot completed successfully")