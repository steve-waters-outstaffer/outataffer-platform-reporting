# metrics_utils.py
from google.cloud import bigquery
import pandas as pd
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# Centralized BigQuery client
client = bigquery.Client()

def get_all_contracts(snapshot_date: datetime.date = None) -> pd.DataFrame:
    """
    Fetch all contracts from BigQuery.

    Args:
        snapshot_date: Date for context (defaults to today, unused here)

    Returns:
        pd.DataFrame: All contracts with contract_id, companyId, country
    """
    if snapshot_date is None:
        snapshot_date = datetime.now().date()

    query = """
    SELECT 
        ec.id AS contract_id,
        ec.companyId,
        ec.employmentLocation.country AS country,
        ec.createdAt,
        ec.updatedAt,
        ec.role.preferredStartDate AS start_date
    FROM `outstaffer-app-prod.firestore_exports.employee_contracts` ec
    LEFT JOIN `outstaffer-app-prod.lookup_tables.contract_status_mapping` sm
      ON ec.status = sm.contract_status
    LEFT JOIN `outstaffer-app-prod.firestore_exports.companies` c
      ON ec.companyId = c.id
    WHERE (ec.__has_error__ IS NULL OR ec.__has_error__ = FALSE)
      AND (c.demoCompany IS NULL OR c.demoCompany = FALSE)
      AND ec.companyId NOT IN ('d4c82ebb-1986-4632-9686-8e72c4d07c85', 'b2affbf5-3653-429a-a7b9-bfc4e25fec7c')
    """

    df = client.query(query).to_dataframe()
    # Convert date columns
    if 'createdAt' in df.columns:
        df['createdAt'] = pd.to_datetime(df['createdAt']).dt.tz_localize(None)
    if 'updatedAt' in df.columns:
        df['updatedAt'] = pd.to_datetime(df['updatedAt']).dt.tz_localize(None)

    logger.info(f"Loaded {len(df)} contracts")
    return df

def get_active_contracts(snapshot_date: datetime.date = None) -> pd.DataFrame:
    """
    Fetch active contracts (mapped_status = 'Active', started by snapshot_date).

    Args:
        snapshot_date: Date for filtering (defaults to today)

    Returns:
        pd.DataFrame: Active contracts with contract_id, companyId, country
    """
    if snapshot_date is None:
        snapshot_date = datetime.now().date()

    query = f"""
    SELECT 
        ec.id AS contract_id,
        ec.companyId,
        ec.employmentLocation.country AS country,
        ec.createdAt,
        ec.updatedAt,
        ec.role.preferredStartDate AS start_date
    FROM `outstaffer-app-prod.firestore_exports.employee_contracts` ec
    LEFT JOIN `outstaffer-app-prod.lookup_tables.contract_status_mapping` sm
      ON ec.status = sm.contract_status
    LEFT JOIN `outstaffer-app-prod.firestore_exports.companies` c
      ON ec.companyId = c.id
    WHERE sm.mapped_status = 'Active'
      AND ec.role.preferredStartDate <= '{snapshot_date}'
      AND (ec.__has_error__ IS NULL OR ec.__has_error__ = FALSE)
      AND (c.demoCompany IS NULL OR c.demoCompany = FALSE)
      AND ec.companyId NOT IN ('d4c82ebb-1986-4632-9686-8e72c4d07c85', 'b2affbf5-3653-429a-a7b9-bfc4e25fec7c')
    """

    df = client.query(query).to_dataframe()
    # Convert date columns
    if 'createdAt' in df.columns:
        df['createdAt'] = pd.to_datetime(df['createdAt']).dt.tz_localize(None)
    if 'updatedAt' in df.columns:
        df['updatedAt'] = pd.to_datetime(df['updatedAt']).dt.tz_localize(None)

    logger.info(f"Loaded {len(df)} active contracts")
    return df

def get_offboarding_contracts(snapshot_date: datetime.date = None) -> pd.DataFrame:
    """
    Fetch active contracts in offboarding status.

    Args:
        snapshot_date: Date for filtering (defaults to today)

    Returns:
        pd.DataFrame: Offboarding contracts with contract_id, companyId, country
    """
    if snapshot_date is None:
        snapshot_date = datetime.now().date()

    query = f"""
    SELECT 
        ec.id AS contract_id,
        ec.companyId,
        ec.employmentLocation.country AS country,
        ec.createdAt,
        ec.updatedAt,
        ec.role.preferredStartDate AS start_date
    FROM `outstaffer-app-prod.firestore_exports.employee_contracts` ec
    LEFT JOIN `outstaffer-app-prod.lookup_tables.contract_status_mapping` sm
      ON ec.status = sm.contract_status
    LEFT JOIN `outstaffer-app-prod.firestore_exports.companies` c
      ON ec.companyId = c.id
    WHERE sm.mapped_status = 'Active'
      AND ec.status = 'OFFBOARDING'
      AND ec.role.preferredStartDate <= '{snapshot_date}'
      AND (ec.__has_error__ IS NULL OR ec.__has_error__ = FALSE)
      AND (c.demoCompany IS NULL OR c.demoCompany = FALSE)
      AND ec.companyId NOT IN ('d4c82ebb-1986-4632-9686-8e72c4d07c85', 'b2affbf5-3653-429a-a7b9-bfc4e25fec7c')
    """

    df = client.query(query).to_dataframe()
    # Convert date columns
    if 'createdAt' in df.columns:
        df['createdAt'] = pd.to_datetime(df['createdAt']).dt.tz_localize(None)
    if 'updatedAt' in df.columns:
        df['updatedAt'] = pd.to_datetime(df['updatedAt']).dt.tz_localize(None)

    logger.info(f"Loaded {len(df)} offboarding contracts")
    return df

