import pandas as pd
import numpy as np
from datetime import datetime
from dateutil.relativedelta import relativedelta
from google.cloud import bigquery
import logging
import sys
import json
from tabulate import tabulate  # For displaying results locally

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger('subscription-snapshot')

# Initialize BigQuery client
client = bigquery.Client()
table_id = 'outstaffer-app-prod.dashboard_metrics.monthly_subscription_snapshot'

# Add a flag for local testing (don't write to BigQuery)
LOCAL_TEST = True  # Set to False when ready to write to BigQuery

def safe_get_nested(obj, path, default=None):
    """Safely navigate nested dictionaries/objects using dot notation path"""
    if obj is None:
        return default

    keys = path.split('.')
    result = obj

    try:
        for key in keys:
            if isinstance(result, dict) and key in result:
                result = result[key]
            elif isinstance(result, list) and key.isdigit() and int(key) < len(result):
                result = result[int(key)]
            else:
                return default
        return result
    except:
        return default

# Fix for numeric value extraction
def extract_number(obj, path):
    """Extract numeric value from nested JSON, handling string conversion"""
    try:
        parts = path.split('.')
        current = obj

        for part in parts:
            if not isinstance(current, dict) or part not in current:
                return 0.0
            current = current[part]

        # Handle different formats that BigQuery might return
        if isinstance(current, (int, float)):
            return float(current)
        elif isinstance(current, str) and current.strip():
            return float(current.strip())
        elif isinstance(current, dict) and 'amount' in current:
            amt = current['amount']
            if isinstance(amt, (int, float)):
                return float(amt)
            elif isinstance(amt, str) and amt.strip():
                return float(amt.strip())
        return 0.0
    except (ValueError, TypeError):
        return 0.0

