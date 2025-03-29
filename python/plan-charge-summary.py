from google.cloud import bigquery
import pandas as pd
import json
from datetime import datetime
from collections import defaultdict

# Initialize BigQuery client
client = bigquery.Client()

def main():
    print("Fetching active employee contracts with plan charges...")

    # Query to get active contracts with latest calculations
    query = """
    WITH active_contracts AS (
        SELECT 
            ec.id,
            ec.employeeId,
            ec.status,
            ec.employmentLocation.country,
            cm.mapped_status,
            cm.contract_status
        FROM `outstaffer-app-prod.firestore_exports.employee_contracts` ec
        LEFT JOIN `outstaffer-app-prod.lookup_tables.contract_status_mapping` cm
            ON ec.status = cm.contract_status
        JOIN `outstaffer-app-prod.firestore_exports.companies` c
            ON ec.companyId = c.id
        WHERE 
            (c.demoCompany IS NULL OR c.demoCompany = FALSE)
            AND cm.mapped_status = 'Active'
    )
    
    -- Let's first print the active status mappings to debug
    SELECT contract_status, COUNT(*) as count
    FROM active_contracts
    GROUP BY contract_status
    ORDER BY count DESC
    """

    try:
        print("Executing query to check active contract statuses...")
        status_df = client.query(query).to_dataframe()

        if len(status_df) == 0:
            print("No active contracts found.")
            return

        print("\nActive contract statuses:")
        print(status_df.to_string(index=False))

        # Now query for the contract details
        contract_query = """
        WITH active_contracts AS (
            SELECT 
                ec.id,
                ec.employeeId,
                ec.status,
                ec.employmentLocation.country,
                cm.mapped_status
            FROM `outstaffer-app-prod.firestore_exports.employee_contracts` ec
            LEFT JOIN `outstaffer-app-prod.lookup_tables.contract_status_mapping` cm
                ON ec.status = cm.contract_status
            JOIN `outstaffer-app-prod.firestore_exports.companies` c
                ON ec.companyId = c.id
            WHERE 
                (c.demoCompany IS NULL OR c.demoCompany = FALSE)
                AND cm.mapped_status = 'Active'
        ),
        
        calculations_exploded AS (
            SELECT
                ec.id AS contract_id,
                ec.employmentLocation.country,
                calc.*,
                -- Debug: Print raw line items structure
                TO_JSON_STRING(calc.monthlyCharges.employerCharges.planCharges.lineItems) AS raw_line_items
            FROM `outstaffer-app-prod.firestore_exports.employee_contracts` ec
            CROSS JOIN UNNEST(ec.calculations) AS calc
            WHERE ec.id IN (SELECT id FROM active_contracts)
        ),
        
        latest_calcs AS (
            SELECT
                contract_id,
                country,
                ANY_VALUE(calculatedAt) AS calculatedAt,
                ANY_VALUE(triggeredBy) AS triggeredBy,
                ANY_VALUE(monthlyCharges.employerCharges.planCharges.categoryTotals) AS categoryTotals,
                ANY_VALUE(monthlyCharges.employerCharges.planCharges.lineItems) AS lineItems,
                ANY_VALUE(monthlyCharges.employerCharges.planCharges.total.amount) AS total_plan_charges,
                ANY_VALUE(monthlyCharges.employerCharges.total.amount) AS total_employer_charges,
                ANY_VALUE(raw_line_items) AS raw_line_items
            FROM (
                SELECT
                    contract_id,
                    country,
                    calculatedAt,
                    triggeredBy,
                    monthlyCharges,
                    raw_line_items,
                    ROW_NUMBER() OVER(PARTITION BY contract_id ORDER BY calculatedAt DESC) AS rn
                FROM calculations_exploded
            )
            WHERE rn = 1
            GROUP BY contract_id, country
        )
        
        SELECT * FROM latest_calcs
        """

        print("\nExecuting main query...")
        df = client.query(contract_query).to_dataframe()

        if len(df) == 0:
            print("No active contracts found with calculation data.")
            return

        print(f"\nAnalyzing {len(df)} active employee contracts...")

        # Debug line items
        print("\nDebugging line items...")
        sample_line_items = []
        for i, (idx, row) in enumerate(df.iterrows()):
            if i >= 3:  # Just check the first 3 records
                break

            if pd.notna(row['raw_line_items']):
                print(f"\nSample raw line items for contract {row['contract_id']}:")
                print(row['raw_line_items'][:500])

                try:
                    line_items = json.loads(row['raw_line_items'])
                    sample_line_items.append(line_items)
                    print(f"Successfully parsed {len(line_items)} line items")
                except Exception as e:
                    print(f"Error parsing line items: {str(e)}")

        # Process and summarize the data
        summarize_plan_charges(df)

    except Exception as e:
        print(f"Error executing query: {str(e)}")
        import traceback
        traceback.print_exc()
