"""
Snapshot script for Requisitions dashboard.

Captures monthly metrics:
- Approved requisitions and positions by country
- Rejected requisitions by country
- Open positions by country
- Revenue projections (MRR, ARR, placement fees) in AUD
"""

import pandas as pd
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
from google.cloud import bigquery
import logging
import sys
import argparse
from snapshot_utils import write_snapshot_to_bigquery
from metrics_utils import get_all_countries, get_fx_rates

# Set up argument parser
parser = argparse.ArgumentParser(description='Generate requisition metrics snapshot')
parser.add_argument('--dry-run', action='store_true', help='Validate without writing data')
parser.add_argument('--month', type=str, help='Month to generate snapshot for (YYYY-MM format)')
args = parser.parse_args()

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s', handlers=[logging.StreamHandler(sys.stdout)])
logger = logging.getLogger('requisition-snapshot')

# Initialize BigQuery client
client = bigquery.Client()
table_id = 'outstaffer-app-prod.dashboard_metrics.requisition_snapshots'

# Determine reporting month
if args.month:
    try:
        # Parse the provided month (YYYY-MM)
        year, month = map(int, args.month.split('-'))
        SNAPSHOT_DATE = date(year, month, 1)
        SNAPSHOT_MONTH = args.month
    except ValueError:
        logger.error(f"Invalid month format: {args.month}. Use YYYY-MM format.")
        sys.exit(1)
else:
    # Use current month
    SNAPSHOT_DATE = datetime.now().date()
    SNAPSHOT_MONTH = SNAPSHOT_DATE.strftime('%Y-%m')

logger.info(f"Processing requisition snapshot for: {SNAPSHOT_MONTH}")

def get_fx_rate(currency, fx_rates_df):
    """Helper function to get FX rate for a currency from the rates dataframe"""
    if currency is None or currency == '':
        return 1.0  # Default rate

    matching_rates = fx_rates_df[fx_rates_df['currency'] == currency]
    if matching_rates.empty:
        logger.warning(f"No FX rate found for currency: {currency}, using default 1.0")
        return 1.0

    # Get latest rate for the currency
    latest_rate = matching_rates.sort_values('fx_date', ascending=False).iloc[0]['rate']
    return float(latest_rate)

def convert_to_aud(amount, currency, fx_rates_df):
    """Convert an amount from its currency to AUD using FX rates"""
    if amount is None or pd.isna(amount):
        return 0.0

    rate = get_fx_rate(currency, fx_rates_df)
    return float(amount) * rate

