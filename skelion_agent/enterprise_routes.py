import hashlib
import json
import os
import secrets
from datetime import timedelta
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, Form
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, EmailStr
from sqlmodel import Session, select

from skelion_agent.auth import create_access_token
from skelion_agent.auth_routes import get_current_actor, require_member_role
from skelion_agent.config import get_async_redis
from skelion_agent.saml_service import SamlValidationError, validate_saml_response
from skelion_agent.database import get_db
from skelion_agent.models import (
    AuditLog,
    AccessReview,
    ComplianceEvidence,
    Membership,
    Organization,
    ScimToken,
    SSOConnection,
    User,
    utc_now,
)

router = APIRouter(tags=["Enterprise Control Plane"])


def require_writable_region() -> None:
    if os.getenv("SKELION_READ_ONLY", "false").lower() == "true":
        raise HTTPException(status_code=503, detail="This deployment region is read-only")


class SSOConnectionRequest(BaseModel):
    provider: str
    issuer_url: Optional[str] = None
    client_id: Optional[str] = None
    client_secret_ref: Optional[str] = None
    certificate_pem_ref: Optional[str] = None
    metadata_url: Optional[str] = None
    entity_id: Optional[str] = None
    enabled: bool = False


class ScimTokenRequest(BaseModel):
    label: str = "SCIM provisioning token"
    expires_in_days: int = 365


class ScimTokenRotationRequest(BaseModel):
    expires_in_days: int = 365


class ScimUserRequest(BaseModel):
    userName: EmailStr
    displayName: Optional[str] = None
    active: bool = True


class AccessReviewUpdate(BaseModel):
    status: str
    notes: Optional[str] = None