def extract_category_totals(category_totals):
    """Extract category totals from the JSON structure"""
    if not isinstance(category_totals, dict):
        return {}

    result = {}
    for category, data in category_totals.items():
        if isinstance(data, dict) and 'amount' in data:
            try:
                result[category] = float(data['amount'])
            except (ValueError, TypeError):
                result[category] = 0
    return result

def extract_line_items(line_items_data):
    """Extract line items from the JSON structure with detailed debugging"""
    result = []

    # Handle different possible formats of the data
    if isinstance(line_items_data, str):
        try:
            line_items = json.loads(line_items_data)
        except json.JSONDecodeError:
            print(f"Failed to parse line items JSON: {line_items_data[:100]}...")
            return result
    elif isinstance(line_items_data, list):
        line_items = line_items_data
    else:
        print(f"Unexpected line items type: {type(line_items_data)}")
        return result

    if not line_items:
        return result

    for item in line_items:
        if not isinstance(item, dict):
            continue

        category = item.get('category', 'Uncategorized')
        label = item.get('label', 'Unknown')
        amount = 0

        # Extract the amount - handle different possible structures
        if 'value' in item:
            if isinstance(item['value'], dict) and 'amount' in item['value']:
                try:
                    amount = float(item['value']['amount'])
                except (ValueError, TypeError):
                    pass
            elif isinstance(item['value'], (int, float, str)):
                try:
                    amount = float(item['value'])
                except (ValueError, TypeError):
                    pass

        quantity = item.get('quantity', 1)

        result.append({
            'category': category,
            'label': label,
            'amount': amount,
            'quantity': quantity
        })

    return result

