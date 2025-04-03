# snapshot-customer-metrics.py

import pandas as pd
from datetime import datetime, timedelta
from google.cloud import bigquery
import logging
import sys
import argparse
from snapshot_utils import write_snapshot_to_bigquery

# Set up argument parser
parser = argparse.ArgumentParser(description='Generate customer metrics snapshot')
parser.add_argument('--dry-run', action='store_true', help='Validate without writing data')
args = parser.parse_args()

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s', handlers=[logging.StreamHandler(sys.stdout)])
logger = logging.getLogger('customer-snapshot')

# Initialize BigQuery client
client = bigquery.Client()
SNAPSHOT_DATE = datetime.now().date()
logger.info(f"Processing customer metrics snapshot for: {SNAPSHOT_DATE}")

# Define the first day of current month for monthly calculations
MONTH_START = SNAPSHOT_DATE.replace(day=1)
# Define the first day of previous month
PREV_MONTH_START = (MONTH_START - timedelta(days=1)).replace(day=1)

# Define output table
table_id = 'outstaffer-app-prod.dashboard_metrics.customer_snapshot'

# Load reference data
logger.info("Loading companies, industries, and sizes...")
companies_df = client.query("""
    SELECT 
        c.id, 
        c.companyName, 
        c.industry, 
        c.size, 
        c.createdAt, 
        c.demoCompany,
        ci.name AS industry_name,
        cs.name AS size_name
    FROM `outstaffer-app-prod.firestore_exports.companies` c
    LEFT JOIN `outstaffer-app-prod.firestore_exports.company_industries` ci
        ON c.industry = ci.id
    LEFT JOIN `outstaffer-app-prod.firestore_exports.company_sizes` cs
        ON c.size = cs.id
    WHERE c.demoCompany IS NULL OR c.demoCompany = FALSE
""").to_dataframe()

# Load users
logger.info("Loading users...")
users_df = client.query("""
    SELECT id, companyId
    FROM `outstaffer-app-prod.firestore_exports.users` u
    WHERE u.status = 'ENABLED' AND 
          (u.__has_error__ IS NULL OR u.__has_error__ = FALSE)
""").to_dataframe()

# Load contracts with full calculation data for revenue metrics
logger.info("Loading contracts and revenue calculations...")
contracts_df = client.query("""
    SELECT 
        ec.id AS contract_id,
        ec.companyId,
        ec.status,
        ec.createdAt,
        ec.updatedAt,
        ec.role.preferredStartDate AS start_date,
        ec.employmentLocation.country AS country,
        sm.mapped_status,
        
        -- Base EOR fees
        CAST(IFNULL((
            SELECT calc.monthlyCharges.employerCharges.planCharges.categoryTotals.EOR.amount
            FROM UNNEST(ec.calculations) AS calc
            ORDER BY calc.calculatedAt DESC LIMIT 1), '0') AS FLOAT64) AS eor_fees,
            
        -- Device fees
        CAST(IFNULL((
            SELECT calc.monthlyCharges.employerCharges.planCharges.categoryTotals.Device.amount
            FROM UNNEST(ec.calculations) AS calc
            ORDER BY calc.calculatedAt DESC LIMIT 1), '0') AS FLOAT64) AS device_fees,
            
        -- Hardware fees
        CAST(IFNULL((
            SELECT calc.monthlyCharges.employerCharges.planCharges.categoryTotals.Hardware.amount
            FROM UNNEST(ec.calculations) AS calc
            ORDER BY calc.calculatedAt DESC LIMIT 1), '0') AS FLOAT64) AS hardware_fees,
            
        -- Software fees
        CAST(IFNULL((
            SELECT calc.monthlyCharges.employerCharges.planCharges.categoryTotals.Software.amount
            FROM UNNEST(ec.calculations) AS calc
            ORDER BY calc.calculatedAt DESC LIMIT 1), '0') AS FLOAT64) AS software_fees,
            
        -- Health fees
        CAST(IFNULL((
            SELECT calc.monthlyCharges.employerCharges.healthCharges.total.amount
            FROM UNNEST(ec.calculations) AS calc
            ORDER BY calc.calculatedAt DESC LIMIT 1), '0') AS FLOAT64) AS health_fees,
            
        -- Currency for FX conversion
        ec.employmentLocation.country AS currency
    FROM `outstaffer-app-prod.firestore_exports.employee_contracts` ec
    JOIN `outstaffer-app-prod.firestore_exports.companies` c 
        ON ec.companyId = c.id
    LEFT JOIN `outstaffer-app-prod.lookup_tables.contract_status_mapping` sm 
        ON ec.status = sm.contract_status
    WHERE (ec.__has_error__ IS NULL OR ec.__has_error__ = FALSE)
        AND (c.demoCompany IS NULL OR c.demoCompany = FALSE)
""").to_dataframe()

