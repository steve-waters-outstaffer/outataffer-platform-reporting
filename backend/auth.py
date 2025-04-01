from fastapi import Header, HTTPException
import os

# Simple API key authentication - store in environment variable in production
API_KEY = os.getenv("API_KEY", "dJ8fK2sP9qR5xV7zT3mA6cE1bN")

def verify_api_key(x_api_key: str = Header(None)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return x_api_key