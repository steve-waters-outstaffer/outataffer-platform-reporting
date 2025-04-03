# metrics_utils.py
import pandas as pd
import numpy as np
from datetime import datetime

# ======== Contract Filtering Functions ========

def get_all_contracts(contracts_df, exclude_errors=True, exclude_demo=True):
    """
    Get all contracts, optionally excluding error records and demo companies.

    Args:
        contracts_df (DataFrame): DataFrame containing contract data
        exclude_errors (bool): If True, exclude records with __has_error__ = TRUE
        exclude_demo (bool): If True, exclude contracts from demo companies

    Returns:
        DataFrame: Filtered contracts
    """
    # This function assumes filtering for errors and demo companies has already
    # been applied in the query, but can be used for additional filtering if needed
    return contracts_df


def get_active_contracts(contracts_df, snapshot_date=None):
    """
    Get all revenue-generating contracts (mapped_status = 'Active', including those in offboarding).

    Args:
        contracts_df (DataFrame): DataFrame containing contract data
        snapshot_date (datetime.date, optional): Date to use for determining if contracts
                                                have started. Defaults to today.

    Returns:
        DataFrame: All active contracts including those in offboarding
    """
    if snapshot_date is None:
        snapshot_date = datetime.now().date()

    # Filter for active status
    active_df = contracts_df[contracts_df['mapped_status'] == 'Active'].copy()

    # Ensure contract is started (start date is in the past or today)
    # This assumes start_date is already converted to datetime.date
    if 'start_date' in active_df.columns:
        active_df = active_df[active_df['start_date'] <= snapshot_date]

    return active_df


def get_revenue_generating_contracts(contracts_df, snapshot_date=None):
    """
    Alias for get_active_contracts() - all contracts that are generating revenue.

    Args:
        contracts_df (DataFrame): DataFrame containing contract data
        snapshot_date (datetime.date, optional): Date to use for determining if contracts
                                                have started. Defaults to today.

    Returns:
        DataFrame: All revenue-generating contracts
    """
    return get_active_contracts(contracts_df, snapshot_date)


def get_offboarding_contracts(contracts_df, snapshot_date=None):
    """
    Get the subset of active contracts that are in offboarding status.

    Args:
        contracts_df (DataFrame): DataFrame containing contract data
        snapshot_date (datetime.date, optional): Not used but included for API consistency

    Returns:
        DataFrame: Active contracts in offboarding status
    """
    # Get active contracts
    active_df = get_active_contracts(contracts_df, snapshot_date)

    # Filter for offboarding status
    offboarding_df = active_df[active_df['status'] == 'OFFBOARDING'].copy()

    return offboarding_df


def get_approved_not_started_contracts(contracts_df, snapshot_date=None):
    """
    Get contracts that are approved but haven't started yet (future start date).

    Args:
        contracts_df (DataFrame): DataFrame containing contract data
        snapshot_date (datetime.date, optional): Date to use for determining if contracts
                                                have started. Defaults to today.

    Returns:
        DataFrame: Approved but not yet started contracts
    """
    if snapshot_date is None:
        snapshot_date = datetime.now().date()

    # Filter for active status with future start date
    not_started_df = contracts_df[
        (contracts_df['mapped_status'] == 'Active') &
        (contracts_df['start_date'] > snapshot_date)
        ].copy()

    return not_started_df


def get_inactive_contracts(contracts_df, snapshot_date=None):
    """
    Get contracts with mapped_status = 'Inactive'.

    Args:
        contracts_df (DataFrame): DataFrame containing contract data
        snapshot_date (datetime.date, optional): Not used but included for API consistency

    Returns:
        DataFrame: Inactive contracts
    """
    # Filter for inactive status
    inactive_df = contracts_df[contracts_df['mapped_status'] == 'Inactive'].copy()

    return inactive_df


