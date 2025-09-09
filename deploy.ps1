# deploy-new.ps1 - Deploy using Cloud Build (no Docker required)

$ErrorActionPreference = "Stop"

$PROJECT_ID = "dashboards-ccc88"
$REGION = "us-central1"
$IMAGE_NAME = "outstaffer-data-scripts"

Write-Host "Using Project ID: $PROJECT_ID" -ForegroundColor Cyan
Write-Host "🚀 Deploying Python data scripts using Cloud Build..." -ForegroundColor Green

# Create a simple cloudbuild.yaml for this deployment
$cloudBuildConfig = @"
steps:
  # Build the container image
  - name: 'gcr.io/cloud-builders/docker'
    args: ['build', '-t', 'gcr.io/$PROJECT_ID/$IMAGE_NAME`:latest', './python']

  # Push the container image to Container Registry
  - name: 'gcr.io/cloud-builders/docker'
    args: ['push', 'gcr.io/$PROJECT_ID/$IMAGE_NAME`:latest']

images:
  - 'gcr.io/$PROJECT_ID/$IMAGE_NAME`:latest'
"@

# Write the config to a temporary file
$cloudBuildConfig | Out-File -FilePath "cloudbuild-temp.yaml" -Encoding UTF8

Write-Host "📦 Building container with Cloud Build..." -ForegroundColor Yellow
gcloud builds submit --config=cloudbuild-temp.yaml .

# Clean up the temp file
Remove-Item "cloudbuild-temp.yaml"

# Deploy Revenue Metrics Job
Write-Host "🔄 Deploying revenue metrics job..." -ForegroundColor Yellow
try {
    gcloud run jobs replace --image="gcr.io/$PROJECT_ID/$IMAGE_NAME`:latest" --region=$REGION --memory=2Gi --cpu=1 --max-retries=2 --parallelism=1 --task-timeout=3600 revenue-metrics-job
} catch {
    Write-Host "Creating new revenue metrics job..." -ForegroundColor Cyan
    gcloud run jobs create revenue-metrics-job --image="gcr.io/$PROJECT_ID/$IMAGE_NAME`:latest" --region=$REGION --memory=2Gi --cpu=1 --max-retries=2 --parallelism=1 --task-timeout=3600
}

# Deploy Plan/Addon Metrics Job
Write-Host "📊 Deploying plan/addon metrics job..." -ForegroundColor Yellow
try {
    gcloud run jobs replace --image="gcr.io/$PROJECT_ID/$IMAGE_NAME`:latest" --region=$REGION --memory=2Gi --cpu=1 --max-retries=2 --parallelism=1 --task-timeout=3600 --set-env-vars=SCRIPT_NAME=snapshot-plan-and-addon-metrics.py plan-addon-metrics-job
} catch {
    Write-Host "Creating new plan/addon metrics job..." -ForegroundColor Cyan
    gcloud run jobs create plan-addon-metrics-job --image="gcr.io/$PROJECT_ID/$IMAGE_NAME`:latest" --region=$REGION --memory=2Gi --cpu=1 --max-retries=2 --parallelism=1 --task-timeout=3600 --set-env-vars=SCRIPT_NAME=snapshot-plan-and-addon-metrics.py
}

# Deploy Customer Metrics Job
Write-Host "👥 Deploying customer metrics job..." -ForegroundColor Yellow
try {
    gcloud run jobs replace --image="gcr.io/$PROJECT_ID/$IMAGE_NAME`:latest" --region=$REGION --memory=2Gi --cpu=1 --max-retries=2 --parallelism=1 --task-timeout=3600 --set-env-vars=SCRIPT_NAME=snapshot-customers.py customers-job
} catch {
    Write-Host "Creating new customer metrics job..." -ForegroundColor Cyan
    gcloud run jobs create customers-job --image="gcr.io/$PROJECT_ID/$IMAGE_NAME`:latest" --region=$REGION --memory=2Gi --cpu=1 --max-retries=2 --parallelism=1 --task-timeout=3600 --set-env-vars=SCRIPT_NAME=snapshot-customers.py
}

Write-Host "✅ Deployment complete!" -ForegroundColor Green
Write-Host ""
Write-Host "🔧 To set up monthly scheduling, run:" -ForegroundColor Cyan
Write-Host "  .\setup-scheduler.ps1" -ForegroundColor White
Write-Host ""
Write-Host "🧪 To test a job manually:" -ForegroundColor Cyan
Write-Host "  gcloud run jobs execute revenue-metrics-job --region=$REGION" -ForegroundColor White
Write-Host "  gcloud run jobs execute plan-addon-metrics-job --region=$REGION" -ForegroundColor White