def get_requisition_metrics(snapshot_date, fx_rates_df):
    """
    Fetch requisition metrics from BigQuery.

    Args:
        snapshot_date: Date to generate metrics for
        fx_rates_df: DataFrame with FX rates

    Returns:
        pd.DataFrame: Metrics by country
    """
    # Calculate month bounds
    month_start = snapshot_date.replace(day=1)
    next_month = (month_start + relativedelta(months=1))

    query = f"""
    -- STEP 1: All requisitions (flattened for logic)
    WITH base_requisitions AS (
      SELECT
        r.id AS requisition_id,
        r.companyId,
        r.basicInfo.countryCode,
        r.status,
        r.jobStatus,
        r.submittedAt,
        r.rejectedAt,
        r.basicInfo.numberOfOpenings,
        r.plan.type AS plan_type,
        r.plan.hardwareAddons,
        r.plan.softwareAddons,
        r.plan.membershipAddons,
        r.recruitmentFee.percentageRate.integer AS recruitment_fee_pct
      FROM `outstaffer-app-prod.firestore_exports.requisitions` r
      LEFT JOIN `outstaffer-app-prod.firestore_exports.companies` c
        ON r.companyId = c.id
      WHERE (r.__has_error__ IS NULL OR r.__has_error__ = FALSE)
        -- Exclude demo companies
        AND (c.demoCompany IS NULL OR c.demoCompany = FALSE)
        -- Exclude specific internal company
        AND r.companyId != 'd4c82ebb-1986-4632-9686-8e72c4d07c85'
    ),

    -- STEP 2: Requisitions flattened for add-on pricing
    exploded_addons AS (
      SELECT
        br.*,
        ha.key AS hardware_addon_key,
        ha.quantity AS hardware_quantity,
        sa AS software_addon_key,
        ma AS membership_addon_key
      FROM base_requisitions br
      LEFT JOIN UNNEST(br.hardwareAddons) ha
      LEFT JOIN UNNEST(br.softwareAddons) sa
      LEFT JOIN UNNEST(br.membershipAddons) ma
    ),

    -- STEP 3: Lookup live pricing from plan + add-ons
    priced_requisitions AS (
      SELECT
        e.*,
        pp.value.amount AS plan_amount,
        pp.value.currency AS plan_currency,
        hap.value.amount AS hardware_amount,
        hap.value.currency AS hardware_currency,
        sap.value.amount AS software_amount,
        sap.value.currency AS software_currency,
        map.value.amount AS membership_amount,
        map.value.currency AS membership_currency
      FROM exploded_addons e
      LEFT JOIN `outstaffer-app-prod.dashboard_metrics.plan_pricing` pp
        ON e.plan_type = pp.id
      LEFT JOIN `outstaffer-app-prod.dashboard_metrics.addon_pricing` hap
        ON e.hardware_addon_key = hap.id
      LEFT JOIN `outstaffer-app-prod.dashboard_metrics.addon_pricing` sap
        ON e.software_addon_key = sap.id
      LEFT JOIN `outstaffer-app-prod.dashboard_metrics.addon_pricing` map
        ON e.membership_addon_key = map.id
    ),

    -- STEP 4: Collapse to requisition-level pricing (without currency conversion)
    requisition_pricing AS (
      SELECT
        requisition_id,
        countryCode,
        status,
        jobStatus,
        submittedAt,
        rejectedAt,
        numberOfOpenings,
        recruitment_fee_pct,
        MAX(plan_amount) AS plan_amount,
        MAX(plan_currency) AS plan_currency,
        SUM(COALESCE(hardware_amount * COALESCE(hardware_quantity, 1), 0)) AS hardware_amount,
        MAX(hardware_currency) AS hardware_currency,
        SUM(COALESCE(software_amount, 0)) AS software_amount,
        MAX(software_currency) AS software_currency,
        SUM(COALESCE(membership_amount, 0)) AS membership_amount,
        MAX(membership_currency) AS membership_currency
      FROM priced_requisitions
      GROUP BY requisition_id, countryCode, status, jobStatus, submittedAt, 
               rejectedAt, numberOfOpenings, recruitment_fee_pct
    ),

    -- STEP 5: Aggregate by country (counts only, no currency conversion)
    country_summary AS (
      SELECT
        countryCode,
        -- Approved this month (matching the snapshot date parameter)
        COUNTIF(status = 'APPROVED' 
                AND EXTRACT(YEAR FROM submittedAt) = {snapshot_date.year} 
                AND EXTRACT(MONTH FROM submittedAt) = {snapshot_date.month}) AS approved_requisitions_count,
        -- Approved positions this month
        SUM(IF(status = 'APPROVED' 
               AND EXTRACT(YEAR FROM submittedAt) = {snapshot_date.year} 
               AND EXTRACT(MONTH FROM submittedAt) = {snapshot_date.month}, 
               CAST(numberOfOpenings AS INT64), 0)) AS approved_positions_count,
        -- Rejected this month
        COUNTIF(status = 'REJECTED' 
                AND EXTRACT(YEAR FROM rejectedAt) = {snapshot_date.year} 
                AND EXTRACT(MONTH FROM rejectedAt) = {snapshot_date.month}) AS rejected_requisitions_count,
        -- Current open positions
        SUM(IF(status = 'APPROVED' AND jobStatus = 'Open', 
               CAST(numberOfOpenings AS INT64), 0)) AS open_positions_count
      FROM requisition_pricing
      GROUP BY countryCode
    )

    -- FINAL OUTPUT (Pricing data joined with counts)
    SELECT
      cs.countryCode,
      cs.approved_requisitions_count,
      cs.approved_positions_count,
      cs.rejected_requisitions_count,
      cs.open_positions_count,
      -- Return raw pricing data for Python-side conversion
      ARRAY_AGG(
        STRUCT(
          rp.requisition_id,
          rp.status,
          rp.plan_amount, 
          rp.plan_currency,
          rp.hardware_amount, 
          rp.hardware_currency,
          rp.software_amount, 
          rp.software_currency,
          rp.membership_amount, 
          rp.membership_currency,
          rp.recruitment_fee_pct
        )
      ) AS pricing_data
    FROM country_summary cs
    LEFT JOIN requisition_pricing rp
      ON cs.countryCode = rp.countryCode
      AND rp.status = 'APPROVED'  -- Only include approved requisitions in revenue calculation
    GROUP BY 
      cs.countryCode,
      cs.approved_requisitions_count,
      cs.approved_positions_count,
      cs.rejected_requisitions_count,
      cs.open_positions_count
    ORDER BY cs.countryCode
    """

    try:
        df = client.query(query).to_dataframe()
        logger.info(f"Retrieved data for {len(df)} countries")
        return df
    except Exception as e:
        logger.error(f"Error querying requisition metrics: {str(e)}")
        raise