def summarize_plan_charges(df):
    """Generate a comprehensive summary of plan charges"""
    total_contracts = len(df)

    # Initialize summary structures
    category_summary = defaultdict(lambda: {'total': 0, 'count': 0, 'avg': 0})
    line_item_summary = defaultdict(lambda: defaultdict(lambda: {'total': 0, 'count': 0, 'items': []}))
    country_summary = defaultdict(lambda: defaultdict(lambda: {'total': 0, 'count': 0}))

    # Track overall totals
    total_plan_charges = 0
    contracts_with_plan_charges = 0
    contracts_with_line_items = 0

    # Process each contract
    for _, row in df.iterrows():
        # Skip contracts with no data
        if pd.isna(row['categoryTotals']) and pd.isna(row['lineItems']) and pd.isna(row['raw_line_items']):
            continue

        # Get category totals
        category_totals = extract_category_totals(row['categoryTotals'])

        # Try to get line items from different possible sources
        line_items = []
        if not pd.isna(row['lineItems']):
            line_items = extract_line_items(row['lineItems'])
        elif not pd.isna(row['raw_line_items']):
            line_items = extract_line_items(row['raw_line_items'])

        # Count contracts with line items
        if line_items:
            contracts_with_line_items += 1

        # Skip if no plan charges
        if not category_totals and not line_items:
            continue

        contracts_with_plan_charges += 1
        country = row['country'] if pd.notna(row['country']) else 'Unknown'

        # Sum up total plan charges
        try:
            contract_total = float(row['total_plan_charges']) if pd.notna(row['total_plan_charges']) else 0
            total_plan_charges += contract_total
        except (ValueError, TypeError):
            contract_total = 0

        # Process category totals
        for category, amount in category_totals.items():
            category_summary[category]['total'] += amount
            category_summary[category]['count'] += 1

            # Track by country
            country_summary[country][category]['total'] += amount
            country_summary[country][category]['count'] += 1

        # Process line items
        for item in line_items:
            category = item['category']
            label = item['label']
            amount = item['amount']
            quantity = item['quantity']

            # Add to line item summary
            line_item_summary[category][label]['total'] += amount
            line_item_summary[category][label]['count'] += 1
            line_item_summary[category][label]['items'].append({
                'amount': amount,
                'quantity': quantity
            })

    # Calculate averages for categories
    for category, data in category_summary.items():
        if data['count'] > 0:
            data['avg'] = data['total'] / data['count']

    # Calculate averages for line items
    for category, items in line_item_summary.items():
        for label, data in items.items():
            if data['count'] > 0:
                data['avg'] = data['total'] / data['count']

    # Print summary
    print("\n" + "="*80)
    print(f"PLAN CHARGES SUMMARY FOR {total_contracts} ACTIVE CONTRACTS")
    print("="*80)

    # Fix the percentage calculation
    print(f"\nContracts with plan charges: {contracts_with_plan_charges} of {total_contracts} ({(contracts_with_plan_charges/total_contracts*100) if total_contracts > 0 else 0:.1f}%)")
    print(f"Contracts with line items: {contracts_with_line_items} of {total_contracts} ({(contracts_with_line_items/total_contracts*100) if total_contracts > 0 else 0:.1f}%)")

    if contracts_with_plan_charges > 0:
        print(f"Total monthly plan charges: ${total_plan_charges:,.2f}")
        print(f"Average monthly plan charges per contract: ${total_plan_charges/contracts_with_plan_charges:,.2f}")
    else:
        print("No plan charges found")

        # Process category totals
        for category, amount in category_totals.items():
            category_summary[category]['total'] += amount
            category_summary[category]['count'] += 1

            # Track by country
            country_summary[country][category]['total'] += amount
            country_summary[country][category]['count'] += 1

        # Process line items
        for item in line_items:
            category = item['category']
            label = item['label']
            amount = item['amount']
            quantity = item['quantity']

            # Add to line item summary
            line_item_summary[category][label]['total'] += amount
            line_item_summary[category][label]['count'] += 1
            line_item_summary[category][label]['items'].append({
                'amount': amount,
                'quantity': quantity
            })

    # Calculate averages for categories
    for category, data in category_summary.items():
        if data['count'] > 0:
            data['avg'] = data['total'] / data['count']

    # Calculate averages for line items
    for category, items in line_item_summary.items():
        for label, data in items.items():
            if data['count'] > 0:
                data['avg'] = data['total'] / data['count']

    # Print summary
    print("\n" + "="*80)
    print(f"PLAN CHARGES SUMMARY FOR {total_contracts} ACTIVE CONTRACTS")
    print("="*80)

    # Fix the percentage calculation
    print(f"\nContracts with plan charges: {contracts_with_plan_charges} of {total_contracts} ({(contracts_with_plan_charges/total_contracts*100) if total_contracts > 0 else 0:.1f}%)")
    if contracts_with_plan_charges > 0:
        print(f"Total monthly plan charges: ${total_plan_charges:,.2f}")
        print(f"Average monthly plan charges per contract: ${total_plan_charges/contracts_with_plan_charges:,.2f}")
    else:
        print("No plan charges found")

    # Category summary
    print("\n" + "-"*80)
    print("CATEGORY SUMMARY")
    print("-"*80)

    sorted_categories = sorted(category_summary.items(), key=lambda x: x[1]['total'], reverse=True)
    print(f"{'Category':<15} {'Total Amount':<15} {'# Contracts':<15} {'Avg Amount':<15} {'% of Total':<15}")
    print("-"*75)

    for category, data in sorted_categories:
        percent = (data['total'] / total_plan_charges * 100) if total_plan_charges > 0 else 0
        total_str = f"${data['total']:,.2f}"
        avg_str = f"${data['avg']:,.2f}"
        print(f"{category:<15} {total_str:<15} {data['count']:<15} {avg_str:<15} {percent:.1f}%")

    # Line item summary
    print("\n" + "-"*80)
    print("LINE ITEM SUMMARY")
    print("-"*80)

    for category in sorted(line_item_summary.keys()):
        print(f"\nCategory: {category}")
        print(f"{'Line Item':<30} {'Total Amount':<15} {'# Contracts':<15} {'Avg Amount':<15} {'Avg Quantity':<15}")
        print("-"*90)

        sorted_items = sorted(line_item_summary[category].items(), key=lambda x: x[1]['total'], reverse=True)

        for label, data in sorted_items:
            avg_quantity = sum(item['quantity'] for item in data['items']) / len(data['items']) if data['items'] else 1
            total_str = f"${data['total']:,.2f}"
            avg_str = f"${data['avg']:,.2f}"
            print(f"{label[:30]:<30} {total_str:<15} {data['count']:<15} {avg_str:<15} {avg_quantity:.2f}")

    # Top countries
    print("\n" + "-"*80)
    print("TOP COUNTRIES BY PLAN CHARGES")
    print("-"*80)

    # Calculate total by country
    country_totals = {}
    for country, categories in country_summary.items():
        country_totals[country] = sum(data['total'] for category, data in categories.items())

    sorted_countries = sorted(country_totals.items(), key=lambda x: x[1], reverse=True)[:10]  # Top 10

    print(f"{'Country':<15} {'Total Amount':<15} {'% of Total':<15} {'Top Category':<20}")
    print("-"*65)

    for country, total in sorted_countries:
        percent = (total / total_plan_charges * 100) if total_plan_charges > 0 else 0

        # Find top category for country
        top_category = max(country_summary[country].items(), key=lambda x: x[1]['total'], default=('None', {'total': 0}))[0]

        total_str = f"${total:,.2f}"
        percent_str = f"{percent:.1f}%"
        print(f"{country:<15} {total_str:<15} {percent_str:<15} {top_category:<20}")

if __name__ == "__main__":
    main()