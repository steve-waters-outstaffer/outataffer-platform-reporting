#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e

# --- Configuration ---
PROJECT_ID="dashboards-ccc88"
YAML_FILE="app.yaml"

# --- Script Start ---
echo "🚀 Starting backend deployment script..."

# 1. Set the active Google Cloud project
echo "Setting active project to $PROJECT_ID..."
gcloud config set project $PROJECT_ID

# 2. Deploy the application to App Engine
echo "Deploying the application from $YAML_FILE..."
# The --quiet flag automatically answers "yes" to prompts.
gcloud app deploy $YAML_FILE --quiet

echo "✅ Backend deployment initiated successfully!"
echo "You can monitor the progress in your Google Cloud Console."