def main():
    try:
        # 1. Define reporting date (first day of previous month)
        snapshot_date = (datetime.now() - relativedelta(months=1)).replace(day=1).date()
        logger.info(f"Processing snapshot for: {snapshot_date}")

        # 2. Load data with early filtering to reduce memory usage
        logger.info("Loading data from BigQuery...")

        # Filter to only load what we need
        query_employee_contracts = """
        SELECT 
            id, 
            status,
            companyId,
            role,
            benefits,
            createdAt,
            updatedAt,
            employmentLocation,
            calculations  -- We're specifically looking for the calculations array
        FROM `outstaffer-app-prod.firestore_exports.employee_contracts`
        WHERE __has_error__ IS NULL OR __has_error__ = FALSE
        """

        query_companies = """
        SELECT id, companyName, demoCompany, createdAt, industry, size 
        FROM `outstaffer-app-prod.firestore_exports.companies`
        WHERE demoCompany IS NULL OR demoCompany = FALSE
        """

        query_status_mapping = """
        SELECT * FROM `outstaffer-app-prod.lookup_tables.contract_status_mapping`
        """

        query_fx_rates = """
        SELECT * FROM `outstaffer-app-prod.dashboard_metrics.fx_rates`
        WHERE target_currency = 'AUD'
        """

        try:
            ec_df = client.query(query_employee_contracts).to_dataframe()
            logger.info(f"Loaded {len(ec_df)} employee contracts")

            companies_df = client.query(query_companies).to_dataframe()
            logger.info(f"Loaded {len(companies_df)} companies")

            status_mapping_df = client.query(query_status_mapping).to_dataframe()
            logger.info(f"Loaded {len(status_mapping_df)} status mappings")

            fx_rates_df = client.query(query_fx_rates).to_dataframe()
            logger.info(f"Loaded {len(fx_rates_df)} FX rates")
        except Exception as e:
            logger.error(f"Error loading data: {str(e)}")
            raise

        # 3. Process contracts
        logger.info("Processing contracts...")
        ec_df = ec_df.merge(status_mapping_df, left_on='status', right_on='contract_status', how='left')
        ec_df = ec_df.merge(companies_df, left_on='companyId', right_on='id', how='left', suffixes=('', '_company'))

        # Extract country from employmentLocation
        ec_df['country'] = ec_df['employmentLocation'].apply(
            lambda x: x.get('country') if isinstance(x, dict) else None
        )

        # Extract the latest calculation for each contract
        ec_df['latest_calc'] = ec_df['calculations'].apply(
            lambda x: x[-1] if isinstance(x, list) and len(x) > 0 else None
        )

        # Extract fee values from the latest calculation - note the updated paths
        ec_df['eor_fees'] = ec_df['latest_calc'].apply(lambda x:
                                                       float(safe_get_nested(x, 'monthlyCharges.employerCharges.planCharges.categoryTotals.EOR.amount', 0))
                                                       if x else 0
                                                       )
        ec_df['device_fees'] = ec_df['latest_calc'].apply(lambda x:
                                                          float(safe_get_nested(x, 'monthlyCharges.employerCharges.planCharges.categoryTotals.Device.amount', 0))
                                                          if x else 0
                                                          )
        ec_df['hardware_fees'] = ec_df['latest_calc'].apply(lambda x:
                                                            float(safe_get_nested(x, 'monthlyCharges.employerCharges.planCharges.categoryTotals.Hardware.amount', 0))
                                                            if x else 0
                                                            )
        ec_df['software_fees'] = ec_df['latest_calc'].apply(lambda x:
                                                            float(safe_get_nested(x, 'monthlyCharges.employerCharges.planCharges.categoryTotals.Software.amount', 0))
                                                            if x else 0
                                                            )
        ec_df['health_fees'] = ec_df['latest_calc'].apply(lambda x:
                                                          float(safe_get_nested(x, 'monthlyCharges.employerCharges.planCharges.categoryTotals.Health.amount', 0))
                                                          if x else 0
                                                          )
        ec_df['placement_fees'] = ec_df['latest_calc'].apply(lambda x:
                                                             float(safe_get_nested(x, 'monthlyCharges.taasCharges.totalFee.value.amount', 0))
                                                             if x else 0
                                                             )

        # Log fee summary for debugging
        non_zero_count = len(ec_df[ec_df['eor_fees'] > 0])
        logger.info(f"Found {non_zero_count} contracts with non-zero EOR fees")
        logger.info(f"Total EOR fees: ${ec_df['eor_fees'].sum():,.2f}")

        # Extract dates and dependent counts
        ec_df['start_date'] = pd.to_datetime(ec_df['role'].apply(
            lambda x: safe_get_nested(x, 'preferredStartDate', None)
        ))
        ec_df['dependent_count'] = ec_df['benefits'].apply(
            lambda x: safe_get_nested(x, 'addOns.DEPENDENT', 0) if x else 0
        )
        ec_df['createdAt'] = pd.to_datetime(ec_df['createdAt'])
        ec_df['updatedAt'] = pd.to_datetime(ec_df['updatedAt'])

        # Create a month string for joining with FX rates
        ec_df['start_month'] = ec_df['start_date'].dt.strftime('%Y-%m-01')

        # 4. Apply FX conversions
        fx_rates_df['fx_date'] = pd.to_datetime(fx_rates_df['fx_date'])
        fx_rates_df['month_key'] = fx_rates_df['fx_date'].dt.strftime('%Y-%m-01')

        # Join on month
        ec_df = ec_df.merge(
            fx_rates_df[['month_key', 'currency', 'rate']],
            left_on=['start_month', 'country'],
            right_on=['month_key', 'currency'],
            how='left'
        )

        # Default rate to 1 for missing values
        ec_df['rate'] = ec_df['rate'].fillna(1).astype(float)

        # Apply FX conversion
        for fee_type in ['eor_fees', 'device_fees', 'hardware_fees', 'software_fees', 'health_fees', 'placement_fees']:
            ec_df[f'{fee_type}_aud'] = ec_df[fee_type] * ec_df['rate']

        # 5. Calculate monthly metrics
        logger.info("Calculating metrics...")

        # Filter active contracts
        active_df = ec_df[
            (ec_df['mapped_status'] == 'Active') &
            (ec_df['start_date'].dt.date <= snapshot_date)
            ].copy()

        # Contracts created/churned in the snapshot month
        snapshot_month = pd.Timestamp(snapshot_date).to_period('M')
        new_df = ec_df[
            (ec_df['mapped_status'] == 'Active') &
            (ec_df['start_date'].dt.to_period('M') == snapshot_month)
            ]

        churned_df = ec_df[
            (ec_df['mapped_status'] == 'Inactive') &
            (ec_df['updatedAt'].dt.to_period('M') == snapshot_month)
            ]

        # Calculate metrics
        metrics = {
            'snapshot_date': snapshot_date,
            'total_active_subscriptions': len(active_df),
            'new_subscriptions': len(new_df),
            'churned_subscriptions': len(churned_df),
            'retention_rate': (1 - len(churned_df) / len(active_df)) * 100 if len(active_df) > 0 else None,
            'churn_rate': (len(churned_df) / len(active_df)) * 100 if len(active_df) > 0 else None,
            'eor_fees_mrr': active_df['eor_fees_aud'].sum(),
            'device_fees_mrr': active_df['device_fees_aud'].sum(),
            'hardware_fees_mrr': active_df['hardware_fees_aud'].sum(),
            'software_fees_mrr': active_df['software_fees_aud'].sum(),
            'health_insurance_mrr': active_df['health_fees_aud'].sum(),
            'placement_fees_mrr': active_df['placement_fees_aud'].sum(),
            'total_customers': active_df['companyId'].nunique(),
            'new_customers_this_month': active_df[
                active_df['createdAt_company'].dt.to_period('M') == snapshot_month
                ]['companyId'].nunique(),
            'avg_days_to_approve': (active_df['updatedAt'] - active_df['createdAt']).dt.days.mean(),
            'plan_change_rate': 0.0,  # Would need historical data to calculate
        }

        # Print a sample of the first few calculations for debugging
        for idx, row in ec_df.head(3).iterrows():
            logger.info(f"Sample calculation for contract {idx}:")
            logger.info(f"  EOR fees: ${row['eor_fees']:,.2f}")
            if isinstance(row['latest_calc'], dict):
                logger.info(f"  Raw calc data: {json.dumps(row['latest_calc'])[:200]}...")

        # Add derived metrics
        metrics['total_mrr'] = (
                metrics['eor_fees_mrr'] +
                metrics['device_fees_mrr'] +
                metrics['hardware_fees_mrr'] +
                metrics['software_fees_mrr'] +
                metrics['health_insurance_mrr']
        )
        metrics['total_arr'] = metrics['total_mrr'] * 12
        metrics['avg_subscription_value'] = (
            metrics['total_mrr'] / metrics['total_active_subscriptions']
            if metrics['total_active_subscriptions'] > 0 else 0
        )

        addon_revenue = (
                metrics['device_fees_mrr'] +
                metrics['hardware_fees_mrr'] +
                metrics['software_fees_mrr'] +
                metrics['health_insurance_mrr']
        )
        metrics['addon_revenue_percentage'] = (
            addon_revenue / metrics['total_mrr'] * 100
            if metrics['total_mrr'] > 0 else 0
        )

        # 6. Calculate add-on counts
        # Extract equipment types from line items
        def has_addon_of_type(items, addon_type):
            if not isinstance(items, list):
                return False
            return any(
                isinstance(item, dict) and
                'label' in item and
                addon_type.lower() in str(item['label']).lower()
                for item in items
            )

        # Path for line items in calculations
        line_items = active_df['latest_calc'].apply(
            lambda x: safe_get_nested(x, 'monthlyCharges.employerCharges.planCharges.lineItems', [])
            if x else []
        )

        metrics['laptops_count'] = sum(
            has_addon_of_type(items, 'laptop') or
            has_addon_of_type(items, 'macbook') or
            has_addon_of_type(items, 'notebook')
            for items in line_items
        )

        metrics['monitors_count'] = sum(
            has_addon_of_type(items, 'monitor') or
            has_addon_of_type(items, 'display') or
            has_addon_of_type(items, 'screen')
            for items in line_items
        )

        metrics['docks_count'] = sum(
            has_addon_of_type(items, 'dock') or
            has_addon_of_type(items, 'docking')
            for items in line_items
        )

        metrics['contracts_with_dependents'] = len(active_df[active_df['dependent_count'] > 0])
        metrics['avg_dependents_per_contract'] = (
            active_df[active_df['dependent_count'] > 0]['dependent_count'].mean()
            if len(active_df[active_df['dependent_count'] > 0]) > 0 else 0
        )

        # 7. Convert to DataFrame for writing to BigQuery
        metrics_df = pd.DataFrame([metrics])

        # 8. Local visualization and validation
        logger.info("Results:")
        for key, value in metrics.items():
            if isinstance(value, (int, float)):
                if 'mrr' in key or 'arr' in key or key == 'avg_subscription_value':
                    logger.info(f"  {key}: ${value:,.2f}")
                elif 'percentage' in key or 'rate' in key:
                    logger.info(f"  {key}: {value:.2f}%")
                else:
                    logger.info(f"  {key}: {value:,}")
            else:
                logger.info(f"  {key}: {value}")

        # 9. Write to BigQuery if not in local test mode
        if not LOCAL_TEST:
            logger.info(f"Writing to BigQuery table: {table_id}")

            # Create the same schema as in your original script
            job_config = bigquery.LoadJobConfig(
                write_disposition="WRITE_APPEND",
                schema=[
                    bigquery.SchemaField("snapshot_date", "DATE"),
                    bigquery.SchemaField("total_active_subscriptions", "INTEGER"),
                    bigquery.SchemaField("new_subscriptions", "INTEGER"),
                    bigquery.SchemaField("churned_subscriptions", "INTEGER"),
                    bigquery.SchemaField("retention_rate", "FLOAT"),
                    bigquery.SchemaField("churn_rate", "FLOAT"),
                    bigquery.SchemaField("eor_fees_mrr", "NUMERIC"),
                    bigquery.SchemaField("device_fees_mrr", "NUMERIC"),
                    bigquery.SchemaField("hardware_fees_mrr", "NUMERIC"),
                    bigquery.SchemaField("software_fees_mrr", "NUMERIC"),
                    bigquery.SchemaField("health_insurance_mrr", "NUMERIC"),
                    bigquery.SchemaField("placement_fees_mrr", "NUMERIC"),
                    bigquery.SchemaField("total_mrr", "NUMERIC"),
                    bigquery.SchemaField("total_arr", "NUMERIC"),
                    bigquery.SchemaField("avg_subscription_value", "NUMERIC"),
                    bigquery.SchemaField("total_customers", "INTEGER"),
                    bigquery.SchemaField("new_customers_this_month", "INTEGER"),
                    bigquery.SchemaField("addon_revenue_percentage", "FLOAT"),
                    bigquery.SchemaField("avg_days_to_approve", "FLOAT"),
                    bigquery.SchemaField("plan_change_rate", "FLOAT"),
                    bigquery.SchemaField("laptops_count", "INTEGER"),
                    bigquery.SchemaField("monitors_count", "INTEGER"),
                    bigquery.SchemaField("docks_count", "INTEGER"),
                    bigquery.SchemaField("contracts_with_dependents", "INTEGER"),
                    bigquery.SchemaField("avg_dependents_per_contract", "FLOAT"),
                ]
            )

            try:
                job = client.load_table_from_dataframe(metrics_df, table_id, job_config=job_config)
                job.result()  # Wait for the job to complete
                logger.info(f"Successfully wrote snapshot for {snapshot_date} to {table_id}")
            except Exception as e:
                logger.error(f"Error writing to BigQuery: {str(e)}")
                raise
        else:
            logger.info("LOCAL_TEST mode: not writing to BigQuery")

        # 10. Save results locally (optional, for further inspection)
        metrics_df.to_csv(f"subscription_snapshot_{snapshot_date}.csv", index=False)
        logger.info(f"Results saved to subscription_snapshot_{snapshot_date}.csv")

        return metrics_df

    except Exception as e:
        logger.error(f"Error in main process: {str(e)}", exc_info=True)
        raise

if __name__ == "__main__":
    main()