# gossipmesh/saas/main.py
"""FastAPI entry point for the GossipMesh SaaS sidecar.
It mounts the metrics router (providing cycle counts and PR‑throughput) and a placeholder webhook
router for the PR‑comment bot.
"""

from fastapi import FastAPI
from gossipmesh.saas.metrics_router import router as metrics_router
from gossipmesh.saas.pr_comment_bot import router as webhook_router

app = FastAPI(title="GossipMesh SaaS", version="0.1.0")

# Register routers
app.include_router(metrics_router, prefix="/metrics", tags=["metrics"])
app.include_router(webhook_router, prefix="/webhooks", tags=["webhooks"])

# Root endpoint for health check
@app.get("/", summary="Health check")
async def health_check():
    return {"status": "ok"}
