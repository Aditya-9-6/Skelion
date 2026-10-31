# skelion_agent/ingest_routes.py — SaaS Telemetry Ingestion, Scoped API Keys & Webhooks

import hashlib
import json
import uuid
import asyncio
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, Header, BackgroundTasks, status
from pydantic import BaseModel, HttpUrl
from sqlmodel import Session, select

from skelion_agent.database import get_db
from skelion_agent.models import Organization, Incident, ApiKey, WebhookSubscription, utc_now
from skelion_agent.api_key_service import get_org_from_api_key_or_jwt, generate_scoped_api_key, hash_api_key
from skelion_agent.email_service import email_service
from core.redact import redact_headers, redact_text as redact_payload

router = APIRouter(prefix="/v1", tags=["SaaS Ingress & Keys"])


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


class CreateWebhookRequest(BaseModel):
    url: str
    events: Optional[List[str]] = ["incident.created", "fix.verified"]


# ---------------------------------------------------------------------------
# Background Webhook Dispatcher
# ---------------------------------------------------------------------------

async def dispatch_webhooks(org_id: str, event_type: str, payload: dict, db_session: Session):
    """Dispatch webhook event to all active endpoints registered by the organization."""
    import httpx
    webhooks = db_session.exec(
        select(WebhookSubscription).where(
            WebhookSubscription.org_id == org_id,
            WebhookSubscription.is_active == True
        )
    ).all()

    for wh in webhooks:
        try:
            events = json.loads(wh.events_json) if wh.events_json else []
            if event_type in events or "*" in events:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    await client.post(
                        wh.url,
                        json={
                            "event": event_type,
                            "timestamp": utc_now().isoformat(),
                            "data": payload
                        },
                        headers={"X-Skelion-Event": event_type}
                    )
        except Exception as e:
            # Webhook dispatch failures never disrupt production
            pass


# ---------------------------------------------------------------------------
# Telemetry Ingress Endpoint
# ---------------------------------------------------------------------------

@router.post("/ingest/incident")
async def ingest_production_incident(
    req: IngestIncidentRequest,
    background_tasks: BackgroundTasks,
    org: Organization = Depends(get_org_from_api_key_or_jwt),
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
            Incident.status != "resolved"
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
            last_seen_at=utc_now()
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
                "fingerprint": fingerprint
            },
            db_session=db
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
                    "summary": req.error_summary
                }
            )

    return {
        "status": status_msg,
        "incident_id": incident_id,
        "fingerprint": fingerprint,
        "fail_open": True,
        "message": "Telemetry accepted with zero PII exposure."
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
            "created_at": k.created_at.isoformat() if k.created_at else utc_now().isoformat(),
            "last_used_at": k.last_used_at.isoformat() if k.last_used_at else None,
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
    raw_key, key_prefix, key_hash = generate_scoped_api_key(prefix=prefix)

    scopes_str = ",".join(req.scopes) if req.scopes else "ingest,read"
    api_key = ApiKey(
        org_id=org.id,
        name=req.name,
        key_prefix=key_prefix,
        key_hash=key_hash,
        scopes=scopes_str,
        is_active=True,
    )
    db.add(api_key)
    db.commit()
    db.refresh(api_key)

    return {
        "id": api_key.id,
        "name": api_key.name,
        "api_key": raw_key,  # Returned only once!
        "prefix": key_prefix,
        "scopes": req.scopes,
        "created_at": api_key.created_at.isoformat(),
        "warning": "Copy this key now. You will not be able to retrieve it again."
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
            WebhookSubscription.org_id == org.id,
            WebhookSubscription.is_active == True
        )
    ).all()

    return [
        {
            "id": w.id,
            "url": w.url,
            "events": json.loads(w.events_json) if w.events_json else [],
            "created_at": w.created_at.isoformat() if w.created_at else utc_now().isoformat(),
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
        is_active=True
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
