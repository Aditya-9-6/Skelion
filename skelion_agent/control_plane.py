import os
import hashlib
from datetime import datetime, timezone
from fastapi import FastAPI, WebSocket
from pydantic import BaseModel
import redis.asyncio as redis

try:
    from skelion_agent.worker import execute_sandboxed_autonomous_loop
except Exception:  # pragma: no cover

    def execute_sandboxed_autonomous_loop(*args, **kwargs):
        raise NotImplementedError("Worker module not available in this environment")


# Import routers
from skelion_agent.metrics_router import router as metrics_router
from skelion_agent.pr_comment_bot import router as pr_comment_bot_router
from skelion_agent.admin import router as admin_router
from skelion_agent.billing_routes import router as billing_router
from skelion_agent.auth_routes import router as auth_router
from skelion_agent.chat_routes import router as chat_router
from skelion_agent.admin_dashboard import router as admin_dashboard_router
from skelion_agent.license_routes import router as license_router
from skelion_agent.ingest_routes import router as ingest_router
from skelion_agent.customer_portal import router as customer_portal_router
from skelion_agent.public_web import router as public_web_router

# Global redis client placeholder (will be set on startup)
redis_client = None

app = FastAPI(title="Skelion SaaS Control Plane", version="2.0.0")


@app.get("/health", tags=["System"])
@app.get("/v1/health", tags=["System"])
async def health_check():
    return {
        "status": "healthy",
        "service": "skelion-control-plane",
        "version": "2.0.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# Enable CORS for webviews and external pilot frontends
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(public_web_router)
app.include_router(auth_router)
app.include_router(ingest_router)
app.include_router(customer_portal_router)
app.include_router(metrics_router)
app.include_router(pr_comment_bot_router)
app.include_router(admin_router)
app.include_router(admin_dashboard_router)
app.include_router(billing_router)
app.include_router(chat_router)
app.include_router(license_router)

from skelion_agent.waf_routes import router as waf_router

app.include_router(waf_router)
from skelion_agent.autonomous_routes import router as autonomous_router

app.include_router(autonomous_router)
from skelion_agent.sync_routes import router as sync_router
app.include_router(sync_router)

# Alias for Phase 2 webhook URL pattern
from skelion_agent.billing_routes import webhook as razorpay_webhook_handler

app.add_api_route("/v1/webhooks/razorpay", razorpay_webhook_handler, methods=["POST"])

# Add fails‑open proxy middleware (target base is the original service)
from skelion_edge.proxy import ProxyMiddleware

app.add_middleware(ProxyMiddleware, target_base="http://127.0.0.1:8000")


# Initialize DB on startup
@app.on_event("startup")
async def on_startup():
    """Startup hook – initialize DB, apply migrations, and ensure auth columns."""
    # Existing DB init
    from skelion_agent.database import init_db

    try:
        init_db()
    except Exception as exc:  # pragma: no cover

        class ProxyFailOpen(Exception):
            pass

        raise ProxyFailOpen(str(exc)) from exc

    # Alembic migrations (optional – skip if alembic.ini missing, e.g., in tests)
    try:
        from alembic import command
        from alembic.config import Config
        import pathlib

        cfg_path = pathlib.Path(__file__).parent.parent / "alembic.ini"
        if cfg_path.is_file():
            alembic_cfg = Config(str(cfg_path))
            command.upgrade(alembic_cfg, "head")
    except Exception:
        # If Alembic is not installed or config missing, ignore – migrations are optional for tests
        pass

    # Run custom billing/auth migration script
    try:
        import skelion_agent.migrate_billing  # noqa: F401,F403
    except Exception:
        pass

    # Initialize Redis client after DB migrations
    global redis_client
    redis_client = redis.from_url(
        os.getenv("REDIS_URL", "redis://localhost:6379/0"), decode_responses=True
    )


# Simple WebSocket manager for panel connections
class PanelConnectionManager:
    def __init__(self):
        self.active_connections: set[WebSocket] = set()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.discard(websocket)

    async def broadcast(self, message: str):
        for connection in list(self.active_connections):
            try:
                await connection.send_text(message)
            except Exception:
                self.disconnect(connection)


panel_ws_manager = PanelConnectionManager()


class HeartbeatPayload(BaseModel):
    node_name: str
    version: str


class TelemetryIngestPayload(BaseModel):
    method: str
    path: str
    status_code: int
    redacted_headers: dict
    redacted_request_body: str
    redacted_response_body: str
    latency_ms: float


def hash_api_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


# Existing endpoint implementations (node heartbeat, telemetry ingest, etc.) remain unchanged below...