# Load FX rates for currency conversion
logger.info("Loading FX rates...")
fx_rates_df = client.query("""
    SELECT 
        currency, 
        rate AS exchange_rate_to_aud,
        fx_date
    FROM `outstaffer-app-prod.dashboard_metrics.fx_rates`
    WHERE target_currency = 'AUD'
    QUALIFY ROW_NUMBER() OVER (PARTITION BY currency ORDER BY fx_date DESC) = 1
""").to_dataframe()

# Prepare metric rows
metrics = []

# Convert date columns
companies_df['createdAt'] = pd.to_datetime(companies_df['createdAt']).dt.date
contracts_df['start_date'] = pd.to_datetime(contracts_df['start_date']).dt.date
contracts_df['createdAt'] = pd.to_datetime(contracts_df['createdAt']).dt.date
contracts_df['updatedAt'] = pd.to_datetime(contracts_df['updatedAt']).dt.date

# Apply FX conversions
contracts_df = contracts_df.merge(fx_rates_df, left_on='currency', right_on='currency', how='left')
contracts_df['exchange_rate_to_aud'] = contracts_df['exchange_rate_to_aud'].fillna(1.0)

# Calculate revenue fields in AUD
fee_columns = ['eor_fees', 'device_fees', 'hardware_fees', 'software_fees', 'health_fees']
for col in fee_columns:
    contracts_df[f'{col}_aud'] = contracts_df[col] * contracts_df['exchange_rate_to_aud']

# Add total MRR field
contracts_df['total_mrr_aud'] = contracts_df[[f'{col}_aud' for col in fee_columns]].sum(axis=1)
contracts_df['addon_mrr_aud'] = contracts_df[[f'{col}_aud' for col in fee_columns if col != 'eor_fees']].sum(axis=1)

# Filter active contracts
active_contracts_df = contracts_df[contracts_df['mapped_status'] == 'Active'].copy()
revenue_contracts_df = contracts_df[contracts_df['mapped_status'].isin(['Active', 'Offboarding'])].copy()

# Identify all unique customer IDs
all_customer_ids = companies_df['id'].unique()
active_customer_ids = revenue_contracts_df['companyId'].unique()

# Find customers with previous contracts who no longer have active contracts (churned)
historical_customer_ids = contracts_df['companyId'].unique()
churned_customer_ids = [cid for cid in historical_customer_ids if cid not in active_customer_ids]

# Find new customers this month
new_companies_this_month = companies_df[companies_df['createdAt'] >= MONTH_START]
new_customer_ids_this_month = new_companies_this_month[
    new_companies_this_month['id'].isin(active_customer_ids)
]['id'].unique()

#----- Basic customer metrics -----

# Total customers
metrics.append({
    'snapshot_date': SNAPSHOT_DATE,
    'metric_type': 'total_customers',
    'id': 'ALL',
    'label': 'All Customers',
    'count': len(all_customer_ids),
    'value_aud': None,
    'percentage': None,
    'rank': None
})

# Active customers
metrics.append({
    'snapshot_date': SNAPSHOT_DATE,
    'metric_type': 'active_customers',
    'id': 'ACTIVE',
    'label': 'Customers with Active Contracts',
    'count': len(active_customer_ids),
    'value_aud': None,
    'percentage': len(active_customer_ids) / len(all_customer_ids) * 100 if len(all_customer_ids) > 0 else 0,
    'rank': None
})

# Churned customers
metrics.append({
    'snapshot_date': SNAPSHOT_DATE,
    'metric_type': 'churned_customers',
    'id': 'CHURNED',
    'label': 'Churned Customers',
    'count': len(churned_customer_ids),
    'value_aud': None,
    'percentage': len(churned_customer_ids) / len(all_customer_ids) * 100 if len(all_customer_ids) > 0 else 0,
    'rank': None
})

# New customers this month
metrics.append({
    'snapshot_date': SNAPSHOT_DATE,
    'metric_type': 'new_customers_this_month',
    'id': 'NEW',
    'label': 'New Customers This Month',
    'count': len(new_customer_ids_this_month),
    'value_aud': None,
    'percentage': len(new_customer_ids_this_month) / len(all_customer_ids) * 100 if len(all_customer_ids) > 0 else 0,
    'rank': None
})

