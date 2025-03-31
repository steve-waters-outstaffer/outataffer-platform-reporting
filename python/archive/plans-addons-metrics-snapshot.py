import pandas as pd
from datetime import datetime
from google.cloud import bigquery
import logging
import sys
import json

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger('plan-addons-snapshot')

# Initialize BigQuery client
client = bigquery.Client()

def main():
    # Define snapshot date as today
    snapshot_date = datetime.now().date()
    logger.info(f"Processing plan and add-on adoption snapshot for: {snapshot_date}")

    # 1. Load add-on metadata from the addons table
    addons_query = """
    SELECT 
        id as addon_id,
        label as addon_label,
        type as addon_type,
        description,
        isActive,
        meta,
        selectOnePerGroupName
    FROM `outstaffer-app-prod.firestore_exports.plan_add_ons`
    """

    addons_df = client.query(addons_query).to_dataframe()
    logger.info(f"Loaded {len(addons_df)} add-on definitions")

    # 2. Load plan categories
    categories_query = """
    SELECT 
        id as category_id,
        name as category_name,
        description
    FROM `outstaffer-app-prod.firestore_exports.plan_categories`
    """

    categories_df = client.query(categories_query).to_dataframe()
    logger.info(f"Loaded {len(categories_df)} plan categories")

    # 3. Load plan metadata
    plans_query = """
    SELECT 
        id as plan_id, 
        name as plan_name,
        category as plan_category
    FROM `outstaffer-app-prod.firestore_exports.plans`
    WHERE id in ('EOR_CORE', 'EOR_PREMIUM', 'HR_CORE', 'HR_PREMIUM')
    """
    plans_df = client.query(plans_query).to_dataframe()
    logger.info(f"Loaded {len(plans_df)} plan definitions")

    # 4. Create categorized device/addon dataframes for easier access
    device_addons = addons_df[addons_df['addon_type'] == 'DEVICE'].copy()
    hardware_addons = addons_df[addons_df['addon_type'] == 'HARDWARE'].copy()
    software_addons = addons_df[addons_df['addon_type'] == 'SOFTWARE'].copy()
    membership_addons = addons_df[addons_df['addon_type'] == 'MEMBERSHIP'].copy()

    # 5. Count active contracts (this is our base count for percentage calculations)
    active_count_query = """
    SELECT COUNT(*) as active_contract_count
    FROM `outstaffer-app-prod.firestore_exports.employee_contracts` ec
    JOIN `outstaffer-app-prod.firestore_exports.companies` c
      ON ec.companyId = c.id
    JOIN `outstaffer-app-prod.lookup_tables.contract_status_mapping` cm
      ON ec.status = cm.contract_status
    WHERE (c.demoCompany IS NULL OR c.demoCompany = FALSE)
      AND (ec.__has_error__ IS NULL OR ec.__has_error__ = FALSE)
      AND cm.mapped_status = 'Active'
    """
    active_count_df = client.query(active_count_query).to_dataframe()
    total_active_contracts = active_count_df['active_contract_count'].iloc[0]
    logger.info(f"Total active contracts: {total_active_contracts}")

    # 6. Get plan type distribution - directly from BigQuery using UNNEST
    plan_query = """
    SELECT 
        ec.plan.type as plan_id,
        COUNT(*) as contract_count
    FROM `outstaffer-app-prod.firestore_exports.employee_contracts` ec
    JOIN `outstaffer-app-prod.firestore_exports.companies` c
      ON ec.companyId = c.id
    JOIN `outstaffer-app-prod.lookup_tables.contract_status_mapping` cm
      ON ec.status = cm.contract_status
    WHERE (c.demoCompany IS NULL OR c.demoCompany = FALSE)
      AND (ec.__has_error__ IS NULL OR ec.__has_error__ = FALSE)
      AND cm.mapped_status = 'Active'
    GROUP BY plan_id
    ORDER BY contract_count DESC
    """
    plan_distribution_df = client.query(plan_query).to_dataframe()
    logger.info(f"Retrieved plan distribution for {len(plan_distribution_df)} different plans")

    # 7. Get device type distribution - directly from BigQuery
    device_query = """
    SELECT 
        ec.plan.deviceUpgrade as device_id,
        COUNT(*) as contract_count
    FROM `outstaffer-app-prod.firestore_exports.employee_contracts` ec
    JOIN `outstaffer-app-prod.firestore_exports.companies` c
      ON ec.companyId = c.id
    JOIN `outstaffer-app-prod.lookup_tables.contract_status_mapping` cm
      ON ec.status = cm.contract_status
    WHERE (c.demoCompany IS NULL OR c.demoCompany = FALSE)
      AND (ec.__has_error__ IS NULL OR ec.__has_error__ = FALSE)
      AND cm.mapped_status = 'Active'
      AND ec.plan.deviceUpgrade IS NOT NULL
    GROUP BY device_id
    ORDER BY contract_count DESC
    """
    device_distribution_df = client.query(device_query).to_dataframe()
    logger.info(f"Retrieved device distribution for {len(device_distribution_df)} different device types")

    # Calculate total number of devices in use (for category percentage)
    total_devices = device_distribution_df['contract_count'].sum()
    logger.info(f"Total contracts with devices: {total_devices}")

    # 8. Get country distribution - directly from BigQuery
    country_query = """
    SELECT 
        ec.employmentLocation.country as country,
        COUNT(*) as contract_count
    FROM `outstaffer-app-prod.firestore_exports.employee_contracts` ec
    JOIN `outstaffer-app-prod.firestore_exports.companies` c
      ON ec.companyId = c.id
    JOIN `outstaffer-app-prod.lookup_tables.contract_status_mapping` cm
      ON ec.status = cm.contract_status
    WHERE (c.demoCompany IS NULL OR c.demoCompany = FALSE)
      AND (ec.__has_error__ IS NULL OR ec.__has_error__ = FALSE)
      AND cm.mapped_status = 'Active'
    GROUP BY country
    ORDER BY contract_count DESC
    """
    country_distribution_df = client.query(country_query).to_dataframe()
    logger.info(f"Retrieved country distribution for {len(country_distribution_df)} different countries")

    # 9. Get hardware add-ons distribution - improved query to properly handle nested fields
    hardware_query = """
    WITH contracts_with_hardware AS (
        SELECT
            ec.id as contract_id,
            ec.plan.hardwareAddons
        FROM `outstaffer-app-prod.firestore_exports.employee_contracts` ec
        JOIN `outstaffer-app-prod.firestore_exports.companies` c
            ON ec.companyId = c.id
        JOIN `outstaffer-app-prod.lookup_tables.contract_status_mapping` cm
            ON ec.status = cm.contract_status
        WHERE (c.demoCompany IS NULL OR c.demoCompany = FALSE)
            AND (ec.__has_error__ IS NULL OR ec.__has_error__ = FALSE)
            AND cm.mapped_status = 'Active'
            AND ec.plan.hardwareAddons IS NOT NULL
            AND ARRAY_LENGTH(ec.plan.hardwareAddons) > 0
    ),
    
    extracted_hardware AS (
        SELECT
            contract_id,
            JSON_EXTRACT_SCALAR(TO_JSON_STRING(addon), '$.key') as hardware_key,
            CAST(COALESCE(JSON_EXTRACT_SCALAR(TO_JSON_STRING(addon), '$.quantity'), '1') AS INT64) as quantity
        FROM contracts_with_hardware,
            UNNEST(hardwareAddons) as addon
        WHERE JSON_EXTRACT_SCALAR(TO_JSON_STRING(addon), '$.key') IS NOT NULL
    )
    
    SELECT 
        hardware_key, 
        COUNT(DISTINCT contract_id) as num_contracts, 
        SUM(quantity) as total_quantity
    FROM extracted_hardware
    GROUP BY hardware_key
    ORDER BY total_quantity DESC
    """

    hardware_distribution_df = client.query(hardware_query).to_dataframe()
    logger.info(f"Retrieved hardware add-ons distribution for {len(hardware_distribution_df)} different items")

    # Calculate total contracts with hardware addons (for category percentage)
    total_hardware_contracts = 0
    if not hardware_distribution_df.empty:
        total_hardware_contracts = hardware_distribution_df['num_contracts'].sum()
    logger.info(f"Total contracts with hardware add-ons: {total_hardware_contracts}")

    # 10. Get software add-ons distribution - improved query to properly handle nested fields
    software_query = """
    WITH contracts_with_software AS (
        SELECT
            ec.id as contract_id,
            ec.plan.softwareAddons
        FROM `outstaffer-app-prod.firestore_exports.employee_contracts` ec
        JOIN `outstaffer-app-prod.firestore_exports.companies` c
            ON ec.companyId = c.id
        JOIN `outstaffer-app-prod.lookup_tables.contract_status_mapping` cm
            ON ec.status = cm.contract_status
        WHERE (c.demoCompany IS NULL OR c.demoCompany = FALSE)
            AND (ec.__has_error__ IS NULL OR ec.__has_error__ = FALSE)
            AND cm.mapped_status = 'Active'
            AND ec.plan.softwareAddons IS NOT NULL
            AND ARRAY_LENGTH(ec.plan.softwareAddons) > 0
    ),
    
    extracted_software AS (
        SELECT
            contract_id,
            -- Try different ways to extract the key
            COALESCE(
                JSON_EXTRACT_SCALAR(TO_JSON_STRING(addon), '$.key'),
                CAST(addon AS STRING)
            ) as software_key,
            1 as quantity  -- Default quantity for software add-ons
        FROM contracts_with_software,
            UNNEST(softwareAddons) as addon
    )
    
    SELECT 
        software_key, 
        COUNT(DISTINCT contract_id) as num_contracts, 
        SUM(quantity) as total_quantity
    FROM extracted_software
    WHERE software_key IS NOT NULL
    GROUP BY software_key
    ORDER BY total_quantity DESC
    """

    software_distribution_df = client.query(software_query).to_dataframe()
    logger.info(f"Retrieved software add-ons distribution for {len(software_distribution_df)} different items")

    # Calculate total contracts with software addons (for category percentage)
    total_software_contracts = 0
    if not software_distribution_df.empty:
        total_software_contracts = software_distribution_df['num_contracts'].sum()
    logger.info(f"Total contracts with software add-ons: {total_software_contracts}")

    # 11. Get membership add-ons distribution - improved query to properly handle nested fields
    membership_query = """
    WITH contracts_with_membership AS (
        SELECT
            ec.id as contract_id,
            ec.plan.membershipAddons
        FROM `outstaffer-app-prod.firestore_exports.employee_contracts` ec
        JOIN `outstaffer-app-prod.firestore_exports.companies` c
            ON ec.companyId = c.id
        JOIN `outstaffer-app-prod.lookup_tables.contract_status_mapping` cm
            ON ec.status = cm.contract_status
        WHERE (c.demoCompany IS NULL OR c.demoCompany = FALSE)
            AND (ec.__has_error__ IS NULL OR ec.__has_error__ = FALSE)
            AND cm.mapped_status = 'Active'
            AND ec.plan.membershipAddons IS NOT NULL
            AND ARRAY_LENGTH(ec.plan.membershipAddons) > 0
    ),
    
    extracted_membership AS (
        SELECT
            contract_id,
            -- Try different ways to extract the key
            COALESCE(
                JSON_EXTRACT_SCALAR(TO_JSON_STRING(addon), '$.key'),
                CAST(addon AS STRING)
            ) as membership_key,
            1 as quantity  -- Default quantity for membership add-ons
        FROM contracts_with_membership,
            UNNEST(membershipAddons) as addon
    )
    
    SELECT 
        membership_key, 
        COUNT(DISTINCT contract_id) as num_contracts, 
        SUM(quantity) as total_quantity
    FROM extracted_membership
    WHERE membership_key IS NOT NULL
    GROUP BY membership_key
    ORDER BY total_quantity DESC
    """

    membership_distribution_df = client.query(membership_query).to_dataframe()
    logger.info(f"Retrieved membership add-ons distribution for {len(membership_distribution_df)} different items")

    # Calculate total contracts with membership addons (for category percentage)
    total_membership_contracts = 0
    if not membership_distribution_df.empty:
        total_membership_contracts = membership_distribution_df['num_contracts'].sum()
    logger.info(f"Total contracts with membership add-ons: {total_membership_contracts}")

    # 12. Get OS distribution based on device types
    os_query = """
    WITH device_addons AS (
      SELECT 
        id as addon_id, 
        label as addon_label, 
        meta
      FROM `outstaffer-app-prod.firestore_exports.plan_add_ons`
      WHERE type = 'DEVICE'
    ),
    
    active_contracts_with_devices AS (
      SELECT
        ec.id as contract_id,
        ec.plan.deviceUpgrade as device_id
      FROM `outstaffer-app-prod.firestore_exports.employee_contracts` ec
      JOIN `outstaffer-app-prod.firestore_exports.companies` c
        ON ec.companyId = c.id
      JOIN `outstaffer-app-prod.lookup_tables.contract_status_mapping` cm
        ON ec.status = cm.contract_status
      WHERE (c.demoCompany IS NULL OR c.demoCompany = FALSE)
        AND (ec.__has_error__ IS NULL OR ec.__has_error__ = FALSE)
        AND cm.mapped_status = 'Active'
        AND ec.plan.deviceUpgrade IS NOT NULL
    ),
    
    os_data AS (
      SELECT
        CASE
          WHEN JSON_EXTRACT_SCALAR(TO_JSON_STRING(da.meta), '$.operatingSystem') IS NOT NULL 
            THEN JSON_EXTRACT_SCALAR(TO_JSON_STRING(da.meta), '$.operatingSystem')
          WHEN STARTS_WITH(ac.device_id, 'WIN_') THEN 'Windows'
          WHEN STARTS_WITH(ac.device_id, 'APPLE_') THEN 'MacOS'
          WHEN LOWER(da.addon_label) LIKE '%windows%' OR LOWER(da.addon_label) LIKE '%win%' THEN 'Windows'
          WHEN LOWER(da.addon_label) LIKE '%mac%' OR LOWER(da.addon_label) LIKE '%apple%' OR LOWER(da.addon_label) LIKE '%macbook%' THEN 'MacOS'
          ELSE 'Unknown OS'
        END AS os_type,
        COUNT(*) as device_count
      FROM active_contracts_with_devices ac
      LEFT JOIN device_addons da ON ac.device_id = da.addon_id
      GROUP BY os_type
    )
    
    SELECT * FROM os_data ORDER BY device_count DESC
    """
    os_distribution_df = client.query(os_query).to_dataframe()
    logger.info(f"Retrieved OS distribution: {os_distribution_df['os_type'].tolist()}")

    # 13. PREPARE COMPLETE DATA (ensure zero count inclusion)

    # Plans - ensure all plans are included
    complete_plan_data = pd.merge(
        plans_df[['plan_id', 'plan_name']],
        plan_distribution_df,
        how='left',
        left_on='plan_id',
        right_on='plan_id'
    )
    complete_plan_data['contract_count'] = complete_plan_data['contract_count'].fillna(0).astype(int)

    # Devices - ensure all device types are included
    complete_device_data = pd.merge(
        device_addons[['addon_id', 'addon_label']],
        device_distribution_df.rename(columns={'device_id': 'addon_id'}),
        how='left',
        on='addon_id'
    )
    complete_device_data['contract_count'] = complete_device_data['contract_count'].fillna(0).astype(int)

    # Hardware add-ons - ensure all hardware types are included
    complete_hardware_data = pd.merge(
        hardware_addons[['addon_id', 'addon_label']],
        hardware_distribution_df.rename(columns={'hardware_key': 'addon_id', 'num_contracts': 'contract_count', 'total_quantity': 'quantity_count'}),
        how='left',
        on='addon_id'
    )
    complete_hardware_data['contract_count'] = complete_hardware_data['contract_count'].fillna(0).astype(int)
    complete_hardware_data['quantity_count'] = complete_hardware_data['quantity_count'].fillna(0).astype(int)

    # Software add-ons - ensure all software types are included
    complete_software_data = pd.merge(
        software_addons[['addon_id', 'addon_label']],
        software_distribution_df.rename(columns={'software_key': 'addon_id', 'num_contracts': 'contract_count', 'total_quantity': 'quantity_count'}),
        how='left',
        on='addon_id'
    )
    complete_software_data['contract_count'] = complete_software_data['contract_count'].fillna(0).astype(int)
    complete_software_data['quantity_count'] = complete_software_data['quantity_count'].fillna(0).astype(int)

    # Membership add-ons - ensure all membership types are included
    complete_membership_data = pd.merge(
        membership_addons[['addon_id', 'addon_label']],
        membership_distribution_df.rename(columns={'membership_key': 'addon_id', 'num_contracts': 'contract_count', 'total_quantity': 'quantity_count'}),
        how='left',
        on='addon_id'
    )
    complete_membership_data['contract_count'] = complete_membership_data['contract_count'].fillna(0).astype(int)
    complete_membership_data['quantity_count'] = complete_membership_data['quantity_count'].fillna(0).astype(int)

    # OS - we can't do a merge here since it's derived, but we can ensure Windows and MacOS are included
    all_os_types = ['Windows', 'MacOS']
    existing_os = os_distribution_df['os_type'].tolist()

    # Add missing OS types with count 0
    for os_type in all_os_types:
        if os_type not in existing_os:
            os_distribution_df = pd.concat([
                os_distribution_df,
                pd.DataFrame([{'os_type': os_type, 'device_count': 0}])
            ])

    # 14. Generate metrics with dual percentages
    plan_metrics = {
        'snapshot_date': snapshot_date,
        'metrics': []
    }

    # Add plan metrics
    for _, row in complete_plan_data.iterrows():
        plan_id = row['plan_id']
        count = row['contract_count']

        # Find plan name if available
        plan_name = row['plan_name'] if pd.notna(row['plan_name']) else str(plan_id)

        plan_metrics['metrics'].append({
            'metric_type': 'plan',
            'id': str(plan_id) if plan_id is not None else "unknown",
            'label': plan_name,
            'count': int(count),
            'overall_percentage': float(count) / total_active_contracts * 100 if total_active_contracts > 0 else 0,
            'category_percentage': 100.0,  # Each plan is its own category
            'contract_count': int(count)
        })

    # Add country metrics
    for _, row in country_distribution_df.iterrows():
        country = row['country']
        count = row['contract_count']

        plan_metrics['metrics'].append({
            'metric_type': 'country',
            'id': str(country) if country is not None else "unknown",
            'label': str(country) if country is not None else "Unknown",
            'count': int(count),
            'overall_percentage': float(count) / total_active_contracts * 100 if total_active_contracts > 0 else 0,
            'category_percentage': 100.0,  # Each country is its own category
            'contract_count': int(count)
        })

    # Add device metrics
    for _, row in complete_device_data.iterrows():
        device_id = row['addon_id']
        count = row['contract_count']
        device_label = row['addon_label'] if pd.notna(row['addon_label']) else str(device_id)

        plan_metrics['metrics'].append({
            'metric_type': 'device',
            'id': str(device_id) if device_id is not None else "unknown",
            'label': device_label if device_label is not None else "Unknown Device",
            'count': int(count),
            'overall_percentage': float(count) / total_active_contracts * 100 if total_active_contracts > 0 else 0,
            'category_percentage': float(count) / total_devices * 100 if total_devices > 0 else 0,
            'contract_count': int(count)
        })

    # Add hardware add-on metrics
    for _, row in complete_hardware_data.iterrows():
        addon_id = row['addon_id']
        contract_count = int(row['contract_count'])
        quantity_count = int(row['quantity_count']) if pd.notna(row.get('quantity_count')) else contract_count
        addon_label = row['addon_label'] if pd.notna(row['addon_label']) else str(addon_id)

        plan_metrics['metrics'].append({
            'metric_type': 'hardware_addon',
            'id': str(addon_id),
            'label': addon_label,
            'count': quantity_count,
            'overall_percentage': float(contract_count) / total_active_contracts * 100 if total_active_contracts > 0 else 0,
            'category_percentage': float(contract_count) / total_hardware_contracts * 100 if total_hardware_contracts > 0 else 0,
            'contract_count': contract_count
        })

    # Add software add-on metrics
    for _, row in complete_software_data.iterrows():
        addon_id = row['addon_id']
        contract_count = int(row['contract_count'])
        quantity_count = int(row['quantity_count']) if pd.notna(row.get('quantity_count')) else contract_count
        addon_label = row['addon_label'] if pd.notna(row['addon_label']) else str(addon_id)

        plan_metrics['metrics'].append({
            'metric_type': 'software_addon',
            'id': str(addon_id),
            'label': addon_label,
            'count': quantity_count,
            'overall_percentage': float(contract_count) / total_active_contracts * 100 if total_active_contracts > 0 else 0,
            'category_percentage': float(contract_count) / total_software_contracts * 100 if total_software_contracts > 0 else 0,
            'contract_count': contract_count
        })

    # Add membership add-on metrics
    for _, row in complete_membership_data.iterrows():
        addon_id = row['addon_id']
        contract_count = int(row['contract_count'])
        quantity_count = int(row['quantity_count']) if pd.notna(row.get('quantity_count')) else contract_count
        addon_label = row['addon_label'] if pd.notna(row['addon_label']) else str(addon_id)

        plan_metrics['metrics'].append({
            'metric_type': 'membership_addon',
            'id': str(addon_id),
            'label': addon_label,
            'count': quantity_count,
            'overall_percentage': float(contract_count) / total_active_contracts * 100 if total_active_contracts > 0 else 0,
            'category_percentage': float(contract_count) / total_membership_contracts * 100 if total_membership_contracts > 0 else 0,
            'contract_count': contract_count
        })

    # Add OS metrics
    for _, row in os_distribution_df.iterrows():
        os_type = row['os_type']
        count = row['device_count']

        plan_metrics['metrics'].append({
            'metric_type': 'os_choice',
            'id': os_type.upper().replace(' ', '_'),
            'label': os_type,
            'count': int(count),
            'overall_percentage': float(count) / total_active_contracts * 100 if total_active_contracts > 0 else 0,
            'category_percentage': float(count) / total_devices * 100 if total_devices > 0 else 0,
            'contract_count': int(count)
        })

    # 15. Convert metrics to DataFrame for BigQuery
    metrics_rows = []
    for metric in plan_metrics['metrics']:
        metrics_row = {
            'snapshot_date': snapshot_date,
            'metric_type': metric['metric_type'],
            'id': str(metric['id']),
            'label': str(metric['label']),
            'count': int(metric['count']),
            'overall_percentage': float(metric['overall_percentage']),
            'category_percentage': float(metric['category_percentage']),
            'contract_count': int(metric['contract_count'])
        }
        metrics_rows.append(metrics_row)

    metrics_df = pd.DataFrame(metrics_rows)

    # Log summary stats before writing
    logger.info(f"Generated metrics summary:")
    metric_summary = metrics_df.groupby('metric_type').size().reset_index(name='count')
    for _, row in metric_summary.iterrows():
        logger.info(f"  - {row['metric_type']}: {row['count']} items")

    # 16. Write to BigQuery
    table_id = 'outstaffer-app-prod.dashboard_metrics.plan_addon_adoption'

    # Define the updated schema with both percentage fields
    job_config = bigquery.LoadJobConfig(
        schema=[
            bigquery.SchemaField("snapshot_date", "DATE"),
            bigquery.SchemaField("metric_type", "STRING"),
            bigquery.SchemaField("id", "STRING"),
            bigquery.SchemaField("label", "STRING"),
            bigquery.SchemaField("count", "INTEGER"),
            bigquery.SchemaField("overall_percentage", "FLOAT"),
            bigquery.SchemaField("category_percentage", "FLOAT"),
            bigquery.SchemaField("contract_count", "INTEGER"),
        ],
        write_disposition="WRITE_APPEND",
    )

    # Write to BigQuery
    try:
        job = client.load_table_from_dataframe(metrics_df, table_id, job_config=job_config)
        job.result()  # Wait for the job to complete
        logger.info(f"Successfully wrote {len(metrics_df)} metrics to {table_id}")
    except Exception as e:
        logger.error(f"Error writing to BigQuery: {str(e)}")
        # Save locally if BigQuery fails
        metrics_df.to_csv(f"plan_adoption_metrics_{snapshot_date}.csv", index=False)
        logger.info(f"Saved metrics to local CSV file")

    # Return metrics for testing/debugging
    return metrics_df

if __name__ == "__main__":
    main()