def _hash_token(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


@router.get("/v1/org/sso")
def get_sso_connection(
    actor=Depends(get_current_actor), session: Session = Depends(get_db)
):
    org, _, _ = actor
    connection = session.exec(
        select(SSOConnection).where(SSOConnection.org_id == org.id)
    ).first()
    if not connection:
        return {"configured": False}
    return {
        "configured": True,
        "provider": connection.provider,
        "issuer_url": connection.issuer_url,
        "client_id": connection.client_id,
        "client_secret_ref": connection.client_secret_ref,
        "certificate_pem_ref": connection.certificate_pem_ref,
        "metadata_url": connection.metadata_url,
        "entity_id": connection.entity_id,
        "enabled": connection.enabled,
    }


@router.put("/v1/org/sso")
def configure_sso(
    req: SSOConnectionRequest,
    actor=Depends(require_member_role("owner")),
    session: Session = Depends(get_db),
):
    require_writable_region()
    if req.provider not in {"oidc", "saml"}:
        raise HTTPException(status_code=422, detail="provider must be oidc or saml")
    if req.provider == "oidc" and not req.issuer_url:
        raise HTTPException(status_code=422, detail="OIDC requires issuer_url")
    if req.provider == "saml" and not req.metadata_url:
        raise HTTPException(status_code=422, detail="SAML requires metadata_url")
    org, user, _ = actor
    connection = session.exec(
        select(SSOConnection).where(SSOConnection.org_id == org.id)
    ).first()
    if not connection:
        connection = SSOConnection(org_id=org.id)
    connection.provider = req.provider
    connection.issuer_url = req.issuer_url
    connection.client_id = req.client_id
    connection.client_secret_ref = req.client_secret_ref
    connection.certificate_pem_ref = req.certificate_pem_ref
    connection.metadata_url = req.metadata_url
    connection.entity_id = req.entity_id
    connection.enabled = req.enabled
    connection.updated_at = utc_now()
    session.add(connection)
    session.add(
        AuditLog(
            actor=user.id,
            org_id=org.id,
            action="sso.updated",
            meta_json=json.dumps({"provider": req.provider, "enabled": req.enabled}),
        )
    )
    session.commit()
    return {"status": "configured", "provider": connection.provider, "enabled": connection.enabled}


@router.get("/v1/org/sso/oidc/authorize")
async def oidc_authorize(
    request: Request,
    actor=Depends(get_current_actor),
    session: Session = Depends(get_db),
):
    org, _, _ = actor
    connection = session.exec(
        select(SSOConnection).where(
            SSOConnection.org_id == org.id,
            SSOConnection.provider == "oidc",
            SSOConnection.enabled == True,  # noqa: E712
        )
    ).first()
    if not connection or not connection.issuer_url or not connection.client_id:
        raise HTTPException(status_code=409, detail="Enabled OIDC connection is required")
    async with httpx.AsyncClient(timeout=10) as client:
        discovery = await client.get(connection.issuer_url.rstrip("/") + "/.well-known/openid-configuration")
        discovery.raise_for_status()
        metadata = discovery.json()
    authorization_endpoint = metadata.get("authorization_endpoint")
    if not authorization_endpoint:
        raise HTTPException(status_code=502, detail="OIDC provider omitted authorization_endpoint")
    state = secrets.token_urlsafe(32)
    nonce = secrets.token_urlsafe(32)
    redirect_uri = os.getenv("OIDC_REDIRECT_URI", str(request.url_for("oidc_callback")))
    redis = get_async_redis()
    await redis.setex(
        f"skelion:oidc:{state}",
        600,
        json.dumps({"org_id": org.id, "nonce": nonce, "redirect_uri": redirect_uri}),
    )
    from urllib.parse import urlencode

    return RedirectResponse(
        authorization_endpoint
        + "?"
        + urlencode(
            {
                "response_type": "code",
                "client_id": connection.client_id,
                "redirect_uri": redirect_uri,
                "scope": "openid email profile",
                "state": state,
                "nonce": nonce,
            }
        )
    )


@router.get("/v1/org/sso/oidc/callback", name="oidc_callback")
async def oidc_callback(
    request: Request,
    code: str,
    state: str,
    session: Session = Depends(get_db),
):
    redis = get_async_redis()
    raw_state = await redis.get(f"skelion:oidc:{state}")
    await redis.delete(f"skelion:oidc:{state}")
    if not raw_state:
        raise HTTPException(status_code=400, detail="Invalid or expired OIDC state")
    state_data = json.loads(raw_state)
    org = session.get(Organization, state_data["org_id"])
    connection = session.exec(
        select(SSOConnection).where(
            SSOConnection.org_id == state_data["org_id"],
            SSOConnection.provider == "oidc",
            SSOConnection.enabled == True,  # noqa: E712
        )
    ).first()
    if not org or not connection or not connection.issuer_url or not connection.client_id:
        raise HTTPException(status_code=400, detail="OIDC connection is unavailable")
    async with httpx.AsyncClient(timeout=10) as client:
        discovery = await client.get(connection.issuer_url.rstrip("/") + "/.well-known/openid-configuration")
        discovery.raise_for_status()
        metadata = discovery.json()
        token_data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": state_data["redirect_uri"],
            "client_id": connection.client_id,
        }
        if connection.client_secret_ref:
            secret = os.getenv(connection.client_secret_ref)
            if not secret:
                raise HTTPException(status_code=503, detail="OIDC client secret reference is not configured")
            token_data["client_secret"] = secret
        token_response = await client.post(metadata["token_endpoint"], data=token_data)
        token_response.raise_for_status()
        tokens = token_response.json()
        id_token = tokens.get("id_token")
        if not id_token:
            raise HTTPException(status_code=502, detail="OIDC provider omitted id_token")
        jwks = await client.get(metadata["jwks_uri"])
        jwks.raise_for_status()
    try:
        import jwt

        header = jwt.get_unverified_header(id_token)
        key = next(
            jwk.key
            for jwk in jwt.PyJWKSet.from_dict(jwks.json())
            if jwk.key_id == header.get("kid")
        )
        claims = jwt.decode(
            id_token,
            key,
            algorithms=["RS256", "RS384", "RS512", "ES256", "ES384", "ES512"],
            audience=connection.client_id,
            issuer=connection.issuer_url,
            options={"require": ["sub", "iss", "aud", "exp", "nonce"]},
        )
    except Exception as exc:
        raise HTTPException(status_code=401, detail="OIDC token validation failed") from exc
    if claims.get("nonce") != state_data["nonce"]:
        raise HTTPException(status_code=401, detail="OIDC nonce validation failed")
    email = claims.get("email")
    if not email:
        raise HTTPException(status_code=401, detail="OIDC identity has no email claim")
    user = session.exec(select(User).where(User.email == email)).first()
    membership = session.exec(
        select(Membership).where(
            Membership.org_id == org.id,
            Membership.user_id == user.id if user else "",
        )
    ).first()
    if not user or not membership:
        raise HTTPException(status_code=403, detail="OIDC user is not an organization member")
    return {
        "access_token": create_access_token(
            {"sub": org.id, "user_id": user.id, "plan": org.plan}
        ),
        "token_type": "bearer",
        "user_id": user.id,
        "organization_id": org.id,
    }