def categorize_contracts(contracts_df, snapshot_date=None):
    """
    Add a 'contract_category' column to the DataFrame categorizing each contract.

    Categories:
    - 'active': Active, revenue-generating contracts (including those in offboarding)
    - 'approved_not_started': Approved contracts with future start date
    - 'inactive': Inactive contracts

    Additional metadata:
    - 'is_offboarding': Boolean flag for contracts in offboarding process

    Args:
        contracts_df (DataFrame): DataFrame containing contract data
        snapshot_date (datetime.date, optional): Date to use for categorization. Defaults to today.

    Returns:
        DataFrame: Original DataFrame with additional 'contract_category' and 'is_offboarding' columns
    """
    if snapshot_date is None:
        snapshot_date = datetime.now().date()

    # Create a copy to avoid modifying the original DataFrame
    df = contracts_df.copy()

    # Default category for all contracts
    df['contract_category'] = 'other'

    # Mark inactive contracts
    df.loc[df['mapped_status'] == 'Inactive', 'contract_category'] = 'inactive'

    # Mark active contracts (standard active and offboarding)
    active_mask = df['mapped_status'] == 'Active'

    # Mark approved not started contracts
    if 'start_date' in df.columns:
        future_start_mask = df['start_date'] > snapshot_date
        df.loc[active_mask & future_start_mask, 'contract_category'] = 'approved_not_started'

        # All others with active status are categorized as 'active'
        df.loc[active_mask & ~future_start_mask, 'contract_category'] = 'active'
    else:
        # If no start_date column, just use the active mask
        df.loc[active_mask, 'contract_category'] = 'active'

    # Add flag for offboarding status
    df['is_offboarding'] = (df['status'] == 'OFFBOARDING')

    return df


def get_new_started_contracts(contracts_df, start_date, end_date=None):
    """
    Get contracts that started within a specific date range.

    Args:
        contracts_df (DataFrame): DataFrame containing contract data
        start_date (datetime.date): Start of the date range
        end_date (datetime.date, optional): End of the date range. Defaults to None.

    Returns:
        DataFrame: Contracts that started within the specified date range
    """
    if end_date is None:
        end_date = datetime.now().date()

    # Filter for active contracts that started within the date range
    new_df = contracts_df[
        (contracts_df['mapped_status'] == 'Active') &
        (contracts_df['start_date'] >= start_date) &
        (contracts_df['start_date'] <= end_date)
        ].copy()

    return new_df


def get_churned_contracts(contracts_df, start_date, end_date=None):
    """
    Get contracts that were marked as inactive within a specific date range.

    Args:
        contracts_df (DataFrame): DataFrame containing contract data
        start_date (datetime.date): Start of the date range
        end_date (datetime.date, optional): End of the date range. Defaults to None.

    Returns:
        DataFrame: Contracts that were churned within the specified date range
    """
    if end_date is None:
        end_date = datetime.now().date()

    # Filter for inactive contracts that were updated within the date range
    churned_df = contracts_df[
        (contracts_df['mapped_status'] == 'Inactive') &
        (contracts_df['updatedAt'] >= start_date) &
        (contracts_df['updatedAt'] <= end_date)
        ].copy()

    return churned_df


# ======== Revenue Calculation Functions ========

