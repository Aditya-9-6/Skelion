# skelion_agent/ingest_routes.py — SaaS Telemetry Ingestion, Scoped API Keys & Webhooks

import hashlib
import hmac
import asyncio
import json
import logging
import uuid
from datetime import timedelta
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from sqlmodel import Session, select

from skelion_agent.database import get_db
from skelion_agent.database import engine
from skelion_agent.models import (
    AuditLog,
    Organization,
    Incident,
    ApiKey,
    WebhookSubscription,
    utc_now,
)
from skelion_agent.api_key_service import (
    get_org_from_api_key_or_jwt,
    generate_scoped_api_key,
    require_scope,
)
from skelion_agent.email_service import email_service
from core.redact import redact_headers, redact_text as redact_payload

router = APIRouter(prefix="/v1", tags=["SaaS Ingress & Keys"])
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Request & Response Schemas
# ---------------------------------------------------------------------------


class IngestIncidentRequest(BaseModel):
    http_method: str = "POST"
    route_path: str = "/api/v1/orders/checkout"
    status_code: int = 500
    error_summary: str = "Unhandled edge exception"
    captured_headers: Optional[Dict[str, Any]] = None
    captured_payload: Optional[str] = None
    latency_ms: Optional[float] = 0.0
    environment: Optional[str] = "production"
    service_name: Optional[str] = "api-service"


class CreateApiKeyRequest(BaseModel):
    name: str = "Production API Key"
    environment: str = "live"  # "live" or "test"
    scopes: Optional[List[str]] = ["ingest", "read"]
    expires_in_days: Optional[int] = 90


class CreateWebhookRequest(BaseModel):
    url: str
    events: Optional[List[str]] = ["incident.created", "fix.verified"]


# ---------------------------------------------------------------------------
# Background Webhook Dispatcher
# ---------------------------------------------------------------------------


async def dispatch_webhooks(
    org_id: str, event_type: str, payload: dict, db_session: Session
):
    """Dispatch webhook event to all active endpoints registered by the organization."""
    import httpx

    # Background tasks must not reuse the request-scoped session after the response.
    with Session(engine) as delivery_session:
        webhooks = delivery_session.exec(
            select(WebhookSubscription).where(
                WebhookSubscription.org_id == org_id,
                WebhookSubscription.is_active == True,
            )
        ).all()

        for wh in webhooks:
            try:
                events = json.loads(wh.events_json) if wh.events_json else []
                if event_type not in events and "*" not in events:
                    continue
                body = json.dumps(
                    {
                        "event": event_type,
                        "timestamp": utc_now().isoformat(),
                        "data": payload,
                    },
                    separators=(",", ":"),
                ).encode("utf-8")
                signature = hmac.new(
                    wh.secret.encode("utf-8"), body, hashlib.sha256
                ).hexdigest()
                delivery_id = f"whd_{uuid.uuid4().hex}"
                async with httpx.AsyncClient(timeout=5.0) as client:
                    delivered = False
                    for attempt in range(3):
                        try:
                            response = await client.post(
                                wh.url,
                                content=body,
                                headers={
                                    "Content-Type": "application/json",
                                    "X-Skelion-Event": event_type,
                                    "X-Skelion-Delivery": delivery_id,
                                    "X-Skelion-Signature": f"sha256={signature}",
                                },
                            )
                            if 200 <= response.status_code < 300:
                                delivered = True
                                break
                        except httpx.HTTPError:
                            pass
                        if attempt < 2:
                            await asyncio.sleep(2**attempt)
                    if not delivered:
                        logger.warning(
                            "Webhook delivery failed: org=%s subscription=%s event=%s",
                            org_id,
                            wh.id,
                            event_type,
                        )
            except Exception:
                logger.exception(
                    "Webhook dispatch error: org=%s subscription=%s event=%s",
                    org_id,
                    wh.id,
                    event_type,
                )


# ---------------------------------------------------------------------------
# Telemetry Ingress Endpoint
# ---------------------------------------------------------------------------


