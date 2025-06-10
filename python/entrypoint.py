#!/usr/bin/env python3
"""
entrypoint.py - Dynamic script runner for Cloud Run Jobs

This allows the same container to run different scripts based on environment variables.
"""

import os
import sys
import subprocess
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('entrypoint')

def main():
    # Get script name from environment variable
    script_name = os.getenv('SCRIPT_NAME', 'snapshot-revenue-metrics.py')

    logger.info(f"🚀 Starting Cloud Run Job: {script_name}")

    # Validate script exists
    if not os.path.exists(script_name):
        logger.error(f"❌ Script not found: {script_name}")
        sys.exit(1)

    # Get any additional arguments from environment
    args = os.getenv('SCRIPT_ARGS', '').split() if os.getenv('SCRIPT_ARGS') else []

    # Build command
    cmd = ['python', script_name] + args

    logger.info(f"🔧 Executing: {' '.join(cmd)}")

    try:
        # Run the script
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)

        # Log output
        if result.stdout:
            logger.info(f"📤 STDOUT:\n{result.stdout}")
        if result.stderr:
            logger.warning(f"📤 STDERR:\n{result.stderr}")

        logger.info("✅ Script completed successfully")

    except subprocess.CalledProcessError as e:
        logger.error(f"❌ Script failed with exit code {e.returncode}")
        if e.stdout:
            logger.error(f"📤 STDOUT:\n{e.stdout}")
        if e.stderr:
            logger.error(f"📤 STDERR:\n{e.stderr}")
        sys.exit(e.returncode)

    except Exception as e:
        logger.error(f"❌ Unexpected error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()