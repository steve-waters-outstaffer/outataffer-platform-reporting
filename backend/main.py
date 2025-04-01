from fastapi import FastAPI, Header, HTTPException
from google.cloud import bigquery
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust to your frontend's URL later
    allow_headers=["X-API-KEY"],
)

API_KEY = "your-simple-internal-api-key"

@app.get("/subscription_metrics")
async def subscription_metrics(x_api_key: str = Header(None)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")

    client = bigquery.Client()
    query = """
        SELECT *
        FROM `your-project.dashboard_metrics.monthly_subscription_snapshot`
        WHERE snapshot_date = (SELECT MAX(snapshot_date) FROM `your-project.dashboard_metrics.monthly_subscription_snapshot`)
    """
    query_job = client.query(query)
    results = query_job.result()
    return [dict(row) for row in results]