@router.post("/ingest/incident")
async def ingest_production_incident(
    req: IngestIncidentRequest,
    background_tasks: BackgroundTasks,
    org: Organization = Depends(require_scope("ingest")),
    db: Session = Depends(get_db),
):
    """
    Drop-in Telemetry Ingestion Endpoint:
    1. Authenticates client via scoped API key (skl_live_...).
    2. Scrubs PII from headers and payload using strict allow-lists.
    3. Groups crashes by deterministic fingerprint.
    4. Upserts incident in organization feed.
    5. Dispatches background webhook alerts.
    """
    # 1. Zero-PII Sanitization
    safe_headers = redact_headers(req.captured_headers or {})
    safe_payload = redact_payload(req.captured_payload or "")

    # 2. Deterministic Error Fingerprinting
    clean_route = req.route_path.split("?")[0]
    fp_raw = f"{req.http_method.upper()}:{clean_route}:{req.status_code}:{req.error_summary[:60]}"
    fingerprint = f"fp_{hashlib.sha256(fp_raw.encode('utf-8')).hexdigest()[:12]}"

    # 3. Check for existing active incident with same fingerprint
    existing_inc = db.exec(
        select(Incident).where(
            Incident.org_id == org.id,
            Incident.fingerprint == fingerprint,
            Incident.status != "resolved",
        )
    ).first()

    if existing_inc:
        existing_inc.occurrence_count += 1
        existing_inc.last_seen_at = utc_now()
        existing_inc.latency_ms = req.latency_ms or existing_inc.latency_ms
        db.add(existing_inc)
        db.commit()
        db.refresh(existing_inc)
        incident_id = existing_inc.id
        status_msg = "occurrence_incremented"
    else:
        # Create new incident record
        incident_id = f"inc_{uuid.uuid4().hex[:10]}"
        new_inc = Incident(
            id=incident_id,
            org_id=org.id,
            fingerprint=fingerprint,
            http_method=req.http_method.upper(),
            route_path=clean_route,
            status_code=req.status_code,
            error_summary=req.error_summary,
            captured_method=req.http_method.upper(),
            captured_headers=safe_headers,
            captured_body=safe_payload,
            latency_ms=req.latency_ms or 0.0,
            occurrence_count=1,
            status="analyzing",
            created_at=utc_now(),
            last_seen_at=utc_now(),
        )
        db.add(new_inc)
        db.commit()
        db.refresh(new_inc)
        status_msg = "incident_created"

        # Dispatch webhook alert in background
        background_tasks.add_task(
            dispatch_webhooks,
            org_id=org.id,
            event_type="incident.created",
            payload={
                "incident_id": incident_id,
                "route": f"{req.http_method} {clean_route}",
                "status_code": req.status_code,
                "summary": req.error_summary,
                "fingerprint": fingerprint,
            },
            db_session=db,
        )

        # Dispatch email alert if notification email configured
        alert_email = org.email or org.billing_email
        if alert_email:
            background_tasks.add_task(
                email_service.send_incident_alert,
                org_name=org.name or "My Team",
                to_email=alert_email,
                incident_data={
                    "route": f"{req.http_method} {clean_route}",
                    "status_code": req.status_code,
                    "summary": req.error_summary,
                },
            )

    return {
        "status": status_msg,
        "incident_id": incident_id,
        "fingerprint": fingerprint,
        "fail_open": True,
        "message": "Telemetry accepted with zero PII exposure.",
    }


# ---------------------------------------------------------------------------
# Scoped API Keys Management
# ---------------------------------------------------------------------------


@router.get("/keys")
def list_api_keys(
    org: Organization = Depends(get_org_from_api_key_or_jwt),
    db: Session = Depends(get_db),
):
    """List all active API keys for the developer organization."""
    keys = db.exec(
        select(ApiKey).where(ApiKey.org_id == org.id, ApiKey.is_active == True)
    ).all()

    return [
        {
            "id": k.id,
            "name": k.name,
            "prefix": k.key_prefix,
            "scopes": k.scopes.split(",") if k.scopes else ["ingest"],
            "created_at": k.created_at.isoformat()
            if k.created_at
            else utc_now().isoformat(),
            "last_used_at": k.last_used_at.isoformat() if k.last_used_at else None,
            "expires_at": k.expires_at.isoformat() if k.expires_at else None,
        }
        for k in keys
    ]