def get_inactive_contracts(snapshot_date: datetime.date = None) -> pd.DataFrame:
    """
    Fetch inactive contracts (mapped_status = 'Inactive').

    Args:
        snapshot_date: Date for context (defaults to today)

    Returns:
        pd.DataFrame: Inactive contracts with contract_id, companyId, country
    """
    if snapshot_date is None:
        snapshot_date = datetime.now().date()

    query = """
    SELECT 
        ec.id AS contract_id,
        ec.companyId,
        ec.employmentLocation.country AS country,
        ec.createdAt,
        ec.updatedAt,
        ec.role.preferredStartDate AS start_date
    FROM `outstaffer-app-prod.firestore_exports.employee_contracts` ec
    LEFT JOIN `outstaffer-app-prod.lookup_tables.contract_status_mapping` sm
      ON ec.status = sm.contract_status
    LEFT JOIN `outstaffer-app-prod.firestore_exports.companies` c
      ON ec.companyId = c.id
    WHERE sm.mapped_status = 'Inactive'
      AND (ec.__has_error__ IS NULL OR ec.__has_error__ = FALSE)
      AND (c.demoCompany IS NULL OR c.demoCompany = FALSE)
      AND ec.companyId NOT IN ('d4c82ebb-1986-4632-9686-8e72c4d07c85', 'b2affbf5-3653-429a-a7b9-bfc4e25fec7c')
    """

    df = client.query(query).to_dataframe()
    # Convert date columns
    if 'createdAt' in df.columns:
        df['createdAt'] = pd.to_datetime(df['createdAt']).dt.tz_localize(None)
    if 'updatedAt' in df.columns:
        df['updatedAt'] = pd.to_datetime(df['updatedAt']).dt.tz_localize(None)

    logger.info(f"Loaded {len(df)} inactive contracts")
    return df

def get_approved_not_started_contracts(snapshot_date: datetime.date = None) -> pd.DataFrame:
    """
    Fetch approved but not started contracts (future start_date).

    Args:
        snapshot_date: Date for filtering (defaults to today)

    Returns:
        pd.DataFrame: Approved not started contracts with contract_id, companyId, country
    """
    if snapshot_date is None:
        snapshot_date = datetime.now().date()

    query = f"""
    SELECT 
        ec.id AS contract_id,
        ec.companyId,
        ec.employmentLocation.country AS country,
        ec.createdAt,
        ec.updatedAt,
        ec.role.preferredStartDate AS start_date
    FROM `outstaffer-app-prod.firestore_exports.employee_contracts` ec
    LEFT JOIN `outstaffer-app-prod.lookup_tables.contract_status_mapping` sm
      ON ec.status = sm.contract_status
    LEFT JOIN `outstaffer-app-prod.firestore_exports.companies` c
      ON ec.companyId = c.id
    WHERE sm.mapped_status = 'Active'
      AND ec.role.preferredStartDate > '{snapshot_date}'
      AND (ec.__has_error__ IS NULL OR ec.__has_error__ = FALSE)
      AND (c.demoCompany IS NULL OR c.demoCompany = FALSE)
      AND ec.companyId NOT IN ('d4c82ebb-1986-4632-9686-8e72c4d07c85', 'b2affbf5-3653-429a-a7b9-bfc4e25fec7c')
    """

    df = client.query(query).to_dataframe()
    # Convert date columns
    if 'createdAt' in df.columns:
        df['createdAt'] = pd.to_datetime(df['createdAt']).dt.tz_localize(None)
    if 'updatedAt' in df.columns:
        df['updatedAt'] = pd.to_datetime(df['updatedAt']).dt.tz_localize(None)

    logger.info(f"Loaded {len(df)} approved not started contracts")
    return df

