# snapshot-revenue-metrics.py
import pandas as pd
from datetime import datetime
from google.cloud import bigquery
import logging
import sys
import argparse
from metrics_utils import (
    get_active_contracts, get_offboarding_contracts, get_inactive_contracts,
    get_approved_not_started_contracts, get_companies, get_fx_rates,
    get_revenue_breakdown, get_individual_revenue_metrics
)
from snapshot_utils import write_snapshot_to_bigquery

# Argument parser
parser = argparse.ArgumentParser(description='Generate revenue metrics snapshot')
parser.add_argument('--dry-run', action='store_true', help='Validate without writing data')
args = parser.parse_args()

# Logging setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', handlers=[logging.StreamHandler(sys.stdout)])
logger = logging.getLogger('subscription-snapshot')

# BigQuery client and table
client = bigquery.Client()
table_id = 'outstaffer-app-prod.dashboard_metrics.monthly_subscription_snapshot'

def main():
    SNAPSHOT_DATE = datetime.now().date()
    logger.info(f"Processing snapshot for: {SNAPSHOT_DATE}")

    # Fetch data using utils
    active_df = get_active_contracts(SNAPSHOT_DATE)
    offboarding_df = get_offboarding_contracts(SNAPSHOT_DATE)
    inactive_df = get_inactive_contracts(SNAPSHOT_DATE)
    approved_not_started_df = get_approved_not_started_contracts(SNAPSHOT_DATE)
    companies_df = get_companies()

    # Ensure date columns are in datetime format
    for df in [active_df, offboarding_df, inactive_df, approved_not_started_df, companies_df]:
        if 'start_date' in df.columns:
            df['start_date'] = pd.to_datetime(df['start_date'], errors='coerce')
        if 'createdAt' in df.columns:
            df['createdAt'] = pd.to_datetime(df['createdAt'], errors='coerce')
        if 'updatedAt' in df.columns:
            df['updatedAt'] = pd.to_datetime(df['updatedAt'], errors='coerce')

    # Combine revenue-generating contracts (active + offboarding)
    revenue_contracts_df = pd.concat([active_df, offboarding_df]).drop_duplicates(subset='contract_id')
    all_contracts_df = pd.concat([revenue_contracts_df, approved_not_started_df]).drop_duplicates(subset='contract_id')

    # Calculate individual revenue metrics
    revenue_metrics_df = get_individual_revenue_metrics(revenue_contracts_df, SNAPSHOT_DATE)

    # Aggregate revenue breakdown
    revenue_breakdown = get_revenue_breakdown(revenue_contracts_df, SNAPSHOT_DATE)

    # New and churned subscriptions
    month_start = SNAPSHOT_DATE.replace(day=1)
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

    # Revenue metrics from breakdown
    eor_fees_mrr = revenue_breakdown['eor_fees_mrr']
    device_fees_mrr = revenue_breakdown['device_fees_mrr']
    hardware_fees_mrr = revenue_breakdown['hardware_fees_mrr']
    software_fees_mrr = revenue_breakdown['software_fees_mrr']
    health_fees_mrr = revenue_breakdown['health_fees_mrr']
    placement_fees = revenue_breakdown['placement_fees']
    finalisation_fees = revenue_breakdown['finalisation_fees']
    one_time_fees = revenue_breakdown['one_time_fees']
    total_mrr = revenue_breakdown['total_mrr']
    total_monthly_revenue = revenue_breakdown['total_monthly_revenue']
    total_arr = revenue_breakdown['total_arr']
    addon_revenue_percentage = revenue_breakdown['addon_percentage']

    # Additional metrics
    total_customers = revenue_contracts_df['companyId'].nunique()
    new_customers_this_month = companies_df[(companies_df['createdAt'].dt.date >= month_start) &
                                            (companies_df['createdAt'].dt.date < next_month)]['id'].nunique()
    avg_subscription_value = total_mrr / revenue_contracts_count if revenue_contracts_count > 0 else 0
    avg_days_from_approval_to_start = all_contracts_df['start_date'].sub(all_contracts_df['createdAt']).dt.days.mean()
    avg_days_until_start = (approved_not_started_df['start_date'] - pd.Timestamp(SNAPSHOT_DATE)).dt.days.mean() if not approved_not_started_df.empty else 0
    plan_change_rate = 0.0  # Requires historical data
    laptops_count = len(revenue_metrics_df[revenue_metrics_df['device_fees_aud'] > 0])

    # Final snapshot dictionary
    snapshot = {
        'snapshot_date': SNAPSHOT_DATE,
        'total_active_subscriptions': total_active_subscriptions,
        'approved_not_started': approved_not_started_count,
        'offboarding_contracts': offboarding_count,
        'total_contracts': total_contracts,
        'revenue_generating_contracts': revenue_contracts_count,
        'new_subscriptions': new_subscriptions,
        'churned_subscriptions': churned_subscriptions,
        'retention_rate': retention_rate,
        'churn_rate': churn_rate,
        'eor_fees_mrr': eor_fees_mrr,
        'device_fees_mrr': device_fees_mrr,
        'hardware_fees_mrr': hardware_fees_mrr,
        'software_fees_mrr': software_fees_mrr,
        'health_insurance_mrr': health_fees_mrr,
        'one_time_fees': one_time_fees,
        'placement_fees': placement_fees,
        'finalisation_fees': finalisation_fees,
        'total_mrr': total_mrr,
        'total_monthly_revenue': total_monthly_revenue,
        'total_arr': total_arr,
        'avg_subscription_value': avg_subscription_value,
        'recurring_revenue_percentage': total_mrr / total_monthly_revenue * 100 if total_monthly_revenue > 0 else 0,
        'one_time_revenue_percentage': 100 - (total_mrr / total_monthly_revenue * 100) if total_monthly_revenue > 0 else 0,
        'total_customers': total_customers,
        'new_customers_this_month': new_customers_this_month,
        'addon_revenue_percentage': addon_revenue_percentage,
        'avg_days_from_approval_to_start': avg_days_from_approval_to_start,
        'avg_days_until_start': avg_days_until_start,
        'plan_change_rate': plan_change_rate,
        'laptops_count': laptops_count,
    }

    # Convert to DataFrame
    metrics_df = pd.DataFrame([snapshot])

    # Define schema
    schema = [
        bigquery.SchemaField("snapshot_date", "DATE"),
        bigquery.SchemaField("total_active_subscriptions", "INTEGER"),
        bigquery.SchemaField("approved_not_started", "INTEGER"),
        bigquery.SchemaField("offboarding_contracts", "INTEGER"),
        bigquery.SchemaField("total_contracts", "INTEGER"),
        bigquery.SchemaField("revenue_generating_contracts", "INTEGER"),
        bigquery.SchemaField("new_subscriptions", "INTEGER"),
        bigquery.SchemaField("churned_subscriptions", "INTEGER"),
        bigquery.SchemaField("retention_rate", "FLOAT"),
        bigquery.SchemaField("churn_rate", "FLOAT"),
        bigquery.SchemaField("eor_fees_mrr", "FLOAT64"),
        bigquery.SchemaField("device_fees_mrr", "FLOAT64"),
        bigquery.SchemaField("hardware_fees_mrr", "FLOAT64"),
        bigquery.SchemaField("software_fees_mrr", "FLOAT64"),
        bigquery.SchemaField("health_insurance_mrr", "FLOAT64"),
        bigquery.SchemaField("one_time_fees", "FLOAT64"),
        bigquery.SchemaField("placement_fees", "FLOAT64"),
        bigquery.SchemaField("finalisation_fees", "FLOAT64"),
        bigquery.SchemaField("total_mrr", "FLOAT64"),
        bigquery.SchemaField("total_monthly_revenue", "FLOAT64"),
        bigquery.SchemaField("total_arr", "FLOAT64"),
        bigquery.SchemaField("avg_subscription_value", "FLOAT64"),
        bigquery.SchemaField("recurring_revenue_percentage", "FLOAT"),
        bigquery.SchemaField("one_time_revenue_percentage", "FLOAT"),
        bigquery.SchemaField("total_customers", "INTEGER"),
        bigquery.SchemaField("new_customers_this_month", "INTEGER"),
        bigquery.SchemaField("addon_revenue_percentage", "FLOAT"),
        bigquery.SchemaField("avg_days_from_approval_to_start", "FLOAT"),
        bigquery.SchemaField("avg_days_until_start", "FLOAT"),
        bigquery.SchemaField("plan_change_rate", "FLOAT"),
        bigquery.SchemaField("laptops_count", "INTEGER"),
    ]

    # Reorder DataFrame to match schema
    metrics_df = metrics_df[[field.name for field in schema]]

    # Write to BigQuery
    success = write_snapshot_to_bigquery(metrics_df, table_id, schema, dry_run=args.dry_run)
    if not success:
        logger.error("Failed to write revenue metrics to BigQuery")
        sys.exit(1)

    # Save locally
    metrics_df.to_csv(f"subscription_snapshot_{SNAPSHOT_DATE}.csv", index=False)
    logger.info(f"Results saved to subscription_snapshot_{SNAPSHOT_DATE}.csv")

    return metrics_df

if __name__ == "__main__":
    main()