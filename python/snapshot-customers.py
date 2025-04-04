# snapshot-customer-metrics.py

import pandas as pd
from datetime import datetime, timedelta
from google.cloud import bigquery
import logging
import sys
import argparse
from snapshot_utils import write_snapshot_to_bigquery
from metrics_utils import (get_companies_with_labels, get_enabled_users, get_all_contracts,
                           get_active_contracts, get_offboarding_contracts, get_fx_rates,
                           get_individual_revenue_metrics, convert_fees_to_aud)

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

# Define key dates
MONTH_START = SNAPSHOT_DATE.replace(day=1)
PREV_MONTH_START = (MONTH_START - timedelta(days=1)).replace(day=1)

# Define output table
table_id = 'outstaffer-app-prod.dashboard_metrics.customer_snapshot'

# Load data using utils
logger.info("Loading companies, users, and contracts...")

# Get contracts
active_contracts_df = get_active_contracts(SNAPSHOT_DATE)
offboarding_contracts_df = get_offboarding_contracts(SNAPSHOT_DATE)
revenue_contracts_df = active_contracts_df.copy()

companies_df = get_companies_with_labels()
users_df = get_enabled_users()
contracts_df = get_all_contracts(SNAPSHOT_DATE)
fx_rates_df = get_fx_rates()


# Prepare contracts data
contracts_df['start_date'] = pd.to_datetime(contracts_df['start_date']).dt.date
contracts_df['createdAt'] = pd.to_datetime(contracts_df['createdAt'])  # Keep as datetime, not just date
contracts_df['updatedAt'] = pd.to_datetime(contracts_df['updatedAt']).dt.date
companies_df['createdAt'] = pd.to_datetime(companies_df['createdAt']).dt.date

# Calculate revenue metrics
contracts_with_revenue = get_individual_revenue_metrics(active_contracts_df, SNAPSHOT_DATE)

# Identify customer segments
all_customer_ids = companies_df['id'].unique()
active_customer_ids = revenue_contracts_df['companyId'].unique()
historical_customer_ids = contracts_df['companyId'].unique()
churned_customer_ids = [cid for cid in historical_customer_ids if cid not in active_customer_ids]
new_companies_this_month = companies_df[companies_df['createdAt'] >= MONTH_START]
new_customer_ids_this_month = new_companies_this_month[new_companies_this_month['id'].isin(active_customer_ids)]['id'].unique()

# Prepare metrics
metrics = []

# Basic customer metrics
metrics.extend([
    {'snapshot_date': SNAPSHOT_DATE, 'metric_type': 'total_customers', 'id': 'ALL', 'label': 'All Customers', 'count': len(all_customer_ids), 'value_aud': None, 'percentage': None, 'rank': None},
    {'snapshot_date': SNAPSHOT_DATE, 'metric_type': 'active_customers', 'id': 'ACTIVE', 'label': 'Customers with Active Contracts', 'count': len(active_customer_ids), 'value_aud': None, 'percentage': len(active_customer_ids) / len(all_customer_ids) * 100 if all_customer_ids.size > 0 else 0, 'rank': None},
    {'snapshot_date': SNAPSHOT_DATE, 'metric_type': 'churned_customers', 'id': 'CHURNED', 'label': 'Churned Customers', 'count': len(churned_customer_ids), 'value_aud': None, 'percentage': len(churned_customer_ids) / len(all_customer_ids) * 100 if all_customer_ids.size > 0 else 0, 'rank': None},
    {'snapshot_date': SNAPSHOT_DATE, 'metric_type': 'new_customers_this_month', 'id': 'NEW', 'label': 'New Customers This Month', 'count': len(new_customer_ids_this_month), 'value_aud': None, 'percentage': len(new_customer_ids_this_month) / len(all_customer_ids) * 100 if all_customer_ids.size > 0 else 0, 'rank': None},
    {'snapshot_date': SNAPSHOT_DATE, 'metric_type': 'net_new_customers', 'id': 'NET_NEW', 'label': 'Net New Customers', 'count': len(new_customer_ids_this_month) - len(churned_customer_ids), 'value_aud': None, 'percentage': None, 'rank': None}
])

# Usage metrics
avg_active_subs = len(revenue_contracts_df) / len(active_customer_ids) if active_customer_ids.size > 0 else 0
users_per_company = users_df.groupby('companyId').id.count()
avg_users = users_per_company.mean() if not users_per_company.empty else 0
first_contracts = contracts_df.sort_values('createdAt').groupby('companyId').first().reset_index()
first_contracts['days_to_first_contract'] = (pd.to_datetime(first_contracts['createdAt']) - pd.to_datetime(companies_df.set_index('id').loc[first_contracts['companyId']]['createdAt'].values)).dt.days
avg_days_to_contract = first_contracts['days_to_first_contract'].mean()