def get_contract_fees(contract_ids: list) -> pd.DataFrame:
    if not contract_ids:
        return pd.DataFrame(columns=['contract_id', 'eor_fees', 'eor_currency', 'device_fees', 'device_currency', ...])

    contract_ids_str = ','.join(f"'{id}'" for id in contract_ids)
    query = f"""
    SELECT 
        ec.id AS contract_id,
        CAST(IFNULL((
          SELECT calc.monthlyCharges.employerCharges.planCharges.categoryTotals.EOR.amount
          FROM UNNEST(ec.calculations) AS calc
          ORDER BY calc.calculatedAt DESC
          LIMIT 1
        ), '0') AS FLOAT64) AS eor_fees,
        IFNULL((
          SELECT JSON_EXTRACT_SCALAR(TO_JSON_STRING(calc.monthlyCharges.employerCharges.planCharges.categoryTotals.EOR), '$.currency')
          FROM UNNEST(ec.calculations) AS calc
          ORDER BY calc.calculatedAt DESC
          LIMIT 1
        ), 'AUD') AS eor_currency,
        CAST(IFNULL((
          SELECT calc.monthlyCharges.employerCharges.planCharges.categoryTotals.Device.amount
          FROM UNNEST(ec.calculations) AS calc
          ORDER BY calc.calculatedAt DESC
          LIMIT 1
        ), '0') AS FLOAT64) AS device_fees,
        IFNULL((
          SELECT JSON_EXTRACT_SCALAR(TO_JSON_STRING(calc.monthlyCharges.employerCharges.planCharges.categoryTotals.Device), '$.currency')
          FROM UNNEST(ec.calculations) AS calc
          ORDER BY calc.calculatedAt DESC
          LIMIT 1
        ), 'AUD') AS device_currency,
        CAST(IFNULL((
          SELECT calc.monthlyCharges.employerCharges.planCharges.categoryTotals.Hardware.amount
          FROM UNNEST(ec.calculations) AS calc
          ORDER BY calc.calculatedAt DESC
          LIMIT 1
        ), '0') AS FLOAT64) AS hardware_fees,
        IFNULL((
          SELECT JSON_EXTRACT_SCALAR(TO_JSON_STRING(calc.monthlyCharges.employerCharges.planCharges.categoryTotals.Hardware), '$.currency')
          FROM UNNEST(ec.calculations) AS calc
          ORDER BY calc.calculatedAt DESC
          LIMIT 1
        ), 'AUD') AS hardware_currency,
        CAST(IFNULL((
          SELECT calc.monthlyCharges.employerCharges.planCharges.categoryTotals.Software.amount
          FROM UNNEST(ec.calculations) AS calc
          ORDER BY calc.calculatedAt DESC
          LIMIT 1
        ), '0') AS FLOAT64) AS software_fees,
        IFNULL((
          SELECT JSON_EXTRACT_SCALAR(TO_JSON_STRING(calc.monthlyCharges.employerCharges.planCharges.categoryTotals.Software), '$.currency')
          FROM UNNEST(ec.calculations) AS calc
          ORDER BY calc.calculatedAt DESC
          LIMIT 1
        ), 'AUD') AS software_currency,
        CAST(IFNULL((
          SELECT calc.monthlyCharges.employerCharges.healthCharges.total.amount
          FROM UNNEST(ec.calculations) AS calc
          ORDER BY calc.calculatedAt DESC
          LIMIT 1
        ), '0') AS FLOAT64) AS health_fees,
        IFNULL((
          SELECT JSON_EXTRACT_SCALAR(TO_JSON_STRING(calc.monthlyCharges.employerCharges.healthCharges.total), '$.currency')
          FROM UNNEST(ec.calculations) AS calc
          ORDER BY calc.calculatedAt DESC
          LIMIT 1
        ), 'AUD') AS health_currency,
        CAST(IFNULL((
          SELECT calc.monthlyCharges.taasCharges.totalFee.value.amount
          FROM UNNEST(ec.calculations) AS calc
          ORDER BY calc.calculatedAt DESC
          LIMIT 1
        ), '0') AS FLOAT64) AS placement_fees,
        IFNULL((
          SELECT JSON_EXTRACT_SCALAR(TO_JSON_STRING(calc.monthlyCharges.taasCharges.totalFee.value), '$.currency')
          FROM UNNEST(ec.calculations) AS calc
          ORDER BY calc.calculatedAt DESC
          LIMIT 1
        ), 'AUD') AS placement_currency,
        CAST(IFNULL((
          SELECT calc.monthlyCharges.oneOffCharges.finalisationFee.amount
          FROM UNNEST(ec.calculations) AS calc
          ORDER BY calc.calculatedAt DESC
          LIMIT 1
        ), '0') AS FLOAT64) AS finalisation_fees,
        IFNULL((
          SELECT JSON_EXTRACT_SCALAR(TO_JSON_STRING(calc.monthlyCharges.oneOffCharges.finalisationFee), '$.currency')
          FROM UNNEST(ec.calculations) AS calc
          ORDER BY calc.calculatedAt DESC
          LIMIT 1
        ), 'AUD') AS finalisation_currency
    FROM `outstaffer-app-prod.firestore_exports.employee_contracts` ec
    WHERE ec.id IN ({contract_ids_str})
      AND ec.calculations IS NOT NULL AND ARRAY_LENGTH(ec.calculations) > 0
    """

    df = client.query(query).to_dataframe()
    logger.info(f"Loaded fees for {len(df)} contracts")
    return df

def get_companies() -> pd.DataFrame:
    """
    Fetch company data from BigQuery.

    Returns:
        pd.DataFrame: Companies data
    """
    query = """
    SELECT id, companyName, demoCompany, createdAt, industry, size 
    FROM `outstaffer-app-prod.firestore_exports.companies`
    WHERE demoCompany IS NULL OR demoCompany = FALSE
    AND id NOT IN ('d4c82ebb-1986-4632-9686-8e72c4d07c85', 'b2affbf5-3653-429a-a7b9-bfc4e25fec7c')
    """

    companies_df = client.query(query).to_dataframe()
    companies_df['createdAt'] = pd.to_datetime(companies_df['createdAt']).dt.tz_localize(None)
    logger.info(f"Loaded {len(companies_df)} companies")
    return companies_df

def get_fx_rates(target_currency: str = 'AUD') -> pd.DataFrame:
    """
    Fetch FX rates from BigQuery.

    Args:
        target_currency: Target currency for rates (default 'AUD')

    Returns:
        pd.DataFrame: FX rates data
    """
    query = f"""
    SELECT * FROM `outstaffer-app-prod.dashboard_metrics.fx_rates`
    WHERE target_currency = '{target_currency}'
    """

    fx_rates_df = client.query(query).to_dataframe()
    fx_rates_df['fx_date'] = pd.to_datetime(fx_rates_df['fx_date']).dt.tz_localize(None)
    logger.info(f"Loaded {len(fx_rates_df)} FX rates")
    return fx_rates_df