def process_pricing_data(df, fx_rates_df):
    """Process the nested pricing data and calculate revenue metrics in AUD"""
    result = []

    for _, row in df.iterrows():
        country_code = row['countryCode']
        pricing_data = row['pricing_data']

        # Initialize revenue values
        mrr_aud = 0.0
        placement_fees_aud = 0.0

        # Process each requisition's pricing data
        if pricing_data:
            for item in pricing_data:
                if item and item.get('status') == 'APPROVED':
                    # MRR components
                    plan_aud = convert_to_aud(item.get('plan_amount'), item.get('plan_currency'), fx_rates_df)
                    hardware_aud = convert_to_aud(item.get('hardware_amount'), item.get('hardware_currency'), fx_rates_df)
                    software_aud = convert_to_aud(item.get('software_amount'), item.get('software_currency'), fx_rates_df)
                    membership_aud = convert_to_aud(item.get('membership_amount'), item.get('membership_currency'), fx_rates_df)

                    # Calculate total MRR
                    req_mrr = plan_aud + hardware_aud + software_aud + membership_aud
                    mrr_aud += req_mrr

                    # Calculate placement fees (assuming average $50K USD salary)
                    recruitment_fee_pct = item.get('recruitment_fee_pct')
                    if recruitment_fee_pct:
                        # Convert USD to AUD for the base salary, then apply percentage
                        usd_rate = get_fx_rate('USD', fx_rates_df)
                        salary_aud = 50000 * usd_rate  # $50K USD in AUD
                        placement_fee = (float(recruitment_fee_pct) / 100) * salary_aud
                        placement_fees_aud += placement_fee

        # ARR is just MRR * 12
        arr_aud = mrr_aud * 12

        # Create result row
        result_row = {
            'countryCode': country_code,
            'approved_requisitions_count': row['approved_requisitions_count'],
            'approved_positions_count': row['approved_positions_count'],
            'rejected_requisitions_count': row['rejected_requisitions_count'],
            'open_positions_count': row['open_positions_count'],
            'mrr_aud': mrr_aud,
            'arr_aud': arr_aud,
            'placement_fees_aud': placement_fees_aud
        }
        result.append(result_row)

    return pd.DataFrame(result)

def main():
    try:
        # Load FX rates
        fx_rates_df = get_fx_rates('AUD')
        logger.info(f"Loaded FX rates for {len(fx_rates_df)} currencies")

        # Get all countries
        countries = get_all_countries()
        countries_df = pd.DataFrame(countries)
        logger.info(f"Loaded {len(countries_df)} countries")

        # Get metrics for countries with requisition activity
        raw_metrics_df = get_requisition_metrics(SNAPSHOT_DATE, fx_rates_df)

        # Process pricing data to calculate MRR/ARR in AUD
        metrics_df = process_pricing_data(raw_metrics_df, fx_rates_df)

        # Combine with all countries using left join
        result_df = countries_df.merge(
            metrics_df,
            how='left',
            left_on='countryCode',
            right_on='countryCode'
        )

        # Fill NaN values with zeros for numeric columns
        numeric_cols = [
            'approved_requisitions_count',
            'approved_positions_count',
            'rejected_requisitions_count',
            'open_positions_count',
            'arr_aud',
            'mrr_aud',
            'placement_fees_aud'
        ]
        result_df[numeric_cols] = result_df[numeric_cols].fillna(0)

        # Add snapshot month column
        result_df['snapshot_month'] = SNAPSHOT_MONTH

        # Reorder columns
        result_df = result_df[[
            'snapshot_month',
            'countryCode',
            'name',  # country name
            'approved_requisitions_count',
            'approved_positions_count',
            'rejected_requisitions_count',
            'open_positions_count',
            'arr_aud',
            'mrr_aud',
            'placement_fees_aud'
        ]]

        # Rename columns to match schema
        result_df = result_df.rename(columns={'name': 'country_name'})

        # Define schema for BigQuery
        schema = [
            bigquery.SchemaField("snapshot_month", "STRING"),
            bigquery.SchemaField("countryCode", "STRING"),
            bigquery.SchemaField("country_name", "STRING"),
            bigquery.SchemaField("approved_requisitions_count", "INTEGER"),
            bigquery.SchemaField("approved_positions_count", "INTEGER"),
            bigquery.SchemaField("rejected_requisitions_count", "INTEGER"),
            bigquery.SchemaField("open_positions_count", "INTEGER"),
            bigquery.SchemaField("arr_aud", "FLOAT"),
            bigquery.SchemaField("mrr_aud", "FLOAT"),
            bigquery.SchemaField("placement_fees_aud", "FLOAT")
        ]

        # Write to BigQuery
        success = write_snapshot_to_bigquery(
            metrics_df=result_df,
            table_id=table_id,
            schema=schema,
            dry_run=args.dry_run
        )

        if not success:
            logger.error("Failed to write requisition metrics to BigQuery")
            sys.exit(1)

        # Generate summary
        total_countries = len(result_df)
        countries_with_reqs = len(result_df[result_df['approved_requisitions_count'] > 0])
        total_approved = result_df['approved_requisitions_count'].sum()
        total_positions = result_df['approved_positions_count'].sum()
        total_mrr = result_df['mrr_aud'].sum()

        logger.info(f"Snapshot summary for {SNAPSHOT_MONTH}:")
        logger.info(f"  Total countries: {total_countries}")
        logger.info(f"  Countries with approved requisitions: {countries_with_reqs}")
        logger.info(f"  Total approved requisitions: {total_approved}")
        logger.info(f"  Total approved positions: {total_positions}")
        logger.info(f"  Total projected MRR: AUD ${total_mrr:,.2f}")

        # Save to CSV for reference
        csv_filename = f"requisition_snapshot_{SNAPSHOT_MONTH}.csv"
        result_df.to_csv(csv_filename, index=False)
        logger.info(f"Saved metrics to {csv_filename}")

        return result_df

    except Exception as e:
        logger.error(f"Error in requisition snapshot generation: {str(e)}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()