import pandas as pd
from datetime import datetime
from google.cloud import bigquery
import logging
import sys
from metrics_utils import (
    get_active_contracts, get_offboarding_contracts, get_inactive_contracts,
    get_approved_not_started_contracts, get_companies, get_revenue_breakdown,get_all_countries
)
from metrics_utils import get_all_contracts
from snapshot_utils import write_snapshot_to_bigquery
import argparse

#Args
parser = argparse.ArgumentParser()
parser.add_argument('--dry-run', action='store_true', default=False)
args = parser.parse_args()

# Logging setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', handlers=[logging.StreamHandler(sys.stdout)])
logger = logging.getLogger('subscription-snapshot')

def main():
    snapshot_date = datetime.now().date()
    logger.info(f"Processing snapshot for: {snapshot_date}")

    # Existing data fetch
    active_df = get_active_contracts(snapshot_date)
    offboarding_df = get_offboarding_contracts(snapshot_date)
    revenue_contracts_df = pd.concat([active_df, offboarding_df]).drop_duplicates(subset='contract_id')
    companies_df = get_companies()
    revenue_breakdown = get_revenue_breakdown(revenue_contracts_df, snapshot_date)
    all_contracts_df = get_all_contracts()

    # New data fetch for additional metrics
    inactive_df = get_inactive_contracts(snapshot_date)
    approved_not_started_df = get_approved_not_started_contracts(snapshot_date)


        # Date conversions
    for df in [active_df, offboarding_df, inactive_df, approved_not_started_df, companies_df]:
        if 'start_date' in df.columns:
            df['start_date'] = pd.to_datetime(df['start_date'], errors='coerce')
        if 'createdAt' in df.columns:
            df['createdAt'] = pd.to_datetime(df['createdAt'], errors='coerce')
        if 'updatedAt' in df.columns:
            df['updatedAt'] = pd.to_datetime(df['updatedAt'], errors='coerce')

    # New and churned subscriptions
    month_start = snapshot_date.replace(day=1)
    next_month = (pd.Timestamp(month_start) + pd.offsets.MonthEnd(0) + pd.offsets.Day(1)).date()
    new_df = active_df[(active_df['start_date'].dt.date >= month_start) & (active_df['start_date'].dt.date < next_month)]
    churned_df = inactive_df[(inactive_df['updatedAt'].dt.date >= month_start) & (inactive_df['updatedAt'].dt.date < next_month)]

    # Metrics calculations
    total_active_subscriptions = len(active_df)
    approved_not_started_count = len(approved_not_started_df)
    offboarding_count = len(offboarding_df)
    total_contracts = len(all_contracts_df)
    revenue_contracts_count = len(revenue_contracts_df)
    new_subscriptions = len(new_df)
    churned_subscriptions = len(churned_df)
    retention_rate = (1 - churned_subscriptions / revenue_contracts_count) * 100 if revenue_contracts_count > 0 else 0
    churn_rate = (churned_subscriptions / revenue_contracts_count) * 100 if revenue_contracts_count > 0 else 0
    total_customers = revenue_contracts_df['companyId'].nunique()
    new_customers_this_month = companies_df[(companies_df['createdAt'].dt.date >= month_start) & (companies_df['createdAt'].dt.date < next_month)]['id'].nunique()
    avg_subscription_value = revenue_breakdown['total_mrr'] / revenue_contracts_count if revenue_contracts_count > 0 else 0
    recurring_revenue_percentage = revenue_breakdown['total_mrr'] / revenue_breakdown['total_monthly_revenue'] * 100 if revenue_breakdown['total_monthly_revenue'] > 0 else 0
    one_time_revenue_percentage = 100 - recurring_revenue_percentage if revenue_breakdown['total_monthly_revenue'] > 0 else 0
    avg_days_until_start = (approved_not_started_df['start_date'] - pd.Timestamp(snapshot_date)).dt.days.mean() if not approved_not_started_df.empty else 0
    plan_change_rate = 0.0  # Placeholder, requires historical data
    laptops_count = len(revenue_contracts_df[revenue_contracts_df['device_fees_aud'] > 0]) if 'device_fees_aud' in revenue_contracts_df.columns else 0

    # Country-level metrics (unchanged)
    all_countries = pd.DataFrame(get_all_countries()).rename(columns={'countryCode': 'country'})
    active_by_country = active_df.groupby('country').agg({'contract_id': 'count'}).rename(columns={'contract_id': 'count'})
    country_metrics = all_countries.merge(active_by_country, on='country', how='left').fillna({'count': 0})

    country_revenue_data = []
    for country in country_metrics['country']:
        country_contracts = revenue_contracts_df[revenue_contracts_df['country'] == country]
        country_revenue = get_revenue_breakdown(country_contracts, snapshot_date)
        country_revenue['country'] = country
        country_revenue['active_subscriptions'] = int(country_metrics[country_metrics['country'] == country]['count'].iloc[0])
        country_revenue_data.append(country_revenue)

    # Transform global metrics to row format
    global_metrics = [
        {'metric_type': 'total_active_subscriptions', 'id': 'total_active', 'label': 'Active Subscriptions', 'count': total_active_subscriptions, 'value_aud': None, 'percentage': None},
        {'metric_type': 'mrr_by_type', 'id': 'eor_fees', 'label': 'EOR Fees', 'count': None, 'value_aud': revenue_breakdown['eor_fees_mrr'], 'percentage': revenue_breakdown['eor_fees_mrr'] / revenue_breakdown['total_mrr'] * 100},
        {'metric_type': 'mrr_by_type', 'id': 'device_fees', 'label': 'Device Fees', 'count': None, 'value_aud': revenue_breakdown['device_fees_mrr'], 'percentage': revenue_breakdown['device_fees_mrr'] / revenue_breakdown['total_mrr'] * 100},
        {'metric_type': 'mrr_by_type', 'id': 'hardware_fees', 'label': 'Hardware Fees', 'count': None, 'value_aud': revenue_breakdown['hardware_fees_mrr'], 'percentage': revenue_breakdown['hardware_fees_mrr'] / revenue_breakdown['total_mrr'] * 100},
        {'metric_type': 'mrr_by_type', 'id': 'software_fees', 'label': 'Software Fees', 'count': None, 'value_aud': revenue_breakdown['software_fees_mrr'], 'percentage': revenue_breakdown['software_fees_mrr'] / revenue_breakdown['total_mrr'] * 100},
        {'metric_type': 'mrr_by_type', 'id': 'health_insurance', 'label': 'Health Insurance', 'count': None, 'value_aud': revenue_breakdown['health_fees_mrr'], 'percentage': revenue_breakdown['health_fees_mrr'] / revenue_breakdown['total_mrr'] * 100},
        {'metric_type': 'total_summary', 'id': 'total_mrr', 'label': 'Total Monthly Revenue', 'count': None, 'value_aud': revenue_breakdown['total_mrr'], 'percentage': 100.0},
        {'metric_type': 'total_summary', 'id': 'total_arr', 'label': 'Annual Recurring Revenue', 'count': None, 'value_aud': revenue_breakdown['total_arr'], 'percentage': 100.0},
        {'metric_type': 'customer_metrics', 'id': 'total_customers', 'label': 'Total Customers', 'count': total_customers, 'value_aud': None, 'percentage': None},
        {'metric_type': 'contract_metrics', 'id': 'approved_not_started', 'label': 'Approved Not Started', 'count': approved_not_started_count, 'value_aud': None, 'percentage': None},
        {'metric_type': 'contract_metrics', 'id': 'offboarding_contracts', 'label': 'Offboarding Contracts', 'count': offboarding_count, 'value_aud': None, 'percentage': None},
        {'metric_type': 'contract_metrics', 'id': 'total_contracts', 'label': 'Total Contracts', 'count': total_contracts, 'value_aud': None, 'percentage': None},
        {'metric_type': 'contract_metrics', 'id': 'revenue_generating_contracts', 'label': 'Revenue Generating Contracts', 'count': revenue_contracts_count, 'value_aud': None, 'percentage': None},
        {'metric_type': 'subscription_metrics', 'id': 'new_subscriptions', 'label': 'New Subscriptions', 'count': new_subscriptions, 'value_aud': None, 'percentage': None},
        {'metric_type': 'subscription_metrics', 'id': 'churned_subscriptions', 'label': 'Churned Subscriptions', 'count': churned_subscriptions, 'value_aud': None, 'percentage': None},
        {'metric_type': 'subscription_metrics', 'id': 'retention_rate', 'label': 'Retention Rate', 'count': None, 'value_aud': None, 'percentage': retention_rate},
        {'metric_type': 'subscription_metrics', 'id': 'churn_rate', 'label': 'Churn Rate', 'count': None, 'value_aud': None, 'percentage': churn_rate},
        {'metric_type': 'one_time_fees', 'id': 'placement_fees', 'label': 'Placement Fees', 'count': None, 'value_aud': revenue_breakdown['placement_fees'], 'percentage': revenue_breakdown['placement_fees'] / revenue_breakdown['total_monthly_revenue'] * 100 if revenue_breakdown['total_monthly_revenue'] > 0 else 0},
        {'metric_type': 'one_time_fees', 'id': 'finalisation_fees', 'label': 'Finalisation Fees', 'count': None, 'value_aud': revenue_breakdown['finalisation_fees'], 'percentage': revenue_breakdown['finalisation_fees'] / revenue_breakdown['total_monthly_revenue'] * 100 if revenue_breakdown['total_monthly_revenue'] > 0 else 0},
        {'metric_type': 'one_time_fees', 'id': 'one_time_fees', 'label': 'One-Time Fees', 'count': None, 'value_aud': revenue_breakdown['one_time_fees'], 'percentage': revenue_breakdown['one_time_fees'] / revenue_breakdown['total_monthly_revenue'] * 100 if revenue_breakdown['total_monthly_revenue'] > 0 else 0},
        {'metric_type': 'total_summary', 'id': 'total_monthly_revenue', 'label': 'Total Monthly Revenue', 'count': None, 'value_aud': revenue_breakdown['total_monthly_revenue'], 'percentage': 100.0},
        {'metric_type': 'customer_metrics', 'id': 'new_customers_this_month', 'label': 'New Customers This Month', 'count': new_customers_this_month, 'value_aud': None, 'percentage': None},
        {'metric_type': 'revenue_metrics', 'id': 'avg_subscription_value', 'label': 'Average Subscription Value', 'count': None, 'value_aud': avg_subscription_value, 'percentage': None},
        {'metric_type': 'revenue_metrics', 'id': 'recurring_revenue_percentage', 'label': 'Recurring Revenue Percentage', 'count': None, 'value_aud': None, 'percentage': recurring_revenue_percentage},
        {'metric_type': 'revenue_metrics', 'id': 'one_time_revenue_percentage', 'label': 'One-Time Revenue Percentage', 'count': None, 'value_aud': None, 'percentage': one_time_revenue_percentage},
        {'metric_type': 'subscription_metrics', 'id': 'addon_revenue_percentage', 'label': 'Add-on Revenue Percentage', 'count': None, 'value_aud': None, 'percentage': revenue_breakdown['addon_percentage']},
        {'metric_type': 'time_metrics', 'id': 'avg_days_until_start', 'label': 'Avg Days Until Start', 'count': None, 'value_aud': avg_days_until_start, 'percentage': None},
        {'metric_type': 'subscription_metrics', 'id': 'plan_change_rate', 'label': 'Plan Change Rate', 'count': None, 'value_aud': None, 'percentage': plan_change_rate},
        {'metric_type': 'device_metrics', 'id': 'laptops_count', 'label': 'Laptops Count', 'count': laptops_count, 'value_aud': None, 'percentage': None},
    ]

    # Transform country metrics to row format (unchanged)
    country_metrics_rows = []
    for data in country_revenue_data:
        country = data['country']
        country_metrics_rows.extend([
            {'metric_type': 'revenue_by_country', 'id': country, 'label': all_countries[all_countries['country'] == country]['name'].iloc[0], 'count': data['active_subscriptions'], 'value_aud': data['total_mrr'], 'percentage': data['total_mrr'] / revenue_breakdown['total_mrr'] * 100 if revenue_breakdown['total_mrr'] > 0 else 0},
        ])

    metrics_df = pd.DataFrame(global_metrics + country_metrics_rows)
    metrics_df['snapshot_date'] = snapshot_date

    # Define expected columns
    expected_columns = ['snapshot_date', 'metric_type', 'id', 'label', 'count', 'value_aud', 'percentage']

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

    schema = [
        bigquery.SchemaField("snapshot_date", "DATE"),
        bigquery.SchemaField("metric_type", "STRING"),
        bigquery.SchemaField("id", "STRING"),
        bigquery.SchemaField("label", "STRING"),
        bigquery.SchemaField("count", "INTEGER"),
        bigquery.SchemaField("value_aud", "FLOAT64"),
        bigquery.SchemaField("percentage", "FLOAT"),
    ]

    success = write_snapshot_to_bigquery(metrics_df, 'outstaffer-app-prod.dashboard_metrics.monthly_revenue_metrics', schema, dry_run=args.dry_run)
    if not success:
        logger.error("Failed to write metrics to BigQuery")
        sys.exit(1)

    metrics_df.to_csv(f"metrics_snapshot_{snapshot_date}.csv", index=False)
    logger.info(f"Results saved to metrics_snapshot_{snapshot_date}.csv")

if __name__ == "__main__":
    main()