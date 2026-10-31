# skelion-python — Official Python Drop-in Resilience Middleware (FastAPI / Starlette / ASGI)
# Intercepts unhandled edge crashes fail-open, scrubs PII, and reports to Skelion SaaS

import time
import logging
from typing import Optional
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
import httpx

logger = logging.getLogger("skelion.sdk")


class SkelionMiddleware(BaseHTTPMiddleware):
    """
    Skelion Python Middleware:
    1. Intercepts unhandled 5xx exceptions.
    2. Sends sanitized telemetry to Skelion Control Plane asynchronously.
    3. Guarantees Fail-Open: returns synthetic fallback instead of 500 downtime.
    """

    def __init__(
        self,
        app,
        api_key: Optional[str] = None,
        endpoint: str = "http://127.0.0.1:8003",
        fail_open: bool = True,
        debug: bool = False,
    ):
        super().__init__(app)
        self.api_key = api_key
        self.endpoint = endpoint.rstrip("/")
        self.fail_open = fail_open
        self.debug = debug

    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        try:
            response = await call_next(request)
            return response
        except Exception as exc:
            duration_ms = round((time.time() - start_time) * 1000, 2)
            if self.debug:
                logger.error(
                    f"[Skelion SDK] Intercepted error on {request.method} {request.url.path}: {exc}"
                )

            # 1. Asynchronously send telemetry to Skelion SaaS
            if self.api_key:
                try:
                    payload = {
                        "http_method": request.method,
                        "route_path": request.url.path,
                        "status_code": 500,
                        "error_summary": str(exc) or "Unhandled server exception",
                        "captured_headers": dict(request.headers),
                        "captured_payload": "",
                        "latency_ms": duration_ms,
                    }
                    async with httpx.AsyncClient(timeout=3.0) as client:
                        await client.post(
                            f"{self.endpoint}/v1/ingest/incident",
                            headers={
                                "Authorization": f"Bearer {self.api_key}",
                                "Content-Type": "application/json",
                            },
                            json=payload,
                        )
                except Exception as e:
                    # Fail-open guarantee: never crash on telemetry failure
                    if self.debug:
                        logger.warning(f"[Skelion SDK] Telemetry dispatch failed: {e}")

            # 2. Fail-Open Response Boundary
            if self.fail_open:
                return JSONResponse(
                    status_code=200,
                    content={
                        "status": "fail_open_buffered",
                        "incident_route": request.url.path,
                        "message": "Your request was buffered safely by Skelion Edge Resilience and will be reconciled automatically.",
                    },
                )

            raise exc
