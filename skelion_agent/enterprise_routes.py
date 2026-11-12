import hashlib
import json
import secrets
from datetime import timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from pydantic import BaseModel, EmailStr
from sqlmodel import Session, select

from skelion_agent.auth_routes import get_current_actor, require_member_role
from skelion_agent.database import get_db
from skelion_agent.models import (
    AuditLog,
    Membership,
    Organization,
    ScimToken,
    SSOConnection,
    User,
    utc_now,
)

router = APIRouter(tags=["Enterprise Control Plane"])


class SSOConnectionRequest(BaseModel):
    provider: str
    issuer_url: Optional[str] = None
    client_id: Optional[str] = None
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


@router.post("/v1/org/scim-tokens")
def create_scim_token(
    req: ScimTokenRequest,
    actor=Depends(require_member_role("owner")),
    session: Session = Depends(get_db),
):
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


@router.get("/v1/system/region")
def system_region():
    import os

    return {
        "region": os.getenv("SKELION_REGION", "primary"),
        "deployment_ring": os.getenv("SKELION_DEPLOYMENT_RING", "stable"),
        "read_only": os.getenv("SKELION_READ_ONLY", "false").lower() == "true",
    }