@router.post("/v1/org/sso/saml/consume")
async def saml_consume(
    saml_response: str = Form(..., alias="SAMLResponse"),
    relay_state: str = Form(..., alias="RelayState"),
    session: Session = Depends(get_db),
):
    redis = get_async_redis()
    raw_state = await redis.get(f"skelion:saml:{relay_state}")
    await redis.delete(f"skelion:saml:{relay_state}")
    if not raw_state:
        raise HTTPException(status_code=400, detail="Invalid or expired SAML state")
    state_data = json.loads(raw_state)
    org = session.get(Organization, state_data["org_id"])
    connection = session.exec(
        select(SSOConnection).where(
            SSOConnection.org_id == state_data["org_id"],
            SSOConnection.provider == "saml",
            SSOConnection.enabled == True,  # noqa: E712
        )
    ).first()
    certificate = (
        os.getenv(connection.certificate_pem_ref)
        if connection and connection.certificate_pem_ref
        else None
    )
    if not org or not connection or not certificate:
        raise HTTPException(status_code=503, detail="SAML certificate configuration is incomplete")
    try:
        identity = validate_saml_response(
            saml_response,
            certificate_pem=certificate,
            expected_issuer=connection.entity_id or "",
            expected_audience=state_data["audience"],
            expected_recipient=state_data["recipient"],
            request_id=state_data.get("request_id"),
        )
    except SamlValidationError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    user = session.exec(select(User).where(User.email == identity["name_id"])).first()
    membership = session.exec(
        select(Membership).where(
            Membership.org_id == org.id,
            Membership.user_id == user.id if user else "",
        )
    ).first()
    if not user or not membership:
        raise HTTPException(status_code=403, detail="SAML user is not an organization member")
    return {
        "access_token": create_access_token(
            {"sub": org.id, "user_id": user.id, "plan": org.plan}
        ),
        "token_type": "bearer",
        "user_id": user.id,
        "organization_id": org.id,
    }


@router.post("/v1/org/scim-tokens")
def create_scim_token(
    req: ScimTokenRequest,
    actor=Depends(require_member_role("owner")),
    session: Session = Depends(get_db),
):
    require_writable_region()
    if not 1 <= req.expires_in_days <= 3650:
        raise HTTPException(status_code=422, detail="expires_in_days must be between 1 and 3650")
    org, user, _ = actor
    raw = f"scim_{secrets.token_urlsafe(32)}"
    token = ScimToken(
        org_id=org.id,
        token_hash=_hash_token(raw),
        label=req.label,
        expires_at=utc_now() + timedelta(days=req.expires_in_days),
    )
    session.add(token)
    session.add(
        AuditLog(
            actor=user.id,
            org_id=org.id,
            action="scim_token.created",
            meta_json=json.dumps({"token_id": token.id}),
        )
    )
    session.commit()
    session.refresh(token)
    return {
        "id": token.id,
        "label": token.label,
        "token": raw,
        "expires_at": token.expires_at.isoformat(),
        "warning": "Store this token securely; it will not be shown again.",
    }


@router.get("/v1/org/scim-tokens")
def list_scim_tokens(
    actor=Depends(require_member_role("owner", "admin")),
    session: Session = Depends(get_db),
):
    org, _, _ = actor
    tokens = session.exec(
        select(ScimToken)
        .where(ScimToken.org_id == org.id)
        .order_by(ScimToken.created_at.desc())
    ).all()
    return {
        "tokens": [
            {
                "id": token.id,
                "label": token.label,
                "active": token.is_active,
                "last_used_at": token.last_used_at.isoformat()
                if token.last_used_at
                else None,
                "expires_at": token.expires_at.isoformat()
                if token.expires_at
                else None,
                "created_at": token.created_at.isoformat(),
            }
            for token in tokens
        ]
    }