def calculate_revenue_metrics(contracts_df, fx_rates_df=None):
    """
    Calculate all revenue metrics for a DataFrame of contracts.
    Adds revenue columns to the DataFrame.

    Args:
        contracts_df (DataFrame): DataFrame containing contract data
        fx_rates_df (DataFrame, optional): DataFrame with FX rates for currency conversion.
                                          Should have 'currency' and 'exchange_rate_to_aud' columns.

    Returns:
        DataFrame: Original DataFrame with additional revenue columns
    """
    if contracts_df.empty:
        return contracts_df

    # Create a copy to avoid modifying the original DataFrame
    df = contracts_df.copy()

    # Check if we need to do FX conversion
    need_fx = 'country' in df.columns and fx_rates_df is not None and not fx_rates_df.empty

    # Apply FX conversion if needed
    if need_fx:
        df = df.merge(
            fx_rates_df[['currency', 'exchange_rate_to_aud']],
            left_on='country',
            right_on='currency',
            how='left'
        )
        df['exchange_rate_to_aud'] = df['exchange_rate_to_aud'].fillna(1.0)
    else:
        df['exchange_rate_to_aud'] = 1.0

    # Handle potential column naming variations
    fee_columns = {
        'eor_fees': ['eor_fees'],
        'device_fees': ['device_fees'],
        'hardware_fees': ['hardware_fees'],
        'software_fees': ['software_fees'],
        'health_fees': ['health_fees', 'health_insurance_mrr'],
        'placement_fees': ['placement_fees', 'placement_fees_monthly']
    }

    # Create AUD columns for each fee type
    for fee_type, column_options in fee_columns.items():
        # Find the first matching column that exists
        column = next((col for col in column_options if col in df.columns), None)

        if column:
            # Fill NaN/None values with 0
            df[column] = df[column].fillna(0)

            # Create AUD column
            aud_column = f"{fee_type}_aud"
            df[aud_column] = df[column] * df['exchange_rate_to_aud']
        else:
            # If none of the column options exist, create a column of zeros
            df[f"{fee_type}_aud"] = 0

    # Calculate total MRR (excluding one-time fees)
    recurring_fee_columns = [
        'eor_fees_aud',
        'device_fees_aud',
        'hardware_fees_aud',
        'software_fees_aud',
        'health_fees_aud'
    ]
    df['total_mrr_aud'] = df[recurring_fee_columns].sum(axis=1)

    # Calculate add-on MRR (excluding core EOR fees)
    addon_fee_columns = [
        'device_fees_aud',
        'hardware_fees_aud',
        'software_fees_aud',
        'health_fees_aud'
    ]
    df['addon_mrr_aud'] = df[addon_fee_columns].sum(axis=1)

    # Calculate ARR
    df['total_arr_aud'] = df['total_mrr_aud'] * 12
    df['addon_arr_aud'] = df['addon_mrr_aud'] * 12

    # Calculate add-on percentage
    df['addon_percentage'] = np.where(
        df['total_mrr_aud'] > 0,
        (df['addon_mrr_aud'] / df['total_mrr_aud']) * 100,
        0
    )

    # Calculate total monthly revenue (including one-time fees)
    df['total_monthly_revenue_aud'] = df['total_mrr_aud'] + df['placement_fees_aud']

    return df


def get_total_mrr(contracts_df, fx_rates_df=None):
    """
    Calculate total MRR (Monthly Recurring Revenue) for a set of contracts.

    Args:
        contracts_df (DataFrame): DataFrame containing contract data
        fx_rates_df (DataFrame, optional): DataFrame with FX rates for currency conversion

    Returns:
        float: Total MRR in AUD
    """
    if contracts_df.empty:
        return 0.0

    # Calculate revenue metrics if needed
    if 'total_mrr_aud' not in contracts_df.columns:
        df = calculate_revenue_metrics(contracts_df, fx_rates_df)
    else:
        df = contracts_df

    return df['total_mrr_aud'].sum()


def get_total_arr(contracts_df, fx_rates_df=None):
    """
    Calculate total ARR (Annual Recurring Revenue) for a set of contracts.

    Args:
        contracts_df (DataFrame): DataFrame containing contract data
        fx_rates_df (DataFrame, optional): DataFrame with FX rates for currency conversion

    Returns:
        float: Total ARR in AUD
    """
    # ARR is just MRR * 12
    return get_total_mrr(contracts_df, fx_rates_df) * 12


def get_addon_mrr(contracts_df, fx_rates_df=None):
    """
    Calculate total add-on MRR (excluding core EOR fees) for a set of contracts.

    Args:
        contracts_df (DataFrame): DataFrame containing contract data
        fx_rates_df (DataFrame, optional): DataFrame with FX rates for currency conversion

    Returns:
        float: Total add-on MRR in AUD
    """
    if contracts_df.empty:
        return 0.0

    # Calculate revenue metrics if needed
    if 'addon_mrr_aud' not in contracts_df.columns:
        df = calculate_revenue_metrics(contracts_df, fx_rates_df)
    else:
        df = contracts_df

    return df['addon_mrr_aud'].sum()


