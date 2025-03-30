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
    """
    plans_df = client.query(plans_query).to_dataframe()
    logger.info(f"Loaded {len(plans_df)} plan definitions")

    # 4. Count active contracts (this is our base count for percentage calculations)
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

    # 5. Get plan type distribution - directly from BigQuery using UNNEST
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

    # 6. Get device type distribution - directly from BigQuery
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

    # 7. Get country distribution - directly from BigQuery
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

    # 8. Get hardware add-ons distribution using UNNEST approach with safe extraction
    hardware_query = """
    WITH hardware_addons AS (
        SELECT
            ec.id as contract_id,
            -- Try to safely extract the key regardless of data structure
            SAFE_CAST(
                IF(addon.key IS NOT NULL, 
                   addon.key, 
                   IF(addon IS STRING, 
                      addon, 
                      TO_JSON_STRING(addon))
                ) AS STRING
            ) as hardware_key,
            -- Default quantity to 1 if not found
            COALESCE(addon.quantity, 1) as quantity
        FROM `outstaffer-app-prod.firestore_exports.employee_contracts` ec
        CROSS JOIN UNNEST(plan.hardwareAddons) as addon
        JOIN `outstaffer-app-prod.firestore_exports.companies` c
            ON ec.companyId = c.id
        JOIN `outstaffer-app-prod.lookup_tables.contract_status_mapping` cm
            ON ec.status = cm.contract_status
        WHERE (c.demoCompany IS NULL OR c.demoCompany = FALSE)
            AND (ec.__has_error__ IS NULL OR ec.__has_error__ = FALSE)
            AND cm.mapped_status = 'Active'
            AND plan.hardwareAddons IS NOT NULL
            AND ARRAY_LENGTH(plan.hardwareAddons) > 0
    )
    
    SELECT 
        hardware_key, 
        COUNT(DISTINCT contract_id) as num_contracts, 
        SUM(quantity) as total_quantity
    FROM hardware_addons
    WHERE hardware_key IS NOT NULL
    GROUP BY hardware_key
    ORDER BY total_quantity DESC
    """
    hardware_distribution_df = client.query(hardware_query).to_dataframe()
    logger.info(f"Retrieved hardware add-ons distribution for {len(hardware_distribution_df)} different items")

    # 9. Get software add-ons distribution using UNNEST approach with safe extraction
    software_query = """
    WITH software_addons AS (
        SELECT
            ec.id as contract_id,
            -- Try to safely extract the key regardless of data structure
            SAFE_CAST(
                IF(addon.key IS NOT NULL, 
                   addon.key, 
                   IF(addon IS STRING, 
                      addon, 
                      TO_JSON_STRING(addon))
                ) AS STRING
            ) as software_key,
            -- Default quantity to 1 if not found
            COALESCE(addon.quantity, 1) as quantity
        FROM `outstaffer-app-prod.firestore_exports.employee_contracts` ec
        CROSS JOIN UNNEST(plan.softwareAddons) as addon
        JOIN `outstaffer-app-prod.firestore_exports.companies` c
            ON ec.companyId = c.id
        JOIN `outstaffer-app-prod.lookup_tables.contract_status_mapping` cm
            ON ec.status = cm.contract_status
        WHERE (c.demoCompany IS NULL OR c.demoCompany = FALSE)
            AND (ec.__has_error__ IS NULL OR ec.__has_error__ = FALSE)
            AND cm.mapped_status = 'Active'
            AND plan.softwareAddons IS NOT NULL
            AND ARRAY_LENGTH(plan.softwareAddons) > 0
    )
    
    SELECT 
        software_key, 
        COUNT(DISTINCT contract_id) as num_contracts, 
        SUM(quantity) as total_quantity
    FROM software_addons
    WHERE software_key IS NOT NULL
    GROUP BY software_key
    ORDER BY total_quantity DESC
    """
    software_distribution_df = client.query(software_query).to_dataframe()
    logger.info(f"Retrieved software add-ons distribution for {len(software_distribution_df)} different items")

    # 10. Get membership add-ons distribution using UNNEST approach with safe extraction
    membership_query = """
    WITH membership_addons AS (
        SELECT
            ec.id as contract_id,
            -- Try to safely extract the key regardless of data structure
            SAFE_CAST(
                IF(addon.key IS NOT NULL, 
                   addon.key, 
                   IF(addon IS STRING, 
                      addon, 
                      TO_JSON_STRING(addon))
                ) AS STRING
            ) as membership_key,
            -- Default quantity to 1 if not found
            COALESCE(addon.quantity, 1) as quantity
        FROM `outstaffer-app-prod.firestore_exports.employee_contracts` ec
        CROSS JOIN UNNEST(plan.membershipAddons) as addon
        JOIN `outstaffer-app-prod.firestore_exports.companies` c
            ON ec.companyId = c.id
        JOIN `outstaffer-app-prod.lookup_tables.contract_status_mapping` cm
            ON ec.status = cm.contract_status
        WHERE (c.demoCompany IS NULL OR c.demoCompany = FALSE)
            AND (ec.__has_error__ IS NULL OR ec.__has_error__ = FALSE)
            AND cm.mapped_status = 'Active'
            AND plan.membershipAddons IS NOT NULL
            AND ARRAY_LENGTH(plan.membershipAddons) > 0
    )
    
    SELECT 
        membership_key, 
        COUNT(DISTINCT contract_id) as num_contracts, 
        SUM(quantity) as total_quantity
    FROM membership_addons
    WHERE membership_key IS NOT NULL
    GROUP BY membership_key
    ORDER BY total_quantity DESC
    """
    membership_distribution_df = client.query(membership_query).to_dataframe()
    logger.info(f"Retrieved membership add-ons distribution for {len(membership_distribution_df)} different items")

    # 11. Fetch OS and device metadata to enrich device data
    device_addons = addons_df[addons_df['addon_type'] == 'DEVICE'].copy()

    # 12. Generate plan adoption metrics
    plan_metrics = {
        'snapshot_date': snapshot_date,
        'metrics': []
    }

    # Add plan metrics
    for _, row in plan_distribution_df.iterrows():
        plan_id = row['plan_id']
        count = row['contract_count']
        # Use plan name if available, otherwise use ID
        plan_name = "Unknown Plan"
        matching_plans = plans_df[plans_df['plan_id'] == plan_id]
        if len(matching_plans) > 0:
            plan_name = matching_plans.iloc[0]['plan_name']
        else:
            plan_name = str(plan_id)

        plan_metrics['metrics'].append({
            'metric_type': 'plan',
            'id': str(plan_id) if plan_id is not None else "unknown",
            'label': plan_name,
            'count': int(count),
            'percentage': float(count) / total_active_contracts * 100 if total_active_contracts > 0 else 0
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
            'percentage': float(count) / total_active_contracts * 100 if total_active_contracts > 0 else 0
        })

    # Add device metrics
    for _, row in device_distribution_df.iterrows():
        device_id = row['device_id']
        count = row['contract_count']

        # Find device label if available
        device_label = device_id
        matching_device = device_addons[device_addons['addon_id'] == device_id]
        if len(matching_device) > 0:
            device_label = matching_device.iloc[0]['addon_label']

        plan_metrics['metrics'].append({
            'metric_type': 'device',
            'id': str(device_id) if device_id is not None else "unknown",
            'label': device_label if device_label is not None else "Unknown Device",
            'count': int(count),
            'percentage': float(count) / total_active_contracts * 100 if total_active_contracts > 0 else 0
        })

    # Add hardware add-on metrics
    for _, row in hardware_distribution_df.iterrows():
        addon_id = row['hardware_key']
        count = row['total_quantity']
        num_contracts = row['num_contracts']

        # Find add-on label if available
        addon_label = addon_id
        matching_addon = addons_df[(addons_df['addon_id'] == addon_id) & (addons_df['addon_type'] == 'HARDWARE')]
        if len(matching_addon) > 0:
            addon_label = matching_addon.iloc[0]['addon_label']

        plan_metrics['metrics'].append({
            'metric_type': 'hardware_addon',
            'id': str(addon_id),
            'label': addon_label,
            'count': int(count),
            'contract_count': int(num_contracts),
            'percentage': float(num_contracts) / total_active_contracts * 100 if total_active_contracts > 0 else 0
        })

    # Add software add-on metrics
    for _, row in software_distribution_df.iterrows():
        addon_id = row['software_key']
        count = row['total_quantity']
        num_contracts = row['num_contracts']

        # Find add-on label if available
        addon_label = addon_id
        matching_addon = addons_df[(addons_df['addon_id'] == addon_id) & (addons_df['addon_type'] == 'SOFTWARE')]
        if len(matching_addon) > 0:
            addon_label = matching_addon.iloc[0]['addon_label']

        plan_metrics['metrics'].append({
            'metric_type': 'software_addon',
            'id': str(addon_id),
            'label': addon_label,
            'count': int(count),
            'contract_count': int(num_contracts),
            'percentage': float(num_contracts) / total_active_contracts * 100 if total_active_contracts > 0 else 0
        })

    # Add membership add-on metrics
    for _, row in membership_distribution_df.iterrows():
        addon_id = row['membership_key']
        count = row['total_quantity']
        num_contracts = row['num_contracts']

        # Find add-on label if available
        addon_label = addon_id
        matching_addon = addons_df[(addons_df['addon_id'] == addon_id) & (addons_df['addon_type'] == 'MEMBERSHIP')]
        if len(matching_addon) > 0:
            addon_label = matching_addon.iloc[0]['addon_label']

        plan_metrics['metrics'].append({
            'metric_type': 'membership_addon',
            'id': str(addon_id),
            'label': addon_label,
            'count': int(count),
            'contract_count': int(num_contracts),
            'percentage': float(num_contracts) / total_active_contracts * 100 if total_active_contracts > 0 else 0
        })

    # 13. Add OS distribution metrics by analyzing devices
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
          WHEN da.meta.operatingSystem IS NOT NULL THEN da.meta.operatingSystem
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

    # Add OS metrics
    for _, row in os_distribution_df.iterrows():
        os_type = row['os_type']
        count = row['device_count']

        plan_metrics['metrics'].append({
            'metric_type': 'os_choice',
            'id': os_type.upper().replace(' ', '_'),
            'label': os_type,
            'count': int(count),
            'percentage': float(count) / total_active_contracts * 100 if total_active_contracts > 0 else 0
        })

    # 14. Convert metrics to DataFrame for BigQuery
    metrics_rows = []
    for metric in plan_metrics['metrics']:
        metrics_row = {
            'snapshot_date': snapshot_date,
            'metric_type': metric['metric_type'],
            'id': str(metric['id']),
            'label': str(metric['label']),
            'count': int(metric['count']),
            'percentage': float(metric['percentage'])
        }

        # Add contract_count if available (for add-ons where count ≠ contract count)
        if 'contract_count' in metric:
            metrics_row['contract_count'] = int(metric['contract_count'])
        else:
            metrics_row['contract_count'] = int(metric['count'])  # Default to count

        metrics_rows.append(metrics_row)

    metrics_df = pd.DataFrame(metrics_rows)

    # Log summary stats before writing
    logger.info(f"Generated metrics summary:")
    metric_summary = metrics_df.groupby('metric_type').size().reset_index(name='count')
    for _, row in metric_summary.iterrows():
        logger.info(f"  - {row['metric_type']}: {row['count']} items")

    # 15. Write to BigQuery
    table_id = 'outstaffer-app-prod.dashboard_metrics.plan_addon_adoption'

    # Define the schema
    job_config = bigquery.LoadJobConfig(
        schema=[
            bigquery.SchemaField("snapshot_date", "DATE"),
            bigquery.SchemaField("metric_type", "STRING"),
            bigquery.SchemaField("id", "STRING"),
            bigquery.SchemaField("label", "STRING"),
            bigquery.SchemaField("count", "INTEGER"),
            bigquery.SchemaField("contract_count", "INTEGER"),
            bigquery.SchemaField("percentage", "FLOAT"),
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