@router.post("/v1/org/scim-tokens/{token_id}/rotate")
def rotate_scim_token(
    token_id: str,
    req: ScimTokenRotationRequest,
    actor=Depends(require_member_role("owner")),
    session: Session = Depends(get_db),
):
    require_writable_region()
    if not 1 <= req.expires_in_days <= 3650:
        raise HTTPException(status_code=422, detail="expires_in_days must be between 1 and 3650")
    org, user, _ = actor
    previous = session.exec(
        select(ScimToken).where(
            ScimToken.id == token_id,
            ScimToken.org_id == org.id,
        )
    ).first()
    if not previous:
        raise HTTPException(status_code=404, detail="SCIM token not found")
    previous.is_active = False
    raw = f"scim_{secrets.token_urlsafe(32)}"
    replacement = ScimToken(
        org_id=org.id,
        token_hash=_hash_token(raw),
        label=previous.label,
        expires_at=utc_now() + timedelta(days=req.expires_in_days),
    )
    session.add(previous)
    session.add(replacement)
    session.add(
        AuditLog(
            actor=user.id,
            org_id=org.id,
            action="scim_token.rotated",
            meta_json=json.dumps({"revoked_token_id": previous.id}),
        )
    )
    session.commit()
    session.refresh(replacement)
    return {
        "id": replacement.id,
        "label": replacement.label,
        "token": raw,
        "expires_at": replacement.expires_at.isoformat(),
        "warning": "Store this token securely; it will not be shown again.",
    }


@router.delete("/v1/org/scim-tokens/{token_id}", status_code=204)
def revoke_scim_token(
    token_id: str,
    actor=Depends(require_member_role("owner")),
    session: Session = Depends(get_db),
):
    require_writable_region()
    org, user, _ = actor
    token = session.exec(
        select(ScimToken).where(
            ScimToken.id == token_id,
            ScimToken.org_id == org.id,
        )
    ).first()
    if not token:
        raise HTTPException(status_code=404, detail="SCIM token not found")
    token.is_active = False
    session.add(token)
    session.add(
        AuditLog(
            actor=user.id,
            org_id=org.id,
            action="scim_token.revoked",
            meta_json=json.dumps({"token_id": token.id}),
        )
    )
    session.commit()


def _scim_org(
    authorization: Optional[str] = Header(None),
    session: Session = Depends(get_db),
) -> Organization:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="SCIM bearer token required")
    token = session.exec(
        select(ScimToken).where(
            ScimToken.token_hash == _hash_token(authorization.split(" ", 1)[1]),
            ScimToken.is_active == True,  # noqa: E712
        )
    ).first()
    if not token or (token.expires_at and token.expires_at <= utc_now()):
        raise HTTPException(status_code=401, detail="Invalid or expired SCIM token")
    token.last_used_at = utc_now()
    session.add(token)
    session.commit()
    org = session.get(Organization, token.org_id)
    if not org:
        raise HTTPException(status_code=401, detail="Organization not found")
    return org


@router.get("/scim/v2.0/Users")
def scim_list_users(
    org: Organization = Depends(_scim_org),
    session: Session = Depends(get_db),
    startIndex: int = Query(1, ge=1),
    count: int = Query(100, ge=1, le=1000),
    filter: Optional[str] = Query(None),
):
    memberships = session.exec(
        select(Membership).where(Membership.org_id == org.id)
    ).all()
    users = [session.get(User, membership.user_id) for membership in memberships]
    users = [user for user in users if user]
    if filter:
        parts = filter.split(" ", 2)
        if len(parts) != 3 or parts[0].lower() != "username" or parts[1].lower() != "eq":
            raise HTTPException(status_code=400, detail="Only userName eq filters are supported")
        expected = parts[2].strip().strip('"\'').lower()
        users = [user for user in users if user.email.lower() == expected]
    active_ids = {
        membership.user_id
        for membership in memberships
    }
    page = users[startIndex - 1 : startIndex - 1 + count]
    return {
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:ListResponse"],
        "totalResults": len(users),
        "startIndex": startIndex,
        "itemsPerPage": len(page),
        "Resources": [
            {
                "id": user.id,
                "userName": user.email,
                "displayName": user.full_name,
                "active": user.id in active_ids,
                "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
            }
            for user in page
        ],
    }


@router.post("/scim/v2.0/Users")
def scim_create_user(
    req: ScimUserRequest,
    org: Organization = Depends(_scim_org),
    session: Session = Depends(get_db),
):
    user = session.exec(select(User).where(User.email == req.userName)).first()
    if not user:
        user = User(email=req.userName, full_name=req.displayName, is_verified=True)
        session.add(user)
        session.commit()
        session.refresh(user)
    membership = session.exec(
        select(Membership).where(
            Membership.org_id == org.id,
            Membership.user_id == user.id,
        )
    ).first()
    if not membership:
        if req.active:
            session.add(Membership(org_id=org.id, user_id=user.id, role="developer"))
        session.commit()
    session.add(
        AuditLog(
            actor="scim",
            org_id=org.id,
            action="scim.user.provisioned",
            meta_json=json.dumps({"user_id": user.id, "active": req.active}),
        )
    )
    session.commit()
    return {
        "id": user.id,
        "userName": user.email,
        "displayName": user.full_name,
        "active": req.active,
        "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
    }