def convert_fees_to_aud(contracts_df: pd.DataFrame, fx_rates_df=None) -> pd.DataFrame:
    """
    Convert contract fees to AUD using fee-specific currency fields.

    Args:
        contracts_df: DataFrame with contract_id, fee columns (eor_fees, etc.), and currency columns (eor_currency, etc.)
        fx_rates_df: DataFrame with FX rates (fetched if None)

    Returns:
        pd.DataFrame: Contracts with AUD-converted fees
    """
    if fx_rates_df is None:
        fx_rates_df = get_fx_rates()

    df = contracts_df.copy()
    logger.info(f"Converting fees for {len(df)} contracts")

    # Get latest FX rate per currency
    latest_fx = fx_rates_df.groupby('currency').apply(
        lambda x: x.loc[x['fx_date'].idxmax()]).reset_index(drop=True)[['currency', 'rate']]
    logger.info(f"FX rates loaded: {latest_fx['currency'].tolist()}")

    # Define fee types and their currency columns
    fee_currency_pairs = [
        ('eor_fees', 'eor_currency'),
        ('device_fees', 'device_currency'),
        ('hardware_fees', 'hardware_currency'),
        ('software_fees', 'software_currency'),
        ('health_fees', 'health_currency'),
        ('placement_fees', 'placement_currency'),
        ('finalisation_fees', 'finalisation_currency'),
    ]

    # Convert each fee type using its currency
    for fee_col, currency_col in fee_currency_pairs:
        if fee_col in df.columns and currency_col in df.columns:
            df = df.merge(
                latest_fx[['currency', 'rate']],
                left_on=currency_col,
                right_on='currency',
                how='left',
                suffixes=('', f'_{fee_col}')
            )
            df[f'{fee_col}_rate'] = df['rate'].fillna(1.0).astype(float)
            df[f'{fee_col}_aud'] = df[fee_col].fillna(0) * df[f'{fee_col}_rate']
            df.drop(columns=['currency', 'rate', f'{fee_col}_rate'], inplace=True)
            logger.info(f"Converted {fee_col}: {df[f'{fee_col}_aud'].sum()} AUD")
        else:
            df[f'{fee_col}_aud'] = 0.0
            logger.warning(f"Missing {fee_col} or {currency_col}, setting {fee_col}_aud to 0")

    return df

def get_revenue_breakdown(contracts_df: pd.DataFrame, snapshot_date: datetime.date = None) -> dict:
    """
    Calculate revenue breakdown from contracts.

    Args:
        contracts_df: DataFrame with contract_id, companyId, country
        snapshot_date: Date for filtering one-time fees (defaults to today)

    Returns:
        dict: Revenue breakdown
    """
    if snapshot_date is None:
        snapshot_date = datetime.now().date()

    if contracts_df.empty:
        return {
            'eor_fees_mrr': 0.0, 'device_fees_mrr': 0.0, 'hardware_fees_mrr': 0.0,
            'software_fees_mrr': 0.0, 'health_fees_mrr': 0.0, 'total_mrr': 0.0,
            'total_arr': 0.0, 'one_time_fees': 0.0, 'placement_fees': 0.0,
            'finalisation_fees': 0.0, 'total_monthly_revenue': 0.0, 'addon_percentage': 0.0
        }

    # Get fees for contracts
    fees_df = get_contract_fees(contracts_df['contract_id'].tolist())

    # Merge fees into contracts dataframe
    df = contracts_df.merge(fees_df, on='contract_id', how='left')

    # Apply FX conversion
    fx_rates_df = get_fx_rates()
    df = convert_fees_to_aud(df, fx_rates_df)

    # Filter one-time fees by date
    month_start = snapshot_date.replace(day=1)
    month_end = (pd.Timestamp(month_start) + pd.DateOffset(months=1) - pd.DateOffset(days=1)).date()

    # Initialize one-time fee columns with 0
    df['placement_fees_in_month'] = 0.0
    df['finalisation_fees_in_month'] = 0.0

    # Only count one-time fees if they were created in this month
    # First make sure 'createdAt' is a datetime
    if 'createdAt' in df.columns:
        mask = (df['createdAt'].dt.date >= month_start) & (df['createdAt'].dt.date <= month_end)
        df.loc[mask, 'placement_fees_in_month'] = df.loc[mask, 'placement_fees_aud']
        df.loc[mask, 'finalisation_fees_in_month'] = df.loc[mask, 'finalisation_fees_aud']

    # Calculate aggregated metrics
    eor_fees_mrr = df['eor_fees_aud'].sum()
    device_fees_mrr = df['device_fees_aud'].sum()
    hardware_fees_mrr = df['hardware_fees_aud'].sum()
    software_fees_mrr = df['software_fees_aud'].sum()
    health_fees_mrr = df['health_fees_aud'].sum()
    placement_fees = df['placement_fees_in_month'].sum()
    finalisation_fees = df['finalisation_fees_in_month'].sum()

    total_mrr = eor_fees_mrr + device_fees_mrr + hardware_fees_mrr + software_fees_mrr + health_fees_mrr
    total_arr = total_mrr * 12
    one_time_fees = placement_fees + finalisation_fees
    total_monthly_revenue = total_mrr + one_time_fees

    addon_mrr = device_fees_mrr + hardware_fees_mrr + software_fees_mrr + health_fees_mrr
    addon_percentage = (addon_mrr / total_mrr * 100) if total_mrr > 0 else 0.0

    return {
        'eor_fees_mrr': eor_fees_mrr,
        'device_fees_mrr': device_fees_mrr,
        'hardware_fees_mrr': hardware_fees_mrr,
        'software_fees_mrr': software_fees_mrr,
        'health_fees_mrr': health_fees_mrr,
        'total_mrr': total_mrr,
        'total_arr': total_arr,
        'one_time_fees': one_time_fees,
        'placement_fees': placement_fees,
        'finalisation_fees': finalisation_fees,
        'total_monthly_revenue': total_monthly_revenue,
        'addon_percentage': addon_percentage
    }