metrics.extend([
    {'snapshot_date': SNAPSHOT_DATE, 'metric_type': 'avg_active_subscriptions_per_customer', 'id': 'AVG_SUBS', 'label': 'Average Active Subscriptions per Customer', 'count': round(avg_active_subs, 2), 'value_aud': None , 'percentage': None, 'rank': None},
    {'snapshot_date': SNAPSHOT_DATE, 'metric_type': 'avg_users_per_customer', 'id': 'AVG_USERS', 'label': 'Average Users per Company', 'count': round(avg_users, 2), 'value_aud': None , 'percentage': None, 'rank': None},
    {'snapshot_date': SNAPSHOT_DATE, 'metric_type': 'avg_days_to_first_contract', 'id': 'AVG_DAYS_TO_CONTRACT', 'label': 'Average Days from Company Creation to First Contract', 'count': None, 'value_aud': round(avg_days_to_contract, 1), 'percentage': None, 'rank': None},
    {'snapshot_date': SNAPSHOT_DATE, 'metric_type': 'active_contracts', 'id': 'ACTIVE_CONTRACTS', 'label': 'Total Active Contracts', 'count': len(revenue_contracts_df), 'value_aud': None, 'percentage': None, 'rank': None}
])

# Revenue metrics
total_mrr = contracts_with_revenue['total_mrr_aud'].sum()
addon_mrr = contracts_with_revenue['addon_mrr_aud'].sum()
total_arr = total_mrr * 12
avg_contract_value = total_mrr / len(revenue_contracts_df) if len(revenue_contracts_df) > 0 else 0
avg_arr_per_customer = total_arr / len(active_customer_ids) if active_customer_ids.size > 0 else 0
addon_percentage = (addon_mrr / total_mrr) * 100 if total_mrr > 0 else 0

metrics.extend([
    {'snapshot_date': SNAPSHOT_DATE, 'metric_type': 'total_mrr', 'id': 'TOTAL_MRR', 'label': 'Total Monthly Recurring Revenue', 'count': None, 'value_aud': round(total_mrr, 2), 'percentage': None, 'rank': None},
    {'snapshot_date': SNAPSHOT_DATE, 'metric_type': 'total_arr', 'id': 'TOTAL_ARR', 'label': 'Total Annual Recurring Revenue', 'count': None, 'value_aud': round(total_arr, 2), 'percentage': None, 'rank': None},
    {'snapshot_date': SNAPSHOT_DATE, 'metric_type': 'avg_contract_value', 'id': 'AVG_CONTRACT_VALUE', 'label': 'Average Contract Value (MRR)', 'count': None, 'value_aud': round(avg_contract_value, 2), 'percentage': None, 'rank': None},
    {'snapshot_date': SNAPSHOT_DATE, 'metric_type': 'avg_arr_per_customer', 'id': 'AVG_ARR_PER_CUSTOMER', 'label': 'Average ARR per Customer', 'count': None, 'value_aud': round(avg_arr_per_customer, 2), 'percentage': None, 'rank': None},
    {'snapshot_date': SNAPSHOT_DATE, 'metric_type': 'addon_revenue_percentage', 'id': 'ADDON_PERCENTAGE', 'label': 'Add-on Revenue as Percentage of Total MRR', 'count': None, 'value_aud': None, 'percentage': round(addon_percentage, 2), 'rank': None}
])

# Top customers by ARR
company_metrics = contracts_with_revenue.groupby('companyId').agg(
    active_contracts=('contract_id', 'count'),
    total_mrr=('total_mrr_aud', 'sum'),
    primary_country=('country', lambda x: x.value_counts().index[0] if len(x) > 0 else None)
).reset_index()
company_metrics['total_arr'] = company_metrics['total_mrr'] * 12
company_metrics['avg_contract_value'] = company_metrics['total_mrr'] / company_metrics['active_contracts']
company_metrics = company_metrics.merge(companies_df[['id', 'companyName', 'industry_name', 'size_name']], left_on='companyId', right_on='id', how='left')
total_company_arr = company_metrics['total_arr'].sum()
company_metrics['arr_percentage'] = (company_metrics['total_arr'] / total_company_arr * 100) if total_company_arr > 0 else 0
top_customers = company_metrics.sort_values(by='total_arr', ascending=False).head(10).reset_index(drop=True)