@router.patch("/scim/v2.0/Users/{user_id}")
async def scim_update_user(
    user_id: str,
    request: Request,
    org: Organization = Depends(_scim_org),
    session: Session = Depends(get_db),
):
    user = session.get(User, user_id)
    membership = session.exec(
        select(Membership).where(
            Membership.org_id == org.id,
            Membership.user_id == user_id,
        )
    ).first()
    if not user:
        raise HTTPException(status_code=404, detail="SCIM user not found")
    document = await request.json()
    for operation in document.get("Operations", []):
        path = str(operation.get("path", "")).lower()
        value = operation.get("value")
        if path in {"active", "user.active"} and isinstance(value, bool):
            if value and not membership:
                session.add(Membership(org_id=org.id, user_id=user.id, role="developer"))
            elif not value and membership:
                session.delete(membership)
        elif path in {"displayname", "name.formatted"} and isinstance(value, str):
            user.full_name = value
        elif path in {"username", "emails.value"} and isinstance(value, str):
            user.email = value
        else:
            raise HTTPException(status_code=422, detail=f"Unsupported SCIM path: {path}")
    session.add(user)
    session.add(
        AuditLog(
            actor="scim",
            org_id=org.id,
            action="scim.user.updated",
            meta_json=json.dumps({"user_id": user.id}),
        )
    )
    session.commit()
    return {
        "id": user.id,
        "userName": user.email,
        "displayName": user.full_name,
        "active": session.exec(
            select(Membership).where(
                Membership.org_id == org.id,
                Membership.user_id == user.id,
            )
        ).first()
        is not None,
        "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
    }


@router.delete("/scim/v2.0/Users/{user_id}", status_code=204)
def scim_deactivate_user(
    user_id: str,
    org: Organization = Depends(_scim_org),
    session: Session = Depends(get_db),
):
    user = session.get(User, user_id)
    membership = session.exec(
        select(Membership).where(
            Membership.org_id == org.id,
            Membership.user_id == user_id,
        )
    ).first()
    if not user:
        raise HTTPException(status_code=404, detail="SCIM user not found")
    if membership:
        session.delete(membership)
    session.add(
        AuditLog(
            actor="scim",
            org_id=org.id,
            action="scim.user.deactivated",
            meta_json=json.dumps({"user_id": user.id}),
        )
    )
    session.commit()


@router.get("/v1/compliance/evidence")
def compliance_evidence(
    actor=Depends(require_member_role("owner", "admin")),
    session: Session = Depends(get_db),
):
    org, _, _ = actor
    audit_count = len(
        session.exec(select(AuditLog).where(AuditLog.org_id == org.id)).all()
    )
    return {
        "organization_id": org.id,
        "controls": {
            "tenant_audit_logging": audit_count > 0,
            "scoped_api_keys": True,
            "signed_webhooks": True,
            "production_secret_validation": True,
            "sso_configured": session.exec(
                select(SSOConnection).where(
                    SSOConnection.org_id == org.id,
                    SSOConnection.enabled == True,  # noqa: E712
                )
            ).first()
            is not None,
        },
        "audit_events": audit_count,
        "generated_at": utc_now().isoformat(),
    }


@router.get("/v1/compliance/audit-export")
def audit_export(
    actor=Depends(require_member_role("owner", "admin")),
    session: Session = Depends(get_db),
):
    org, _, _ = actor
    events = session.exec(
        select(AuditLog)
        .where(AuditLog.org_id == org.id)
        .order_by(AuditLog.ts.asc(), AuditLog.id.asc())
    ).all()
    previous = "0" * 64
    records = []
    for event in events:
        payload = {
            "id": event.id,
            "actor": event.actor,
            "action": event.action,
            "meta_json": event.meta_json,
            "ts": event.ts.isoformat(),
            "previous_hash": previous,
        }
        digest = hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        payload["hash"] = digest
        previous = digest
        records.append(payload)
    evidence = ComplianceEvidence(
        org_id=org.id,
        control="audit_log_export",
        evidence_hash=previous,
        payload_json=json.dumps({"count": len(records), "head": previous}),
    )
    session.add(evidence)
    session.commit()
    return {
        "organization_id": org.id,
        "algorithm": "sha256-chain",
        "head_hash": previous,
        "events": records,
    }


