$PROJECT_ID = "dashboards-ccc88"
$REGION = "us-central1"

$jobs = @(
    @{ Name = "revenue-metrics-monthly"; Schedule = "0 2 28 * *"; Description = "End-of-month revenue metrics data collection"; Path = "revenue-metrics-job" },
    @{ Name = "plan-addon-metrics-monthly"; Schedule = "5 2 28 * *"; Description = "End-of-month plan and addon metrics data collection"; Path = "plan-addon-metrics-job" },
    @{ Name = "geographic-metrics-monthly"; Schedule = "10 2 28 * *"; Description = "End-of-month geographic metrics data collection"; Path = "geographic-metrics-job" },
    @{ Name = "health-insurance-monthly"; Schedule = "15 2 28 * *"; Description = "End-of-month health insurance metrics data collection"; Path = "health-insurance-job" },
    @{ Name = "customers-monthly"; Schedule = "20 2 28 * *"; Description = "End-of-month customer metrics data collection"; Path = "customers-job" },
    @{ Name = "requisitions-monthly"; Schedule = "25 2 28 * *"; Description = "End-of-month requisitions data collection"; Path = "requisitions-job" }
)

foreach ($job in $jobs) {
    $uri = \"https://$REGION-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/$PROJECT_ID/jobs/$($job.Path):run\"
    gcloud scheduler jobs describe $($job.Name) --location=$REGION > $null 2>&1

    if ($LASTEXITCODE -eq 0) {
        Write-Host "🔄 Updating $($job.Name)" -ForegroundColor Cyan
        gcloud scheduler jobs update http $($job.Name) --location=$REGION --schedule=\"$($job.Schedule)\" --description=\"$($job.Description)\"
    } else {
        Write-Host "🆕 Creating $($job.Name)" -ForegroundColor Yellow
        gcloud scheduler jobs create http $($job.Name) `
            --location=$REGION `
            --schedule=\"$($job.Schedule)\" `
            --time-zone=\"UTC\" `
            --uri=$uri `
            --http-method=POST `
            --oauth-service-account-email=\"$PROJECT_ID@appspot.gserviceaccount.com\" `
            --description=\"$($job.Description)\"
    }
}
