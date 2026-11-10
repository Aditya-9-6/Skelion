"""Vercel serverless function entry point for FastAPI admin API.
This file imports the existing FastAPI app defined in `admin_api/main.py` and exposes it as `app`.
Vercel will treat this as an ASGI handler.
"""

# Import the FastAPI app from the admin_api package
from admin_api.main import app as fastapi_app

# Export as `app` for Vercel
app = fastapi_app
