import pandas as pd
from google.cloud import bigquery
import logging
import sys
from datetime import datetime
import re

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger('plan-addons-snapshot')

# Initialize BigQuery client
client = bigquery.Client()

def get_os_from_device(device_meta, device_id, device_label):
    """
    Dynamically determine OS from device metadata, falling back to ID/label parsing
    """
    # First try to get from metadata
    if isinstance(device_meta, dict) and 'operatingSystem' in device_meta:
        return device_meta['operatingSystem']

    # Fall back to ID/label pattern matching
    if device_id:
        if device_id.startswith('WIN_'):
            return 'Windows'
        elif device_id.startswith('APPLE_'):
            return 'MacOS'

    # Try to parse from label
    if isinstance(device_label, str):
        label_lower = device_label.lower()
        if any(term in label_lower for term in ['windows', 'win']):
            return 'Windows'
        elif any(term in label_lower for term in ['mac', 'apple', 'macbook']):
            return 'MacOS'

    # If all else fails
    return 'Unknown OS'

def get_persona_from_device(device_meta, device_id, device_label):
    """
    Dynamically determine user persona from metadata, falling back to ID/label parsing
    """
    # First try to get from metadata
    if isinstance(device_meta, dict) and 'userPersona' in device_meta:
        return device_meta['userPersona']

    # Try to parse from ID
    if device_id:
        # Extract the persona part from device_id if it follows a pattern
        if '_EVERYDAY' in device_id:
            return 'Everyday task'
        elif '_POWER' in device_id:
            return 'Power users'
        elif '_DES_DEV' in device_id:
            return 'Designers/Developers'
        elif '_ULTIMATE' in device_id:
            return 'Ultimate'

    # Try to parse from label
    if isinstance(device_label, str):
        label_lower = device_label.lower()

        # Look for persona indicators in the label
        if 'everyday' in label_lower or '(everyday' in label_lower:
            return 'Everyday task'
        elif 'power' in label_lower:
            return 'Power users'
        elif 'designer' in label_lower or 'developer' in label_lower:
            return 'Designers/Developers'
        elif 'ultimate' in label_lower:
            return 'Ultimate'

    # If all else fails
    return 'Unknown Persona'

def get_hardware_group(addon_id, addon_label, select_one_group_name):
    """
    Determine hardware group from selectOnePerGroupName or by pattern matching
    """
    # First check if we have a group name
    if select_one_group_name:
        return select_one_group_name

    # Otherwise try to determine from ID/label
    if addon_id:
        # Check common patterns
        if addon_id.startswith('MONITOR_'):
            return 'MONITOR'
        elif 'DOCK' in addon_id:
            return 'DOCK'
        elif 'KEYBOARD' in addon_id or 'MOUSE' in addon_id:
            return 'INPUT_DEVICE'

    # Try to parse from label
    if isinstance(addon_label, str):
        label_lower = addon_label.lower()
        if 'monitor' in label_lower or '"' in label_lower: # Monitors often have inch symbol
            return 'MONITOR'
        elif 'dock' in label_lower:
            return 'DOCK'
        elif 'keyboard' in label_lower or 'mouse' in label_lower:
            return 'INPUT_DEVICE'

    # If we can't determine a group, return the ID itself
    return addon_id

def extract_meta_field(meta_field):
    """Helper function to extract and parse meta field from add-on"""
    if isinstance(meta_field, dict):
        return meta_field

    # Try to parse JSON if it's a string
    if isinstance(meta_field, str):
        try:
            import json
            return json.loads(meta_field)
        except:
            pass

    return {}