for idx, row in top_customers.iterrows():
    industry_label = row['industry_name'] if pd.notna(row['industry_name']) else 'Unknown Industry'
    size_label = row['size_name'] if pd.notna(row['size_name']) else 'Unknown Size'
    metrics.append({
        'snapshot_date': SNAPSHOT_DATE, 'metric_type': 'top_customer_by_arr', 'id': row['companyId'],
        'label': f"{row['companyName']} ({industry_label}, {size_label})", 'count': int(row['active_contracts']),
        'value_aud': round(row['total_arr'], 2), 'percentage': round(row['arr_percentage'], 2), 'rank': idx + 1
    })

top10_total_arr = top_customers['total_arr'].sum()
top10_percentage = (top10_total_arr / total_company_arr) * 100 if total_company_arr > 0 else 0
metrics.append({
    'snapshot_date': SNAPSHOT_DATE, 'metric_type': 'revenue_concentration', 'id': 'TOP_10',
    'label': 'Top 10 Customer Revenue %', 'count': None, 'value_aud': None, 'percentage': round(top10_percentage, 2), 'rank': None
})

# After the "Top customers by ARR" section and before creating the metrics DataFrame

# ---------- Company Size Distribution ----------
logger.info("Calculating company size distribution metrics...")

# Get active companies with size data
active_companies_with_size = company_metrics[['companyId', 'id', 'size_name', 'total_arr', 'active_contracts']]
active_companies_with_size = active_companies_with_size.dropna(subset=['size_name'])

# Group by size
size_metrics = active_companies_with_size.groupby('size_name').agg(
    customer_count=('companyId', 'nunique'),
    total_arr=('total_arr', 'sum'),
    contract_count=('active_contracts', 'sum')
).reset_index()

# Calculate percentages and averages
size_metrics['customer_percentage'] = size_metrics['customer_count'] / len(active_customer_ids) * 100 if active_customer_ids.size > 0 else 0
size_metrics['arr_percentage'] = size_metrics['total_arr'] / total_company_arr * 100 if total_company_arr > 0 else 0
size_metrics['avg_arr_per_customer'] = size_metrics['total_arr'] / size_metrics['customer_count']

# Sort by customer count descending
size_metrics = size_metrics.sort_values('customer_count', ascending=False).reset_index(drop=True)
# Ensure consistent schema
expected_columns = ['snapshot_date', 'metric_type', 'id', 'label', 'count', 'value_aud', 'percentage', 'rank']

def safe_metric_append(metric_dict):
    # Fill all fields, even if missing
    row = {}
    for field in expected_columns:
        val = metric_dict.get(field)
        if field in ['count', 'rank']:
            row[field] = int(val) if pd.notnull(val) else 0
        elif field in ['value_aud', 'percentage']:
            row[field] = float(val) if pd.notnull(val) else None
        elif field == 'snapshot_date':
            row[field] = pd.to_datetime(val).date() if pd.notnull(val) else SNAPSHOT_DATE
        else:
            row[field] = str(val).replace('\n', ' ').replace('\r', ' ').strip() if pd.notnull(val) else ''
    metrics.append(row)


# Add size metrics
for idx, row in size_metrics.iterrows():
    safe_metric_append({
        'snapshot_date': SNAPSHOT_DATE,
        'metric_type': 'company_size_distribution',
        'id': f"SIZE_{idx}",
        'label': row['size_name'],
        'count': int(row['customer_count']),
        'value_aud': round(row['total_arr'], 2),
        'percentage': round(row['customer_percentage'], 2),
        'rank': idx + 1
    })

    # Also add specific ARR metrics for each size
    safe_metric_append({
        'snapshot_date': SNAPSHOT_DATE,
        'metric_type': 'company_size_arr',
        'id': f"SIZE_ARR_{idx}",
        'label': f"ARR: {row['size_name']}",
        'count': None,
        'value_aud': round(row['total_arr'], 2),
        'percentage': round(row['arr_percentage'], 2),
        'rank': idx + 1
    })

    # Add average ARR per customer in this size band
    safe_metric_append({
        'snapshot_date': SNAPSHOT_DATE,
        'metric_type': 'company_size_avg_arr',
        'id': f"SIZE_AVG_{idx}",
        'label': f"Avg ARR: {row['size_name']}",
        'count': None,
        'value_aud': round(row['avg_arr_per_customer'], 2),
        'percentage': None,
        'rank': idx + 1
    })

