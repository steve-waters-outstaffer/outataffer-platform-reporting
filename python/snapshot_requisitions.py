# python/snapshot_requisitions.py
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
        year, month = map(int, args.month.split('-'))
        SNAPSHOT_DATE = date(year, month, 1)
    except ValueError:
        logger.error(f"Invalid month format: {args.month}. Use YYYY-MM format.")
        sys.exit(1)
else:
    SNAPSHOT_DATE = datetime.now().date()

SNAPSHOT_MONTH = SNAPSHOT_DATE.strftime('%Y-%m')
logger.info(f"Processing requisition snapshot for: {SNAPSHOT_MONTH}")

def get_fx_rate(currency, fx_rates_df):
    if currency is None or currency == '' or pd.isna(currency):
        return 1.0
    rate_row = fx_rates_df[fx_rates_df['currency'] == currency]
    if rate_row.empty:
        logger.warning(f"No FX rate for {currency}, using 1.0")
        return 1.0
    return float(rate_row['rate'].iloc[0])

def convert_to_aud(amount, currency, fx_rates_df):
    if amount is None or pd.isna(amount):
        return 0.0
    rate = get_fx_rate(currency, fx_rates_df)
    return float(amount) * rate

def get_requisition_data(snapshot_date):
    month_start = snapshot_date.replace(day=1)
    next_month = (month_start + relativedelta(months=1))

    query = f"""
    WITH base_requisitions AS (
      SELECT
        r.id AS requisition_id,
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
        r.recruitmentFee.percentageRate.integer AS recruitment_fee_pct,
        (SELECT value.amount FROM UNNEST(r.salary) WHERE value.period = 'YEAR' and value.currency is not null limit 1) as yearly_salary,
        (SELECT value.currency FROM UNNEST(r.salary) WHERE value.period = 'YEAR' and value.currency is not null limit 1) as salary_currency
      FROM `outstaffer-app-prod.firestore_exports.requisitions` r
      JOIN `outstaffer-app-prod.firestore_exports.companies` c ON r.companyId = c.id
      WHERE (r.__has_error__ IS NULL OR r.__has_error__ = FALSE)
        AND (c.demoCompany IS NULL OR c.demoCompany = FALSE)
        AND r.companyId != 'd4c82ebb-1986-4632-9686-8e72c4d07c85'
    ),
    addon_pricing AS (
        SELECT id, value.amount, value.currency FROM `outstaffer-app-prod.dashboard_metrics.addon_pricing`
    ),
    plan_pricing AS (
        SELECT id, value.amount, value.currency FROM `outstaffer-app-prod.dashboard_metrics.plan_pricing`
    )
    SELECT
      br.*,
      pp.amount AS plan_amount,
      pp.currency AS plan_currency,
      (SELECT SUM(ap.amount) FROM UNNEST(br.hardwareAddons) AS ha JOIN addon_pricing AS ap ON ap.id = ha.key) AS hardware_amount,
      (SELECT STRING_AGG(DISTINCT ap.currency) FROM UNNEST(br.hardwareAddons) AS ha JOIN addon_pricing AS ap ON ap.id = ha.key) AS hardware_currency,
      (SELECT SUM(ap.amount) FROM UNNEST(br.softwareAddons) AS sa JOIN addon_pricing AS ap ON ap.id = sa) AS software_amount,
      (SELECT STRING_AGG(DISTINCT ap.currency) FROM UNNEST(br.softwareAddons) AS sa JOIN addon_pricing AS ap ON ap.id = sa) AS software_currency,
      (SELECT SUM(ap.amount) FROM UNNEST(br.membershipAddons) AS ma JOIN addon_pricing AS ap ON ap.id = ma) AS membership_amount,
      (SELECT STRING_AGG(DISTINCT ap.currency) FROM UNNEST(br.membershipAddons) AS ma JOIN addon_pricing AS ap ON ap.id = ma) AS membership_currency
    FROM base_requisitions br
    LEFT JOIN plan_pricing pp ON br.plan_type = pp.id
    """
    try:
        df = client.query(query).to_dataframe()
        logger.info(f"Retrieved data for {len(df)} requisitions")
        return df
    except Exception as e:
        logger.error(f"Error querying requisition data: {str(e)}")
        raise

