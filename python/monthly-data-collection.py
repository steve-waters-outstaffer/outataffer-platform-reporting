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

def main():
    try:
        # 1. Define reporting date (today's date for point-in-time snapshot)
        snapshot_date = datetime.now().date()
        logger.info(f"Processing snapshot for: {snapshot_date}")

        # 2. Load company data, status mapping, and FX rates
        logger.info("Loading reference data from BigQuery...")

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
            companies_df = client.query(query_companies).to_dataframe()
            logger.info(f"Loaded {len(companies_df)} companies")

            status_mapping_df = client.query(query_status_mapping).to_dataframe()
            logger.info(f"Loaded {len(status_mapping_df)} status mappings")

            fx_rates_df = client.query(query_fx_rates).to_dataframe()
            logger.info(f"Loaded {len(fx_rates_df)} FX rates")
        except Exception as e:
            logger.error(f"Error loading reference data: {str(e)}")
            raise

        # 3. Load contract data with calculated fields using UNNEST approach
        logger.info("Loading contract data with calculations...")

        # Updated query using UNNEST for correct calculation data access
        query_contracts_with_calculations = """
        SELECT 
            ec.id AS contract_id,
            ec.status,
            ec.companyId,
            ec.employmentLocation.country AS country,
            ec.createdAt,
            ec.updatedAt,
            ec.role.preferredStartDate AS start_date,
            IFNULL(ec.benefits.addOns.DEPENDENT, 0) AS dependent_count,
            ec.benefits.healthInsurance AS health_plan,
            sm.mapped_status,
            
            -- Latest calculation data
            -- Get the most recent calculation for each contract
            ARRAY(
              SELECT AS STRUCT * 
              FROM UNNEST(ec.calculations) AS calc
              ORDER BY calc.calculatedAt DESC
              LIMIT 1
            )[OFFSET(0)] AS latest_calc,
            
            -- Extract fee values directly using correct paths
            CAST(IFNULL((
              SELECT calc.monthlyCharges.employerCharges.planCharges.categoryTotals.EOR.amount
              FROM UNNEST(ec.calculations) AS calc
              ORDER BY calc.calculatedAt DESC
              LIMIT 1
            ), '0') AS FLOAT64) AS eor_fees,
            
            CAST(IFNULL((
              SELECT calc.monthlyCharges.employerCharges.planCharges.categoryTotals.Device.amount
              FROM UNNEST(ec.calculations) AS calc
              ORDER BY calc.calculatedAt DESC
              LIMIT 1
            ), '0') AS FLOAT64) AS device_fees,
            
            CAST(IFNULL((
              SELECT calc.monthlyCharges.employerCharges.planCharges.categoryTotals.Hardware.amount
              FROM UNNEST(ec.calculations) AS calc
              ORDER BY calc.calculatedAt DESC
              LIMIT 1
            ), '0') AS FLOAT64) AS hardware_fees,
            
            CAST(IFNULL((
              SELECT calc.monthlyCharges.employerCharges.planCharges.categoryTotals.Software.amount
              FROM UNNEST(ec.calculations) AS calc
              ORDER BY calc.calculatedAt DESC
              LIMIT 1
            ), '0') AS FLOAT64) AS software_fees,
            
            CAST(IFNULL((
              SELECT calc.monthlyCharges.employerCharges.healthCharges.total.amount
              FROM UNNEST(ec.calculations) AS calc
              ORDER BY calc.calculatedAt DESC
              LIMIT 1
            ), '0') AS FLOAT64) AS health_fees,
            
            CAST(IFNULL((
              SELECT calc.monthlyCharges.taasCharges.totalFee.value.amount
              FROM UNNEST(ec.calculations) AS calc
              ORDER BY calc.calculatedAt DESC
              LIMIT 1
            ), '0') AS FLOAT64) AS placement_fees
            
        FROM `outstaffer-app-prod.firestore_exports.employee_contracts` ec
        LEFT JOIN `outstaffer-app-prod.lookup_tables.contract_status_mapping` sm
          ON ec.status = sm.contract_status
        WHERE (ec.__has_error__ IS NULL OR ec.__has_error__ = FALSE)
        AND ec.calculations IS NOT NULL AND ARRAY_LENGTH(ec.calculations) > 0
        """

        try:
            contracts_df = client.query(query_contracts_with_calculations).to_dataframe()
            logger.info(f"Loaded {len(contracts_df)} contracts with calculation data")

            # Log a sample of fee values to verify extraction
            sample_contracts = contracts_df.head(5)
            for idx, row in sample_contracts.iterrows():
                logger.info(f"Contract {row['contract_id']} fees: EOR=${row['eor_fees']:.2f}, Device=${row['device_fees']:.2f}, Health=${row['health_fees']:.2f}")

        except Exception as e:
            logger.error(f"Error loading contract data: {str(e)}")
            raise

        # 4. Join with companies data
        contracts_df = contracts_df.merge(
            companies_df[['id', 'companyName', 'createdAt']],
            left_on='companyId',
            right_on='id',
            how='left',
            suffixes=('', '_company')
        )

        # Convert dates
        contracts_df['createdAt'] = pd.to_datetime(contracts_df['createdAt'])
        contracts_df['updatedAt'] = pd.to_datetime(contracts_df['updatedAt'])
        contracts_df['start_date'] = pd.to_datetime(contracts_df['start_date'])
        contracts_df['createdAt_company'] = pd.to_datetime(contracts_df['createdAt_company'])

        # Convert timezone-aware datetime columns to timezone-naive right after loading dates
        # This ensures all datetime operations will be consistent
        for date_col in ['start_date', 'createdAt', 'updatedAt', 'createdAt_company']:
            if date_col in contracts_df.columns:
                contracts_df[date_col] = contracts_df[date_col].dt.tz_localize(None)

        # Create a month string for joining with FX rates
        contracts_df['start_month'] = contracts_df['start_date'].dt.strftime('%Y-%m-01')

        # 5. Apply FX conversions
        fx_rates_df['fx_date'] = pd.to_datetime(fx_rates_df['fx_date'])
        fx_rates_df['month_key'] = fx_rates_df['fx_date'].dt.strftime('%Y-%m-01')

        # Join on month and country
        contracts_df = contracts_df.merge(
            fx_rates_df[['month_key', 'currency', 'rate']],
            left_on=['start_month', 'country'],
            right_on=['month_key', 'currency'],
            how='left'
        )

        # Default rate to 1 for missing values
        contracts_df['rate'] = contracts_df['rate'].fillna(1).astype(float)

        # Apply FX conversion
        for fee_type in ['eor_fees', 'device_fees', 'hardware_fees', 'software_fees', 'health_fees', 'placement_fees']:
            contracts_df[f'{fee_type}_aud'] = contracts_df[fee_type] * contracts_df['rate']

        # 6. Calculate monthly metrics
        logger.info("Calculating metrics...")

        # Filter active contracts and categorize as 'active', 'offboarding', or 'approved_not_started'
        active_df = contracts_df[contracts_df['mapped_status'] == 'Active'].copy()

        # Add contract status categorization
        active_df['contract_category'] = 'active'

        # Identify contracts in offboarding
        mask_offboarding = (active_df['status'] == 'OFFBOARDING')
        active_df.loc[mask_offboarding, 'contract_category'] = 'offboarding'

        # Identify future start dates (not started yet)
        mask_future_start = (active_df['start_date'].dt.date > snapshot_date)
        active_df.loc[mask_future_start, 'contract_category'] = 'approved_not_started'

        # Current active contracts (already started, not offboarding)
        current_active_df = active_df[active_df['contract_category'] == 'active']

        # Approved but not yet started
        approved_not_started_df = active_df[active_df['contract_category'] == 'approved_not_started']

        # In offboarding process
        offboarding_df = active_df[active_df['contract_category'] == 'offboarding']

        # Calculate days from approval to start for all contracts
        active_df['days_from_approval_to_start'] = (active_df['start_date'] - active_df['createdAt']).dt.days

        # For approved_not_started, calculate days until start
        if len(approved_not_started_df) > 0:
            approved_not_started_df['days_until_start'] = (approved_not_started_df['start_date'] - pd.Timestamp(snapshot_date).tz_localize(None)).dt.days

        # Contracts created/churned in the snapshot month
        # Ensure snapshot dates are timezone-naive for consistent comparison
        snapshot_month_start = pd.Timestamp(snapshot_date.replace(day=1)).tz_localize(None)
        next_month = (snapshot_month_start + pd.DateOffset(months=1))

        new_df = contracts_df[
            (contracts_df['mapped_status'] == 'Active') &
            (contracts_df['start_date'] >= snapshot_month_start) &
            (contracts_df['start_date'] < next_month)
            ]

        churned_df = contracts_df[
            (contracts_df['mapped_status'] == 'Inactive') &
            (contracts_df['updatedAt'] >= snapshot_month_start) &
            (contracts_df['updatedAt'] < next_month)
            ]

        # Calculate metrics
        metrics = {
            'snapshot_date': snapshot_date,
            'total_active_subscriptions': len(current_active_df),
            'approved_not_started': len(approved_not_started_df),
            'offboarding_contracts': len(offboarding_df),
            'total_contracts': len(active_df),  # Active, approved_not_started, and offboarding
            'new_subscriptions': len(new_df),
            'churned_subscriptions': len(churned_df),
            'retention_rate': (1 - len(churned_df) / len(current_active_df)) * 100 if len(current_active_df) > 0 else None,
            'churn_rate': (len(churned_df) / len(current_active_df)) * 100 if len(current_active_df) > 0 else None,
            'eor_fees_mrr': current_active_df['eor_fees_aud'].sum(),
            'device_fees_mrr': current_active_df['device_fees_aud'].sum(),
            'hardware_fees_mrr': current_active_df['hardware_fees_aud'].sum(),
            'software_fees_mrr': current_active_df['software_fees_aud'].sum(),
            'health_insurance_mrr': current_active_df['health_fees_aud'].sum(),
            'placement_fees_mrr': current_active_df['placement_fees_aud'].sum(),
            'total_customers': current_active_df['companyId'].nunique(),
            'new_customers_this_month': active_df[
                (active_df['createdAt_company'] >= snapshot_month_start) &
                (active_df['createdAt_company'] < next_month)
                ]['companyId'].nunique(),
            'avg_days_from_approval_to_start': active_df['days_from_approval_to_start'].mean(),
            'avg_days_until_start': approved_not_started_df['days_until_start'].mean() if len(approved_not_started_df) > 0 else 0,
            'plan_change_rate': 0.0,  # Would need historical data to calculate
        }

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

        # 7. Calculate add-on counts
        metrics['laptops_count'] = current_active_df[current_active_df['device_fees'] > 0].shape[0]
        metrics['monitors_count'] = 0  # Would need more detailed line item analysis
        metrics['docks_count'] = 0     # Would need more detailed line item analysis

        metrics['contracts_with_dependents'] = len(current_active_df[current_active_df['dependent_count'] > 0])
        metrics['avg_dependents_per_contract'] = (
            current_active_df[current_active_df['dependent_count'] > 0]['dependent_count'].mean()
            if len(current_active_df[current_active_df['dependent_count'] > 0]) > 0 else 0
        )

        # 8. Convert to DataFrame for writing to BigQuery
        metrics_df = pd.DataFrame([metrics])

        # 9. Local visualization and validation
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

        # 10. Write to BigQuery if not in local test mode
        if not LOCAL_TEST:
            logger.info(f"Writing to BigQuery table: {table_id}")

            # Define the schema
            job_config = bigquery.LoadJobConfig(
                write_disposition="WRITE_APPEND",
                schema=[
                    bigquery.SchemaField("snapshot_date", "DATE"),
                    bigquery.SchemaField("total_active_subscriptions", "INTEGER"),
                    bigquery.SchemaField("approved_not_started", "INTEGER"),
                    bigquery.SchemaField("offboarding_contracts", "INTEGER"),
                    bigquery.SchemaField("total_contracts", "INTEGER"),
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
                    bigquery.SchemaField("avg_days_from_approval_to_start", "FLOAT"),
                    bigquery.SchemaField("avg_days_until_start", "FLOAT"),
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

        # 11. Save results locally (optional, for further inspection)
        metrics_df.to_csv(f"subscription_snapshot_{snapshot_date}.csv", index=False)
        logger.info(f"Results saved to subscription_snapshot_{snapshot_date}.csv")

        return metrics_df

    except Exception as e:
        logger.error(f"Error in main process: {str(e)}", exc_info=True)
        raise

if __name__ == "__main__":
    main()