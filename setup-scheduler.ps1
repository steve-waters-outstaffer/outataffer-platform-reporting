# setup-scheduler.ps1 - Set up monthly Cloud Scheduler jobs (PowerShell)

$ErrorActionPreference = "Stop"

$PROJECT_ID = "outstaffer-app-prod"
$REGION = "us-central1"

Write-Host "⏰ Setting up monthly Cloud Scheduler jobs..." -ForegroundColor Green

# Create scheduler job for revenue metrics (1st of every month at 2 AM UTC)
Write-Host "📅 Creating revenue metrics scheduler..." -ForegroundColor Yellow
try {
    gcloud scheduler jobs create http revenue-metrics-monthly --location=$REGION --schedule="0 2 1 * *" --time-zone="UTC" --uri="https://$REGION-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/$PROJECT_ID/jobs/revenue-metrics-job:run" --http-method=POST --oauth-service-account-email="$PROJECT_ID@appspot.gserviceaccount.com" --description="Monthly revenue metrics data collection"
} catch {
    Write-Host "Updating existing revenue metrics scheduler..." -ForegroundColor Cyan
    gcloud scheduler jobs update http revenue-metrics-monthly --location=$REGION --schedule="0 2 1 * *" --time-zone="UTC" --uri="https://$REGION-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/$PROJECT_ID/jobs/revenue-metrics-job:run" --http-method=POST --oauth-service-account-email="$PROJECT_ID@appspot.gserviceaccount.com" --description="Monthly revenue metrics data collection"
}

# Create scheduler job for plan/addon metrics (1st of every month at 3 AM UTC)
Write-Host "📊 Creating plan/addon metrics scheduler..." -ForegroundColor Yellow
try {
    gcloud scheduler jobs create http plan-addon-metrics-monthly --location=$REGION --schedule="0 3 1 * *" --time-zone="UTC" --uri="https://$REGION-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/$PROJECT_ID/jobs/plan-addon-metrics-job:run" --http-method=POST --oauth-service-account-email="$PROJECT_ID@appspot.gserviceaccount.com" --description="Monthly plan and addon metrics data collection"
} catch {
    Write-Host "Updating existing plan/addon metrics scheduler..." -ForegroundColor Cyan
    gcloud scheduler jobs update http plan-addon-metrics-monthly --location=$REGION --schedule="0 3 1 * *" --time-zone="UTC" --uri="https://$REGION-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/$PROJECT_ID/jobs/plan-addon-metrics-job:run" --http-method=POST --oauth-service-account-email="$PROJECT_ID@appspot.gserviceaccount.com" --description="Monthly plan and addon metrics data collection"
}

Write-Host "✅ Scheduler setup complete!" -ForegroundColor Green
Write-Host ""
Write-Host "📋 Your monthly jobs are now scheduled:" -ForegroundColor Cyan
Write-Host "  • Revenue metrics: 1st of month at 2:00 AM UTC" -ForegroundColor White
Write-Host "  • Plan/addon metrics: 1st of month at 3:00 AM UTC" -ForegroundColor White
Write-Host ""
Write-Host "🔍 To view scheduled jobs:" -ForegroundColor Cyan
Write-Host "  gcloud scheduler jobs list --location=$REGION" -ForegroundColor White
Write-Host ""
Write-Host "🧪 To test scheduler jobs manually:" -ForegroundColor Cyan
Write-Host "  gcloud scheduler jobs run revenue-metrics-monthly --location=$REGION" -ForegroundColor White
Write-Host "  gcloud scheduler jobs run plan-addon-metrics-monthly --location=$REGION" -ForegroundColor White