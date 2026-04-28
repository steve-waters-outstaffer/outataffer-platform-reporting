#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e

# --- Configuration ---
PROJECT_ID="dashboards-ccc88"
REGION="us-central1"
IMAGE_NAME="outstaffer-data-scripts"

# --- Script Start ---
echo "Using Project ID: $PROJECT_ID"
echo "🚀 Deploying Python data scripts using Cloud Build..."

# Enable necessary APIs
echo "📋 Enabling required APIs..."
gcloud services enable cloudbuild.googleapis.com --project="$PROJECT_ID"
gcloud services enable run.googleapis.com --project="$PROJECT_ID"
gcloud services enable artifactregistry.googleapis.com --project="$PROJECT_ID"

# Create a simple cloudbuild.yaml for this deployment
cat <<EOF > cloudbuild-temp.yaml
steps:
  # Build the container image
  - name: 'gcr.io/cloud-builders/docker'
    args: ['build', '-t', 'gcr.io/$PROJECT_ID/$IMAGE_NAME', './python']

  # Push the container image to Container Registry
  - name: 'gcr.io/cloud-builders/docker'
    args: ['push', 'gcr.io/$PROJECT_ID/$IMAGE_NAME']

images:
  - 'gcr.io/$PROJECT_ID/$IMAGE_NAME'
EOF

echo "📦 Building container with Cloud Build..."
gcloud builds submit --config=cloudbuild-temp.yaml . --project="$PROJECT_ID"

# Clean up the temp file
rm cloudbuild-temp.yaml

# Function to deploy or create a job
deploy_job() {
  JOB_NAME=$1
  ENV_VARS_STRING=""
  # a little trick to handle the fact that the revenue job has no env vars
  if [ -n "$2" ]; then
    ENV_VARS_STRING="--set-env-vars=$2"
  fi

  echo "🔄 Deploying $JOB_NAME job..."

  # The '||' operator will execute the second command only if the first one fails
  gcloud run jobs update "$JOB_NAME" \
    --image="gcr.io/$PROJECT_ID/$IMAGE_NAME" \
    --region="$REGION" \
    --memory=2Gi \
    --cpu=1 \
    --max-retries=2 \
    --parallelism=1 \
    --task-timeout=3600 \
    $ENV_VARS_STRING \
    --project="$PROJECT_ID" \
  || \
  (echo "Creating new $JOB_NAME job..." && \
  gcloud run jobs create "$JOB_NAME" \
    --image="gcr.io/$PROJECT_ID/$IMAGE_NAME" \
    --region="$REGION" \
    --memory=2Gi \
    --cpu=1 \
    --max-retries=2 \
    --parallelism=1 \
    --task-timeout=3600 \
    $ENV_VARS_STRING \
    --project="$PROJECT_ID")
}

# Deploy all jobs
deploy_job "revenue-metrics-job"
deploy_job "plan-addon-metrics-job" "SCRIPT_NAME=snapshot-plan-and-addon-metrics.py"
deploy_job "customers-job" "SCRIPT_NAME=snapshot-customers.py"
deploy_job "geographic-metrics-job" "SCRIPT_NAME=snapshot-geographic-metrics.py"
deploy_job "health-insurance-job" "SCRIPT_NAME=snapshot-health-insruance.py"
deploy_job "requisitions-job" "SCRIPT_NAME=snapshot_requisitions.py"


echo "✅ Deployment complete!"
echo ""
echo "🧪 To test a job manually:"
echo "  gcloud run jobs execute revenue-metrics-job --region=$REGION --project=$PROJECT_ID"
echo "  gcloud run jobs execute customers-job --region=$REGION --project=$PROJECT_ID"