def get_total_mrr(contracts_df: pd.DataFrame, snapshot_date: datetime.date = None) -> float:
    """
    Calculate total MRR for a set of contracts.

    Args:
        contracts_df: DataFrame with contract_id, companyId, country
        snapshot_date: Date for filtering (defaults to today)

    Returns:
        float: Total MRR in AUD
    """
    revenue = get_revenue_breakdown(contracts_df, snapshot_date)
    return revenue['total_mrr']

def get_total_arr(contracts_df: pd.DataFrame, snapshot_date: datetime.date = None) -> float:
    """
    Calculate total ARR for a set of contracts.

    Args:
        contracts_df: DataFrame with contract_id, companyId, country
        snapshot_date: Date for filtering (defaults to today)

    Returns:
        float: Total ARR in AUD
    """
    revenue = get_revenue_breakdown(contracts_df, snapshot_date)
    return revenue['total_arr']

def get_total_one_time_fees(contracts_df: pd.DataFrame, snapshot_date: datetime.date = None) -> float:
    """
    Calculate total one-time fees for a set of contracts.

    Args:
        contracts_df: DataFrame with contract_id, companyId, country
        snapshot_date: Date for filtering one-time fees (defaults to today)

    Returns:
        float: Total one-time fees in AUD for the specified month
    """
    revenue = get_revenue_breakdown(contracts_df, snapshot_date)
    return revenue['one_time_fees']

def get_revenue_by_category(contracts_df: pd.DataFrame, snapshot_date: datetime.date = None) -> dict:
    """
    Calculate total revenue by category for a set of contracts.

    Args:
        contracts_df: DataFrame with contract_id, companyId, country
        snapshot_date: Date for filtering one-time fees (defaults to today)

    Returns:
        dict: Totals for each revenue category in AUD
    """
    if contracts_df.empty:
        return {
            'eor_fees': 0.0, 'device_fees': 0.0, 'hardware_fees': 0.0,
            'software_fees': 0.0, 'health_fees': 0.0, 'placement_fees': 0.0,
            'finalisation_fees': 0.0
        }

    if snapshot_date is None:
        snapshot_date = datetime.now().date()

    # Get fees for contracts
    fees_df = get_contract_fees(contracts_df['contract_id'].tolist())

    # Merge fees into contracts dataframe
    df = contracts_df.merge(fees_df, on='contract_id', how='left')

    # Apply FX conversion
    fx_rates_df = get_fx_rates()
    df = convert_fees_to_aud(df, fx_rates_df)

    # Filter one-time fees by date
    month_start = snapshot_date.replace(day=1)
    month_end = (pd.Timestamp(month_start) + pd.DateOffset(months=1) - pd.DateOffset(days=1)).date()

    # Default values
    result = {
        'eor_fees': df['eor_fees_aud'].sum(),
        'device_fees': df['device_fees_aud'].sum(),
        'hardware_fees': df['hardware_fees_aud'].sum(),
        'software_fees': df['software_fees_aud'].sum(),
        'health_fees': df['health_fees_aud'].sum(),
        'placement_fees': 0.0,
        'finalisation_fees': 0.0
    }

    # Only count one-time fees if they were created in this month
    if 'createdAt' in df.columns:
        month_mask = (df['createdAt'].dt.date >= month_start) & (df['createdAt'].dt.date <= month_end)
        result['placement_fees'] = df.loc[month_mask, 'placement_fees_aud'].sum()
        result['finalisation_fees'] = df.loc[month_mask, 'finalisation_fees_aud'].sum()

    return result

def get_individual_revenue_metrics(contracts_df: pd.DataFrame, snapshot_date: datetime.date = None) -> pd.DataFrame:
    """
    Calculate individual revenue metrics for each contract.

    Args:
        contracts_df: DataFrame with contract_id, companyId, country
        snapshot_date: Date for filtering one-time fees (defaults to today)

    Returns:
        pd.DataFrame: Contracts with calculated revenue metrics
    """

    if snapshot_date is None:
        snapshot_date = datetime.now().date()

    if contracts_df.empty:
        return contracts_df

    # Get fees for contracts
    fees_df = get_contract_fees(contracts_df['contract_id'].tolist())

    # Merge fees into contracts dataframe
    df = contracts_df.merge(fees_df, on='contract_id', how='left')

    # Ensure createdAt is datetime
    if 'createdAt' in df.columns:
        df['createdAt'] = pd.to_datetime(df['createdAt'], errors='coerce')

    # Fill NA values with 0 for fee columns
    fee_types = ['eor_fees', 'device_fees', 'hardware_fees', 'software_fees',
                 'health_fees', 'placement_fees', 'finalisation_fees']
    for fee_type in fee_types:
        if fee_type in df.columns:
            df[fee_type] = df[fee_type].fillna(0)

    # Apply FX conversion
    fx_rates_df = get_fx_rates()
    df = convert_fees_to_aud(df, fx_rates_df)

    # Define recurring fee types for MRR calculation
    recurring_fees = ['eor_fees_aud', 'device_fees_aud', 'hardware_fees_aud',
                      'software_fees_aud', 'health_fees_aud']
    df['total_mrr_aud'] = df[recurring_fees].sum(axis=1)

    # Define addon fee types
    addon_fees = ['device_fees_aud', 'hardware_fees_aud', 'software_fees_aud',
                  'health_fees_aud']
    df['addon_mrr_aud'] = df[addon_fees].sum(axis=1)

    # Calculate ARR
    df['total_arr_aud'] = df['total_mrr_aud'] * 12
    df['addon_arr_aud'] = df['addon_mrr_aud'] * 12

    # Calculate addon percentage
    df['addon_percentage'] = (df['addon_mrr_aud'] / df['total_mrr_aud'] * 100).fillna(0)

    # Filter one-time fees by date
    month_start = snapshot_date.replace(day=1)
    month_end = (pd.Timestamp(month_start) + pd.DateOffset(months=1) - pd.DateOffset(days=1)).date()

    df['placement_fees_in_month'] = 0.0
    df['finalisation_fees_in_month'] = 0.0

    # Only count one-time fees if createdAt is valid and within the month
    if 'createdAt' in df.columns and df['createdAt'].notna().any():
        month_mask = (df['createdAt'].dt.date >= month_start) & (df['createdAt'].dt.date <= month_end)
        df.loc[month_mask, 'placement_fees_in_month'] = df.loc[month_mask, 'placement_fees_aud']
        df.loc[month_mask, 'finalisation_fees_in_month'] = df.loc[month_mask, 'finalisation_fees_aud']

    df['one_time_fees_in_month'] = df['placement_fees_in_month'] + df['finalisation_fees_in_month']
    df['total_monthly_revenue_aud'] = df['total_mrr_aud'] + df['one_time_fees_in_month']

    logger.info(f"Calculated individual revenue metrics for {len(df)} contracts")
    return df