def get_total_one_time_fees(contracts_df, fx_rates_df=None):
    """
    Calculate total one-time fees (e.g., placement fees) for a set of contracts.

    Args:
        contracts_df (DataFrame): DataFrame containing contract data
        fx_rates_df (DataFrame, optional): DataFrame with FX rates for currency conversion

    Returns:
        float: Total one-time fees in AUD
    """
    if contracts_df.empty:
        return 0.0

    # Calculate revenue metrics if needed
    if 'placement_fees_aud' not in contracts_df.columns:
        df = calculate_revenue_metrics(contracts_df, fx_rates_df)
    else:
        df = contracts_df

    return df['placement_fees_aud'].sum()


def get_revenue_breakdown(contracts_df, fx_rates_df=None):
    """
    Get a detailed breakdown of revenue by component for a set of contracts.

    Args:
        contracts_df (DataFrame): DataFrame containing contract data
        fx_rates_df (DataFrame, optional): DataFrame with FX rates for currency conversion

    Returns:
        dict: Revenue breakdown with the following keys:
              eor_fees_mrr, device_fees_mrr, hardware_fees_mrr, software_fees_mrr,
              health_fees_mrr, total_mrr, addon_mrr, total_arr, addon_arr,
              addon_percentage, one_time_fees, total_monthly_revenue
    """
    if contracts_df.empty:
        return {
            'eor_fees_mrr': 0.0,
            'device_fees_mrr': 0.0,
            'hardware_fees_mrr': 0.0,
            'software_fees_mrr': 0.0,
            'health_fees_mrr': 0.0,
            'total_mrr': 0.0,
            'addon_mrr': 0.0,
            'total_arr': 0.0,
            'addon_arr': 0.0,
            'addon_percentage': 0.0,
            'one_time_fees': 0.0,
            'total_monthly_revenue': 0.0
        }

    # Calculate revenue metrics if needed
    if 'total_mrr_aud' not in contracts_df.columns:
        df = calculate_revenue_metrics(contracts_df, fx_rates_df)
    else:
        df = contracts_df

    # Calculate component totals
    eor_fees_mrr = df['eor_fees_aud'].sum()
    device_fees_mrr = df['device_fees_aud'].sum()
    hardware_fees_mrr = df['hardware_fees_aud'].sum()
    software_fees_mrr = df['software_fees_aud'].sum()
    health_fees_mrr = df['health_fees_aud'].sum()
    total_mrr = df['total_mrr_aud'].sum()
    addon_mrr = df['addon_mrr_aud'].sum()
    one_time_fees = df['placement_fees_aud'].sum()
    total_monthly_revenue = df['total_monthly_revenue_aud'].sum()

    # Calculate ARR values
    total_arr = total_mrr * 12
    addon_arr = addon_mrr * 12

    # Calculate add-on percentage
    addon_percentage = (addon_mrr / total_mrr) * 100 if total_mrr > 0 else 0.0

    return {
        'eor_fees_mrr': eor_fees_mrr,
        'device_fees_mrr': device_fees_mrr,
        'hardware_fees_mrr': hardware_fees_mrr,
        'software_fees_mrr': software_fees_mrr,
        'health_fees_mrr': health_fees_mrr,
        'total_mrr': total_mrr,
        'addon_mrr': addon_mrr,
        'total_arr': total_arr,
        'addon_arr': addon_arr,
        'addon_percentage': addon_percentage,
        'one_time_fees': one_time_fees,
        'total_monthly_revenue': total_monthly_revenue
    }


def get_avg_contract_value(contracts_df, fx_rates_df=None):
    """
    Calculate the average MRR per contract.

    Args:
        contracts_df (DataFrame): DataFrame containing contract data
        fx_rates_df (DataFrame, optional): DataFrame with FX rates for currency conversion

    Returns:
        float: Average contract value (MRR) in AUD
    """
    if contracts_df.empty:
        return 0.0

    total_mrr = get_total_mrr(contracts_df, fx_rates_df)
    contract_count = len(contracts_df)

    return total_mrr / contract_count if contract_count > 0 else 0.0