# Net new customers
net_new = len(new_customer_ids_this_month) - len(churned_customer_ids)
metrics.append({
    'snapshot_date': SNAPSHOT_DATE,
    'metric_type': 'net_new_customers',
    'id': 'NET_NEW',
    'label': 'Net New Customers',
    'count': net_new,
    'value_aud': None,
    'percentage': None,
    'rank': None
})

#----- Usage metrics -----

# Average subscriptions per customer
if len(active_customer_ids) > 0:
    avg_active_subs = len(revenue_contracts_df) / len(active_customer_ids)
else:
    avg_active_subs = 0

metrics.append({
    'snapshot_date': SNAPSHOT_DATE,
    'metric_type': 'avg_active_subscriptions_per_customer',
    'id': 'AVG_SUBS',
    'label': 'Average Active Subscriptions per Customer',
    'count': None,
    'value_aud': round(avg_active_subs, 2),
    'percentage': None,
    'rank': None
})

# Users per customer (average)
users_per_company = users_df.groupby('companyId').id.count()
avg_users = users_per_company.mean() if not users_per_company.empty else 0
metrics.append({
    'snapshot_date': SNAPSHOT_DATE,
    'metric_type': 'avg_users_per_customer',
    'id': 'AVG_USERS',
    'label': 'Average Users per Company',
    'count': None,
    'value_aud': round(avg_users, 2),
    'percentage': None,
    'rank': None
})

# Average days to first contract
# First, find the first contract date for each company
first_contracts = contracts_df.sort_values('createdAt').groupby('companyId').first().reset_index()
first_contracts['days_to_first_contract'] = (
        pd.to_datetime(first_contracts['createdAt']) -
        pd.to_datetime(companies_df.set_index('id').loc[first_contracts['companyId']]['createdAt'].values)
).dt.days

avg_days_to_contract = first_contracts['days_to_first_contract'].mean()
metrics.append({
    'snapshot_date': SNAPSHOT_DATE,
    'metric_type': 'avg_days_to_first_contract',
    'id': 'AVG_DAYS_TO_CONTRACT',
    'label': 'Average Days from Company Creation to First Contract',
    'count': None,
    'value_aud': round(avg_days_to_contract, 1),
    'percentage': None,
    'rank': None
})

# Active contracts count
metrics.append({
    'snapshot_date': SNAPSHOT_DATE,
    'metric_type': 'active_contracts',
    'id': 'ACTIVE_CONTRACTS',
    'label': 'Total Active Contracts',
    'count': len(revenue_contracts_df),
    'value_aud': None,
    'percentage': None,
    'rank': None
})

#----- Revenue metrics -----

# Calculate total MRR and ARR
total_mrr = revenue_contracts_df['total_mrr_aud'].sum()
addon_mrr = revenue_contracts_df['addon_mrr_aud'].sum()
total_arr = total_mrr * 12

metrics.append({
    'snapshot_date': SNAPSHOT_DATE,
    'metric_type': 'total_mrr',
    'id': 'TOTAL_MRR',
    'label': 'Total Monthly Recurring Revenue',
    'count': None,
    'value_aud': round(total_mrr, 2),
    'percentage': None,
    'rank': None
})

metrics.append({
    'snapshot_date': SNAPSHOT_DATE,
    'metric_type': 'total_arr',
    'id': 'TOTAL_ARR',
    'label': 'Total Annual Recurring Revenue',
    'count': None,
    'value_aud': round(total_arr, 2),
    'percentage': None,
    'rank': None
})

# Average contract value
if len(revenue_contracts_df) > 0:
    avg_contract_value = total_mrr / len(revenue_contracts_df)
else:
    avg_contract_value = 0

metrics.append({
    'snapshot_date': SNAPSHOT_DATE,
    'metric_type': 'avg_contract_value',
    'id': 'AVG_CONTRACT_VALUE',
    'label': 'Average Contract Value (MRR)',
    'count': None,
    'value_aud': round(avg_contract_value, 2),
    'percentage': None,
    'rank': None
})

# Average ARR per customer
if len(active_customer_ids) > 0:
    avg_arr_per_customer = total_arr / len(active_customer_ids)
else:
    avg_arr_per_customer = 0

metrics.append({
    'snapshot_date': SNAPSHOT_DATE,
    'metric_type': 'avg_arr_per_customer',
    'id': 'AVG_ARR_PER_CUSTOMER',
    'label': 'Average ARR per Customer',
    'count': None,
    'value_aud': round(avg_arr_per_customer, 2),
    'percentage': None,
    'rank': None
})