# Company functions

def get_companies_with_labels() -> pd.DataFrame:
    """
    Fetch companies with industry and size labels.

    Returns:
        pd.DataFrame: Companies with joined industry/size labels
    """
    query = """
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
    AND c.id NOT IN ('d4c82ebb-1986-4632-9686-8e72c4d07c85', 'b2affbf5-3653-429a-a7b9-bfc4e25fec7c')
    """

    companies_df = client.query(query).to_dataframe()
    companies_df['createdAt'] = pd.to_datetime(companies_df['createdAt']).dt.tz_localize(None)
    logger.info(f"Loaded {len(companies_df)} companies with labels")
    return companies_df

def get_enabled_users() -> pd.DataFrame:
    """
    Fetch enabled users.

    Returns:
        pd.DataFrame: User records with companyId
    """
    query = """
    SELECT id, companyId
    FROM `outstaffer-app-prod.firestore_exports.users`
    WHERE status = 'ENABLED'
      AND (__has_error__ IS NULL OR __has_error__ = FALSE)
    """

    users_df = client.query(query).to_dataframe()
    logger.info(f"Loaded {len(users_df)} enabled users")
    return users_df

#Plans and add-ons

def get_plan_addons():
    """
    Fetch plan add-ons metadata from BigQuery.

    Returns:
        pd.DataFrame: Plan add-ons with id, label, type, meta, isActive
    """
    query = """
        SELECT id, label, type, meta, isActive 
        FROM `outstaffer-app-prod.firestore_exports.plan_add_ons`
    """
    addons_df = client.query(query).to_dataframe()
    logger.info(f"Loaded {len(addons_df)} plan add-ons")
    return addons_df

def get_plans():
    """
    Fetch active plans metadata from BigQuery.

    Returns:
        pd.DataFrame: Active plans with id, name
    """
    query = """
        SELECT id, name 
        FROM `outstaffer-app-prod.firestore_exports.plans` 
        WHERE active = TRUE
    """
    plans_df = client.query(query).to_dataframe()
    logger.info(f"Loaded {len(plans_df)} active plans")
    return plans_df

def get_contracts_with_addon_data(contract_ids=None, snapshot_date=None):
    """
    Fetch contracts with plan and add-on data, optionally filtered by contract IDs.

    Args:
        contract_ids: Optional list of contract IDs to fetch (if None, fetches all)
        snapshot_date: Date for filtering (defaults to today)

    Returns:
        pd.DataFrame: Contracts with plan and add-on data
    """
    if snapshot_date is None:
        snapshot_date = datetime.now().date()

    # Build WHERE clause for contract IDs if provided
    contract_filter = ""
    if contract_ids and len(contract_ids) > 0:
        contract_ids_str = ','.join(f"'{id}'" for id in contract_ids)
        contract_filter = f"AND ec.id IN ({contract_ids_str})"

    query = f"""
        SELECT
            ec.id AS contract_id,
            ec.companyId,
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
        AND ec.companyId NOT IN ('d4c82ebb-1986-4632-9686-8e72c4d07c85', 'b2affbf5-3653-429a-a7b9-bfc4e25fec7c')
          AND (ec.__has_error__ IS NULL OR ec.__has_error__ = FALSE)
          {contract_filter}
    """

    contracts_df = client.query(query).to_dataframe()

    # Log differently based on whether we filtered by contract IDs
    if contract_ids and len(contract_ids) > 0:
        logger.info(f"Loaded {len(contracts_df)} contracts with add-on data out of {len(contract_ids)} requested")
    else:
        logger.info(f"Loaded {len(contracts_df)} contracts with add-on data")

    return contracts_df

def aggregate_addons(contracts_df, col, addon_type):
    """
    Process add-on data from contracts.

    Args:
        contracts_df: DataFrame with contract data
        col: Column name containing add-on data
        addon_type: Type of add-on for logging

    Returns:
        pd.DataFrame: Aggregated add-on counts with addon_id and contract_count
    """
    if contracts_df.empty:
        logger.info(f"No contracts provided for {addon_type} add-on aggregation")
        return pd.DataFrame(columns=['addon_id', 'contract_count'])

    # Make sure the required columns exist
    if 'contract_id' not in contracts_df.columns or col not in contracts_df.columns:
        logger.warning(f"Required columns missing for {addon_type} add-on aggregation. Need 'contract_id' and '{col}'")
        return pd.DataFrame(columns=['addon_id', 'contract_count'])

    extracted = contracts_df[["contract_id", col]].dropna()
    if extracted.empty:
        logger.info(f"No {addon_type} add-ons found in the provided contracts")
        return pd.DataFrame(columns=['addon_id', 'contract_count'])

    exploded = extracted.explode(col)
    exploded = exploded[exploded[col].notnull()]

    def extract_addon_key(x):
        if isinstance(x, dict):
            return x.get('key') or "OTHER"
        return str(x) if x else "OTHER"

    exploded['addon_id'] = exploded[col].apply(extract_addon_key)
    result = exploded.groupby('addon_id').contract_id.nunique().reset_index(name='contract_count')
    logger.info(f"Aggregated {addon_type} add-ons: {len(result)} unique add-ons found across {len(extracted)} contracts")
    return result

