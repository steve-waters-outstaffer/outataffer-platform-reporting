from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import revenue, addons, health_insurance
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Outstaffer Dashboard API")

# Set up CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Update to your frontend URL in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include the routers
app.include_router(revenue.router, prefix="/revenue", tags=["Revenue"])
app.include_router(addons.router, prefix="/addons", tags=["Add-ons"])
app.include_router(health_insurance.router, prefix="/health-insurance", tags=["Health Insurance"])

@app.get("/health")
async def health():
    """Health check endpoint"""
    from datetime import datetime
    return {"status": "ok", "timestamp": datetime.now().isoformat()}

@app.get("/test_bigquery")
async def test_bigquery():
    try:
        query = """
            SELECT 1 as test
        """
        query_job = client.query(query)
        results = query_job.result()
        rows = list(results)
        return {"success": True, "result": dict(rows[0])}
    except Exception as e:
        return {"success": False, "error": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)