from google.cloud import bigquery
import json
from datetime import datetime

# Initialize BigQuery client
client = bigquery.Client()

# Contract ID to analyze
CONTRACT_ID = "0207818e-70f5-4dee-bc25-b672e32e74b0"

# Query to get the latest calculation using UNNEST approach
print(f"Fetching latest calculation data for contract ID: {CONTRACT_ID}")
query = f"""
SELECT 
    ec.id,
    ec.status,
    calc.calculatedAt,
    calc.triggeredBy,
    calc.monthlyCharges.employerCharges.planCharges.categoryTotals.EOR.amount as eor_fee,
    calc.monthlyCharges.employerCharges.planCharges.categoryTotals.Health.amount as health_fee,
    calc.monthlyCharges.employerCharges.planCharges.categoryTotals.Device.amount as device_fee,
    calc.monthlyCharges.employerCharges.planCharges.categoryTotals.Hardware.amount as hardware_fee,
    calc.monthlyCharges.employerCharges.planCharges.categoryTotals.Software.amount as software_fee,
    calc.monthlyCharges.employerCharges.total.amount as total_monthly,
    calc.monthlyCharges.employerCharges.employeeCharges.baseSalary.amount as base_salary,
    calc.monthlyCharges.employerCharges.employeeCharges.totalEmployeeCharges.amount as employee_charges,
    calc.monthlyCharges.taasCharges.totalFee.value.amount as placement_fee,
    calc.monthlyCharges.oneOffCharges.securityDeposit.amount as security_deposit
FROM `outstaffer-app-prod.firestore_exports.employee_contracts` ec,
     UNNEST(ec.calculations) as calc
WHERE ec.id = '{CONTRACT_ID}'
ORDER BY calc.calculatedAt DESC
LIMIT 1
"""

# Execute the query
df = client.query(query).to_dataframe()

if len(df) == 0:
    print(f"No data found for contract ID: {CONTRACT_ID}")
    exit()

# Get the row data
row = df.iloc[0]

print(f"\n=== Latest Calculation for Contract {row['id']} (Status: {row['status']}) ===")
print(f"Calculation Date: {row['calculatedAt']}")
print(f"Triggered By: {row['triggeredBy']}")

print("\n--- Fee Values ---")
print(f"EOR Fee: {row['eor_fee']}")
print(f"Health Fee: {row['health_fee'] or 'None'}")
print(f"Device Fee: {row['device_fee']}")
print(f"Hardware Fee: {row['hardware_fee']}")
print(f"Software Fee: {row['software_fee']}")

print("\n--- Monthly Charges ---")
print(f"Base Salary: {row['base_salary']}")
print(f"Employee Charges: {row['employee_charges']}")
print(f"Total Monthly: {row['total_monthly']}")

if row['total_monthly']:
    try:
        monthly = float(row['total_monthly'])
        arr = monthly * 12
        print(f"Calculated ARR: {arr}")
    except Exception as e:
        print(f"Error calculating ARR: {e}")

print("\n--- One-Time Charges ---")
print(f"Placement Fee: {row['placement_fee']}")
print(f"Security Deposit: {row['security_deposit']}")

# Also provide the BigQuery SQL that can be used directly
print("\n=== SQL Query for BigQuery ===")
print(query)