def map_device_to_os(device_meta):
    """
    Map device types to operating systems.

    Args:
        device_meta: DataFrame with device metadata

    Returns:
        pd.DataFrame: Mapping from device_id to os_type
    """
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
    logger.info(f"Mapped {len(os_df)} devices to OS types")
    return os_df

#Health insurance

# Health Insurance Utilities

def get_health_insurance_plans_by_country(client=None):
    """
    Fetch health insurance plan availability by country from BigQuery.

    Args:
        client: BigQuery client (uses module-level client if None)

    Returns:
        pd.DataFrame: Health insurance plans with availability by country
    """
    if client is None:
        client = globals().get('client')  # Use module-level client

    logger = logging.getLogger(__name__)
    logger.info("Loading health insurance plan availability by country...")

    # This approach uses explicit JSON paths for each country
    # instead of dynamic path construction which doesn't work in BigQuery
    query = """
    WITH plans AS (
      SELECT 
        id AS plan_id,
        key AS plan_key,
        label AS plan_label,
        description,
        countryFieldOverrides
      FROM `outstaffer-app-prod.firestore_exports.health_insurance_options`
      WHERE (__has_error__ IS NULL OR __has_error__ = FALSE)
    ),
    
    -- Extract each country's availability explicitly
    expanded_countries AS (
      SELECT
        plan_id,
        plan_key,
        plan_label,
        description,
        -- Australia
        'AU' AS country,
        CASE
          WHEN JSON_EXTRACT_SCALAR(TO_JSON_STRING(countryFieldOverrides), '$.AU.isDisabled') = 'true' THEN FALSE
          WHEN JSON_EXTRACT_SCALAR(TO_JSON_STRING(countryFieldOverrides), '$.AU.isDisabled') = 'false' THEN TRUE
          ELSE TRUE
        END AS is_enabled,
        IFNULL(
          JSON_EXTRACT_SCALAR(TO_JSON_STRING(countryFieldOverrides), '$.AU.description'),
          description
        ) AS country_description
      FROM plans
      
      UNION ALL
      
      SELECT
        plan_id,
        plan_key,
        plan_label,
        description,
        -- Philippines
        'PH' AS country,
        CASE
          WHEN JSON_EXTRACT_SCALAR(TO_JSON_STRING(countryFieldOverrides), '$.PH.isDisabled') = 'true' THEN FALSE
          WHEN JSON_EXTRACT_SCALAR(TO_JSON_STRING(countryFieldOverrides), '$.PH.isDisabled') = 'false' THEN TRUE
          ELSE TRUE
        END AS is_enabled,
        IFNULL(
          JSON_EXTRACT_SCALAR(TO_JSON_STRING(countryFieldOverrides), '$.PH.description'),
          description
        ) AS country_description
      FROM plans
      
      UNION ALL
      
      SELECT
        plan_id,
        plan_key,
        plan_label,
        description,
        -- Singapore
        'SG' AS country,
        CASE
          WHEN JSON_EXTRACT_SCALAR(TO_JSON_STRING(countryFieldOverrides), '$.SG.isDisabled') = 'true' THEN FALSE
          WHEN JSON_EXTRACT_SCALAR(TO_JSON_STRING(countryFieldOverrides), '$.SG.isDisabled') = 'false' THEN TRUE
          ELSE TRUE
        END AS is_enabled,
        IFNULL(
          JSON_EXTRACT_SCALAR(TO_JSON_STRING(countryFieldOverrides), '$.SG.description'),
          description
        ) AS country_description
      FROM plans
      
      UNION ALL
      
      SELECT
        plan_id,
        plan_key,
        plan_label,
        description,
        -- Thailand
        'TH' AS country,
        CASE
          WHEN JSON_EXTRACT_SCALAR(TO_JSON_STRING(countryFieldOverrides), '$.TH.isDisabled') = 'true' THEN FALSE
          WHEN JSON_EXTRACT_SCALAR(TO_JSON_STRING(countryFieldOverrides), '$.TH.isDisabled') = 'false' THEN TRUE
          ELSE TRUE
        END AS is_enabled,
        IFNULL(
          JSON_EXTRACT_SCALAR(TO_JSON_STRING(countryFieldOverrides), '$.TH.description'),
          description
        ) AS country_description
      FROM plans
      
      UNION ALL
      
      SELECT
        plan_id,
        plan_key,
        plan_label,
        description,
        -- Vietnam
        'VN' AS country,
        CASE
          WHEN JSON_EXTRACT_SCALAR(TO_JSON_STRING(countryFieldOverrides), '$.VN.isDisabled') = 'true' THEN FALSE
          WHEN JSON_EXTRACT_SCALAR(TO_JSON_STRING(countryFieldOverrides), '$.VN.isDisabled') = 'false' THEN TRUE
          ELSE TRUE
        END AS is_enabled,
        IFNULL(
          JSON_EXTRACT_SCALAR(TO_JSON_STRING(countryFieldOverrides), '$.VN.description'),
          description
        ) AS country_description
      FROM plans
      
      UNION ALL
      
      SELECT
        plan_id,
        plan_key,
        plan_label,
        description,
        -- Malaysia
        'MY' AS country,
        CASE
          WHEN JSON_EXTRACT_SCALAR(TO_JSON_STRING(countryFieldOverrides), '$.MY.isDisabled') = 'true' THEN FALSE
          WHEN JSON_EXTRACT_SCALAR(TO_JSON_STRING(countryFieldOverrides), '$.MY.isDisabled') = 'false' THEN TRUE
          ELSE TRUE
        END AS is_enabled,
        IFNULL(
          JSON_EXTRACT_SCALAR(TO_JSON_STRING(countryFieldOverrides), '$.MY.description'),
          description
        ) AS country_description
      FROM plans
      
      UNION ALL
      
      SELECT
        plan_id,
        plan_key,
        plan_label,
        description,
        -- India
        'IN' AS country,
        CASE
          WHEN JSON_EXTRACT_SCALAR(TO_JSON_STRING(countryFieldOverrides), '$.IN.isDisabled') = 'true' THEN FALSE
          WHEN JSON_EXTRACT_SCALAR(TO_JSON_STRING(countryFieldOverrides), '$.IN.isDisabled') = 'false' THEN TRUE
          ELSE TRUE
        END AS is_enabled,
        IFNULL(
          JSON_EXTRACT_SCALAR(TO_JSON_STRING(countryFieldOverrides), '$.IN.description'),
          description
        ) AS country_description
      FROM plans
    )
    
    -- Filter to only include enabled plans and return the final result
    SELECT
      plan_id,
      plan_key,
      plan_label,
      country,
      is_enabled,
      country_description
    FROM expanded_countries
    WHERE is_enabled = TRUE
    ORDER BY country, plan_label
    """

    availability_df = client.query(query).to_dataframe()
    logger.info(f"Loaded {len(availability_df)} plan-country availability rows")
    return availability_df