@router.post("/v1/compliance/access-reviews")
def create_access_review(
    actor=Depends(require_member_role("owner", "admin")),
    session: Session = Depends(get_db),
):
    org, user, _ = actor
    review = AccessReview(org_id=org.id, reviewer_id=user.id)
    session.add(review)
    session.commit()
    session.refresh(review)
    return {"id": review.id, "status": review.status, "created_at": review.created_at.isoformat()}


@router.get("/v1/compliance/access-reviews")
def list_access_reviews(
    actor=Depends(require_member_role("owner", "admin")),
    session: Session = Depends(get_db),
):
    org, _, _ = actor
    reviews = session.exec(
        select(AccessReview)
        .where(AccessReview.org_id == org.id)
        .order_by(AccessReview.created_at.desc())
    ).all()
    return {
        "reviews": [
            {
                "id": review.id,
                "reviewer_id": review.reviewer_id,
                "status": review.status,
                "notes": review.notes,
                "created_at": review.created_at.isoformat(),
                "reviewed_at": review.reviewed_at.isoformat()
                if review.reviewed_at
                else None,
            }
            for review in reviews
        ]
    }


@router.patch("/v1/compliance/access-reviews/{review_id}")
def update_access_review(
    review_id: str,
    req: AccessReviewUpdate,
    actor=Depends(require_member_role("owner", "admin")),
    session: Session = Depends(get_db),
):
    if req.status not in {"open", "completed", "accepted", "remediated"}:
        raise HTTPException(status_code=422, detail="Invalid access review status")
    org, user, _ = actor
    review = session.exec(
        select(AccessReview).where(
            AccessReview.id == review_id,
            AccessReview.org_id == org.id,
        )
    ).first()
    if not review:
        raise HTTPException(status_code=404, detail="Access review not found")
    review.status = req.status
    review.notes = req.notes
    review.reviewer_id = user.id
    review.reviewed_at = utc_now() if req.status != "open" else None
    session.add(review)
    session.add(
        AuditLog(
            actor=user.id,
            org_id=org.id,
            action="compliance.access_review.updated",
            meta_json=json.dumps({"review_id": review.id, "status": review.status}),
        )
    )
    session.commit()
    return {
        "id": review.id,
        "status": review.status,
        "reviewed_at": review.reviewed_at,
    }


@router.get("/v1/compliance/retention")
def retention_report(
    actor=Depends(require_member_role("owner", "admin")),
    session: Session = Depends(get_db),
):
    org, _, _ = actor
    now = utc_now()
    audit_count = len(
        session.exec(select(AuditLog).where(AuditLog.org_id == org.id)).all()
    )
    evidence_count = len(
        session.exec(
            select(ComplianceEvidence).where(ComplianceEvidence.org_id == org.id)
        ).all()
    )
    return {
        "organization_id": org.id,
        "generated_at": now.isoformat(),
        "policy": {
            "audit_retention_days": int(os.getenv("AUDIT_RETENTION_DAYS", "365")),
            "evidence_retention_days": int(os.getenv("EVIDENCE_RETENTION_DAYS", "2555")),
            "deletion_mode": "operator_approved",
        },
        "counts": {"audit_events": audit_count, "evidence_records": evidence_count},
    }


@router.get("/v1/system/region/health")
def region_health():
    return {
        "region": os.getenv("SKELION_REGION", "primary"),
        "deployment_ring": os.getenv("SKELION_DEPLOYMENT_RING", "stable"),
        "read_only": os.getenv("SKELION_READ_ONLY", "false").lower() == "true",
        "failover_target": os.getenv("SKELION_FAILOVER_TARGET"),
        "database_role": os.getenv("SKELION_DATABASE_ROLE", "primary"),
        "queue_role": os.getenv("SKELION_QUEUE_ROLE", "primary"),
    }


@router.get("/v1/system/region")
def system_region():
    import os

    return {
        "region": os.getenv("SKELION_REGION", "primary"),
        "deployment_ring": os.getenv("SKELION_DEPLOYMENT_RING", "stable"),
        "read_only": os.getenv("SKELION_READ_ONLY", "false").lower() == "true",
    }
