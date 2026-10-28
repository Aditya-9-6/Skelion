import json
import logging
import httpx
from fastapi import Request, Response
from fastapi.routing import APIRoute

from skelion_edge.waf_shield import (
    inspect_request_security,
    record_threat_event,
)

logger = logging.getLogger("skelion_edge.proxy")


class ProxyMiddleware:
    """Catch-all proxy and Ingress Security Shield.
    1. Inspects incoming requests with Spryzen WAF & Project Tartarus Deception.
    2. Intercepts scanner probes (.env, .git) with synthetic honeypots.
    3. Blocks OWASP attacks (SQLi, XSS, RCE, LFI) before backend execution.
    4. Forwards unhandled exceptions to `target_base` (fail-open mode).
    """

    def __init__(self, app, target_base: str):
        self.app = app
        self.target_base = target_base.rstrip('/')

    async def __call__(self, scope, receive, send):
        if scope.get('type') != 'http':
            await self.app(scope, receive, send)
            return

        # Safe body accumulation for inspection without consuming the ASGI stream
        body_bytes = b""
        orig_receive = receive
        if scope.get("method") in ("POST", "PUT", "PATCH", "DELETE"):
            chunks = []
            while True:
                message = await orig_receive()
                chunks.append(message.get("body", b""))
                if not message.get("more_body", False):
                    break
            body_bytes = b"".join(chunks)

            body_sent = False
            async def receive_wrapper():
                nonlocal body_sent
                if not body_sent:
                    body_sent = True
                    return {"type": "http.request", "body": body_bytes, "more_body": False}
                return await orig_receive()

            receive = receive_wrapper

        request = Request(scope, receive=receive)

        # 1. Spryzen Ingress WAF & Tartarus Inspection
        try:
            body_text = body_bytes.decode("utf-8", errors="ignore") if body_bytes else ""
            is_blocked, threat, deception = inspect_request_security(
                method=request.method,
                path=request.url.path,
                query_params=request.url.query,
                headers=dict(request.headers),
                body=body_text
            )

            if is_blocked:
                client_ip = request.client.host if request.client else "unknown"
                if threat:
                    record_threat_event(threat, client_ip=client_ip)
                    logger.warning(f"[Spryzen WAF Shield] Blocked {threat.get('type')}: {threat.get('signature')} from {client_ip} on {request.url.path}")

                if deception:
                    # Serve Tartarus Deception Honeypot response
                    resp = Response(
                        content=deception["content"],
                        status_code=deception["status_code"],
                        headers=deception["headers"]
                    )
                    await resp(scope, receive, send)
                    return
                else:
                    # Return 403 Forbidden with WAF diagnostic payload
                    resp = Response(
                        content=json.dumps({
                            "error": "Forbidden",
                            "engine": "Spryzen WAF Shield (Skelion Edge)",
                            "blocked_reason": "Malicious payload detected by Ingress Security Engine",
                            "threat": threat
                        }),
                        status_code=403,
                        media_type="application/json"
                    )
                    await resp(scope, receive, send)
                    return
        except Exception as waf_err:
            logger.error(f"Error during WAF inspection: {waf_err}")

        # 2. Normal routing first
        try:
            await self.app(scope, receive, send)
        except Exception as exc:
            # Forward request unchanged on failure (fails-open behaviour)
            logger.exception("Proxy fail-open: forwarding request after exception")
            async with httpx.AsyncClient() as client:
                url = f"{self.target_base}{request.url.path}"
                resp = await client.request(
                    request.method,
                    url,
                    headers=request.headers.raw,
                    content=body_bytes or await request.body(),
                    timeout=10,
                )
                await Response(
                    resp.content,
                    status_code=resp.status_code,
                    headers=dict(resp.headers),
                )(scope, receive, send)