def get_contracts_with_health_insurance_data(contracts_df, plans_df=None, client=None):
    """
    Enrich contract data with health insurance information including plan details.

    Args:
        contracts_df: DataFrame containing contracts with at least contract_id
        plans_df: Optional DataFrame with plan data from get_health_insurance_plans_by_country()
        client: BigQuery client (uses module-level client if None)

    Returns:
        pd.DataFrame: Contracts with added health insurance data and plan details
    """
    if client is None:
        client = globals().get('client')  # Use module-level client

    if contracts_df.empty:
        return contracts_df  # Return empty df if no contracts

    logger = logging.getLogger(__name__)

    # Extract contract IDs
    contract_ids = contracts_df['contract_id'].tolist()
    contract_ids_str = ','.join(f"'{id}'" for id in contract_ids)

    # Get health insurance data for contracts
    query = f"""
    SELECT
        ec.id AS contract_id,
        ec.employmentLocation.country AS country,
        ec.benefits.healthInsurance AS insurance_plan_id,
        ec.benefits.addOns.DEPENDENT AS dependent_count
    FROM `outstaffer-app-prod.firestore_exports.employee_contracts` ec
    WHERE ec.id IN ({contract_ids_str})
      AND (ec.__has_error__ IS NULL OR ec.__has_error__ = FALSE)
      AND ec.companyId NOT IN ('d4c82ebb-1986-4632-9686-8e72c4d07c85', 'b2affbf5-3653-429a-a7b9-bfc4e25fec7c')
    """

    logger.info(f"Loading health insurance data for {len(contract_ids)} contracts...")
    health_df = client.query(query).to_dataframe()
    logger.info(f"Loaded health insurance data for {len(health_df)} contracts")

    # Merge health insurance data with the original contracts dataframe
    # Using left join to ensure we keep all original contracts even if no health data
    merged_df = contracts_df.merge(
        health_df,
        on='contract_id',
        how='left',
        suffixes=('', '_health')
    )

    # Handle duplicate country columns (if both dataframes have it)
    if 'country_health' in merged_df.columns:
        # Prefer original country if available, otherwise use health country
        merged_df['country'] = merged_df['country'].fillna(merged_df['country_health'])
        merged_df.drop('country_health', axis=1, inplace=True)

    # If we have plans data, join it to get plan details
    if plans_df is None:
        logger.info("Fetching health insurance plans data...")
        plans_df = get_health_insurance_plans_by_country(client)

    # Rename plans columns for clarity
    plans_df = plans_df.rename(columns={
        'plan_id': 'insurance_plan_id',
        'plan_label': 'insurance_plan_label',
        'plan_key': 'insurance_plan_key',
        'country_description': 'insurance_plan_description'
    })

    # Create a composite key for joining plan data
    plans_df['merge_key'] = plans_df['country'] + '_' + plans_df['insurance_plan_id']
    merged_df['merge_key'] = merged_df['country'].astype(str) + '_' + merged_df['insurance_plan_id'].astype(str)

    # Join plan details
    result_df = merged_df.merge(
        plans_df[['merge_key', 'insurance_plan_label', 'insurance_plan_key',
                  'insurance_plan_description', 'is_enabled']],
        on='merge_key',
        how='left'
    )

    # Clean up
    result_df.drop('merge_key', axis=1, inplace=True)

    # Add a flag to identify if a contract has a valid insurance plan for its country
    result_df['has_valid_insurance'] = result_df['is_enabled'].fillna(False)

    return result_df

# Country functions

def get_all_countries():
    from google.cloud import bigquery
    client = bigquery.Client()

    query = """
        SELECT countryCode, name
        FROM `outstaffer-app-prod.firestore_exports.countries`
        WHERE (__has_error__ IS NULL OR __has_error__ = FALSE)
        AND 'EMPLOYEE' IN UNNEST(type)
    """
    result = client.query(query)
    return [dict(row) for row in result]