def main():
    # Define snapshot date as today
    snapshot_date = datetime.now().date()
    logger.info(f"Processing plan and add-on adoption snapshot for: {snapshot_date}")

    # 1. Load add-on metadata from the actual table - including the meta field
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

    # Debug output to check hardware add-ons in the reference data
    hardware_addon_ids = set(addons_df[addons_df['addon_type'] == 'HARDWARE']['addon_id'])
    logger.info(f"Hardware add-on IDs in reference data: {hardware_addon_ids}")

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

    # 4. Load ONLY active contracts with filtered conditions in the query
    contracts_query = """
    SELECT 
        ec.id as contract_id,
        ec.companyId,
        ec.status as contract_status,
        ec.employmentLocation.country as country,
        ec.plan, -- Include the plan field
        ec.plan.type as plan_id, -- Extract the plan type ID
        ec.createdAt,
        ec.updatedAt
    FROM `outstaffer-app-prod.firestore_exports.employee_contracts` ec
    JOIN `outstaffer-app-prod.firestore_exports.companies` c
      ON ec.companyId = c.id
    JOIN `outstaffer-app-prod.lookup_tables.contract_status_mapping` cm
      ON ec.status = cm.contract_status
    WHERE (c.demoCompany IS NULL OR c.demoCompany = FALSE)
      AND (ec.__has_error__ IS NULL OR ec.__has_error__ = FALSE)
      AND cm.mapped_status = 'Active'
    """
    active_contracts_df = client.query(contracts_query).to_dataframe()
    logger.info(f"Loaded {len(active_contracts_df)} active contracts")

    # Debug the plan field structure in a few contracts
    hardware_keys_found = set()
    for i, (_, contract) in enumerate(active_contracts_df.head(3).iterrows()):
        plan_data = contract['plan']
        logger.info(f"Sample contract {i+1} plan: {type(plan_data)}")

        if isinstance(plan_data, dict):
            logger.info(f"  Plan keys: {plan_data.keys()}")
            if 'hardwareAddons' in plan_data:
                logger.info(f"  Hardware addons: {plan_data['hardwareAddons']}")
                # Collect all hardware keys
                if isinstance(plan_data['hardwareAddons'], list):
                    for addon in plan_data['hardwareAddons']:
                        if isinstance(addon, dict) and 'key' in addon:
                            hardware_keys_found.add(addon['key'])

    logger.info(f"Hardware add-on keys found in sample contracts: {hardware_keys_found}")

    # Check for mismatches
    hardware_mismatches = hardware_keys_found - hardware_addon_ids
    logger.info(f"Keys in contracts but not in add-ons dataframe: {hardware_mismatches}")

    # 5. Get plan details directly rather than merging to avoid dictionary issues
    def get_plan_name(plan_id):
        if plan_id is None:
            return "Unknown Plan"
        plan_rows = plans_df[plans_df['plan_id'] == plan_id]
        if len(plan_rows) > 0:
            return plan_rows.iloc[0]['plan_name']
        return plan_id  # Default to ID if not found

    # Apply the function safely with null handling
    active_contracts_df['plan_name'] = active_contracts_df['plan_id'].apply(
        lambda x: get_plan_name(x) if pd.notna(x) else "Unknown Plan"
    )

    # 6. Extract add-ons from plan field
    def extract_device_type(plan):
        if plan is None or not isinstance(plan, dict):
            return None
        return plan.get('deviceUpgrade')

    def extract_hardware_addons(plan):
        if plan is None or not isinstance(plan, dict):
            return []
        hardware = plan.get('hardwareAddons', [])
        return hardware if isinstance(hardware, list) else []

    def extract_software_addons(plan):
        if plan is None or not isinstance(plan, dict):
            return []
        software = plan.get('softwareAddons', [])
        return software if isinstance(software, list) else []

    def extract_membership_addons(plan):
        if plan is None or not isinstance(plan, dict):
            return []
        membership = plan.get('membershipAddons', [])
        return membership if isinstance(membership, list) else []

    # Extract add-ons from plan
    active_contracts_df['device_type'] = active_contracts_df['plan'].apply(extract_device_type)
    active_contracts_df['hardware_addons'] = active_contracts_df['plan'].apply(extract_hardware_addons)
    active_contracts_df['software_addons'] = active_contracts_df['plan'].apply(extract_software_addons)
    active_contracts_df['membership_addons'] = active_contracts_df['plan'].apply(extract_membership_addons)

    # Check extraction results
    total_devices = active_contracts_df['device_type'].notna().sum()
    total_hw = sum(len(addons) for addons in active_contracts_df['hardware_addons'] if isinstance(addons, list))
    total_sw = sum(len(addons) for addons in active_contracts_df['software_addons'] if isinstance(addons, list))
    total_mb = sum(len(addons) for addons in active_contracts_df['membership_addons'] if isinstance(addons, list))

    logger.info(f"Extracted {total_devices} devices, {total_hw} hardware add-ons, {total_sw} software add-ons, {total_mb} membership add-ons")

    # 7. Generate plan adoption metrics
    plan_metrics = {
        'snapshot_date': snapshot_date,
        'metrics': []
    }

    # Plan type adoption
    plan_counts = active_contracts_df['plan_id'].value_counts().reset_index()
    plan_counts.columns = ['plan_id', 'contract_count']

    for _, row in plan_counts.iterrows():
        plan_id = row['plan_id']
        count = row['contract_count']
        # Use plan name if available, otherwise use ID
        matching_plans = active_contracts_df[active_contracts_df['plan_id'] == plan_id]
        plan_name = matching_plans['plan_name'].iloc[0] if len(matching_plans) > 0 else plan_id

        plan_metrics['metrics'].append({
            'metric_type': 'plan',
            'id': plan_id,
            'label': plan_name,
            'count': int(count),
            'percentage': float(count) / len(active_contracts_df) * 100 if len(active_contracts_df) > 0 else 0
        })

    # Country distribution
    country_counts = active_contracts_df['country'].value_counts().reset_index()
    country_counts.columns = ['country', 'contract_count']

    for _, row in country_counts.iterrows():
        country = row['country']
        count = row['contract_count']

        plan_metrics['metrics'].append({
            'metric_type': 'country',
            'id': country,
            'label': country,
            'count': int(count),
            'percentage': float(count) / len(active_contracts_df) * 100 if len(active_contracts_df) > 0 else 0
        })

    # 8. Process device choices with dynamic OS and persona detection
    device_counts = active_contracts_df['device_type'].value_counts().reset_index()
    device_counts.columns = ['device_id', 'device_count']

    # Debug device counts
    logger.info(f"Device counts: {device_counts.to_dict(orient='records')}")

    # Initialize OS and persona dictionaries
    os_counts = {}
    persona_counts = {}

    # Get all device addons for metadata reference
    device_addons = addons_df[addons_df['addon_type'] == 'DEVICE'].copy()

    # Process each device to determine OS and persona
    for _, contract in active_contracts_df.iterrows():
        device_id = contract['device_type']
        if not device_id:
            continue

        # Find device metadata if available
        device_meta = {}
        device_label = None
        matching_device = device_addons[device_addons['addon_id'] == device_id]

        if len(matching_device) > 0:
            device_meta = extract_meta_field(matching_device.iloc[0]['meta'])
            device_label = matching_device.iloc[0]['addon_label']

        # Determine OS dynamically
        os_type = get_os_from_device(device_meta, device_id, device_label)
        if os_type in os_counts:
            os_counts[os_type] += 1
        else:
            os_counts[os_type] = 1

        # Determine persona dynamically
        persona = get_persona_from_device(device_meta, device_id, device_label)
        if persona in persona_counts:
            persona_counts[persona] += 1
        else:
            persona_counts[persona] = 1

    # Generate device metrics
    device_metrics = []

    # Make sure we include all possible device types, even if count is 0
    for _, addon in device_addons.iterrows():
        addon_id = addon['addon_id']
        count = device_counts.loc[device_counts['device_id'] == addon_id, 'device_count'].iloc[0] if len(device_counts.loc[device_counts['device_id'] == addon_id]) > 0 else 0

        device_metrics.append({
            'metric_type': 'device',
            'id': addon_id,
            'label': addon['addon_label'],
            'count': int(count),
            'percentage': float(count) / len(active_contracts_df) * 100 if len(active_contracts_df) > 0 else 0
        })

    # Also include any devices found that aren't in our add-ons table
    for _, row in device_counts.iterrows():
        device_id = row['device_id']
        if device_id is not None and not device_addons['addon_id'].isin([device_id]).any():
            device_metrics.append({
                'metric_type': 'device',
                'id': device_id,
                'label': device_id,  # Use ID as label since we don't have the proper label
                'count': int(row['device_count']),
                'percentage': float(row['device_count']) / len(active_contracts_df) * 100 if len(active_contracts_df) > 0 else 0
            })

    plan_metrics['metrics'].extend(device_metrics)

    # 9. Process hardware add-ons with dynamic grouping
    # Initialize counter for all hardware add-ons
    hardware_addon_counts = {}
    hardware_group_counts = {}  # For group totals

    # Initialize group mappings to track which items belong to which groups
    hardware_groups = {}

    # Get all hardware addons
    hardware_addons = addons_df[addons_df['addon_type'] == 'HARDWARE'].copy()

    # Debug hardware add-ons
    logger.info(f"Hardware add-ons reference data: {hardware_addons[['addon_id', 'addon_label']].to_dict(orient='records')}")

    # Build group mapping first
    for _, addon in hardware_addons.iterrows():
        addon_id = addon['addon_id']
        group_name = get_hardware_group(addon_id, addon['addon_label'], addon.get('selectOnePerGroupName'))
        hardware_groups[addon_id] = group_name

        # Initialize counters
        hardware_addon_counts[addon_id] = 0
        if group_name not in hardware_group_counts:
            hardware_group_counts[group_name] = 0

    # Count occurrences in contracts - Debug and fix issue with hardware add-ons
    hardware_keys_in_contracts = []
    for _, contract in active_contracts_df.iterrows():
        hardware_addons_list = contract['hardware_addons']
        if not isinstance(hardware_addons_list, list):
            logger.info(f"Non-list hardware addons found: {type(hardware_addons_list)}")
            continue

        for addon in hardware_addons_list:
            if isinstance(addon, dict) and 'key' in addon:
                addon_key = addon['key']
                quantity = addon.get('quantity', 1)
                hardware_keys_in_contracts.append(addon_key)

                if addon_key in hardware_addon_counts:
                    hardware_addon_counts[addon_key] += quantity

                    # Also increment the group counter if this item belongs to a group
                    if addon_key in hardware_groups:
                        group_name = hardware_groups[addon_key]
                        hardware_group_counts[group_name] += quantity
                else:
                    # Add any hardware types not in our add-ons table
                    hardware_addon_counts[addon_key] = quantity

                    # Try to determine group dynamically
                    group_name = get_hardware_group(addon_key, addon_key, None)  # Use key as label for unknown items

                    if group_name not in hardware_group_counts:
                        hardware_group_counts[group_name] = 0
                    hardware_group_counts[group_name] += quantity

    # Debug hardware counts
    logger.info(f"Hardware keys found in contracts: {set(hardware_keys_in_contracts)}")
    logger.info(f"Hardware addon counts: {hardware_addon_counts}")
    logger.info(f"Hardware group counts: {hardware_group_counts}")

    # Add individual hardware items to metrics
    for addon_id, count in hardware_addon_counts.items():
        matching_addons = hardware_addons[hardware_addons['addon_id'] == addon_id]
        addon_label = matching_addons.iloc[0]['addon_label'] if len(matching_addons) > 0 else addon_id

        plan_metrics['metrics'].append({
            'metric_type': 'hardware_addon',
            'id': addon_id,
            'label': addon_label,
            'count': int(count),
            'percentage': float(count) / len(active_contracts_df) * 100 if len(active_contracts_df) > 0 else 0
        })

    # Add hardware group totals to metrics
    for group_name, count in hardware_group_counts.items():
        # Skip groups with 0 or if they're the same as an individual item
        if count == 0 or group_name in hardware_addon_counts:
            continue

        plan_metrics['metrics'].append({
            'metric_type': 'hardware_group',
            'id': f"GROUP_{group_name}",
            'label': f"All {group_name.lower().replace('_', ' ')}s",
            'count': int(count),
            'percentage': float(count) / len(active_contracts_df) * 100 if len(active_contracts_df) > 0 else 0
        })

    # 10. Process software add-ons - UPDATED for the new plan structure
    software_addon_counts = {}

    # Initialize counts for all software add-ons
    for _, addon in addons_df[addons_df['addon_type'] == 'SOFTWARE'].iterrows():
        software_addon_counts[addon['addon_id']] = 0

    # Count occurrences in contracts
    software_keys_in_contracts = []
    for _, contract in active_contracts_df.iterrows():
        software_addons = contract['software_addons']
        if not isinstance(software_addons, list):
            continue

        for addon_id in software_addons:
            software_keys_in_contracts.append(addon_id)
            if addon_id in software_addon_counts:
                software_addon_counts[addon_id] += 1
            else:
                # Add any software types not in our add-ons table
                software_addon_counts[addon_id] = 1

    # Debug software counts
    logger.info(f"Software keys found in contracts: {set(software_keys_in_contracts)}")
    logger.info(f"Software addon counts: {software_addon_counts}")

    # Add to metrics
    for addon_id, count in software_addon_counts.items():
        matching_addons = addons_df[(addons_df['addon_id'] == addon_id) & (addons_df['addon_type'] == 'SOFTWARE')]
        addon_label = matching_addons.iloc[0]['addon_label'] if len(matching_addons) > 0 else addon_id

        plan_metrics['metrics'].append({
            'metric_type': 'software_addon',
            'id': addon_id,
            'label': addon_label,
            'count': int(count),
            'percentage': float(count) / len(active_contracts_df) * 100 if len(active_contracts_df) > 0 else 0
        })

    # 11. Process membership add-ons - UPDATED for the new plan structure
    membership_addon_counts = {}

    # Initialize counts for all membership add-ons
    for _, addon in addons_df[addons_df['addon_type'] == 'MEMBERSHIP'].iterrows():
        membership_addon_counts[addon['addon_id']] = 0

    # Count occurrences in contracts
    membership_keys_in_contracts = []
    for _, contract in active_contracts_df.iterrows():
        membership_addons = contract['membership_addons']
        if not isinstance(membership_addons, list):
            continue

        for addon_id in membership_addons:
            membership_keys_in_contracts.append(addon_id)
            if addon_id in membership_addon_counts:
                membership_addon_counts[addon_id] += 1
            else:
                # Add any membership types not in our add-ons table
                membership_addon_counts[addon_id] = 1

    # Debug membership counts
    logger.info(f"Membership keys found in contracts: {set(membership_keys_in_contracts)}")
    logger.info(f"Membership addon counts: {membership_addon_counts}")

    # Add to metrics
    for addon_id, count in membership_addon_counts.items():
        matching_addons = addons_df[(addons_df['addon_id'] == addon_id) & (addons_df['addon_type'] == 'MEMBERSHIP')]
        addon_label = matching_addons.iloc[0]['addon_label'] if len(matching_addons) > 0 else addon_id

        plan_metrics['metrics'].append({
            'metric_type': 'membership_addon',
            'id': addon_id,
            'label': addon_label,
            'count': int(count),
            'percentage': float(count) / len(active_contracts_df) * 100 if len(active_contracts_df) > 0 else 0
        })

    # 12. Add dynamic OS distribution metrics
    for os_type, count in os_counts.items():
        plan_metrics['metrics'].append({
            'metric_type': 'os_choice',
            'id': os_type.upper().replace(' ', '_'),
            'label': os_type,
            'count': int(count),
            'percentage': float(count) / len(active_contracts_df) * 100 if len(active_contracts_df) > 0 else 0
        })

    # 13. Add dynamic user persona metrics
    for persona, count in persona_counts.items():
        plan_metrics['metrics'].append({
            'metric_type': 'user_persona',
            'id': persona.upper().replace(' ', '_').replace('/', '_'),
            'label': persona,
            'count': int(count),
            'percentage': float(count) / len(active_contracts_df) * 100 if len(active_contracts_df) > 0 else 0
        })

    # 14. Convert metrics to DataFrame for BigQuery
    metrics_rows = []
    for metric in plan_metrics['metrics']:
        metrics_rows.append({
            'snapshot_date': snapshot_date,
            'metric_type': metric['metric_type'],
            'id': str(metric['id']),  # Ensure ID is string
            'label': str(metric['label']),  # Ensure label is string
            'count': int(metric['count']),
            'percentage': float(metric['percentage'])
        })

    metrics_df = pd.DataFrame(metrics_rows)

    # Log summary stats before writing
    logger.info(f"Generated metrics for:")
    for metric_type in metrics_df['metric_type'].unique():
        count = len(metrics_df[metrics_df['metric_type'] == metric_type])
        logger.info(f"  - {metric_type}: {count} items")

    # Log metrics with non-zero counts
    non_zero_metrics = metrics_df[metrics_df['count'] > 0]
    logger.info(f"Metrics with non-zero counts: {len(non_zero_metrics)} of {len(metrics_df)}")
    if len(non_zero_metrics) > 0:
        logger.info(f"Sample non-zero metrics: {non_zero_metrics.head(5)[['metric_type', 'id', 'count']].to_dict(orient='records')}")

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