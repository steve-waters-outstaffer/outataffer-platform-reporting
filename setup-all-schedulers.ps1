# setup-schedulers-fixed.ps1 - Set up monthly Cloud Scheduler for all 6 jobs

$PROJECT_ID = "dashboards-ccc88"
$REGION = "us-central1"

Write-Host "⏰ Setting up monthly Cloud Scheduler for all data jobs..." -ForegroundColor Green

# Revenue metrics scheduler
Write-Host "📅 Creating revenue metrics scheduler..." -ForegroundColor Yellow
try {
    gcloud scheduler jobs create http revenue-metrics-monthly --location=$REGION --schedule="0 2 28 * *" --time-zone="UTC" --uri="https://$REGION-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/$PROJECT_ID/jobs/revenue-metrics-job:run" --http-method=POST --oauth-service-account-email="$PROJECT_ID@appspot.gserviceaccount.com" --description="End-of-month revenue metrics data collection"
} catch {
    Write-Host "Updating existing revenue metrics scheduler..." -ForegroundColor Cyan
    gcloud scheduler jobs update http revenue-metrics-monthly --location=$REGION --schedule="0 2 28 * *" --description="End-of-month revenue metrics data collection"
}

# Plan/addon metrics scheduler
Write-Host "📅 Creating plan/addon metrics scheduler..." -ForegroundColor Yellow
try {
    gcloud scheduler jobs create http plan-addon-metrics-monthly --location=$REGION --schedule="5 2 28 * *" --time-zone="UTC" --uri="https://$REGION-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/$PROJECT_ID/jobs/plan-addon-metrics-job:run" --http-method=POST --oauth-service-account-email="$PROJECT_ID@appspot.gserviceaccount.com" --description="End-of-month plan and addon metrics data collection"
} catch {
    Write-Host "Updating existing plan/addon metrics scheduler..." -ForegroundColor Cyan
    gcloud scheduler jobs update http plan-addon-metrics-monthly --location=$REGION --schedule="5 2 28 * *" --description="End-of-month plan and addon metrics data collection"
}

# Geographic metrics scheduler
Write-Host "📅 Creating geographic metrics scheduler..." -ForegroundColor Yellow
try {
    gcloud scheduler jobs create http geographic-metrics-monthly --location=$REGION --schedule="10 2 28 * *" --time-zone="UTC" --uri="https://$REGION-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/$PROJECT_ID/jobs/geographic-metrics-job:run" --http-method=POST --oauth-service-account-email="$PROJECT_ID@appspot.gserviceaccount.com" --description="End-of-month geographic metrics data collection"
} catch {
    Write-Host "Updating existing geographic metrics scheduler..." -ForegroundColor Cyan
    gcloud scheduler jobs update http geographic-metrics-monthly --location=$REGION --schedule="10 2 28 * *" --description="End-of-month geographic metrics data collection"
}

# Health insurance scheduler
Write-Host "📅 Creating health insurance scheduler..." -ForegroundColor Yellow
try {
    gcloud scheduler jobs create http health-insurance-monthly --location=$REGION --schedule="15 2 28 * *" --time-zone="UTC" --uri="https://$REGION-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/$PROJECT_ID/jobs/health-insurance-job:run" --http-method=POST --oauth-service-account-email="$PROJECT_ID@appspot.gserviceaccount.com" --description="End-of-month health insurance metrics data collection"
} catch {
    Write-Host "Updating existing health insurance scheduler..." -ForegroundColor Cyan
    gcloud scheduler jobs update http health-insurance-monthly --location=$REGION --schedule="15 2 28 * *" --description="End-of-month health insurance metrics data collection"
}

# Customers scheduler
Write-Host "📅 Creating customers scheduler..." -ForegroundColor Yellow
try {
    gcloud scheduler jobs create http customers-monthly --location=$REGION --schedule="20 2 28 * *" --time-zone="UTC" --uri="https://$REGION-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/$PROJECT_ID/jobs/customers-job:run" --http-method=POST --oauth-service-account-email="$PROJECT_ID@appspot.gserviceaccount.com" --description="End-of-month customer metrics data collection"
} catch {
    Write-Host "Updating existing customers scheduler..." -ForegroundColor Cyan
    gcloud scheduler jobs update http customers-monthly --location=$REGION --schedule="20 2 28 * *" --description="End-of-month customer metrics data collection"
}

# Requisitions scheduler
Write-Host "📅 Creating requisitions scheduler..." -ForegroundColor Yellow
try {
    gcloud scheduler jobs create http requisitions-monthly --location=$REGION --schedule="25 2 28 * *" --time-zone="UTC" --uri="https://$REGION-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/$PROJECT_ID/jobs/requisitions-job:run" --http-method=POST --oauth-service-account-email="$PROJECT_ID@appspot.gserviceaccount.com" --description="End-of-month requisitions data collection"
} catch {
    Write-Host "Updating existing requisitions scheduler..." -ForegroundColor Cyan
    gcloud scheduler jobs update http requisitions-monthly --location=$REGION --schedule="25 2 28 * *" --description="End-of-month requisitions data collection"
}

Write-Host ""
Write-Host "✅ All schedulers created successfully!" -ForegroundColor Green
Write-Host ""
Write-Host "📋 Monthly schedule (28th of every month, UTC):" -ForegroundColor Cyan
Write-Host "  • 2:00 AM - Revenue metrics" -ForegroundColor White
Write-Host "  • 2:05 AM - Plan/addon metrics" -ForegroundColor White
Write-Host "  • 2:10 AM - Geographic metrics" -ForegroundColor White
Write-Host "  • 2:15 AM - Health insurance" -ForegroundColor White
Write-Host "  • 2:20 AM - Customer metrics" -ForegroundColor White
Write-Host "  • 2:25 AM - Requisitions" -ForegroundColor White
Write-Host ""
Write-Host "📅 Next run: June 28th, 2025 at 2:00 AM UTC" -ForegroundColor Cyan
Write-Host ""
Write-Host "🔍 View all scheduled jobs with:" -ForegroundColor Cyan
Write-Host "  gcloud scheduler jobs list --location=$REGION" -ForegroundColor White