# ---------- Industry Distribution ----------
logger.info("Calculating industry distribution metrics...")

# Get active companies with industry data
active_companies_with_industry = company_metrics[['companyId', 'id', 'industry_name', 'total_arr', 'active_contracts']]
active_companies_with_industry = active_companies_with_industry.dropna(subset=['industry_name'])

# Group by industry
industry_metrics = active_companies_with_industry.groupby('industry_name').agg(
    customer_count=('companyId', 'nunique'),
    total_arr=('total_arr', 'sum'),
    contract_count=('active_contracts', 'sum')
).reset_index()

# Calculate percentages and averages
industry_metrics['customer_percentage'] = industry_metrics['customer_count'] / len(active_customer_ids) * 100 if active_customer_ids.size > 0 else 0
industry_metrics['arr_percentage'] = industry_metrics['total_arr'] / total_company_arr * 100 if total_company_arr > 0 else 0
industry_metrics['avg_arr_per_customer'] = industry_metrics['total_arr'] / industry_metrics['customer_count']

# Get top 10 industries by customer count
top_industries_by_count = industry_metrics.sort_values('customer_count', ascending=False).head(10).reset_index(drop=True)

# Add industry count metrics
for idx, row in top_industries_by_count.iterrows():
    safe_metric_append({
        'snapshot_date': SNAPSHOT_DATE,
        'metric_type': 'top_industry_by_count',
        'id': f"IND_COUNT_{idx}",
        'label': row['industry_name'],
        'count': int(row['customer_count']),
        'value_aud': round(row['total_arr'], 2),
        'percentage': round(row['customer_percentage'], 2),
        'rank': idx + 1
    })

# Get top 10 industries by ARR
top_industries_by_arr = industry_metrics.sort_values('total_arr', ascending=False).head(10).reset_index(drop=True)

# Add industry ARR metrics
for idx, row in top_industries_by_arr.iterrows():
    safe_metric_append({
        'snapshot_date': SNAPSHOT_DATE,
        'metric_type': 'top_industry_by_arr',
        'id': f"IND_ARR_{idx}",
        'label': row['industry_name'],
        'count': int(row['customer_count']),
        'value_aud': round(row['total_arr'], 2),
        'percentage': round(row['arr_percentage'], 2),
        'rank': idx + 1
    })

# Create metrics DataFrame
metrics_df = pd.DataFrame(metrics)
metrics_df['count'] = pd.to_numeric(metrics_df['count'], errors='coerce').fillna(0).astype(int)
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

# Ensure consistent schema

for col in expected_columns:
    if col not in metrics_df.columns:
        metrics_df[col] = None  # Add missing columns

# Reorder columns to match schema exactly
metrics_df = metrics_df[expected_columns]

# Final cleanup for BigQuery compatibility
metrics_df['snapshot_date'] = pd.to_datetime(metrics_df['snapshot_date']).dt.date
metrics_df['metric_type'] = metrics_df['metric_type'].fillna('').astype(str)
metrics_df['id'] = metrics_df['id'].fillna('').astype(str)
metrics_df['label'] = metrics_df['label'].fillna('').astype(str)
metrics_df['count'] = pd.to_numeric(metrics_df['count'], errors='coerce').fillna(0).astype(int)
metrics_df['value_aud'] = pd.to_numeric(metrics_df['value_aud'], errors='coerce')
metrics_df['percentage'] = pd.to_numeric(metrics_df['percentage'], errors='coerce')
metrics_df['rank'] = pd.to_numeric(metrics_df['rank'], errors='coerce').fillna(0).astype(int)

# Write to BigQuery or display summary in dry run mode
if args.dry_run:
    logger.info("Dry run enabled - not writing to BigQuery")
    summary = metrics_df.groupby('metric_type').size().reset_index(name='count')
    print("\nMetrics summary:")
    for _, row in summary.iterrows():
        print(f"  {row['metric_type']}: {row['count']} entries")
    csv_file = f"customer_metrics_{SNAPSHOT_DATE}.csv"
    metrics_df.to_csv(csv_file, index=False)
    logger.info(f"Saved metrics to {csv_file}")
else:
    success = write_snapshot_to_bigquery(metrics_df=metrics_df, table_id=table_id, schema=schema, dry_run=False)
    if success:
        logger.info(f"Successfully wrote {len(metrics_df)} rows to {table_id}")
    else:
        logger.error(f"Failed to write to {table_id}")
        sys.exit(1)

logger.info("Customer metrics snapshot completed")