@router.post("/keys")
def create_api_key(
    req: CreateApiKeyRequest,
    org: Organization = Depends(get_org_from_api_key_or_jwt),
    db: Session = Depends(get_db),
):
    """
    Generate a new scoped API key.
    The raw key is returned ONCE upon creation.
    """
    prefix = "skl_live_" if req.environment == "live" else "skl_test_"
    requested_scopes = set(req.scopes or ["ingest", "read"])
    from skelion_agent.api_key_service import VALID_SCOPES

    invalid_scopes = requested_scopes - VALID_SCOPES
    if invalid_scopes:
        raise HTTPException(
            status_code=422,
            detail=f"Unsupported API key scopes: {', '.join(sorted(invalid_scopes))}",
        )
    if req.expires_in_days is not None and not 1 <= req.expires_in_days <= 3650:
        raise HTTPException(
            status_code=422, detail="expires_in_days must be between 1 and 3650"
        )
    raw_key, key_prefix, key_hash = generate_scoped_api_key(prefix=prefix)

    scopes_str = ",".join(sorted(requested_scopes))
    expires_at = (
        utc_now() + timedelta(days=req.expires_in_days)
        if req.expires_in_days is not None
        else None
    )
    api_key = ApiKey(
        org_id=org.id,
        name=req.name,
        key_prefix=key_prefix,
        key_hash=key_hash,
        scopes=scopes_str,
        is_active=True,
        expires_at=expires_at,
    )
    db.add(api_key)
    db.commit()
    db.refresh(api_key)
    db.add(
        AuditLog(
            actor=org.id,
            org_id=org.id,
            action="api_key.created",
            meta_json=json.dumps(
                {"key_id": api_key.id, "scopes": sorted(requested_scopes)}
            ),
        )
    )
    db.commit()

    return {
        "id": api_key.id,
        "name": api_key.name,
        "api_key": raw_key,  # Returned only once!
        "prefix": key_prefix,
        "scopes": req.scopes,
        "created_at": api_key.created_at.isoformat(),
        "expires_at": api_key.expires_at.isoformat() if api_key.expires_at else None,
        "warning": "Copy this key now. You will not be able to retrieve it again.",
    }


@router.delete("/keys/{key_id}")
def revoke_api_key(
    key_id: str,
    org: Organization = Depends(get_org_from_api_key_or_jwt),
    db: Session = Depends(get_db),
):
    """Revoke an API key immediately."""
    api_key = db.get(ApiKey, key_id)
    if not api_key or api_key.org_id != org.id:
        raise HTTPException(status_code=404, detail="API key not found")

    api_key.is_active = False
    db.add(api_key)
    db.add(
        AuditLog(
            actor=org.id,
            org_id=org.id,
            action="api_key.revoked",
            meta_json=json.dumps({"key_id": api_key.id}),
        )
    )
    db.commit()

    return {"status": "revoked", "id": key_id}


# ---------------------------------------------------------------------------
# Webhook Subscriptions Management
# ---------------------------------------------------------------------------


@router.get("/webhooks")
def list_webhooks(
    org: Organization = Depends(get_org_from_api_key_or_jwt),
    db: Session = Depends(get_db),
):
    """List all registered webhook alert subscriptions."""
    webhooks = db.exec(
        select(WebhookSubscription).where(
            WebhookSubscription.org_id == org.id, WebhookSubscription.is_active == True
        )
    ).all()

    return [
        {
            "id": w.id,
            "url": w.url,
            "events": json.loads(w.events_json) if w.events_json else [],
            "created_at": w.created_at.isoformat()
            if w.created_at
            else utc_now().isoformat(),
        }
        for w in webhooks
    ]


@router.post("/webhooks")
def create_webhook(
    req: CreateWebhookRequest,
    org: Organization = Depends(get_org_from_api_key_or_jwt),
    db: Session = Depends(get_db),
):
    """Register a new webhook URL (Slack, Discord, PagerDuty, or custom)."""
    wh = WebhookSubscription(
        org_id=org.id,
        url=req.url,
        events_json=json.dumps(req.events or ["incident.created"]),
        is_active=True,
    )
    db.add(wh)
    db.commit()
    db.refresh(wh)

    return {
        "status": "created",
        "id": wh.id,
        "url": wh.url,
        "secret": wh.secret,
        "events": req.events,
    }


@router.delete("/webhooks/{wh_id}")
def delete_webhook(
    wh_id: str,
    org: Organization = Depends(get_org_from_api_key_or_jwt),
    db: Session = Depends(get_db),
):
    """Delete a webhook subscription."""
    wh = db.get(WebhookSubscription, wh_id)
    if not wh or wh.org_id != org.id:
        raise HTTPException(status_code=404, detail="Webhook subscription not found")

    wh.is_active = False
    db.add(wh)
    db.commit()
    return {"status": "deleted", "id": wh_id}