def main():
    try:
        fx_rates_df = get_fx_rates('AUD')
        all_countries_df = pd.DataFrame(get_all_countries())
        requisition_data_df = get_requisition_data(SNAPSHOT_DATE)

        # Calculate MRR and Placement Fees in original currency
        requisition_data_df['mrr'] = requisition_data_df[['plan_amount', 'hardware_amount', 'software_amount', 'membership_amount']].sum(axis=1)
        requisition_data_df['placement_fee'] = requisition_data_df['yearly_salary'] * (requisition_data_df['recruitment_fee_pct'] / 100)

        # Convert to AUD
        requisition_data_df['mrr_aud'] = requisition_data_df.apply(lambda row: convert_to_aud(row['mrr'], row['plan_currency'], fx_rates_df), axis=1)
        requisition_data_df['placement_fees_aud'] = requisition_data_df.apply(lambda row: convert_to_aud(row['placement_fee'], row['salary_currency'], fx_rates_df), axis=1)
        requisition_data_df['arr_aud'] = requisition_data_df['mrr_aud'] * 12

        month_start_dt = datetime.combine(SNAPSHOT_DATE.replace(day=1), datetime.min.time())
        next_month_start_dt = month_start_dt + relativedelta(months=1)

        requisition_data_df['submittedAt'] = pd.to_datetime(requisition_data_df['submittedAt'], errors='coerce', utc=True)
        requisition_data_df['rejectedAt'] = pd.to_datetime(requisition_data_df['rejectedAt'], errors='coerce', utc=True)
        month_start_dt = pd.to_datetime(month_start_dt, utc=True)
        next_month_start_dt = pd.to_datetime(next_month_start_dt, utc=True)

        # Aggregate metrics by country
        country_agg = requisition_data_df.groupby('countryCode').apply(lambda x: pd.Series({
            'approved_requisitions_count': x[(x['status'] == 'APPROVED') & (x['submittedAt'] >= month_start_dt) & (x['submittedAt'] < next_month_start_dt)].shape[0],
            'approved_positions_count': x[(x['status'] == 'APPROVED') & (x['submittedAt'] >= month_start_dt) & (x['submittedAt'] < next_month_start_dt)]['numberOfOpenings'].sum(),
            'rejected_requisitions_count': x[(x['status'] == 'REJECTED') & (x['rejectedAt'] >= month_start_dt) & (x['rejectedAt'] < next_month_start_dt)].shape[0],
            'open_positions_count': x[(x['status'] == 'APPROVED') & (x['jobStatus'] == 'Open')]['numberOfOpenings'].sum(),
            'mrr_aud': x[x['status'] == 'APPROVED']['mrr_aud'].sum(),
            'arr_aud': x[x['status'] == 'APPROVED']['arr_aud'].sum(),
            'placement_fees_aud': x[(x['status'] == 'APPROVED') & (x['submittedAt'] >= month_start_dt) & (x['submittedAt'] < next_month_start_dt)]['placement_fees_aud'].sum()
        })).reset_index()

        # Merge with all countries to ensure all are present
        merged_df = all_countries_df.merge(country_agg, how='left', on='countryCode')
        merged_df = merged_df.fillna(0)

        # Transform to long format for BigQuery
        metrics_list = []
        for _, row in merged_df.iterrows():
            country_code = row['countryCode']
            country_name = row['name']
            for metric in ['approved_requisitions', 'approved_positions', 'rejected_requisitions', 'open_positions']:
                metrics_list.append({'metric_type': metric, 'id': country_code, 'label': country_name, 'count': row[f'{metric}_count'], 'value_aud': None, 'percentage': None})
            for metric in ['mrr_aud', 'arr_aud', 'placement_fees_aud']:
                metrics_list.append({'metric_type': metric, 'id': country_code, 'label': country_name, 'count': None, 'value_aud': row[metric], 'percentage': None})

        final_df = pd.DataFrame(metrics_list)
        final_df['snapshot_date'] = SNAPSHOT_DATE
        final_df['count'] = final_df['count'].astype(pd.Int64Dtype())

        schema = [
            bigquery.SchemaField("snapshot_date", "DATE"),
            bigquery.SchemaField("metric_type", "STRING"),
            bigquery.SchemaField("id", "STRING"),
            bigquery.SchemaField("label", "STRING"),
            bigquery.SchemaField("count", "INTEGER"),
            bigquery.SchemaField("value_aud", "FLOAT"),
            bigquery.SchemaField("percentage", "FLOAT")
        ]

        expected_columns = [field.name for field in schema]
        final_df = final_df[expected_columns]

        success = write_snapshot_to_bigquery(
            metrics_df=final_df,
            table_id=table_id,
            schema=schema,
            dry_run=args.dry_run
        )

        if not success:
            logger.error("Failed to write requisition metrics to BigQuery")
            sys.exit(1)

        logger.info(f"Successfully processed and wrote {len(final_df)} metric rows to BigQuery.")

    except Exception as e:
        logger.error(f"Error in requisition snapshot generation: {str(e)}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()

