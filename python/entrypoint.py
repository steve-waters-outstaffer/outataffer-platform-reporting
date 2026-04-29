#!/usr/bin/env python3
"""
entrypoint.py - Dynamic script runner for Cloud Run Jobs

Runs snapshot scripts based on the SCRIPT_NAME environment variable.
All scripts follow the same pattern: query a BigQuery view, write to a
dashboard_metrics table.

Available scripts:
  snapshot_revenue.py           — monthly_revenue_metrics
  snapshot_customers.py         — customer_snapshot
  snapshot_geographic.py        — geographic_metrics
  snapshot_health_insurance.py  — health_insurance_metrics
  snapshot_plan_addons.py       — plan_addon_adoption
  snapshot_requisitions.py      — requisition_snapshots
"""

import os
import sys
import subprocess
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('entrypoint')

VALID_SCRIPTS = {
    'snapshot_revenue.py',
    'snapshot_customers.py',
    'snapshot_geographic.py',
    'snapshot_health_insurance.py',
    'snapshot_plan_addons.py',
    'snapshot_requisitions.py',
}

def main():
    script_name = os.getenv('SCRIPT_NAME', 'snapshot_revenue.py')

    logger.info(f"Starting Cloud Run Job: {script_name}")

    if script_name not in VALID_SCRIPTS:
        logger.error(f"Unknown script: {script_name}. Valid options: {sorted(VALID_SCRIPTS)}")
        sys.exit(1)

    if not os.path.exists(script_name):
        logger.error(f"Script not found on disk: {script_name}")
        sys.exit(1)

    args = os.getenv('SCRIPT_ARGS', '').split() if os.getenv('SCRIPT_ARGS') else []
    cmd = ['python', script_name] + args

    logger.info(f"Executing: {' '.join(cmd)}")

    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)

        if result.stdout:
            logger.info(f"STDOUT:\n{result.stdout}")
        if result.stderr:
            logger.warning(f"STDERR:\n{result.stderr}")

        logger.info("Script completed successfully")

    except subprocess.CalledProcessError as e:
        logger.error(f"Script failed with exit code {e.returncode}")
        if e.stdout:
            logger.error(f"STDOUT:\n{e.stdout}")
        if e.stderr:
            logger.error(f"STDERR:\n{e.stderr}")
        sys.exit(e.returncode)

    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