# Addon revenue percentage
if total_mrr > 0:
    addon_percentage = (addon_mrr / total_mrr) * 100
else:
    addon_percentage = 0

metrics.append({
    'snapshot_date': SNAPSHOT_DATE,
    'metric_type': 'addon_revenue_percentage',
    'id': 'ADDON_PERCENTAGE',
    'label': 'Add-on Revenue as Percentage of Total MRR',
    'count': None,
    'value_aud': None,
    'percentage': round(addon_percentage, 2),
    'rank': None
})

#----- Top customers by ARR -----

# Calculate company-level metrics
company_metrics = revenue_contracts_df.groupby('companyId').agg(
    active_contracts=('contract_id', 'count'),
    total_mrr=('total_mrr_aud', 'sum'),
    primary_country=('country', lambda x: x.value_counts().index[0] if len(x) > 0 else None)
).reset_index()

company_metrics['total_arr'] = company_metrics['total_mrr'] * 12
company_metrics['avg_contract_value'] = company_metrics['total_mrr'] / company_metrics['active_contracts']

# Add company details
company_metrics = company_metrics.merge(
    companies_df[['id', 'companyName', 'industry', 'size', 'industry_name', 'size_name']],
    left_on='companyId',
    right_on='id',
    how='left'
)

# Calculate percentages of total ARR
total_company_arr = company_metrics['total_arr'].sum()
company_metrics['arr_percentage'] = (company_metrics['total_arr'] / total_company_arr * 100) if total_company_arr > 0 else 0

# Get top 10 customers by ARR
top_customers = company_metrics.sort_values(by='total_arr', ascending=False).head(10).reset_index(drop=True)

for idx, row in top_customers.iterrows():
    industry_label = row['industry_name'] if pd.notna(row['industry_name']) else 'Unknown Industry'
    size_label = row['size_name'] if pd.notna(row['size_name']) else 'Unknown Size'

    metrics.append({
        'snapshot_date': SNAPSHOT_DATE,
        'metric_type': 'top_customer_by_arr',
        'id': row['companyId'],
        'label': f"{row['companyName']} ({industry_label}, {size_label})",
        'count': int(row['active_contracts']),
        'value_aud': round(row['total_arr'], 2),
        'percentage': round(row['arr_percentage'], 2),
        'rank': idx + 1
    })

# Create metrics DataFrame
metrics_df = pd.DataFrame(metrics)

# Ensure numeric columns that must be integers are cast correctly
for col in ['count', 'contract_count']:
    if col in metrics_df.columns:
        metrics_df[col] = pd.to_numeric(metrics_df[col], errors='coerce').fillna(0).astype(int)
    if 'rank' in metrics_df.columns:
        metrics_df['rank'] = pd.to_numeric(metrics_df['rank'], errors='coerce').fillna(0).astype(int)

logger.info(f"Prepared {len(metrics_df)} metric rows")

# Define schema for BigQuery
schema = [
    bigquery.SchemaField("snapshot_date", "DATE"),
    bigquery.SchemaField("metric_type", "STRING"),
    bigquery.SchemaField("id", "STRING"),
    bigquery.SchemaField("label", "STRING"),
    bigquery.SchemaField("count", "INTEGER"),
    bigquery.SchemaField("value_aud", "FLOAT"),
    bigquery.SchemaField("percentage", "FLOAT"),
    bigquery.SchemaField("rank", "INTEGER"),
]

# Write to BigQuery or display summary in dry run mode
if args.dry_run:
    logger.info("Dry run enabled - not writing to BigQuery")

    # Display summary by metric type
    summary = metrics_df.groupby('metric_type').size().reset_index(name='count')
    print("\nMetrics summary:")
    for _, row in summary.iterrows():
        print(f"  {row['metric_type']}: {row['count']} entries")

    # Save to CSV for inspection
    csv_file = f"customer_metrics_{SNAPSHOT_DATE}.csv"
    metrics_df.to_csv(csv_file, index=False)
    logger.info(f"Saved metrics to {csv_file}")
else:
    # Write to BigQuery using the utility
    success = write_snapshot_to_bigquery(
        metrics_df=metrics_df,
        table_id=table_id,
        schema=schema,
        dry_run=False
    )

    if success:
        logger.info(f"Successfully wrote {len(metrics_df)} rows to {table_id}")
    else:
        logger.error(f"Failed to write to {table_id}")
        sys.exit(1)

logger.info("Customer metrics snapshot completed")