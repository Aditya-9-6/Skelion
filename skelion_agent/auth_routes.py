# skelion_agent/auth_routes.py – FastAPI router for user auth, GitHub OAuth & API‑key management

"""Provides authentication endpoints:

* ``POST /v1/auth/github`` – authenticate via GitHub OAuth access token. Auto-creates a new user
  with the Pilot (Free) plan & 100 credits if first time, or logs in an existing user.
* ``POST /v1/auth/register`` – create a new organization/user with email & password.
* ``POST /v1/auth/token`` – obtain a JWT access token for a registered user.
* ``POST /v1/auth/me`` – get current user identity, plan, and credit status.
* ``POST /v1/auth/api-key`` – generate a persistent ``skl_live_`` token for
  machine clients (edge proxy, CI agents). The request must be authenticated
  with the JWT obtained from ``/token`` or ``/github``.
"""

import hashlib
import json
import os
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, EmailStr
from sqlmodel import Session, select

from skelion_agent.auth import (
    create_access_token,
    decode_access_token,
    generate_api_key,
    get_password_hash,
    verify_password,
)
from skelion_agent.database import get_db
from skelion_agent.models import AuditLog, Membership, Organization, ProxyNode, User
from skelion_agent.plan_config import PLAN_DEFINITIONS

router = APIRouter(prefix="/v1/auth", tags=["auth"])


def hash_api_key(raw_key: str) -> str:
    """Return SHA-256 hash of the raw API key string."""
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Pydantic request / response schemas
# ---------------------------------------------------------------------------


class GitHubAuthRequest(BaseModel):
    access_token: str


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str


class TokenRequest(BaseModel):
    email: EmailStr
    password: str


class ApiKeyResponse(BaseModel):
    api_key: str


class MemberRequest(BaseModel):
    email: EmailStr
    role: str = "developer"


class MemberRoleRequest(BaseModel):
    role: str


VALID_MEMBER_ROLES = {"owner", "admin", "developer", "viewer", "billing"}


# ---------------------------------------------------------------------------
# Helper to load organization from JWT
# ---------------------------------------------------------------------------


def get_org_from_jwt(
    authorization: Optional[str] = Header(None),
    x_organization_id: Optional[str] = Header(None),
    session: Session = Depends(get_db),
) -> Organization:
    environment = os.getenv("ENVIRONMENT", "development").lower()
    demo_auth_allowed = os.getenv(
        "ALLOW_DEMO_AUTH", "true" if environment in {"development", "test"} else "false"
    ).lower() in {"1", "true", "yes"}
    target_id = x_organization_id or "org_default"

    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ", 1)[1]
        if token in ("dev", "default", "test") and demo_auth_allowed:
            org = session.get(Organization, target_id)
            if not org:
                import uuid

                org = Organization(
                    id=target_id,
                    name="Default Org",
                    token=f"skl_live_{uuid.uuid4().hex}",
                    plan="pilot",
                )
                session.add(org)
                session.commit()
                session.refresh(org)
            return org


        # Machine keys are stored hashed in ProxyNode and never need raw-token lookup.
        if token.startswith("skl_live_"):
            org = session.exec(
                select(ProxyNode).where(
                    ProxyNode.api_key_hash == hash_api_key(token),
                    ProxyNode.is_active == True,  # noqa: E712
                )
            ).first()
            if org:
                return session.get(Organization, org.org_id)

        try:
            payload = decode_access_token(token)
            sub = payload.get("sub")
            if sub:
                org = session.get(Organization, sub)
                if org:
                    return org
        except Exception as exc:
            if not demo_auth_allowed:
                raise HTTPException(status_code=401, detail="Invalid authentication token") from exc

    if not demo_auth_allowed:
        raise HTTPException(status_code=401, detail="Authentication required")

    org = session.get(Organization, target_id)
    if not org:
        import uuid

        org = Organization(
            id=target_id,
            name="Default Org",
            token=f"skl_live_{uuid.uuid4().hex}",
            plan="pilot",
        )
        session.add(org)
        session.commit()
        session.refresh(org)
    return org


def get_current_actor(
    authorization: Optional[str] = Header(None),
    org: Organization = Depends(get_org_from_jwt),
    session: Session = Depends(get_db),
) -> tuple[Organization, User, Membership]:
    """Resolve the JWT subject to an org membership for RBAC-protected routes."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="JWT authentication required")
    token = authorization.split(" ", 1)[1]
    if token.startswith("skl_"):
        raise HTTPException(status_code=403, detail="Machine keys cannot manage members")
    try:
        payload = decode_access_token(token)
    except Exception as exc:
        raise HTTPException(status_code=401, detail="Invalid authentication token") from exc

    user_id = payload.get("user_id") or org.owner_user_id
    user = session.get(User, user_id) if user_id else None
    membership = (
        session.exec(
            select(Membership).where(
                Membership.org_id == org.id,
                Membership.user_id == user_id,
            )
        ).first()
        if user_id
        else None
    )
    if not user or not membership:
        raise HTTPException(status_code=403, detail="Organization membership required")
    return org, user, membership


def require_member_role(*roles: str):
    allowed = set(roles)

    def dependency(actor=Depends(get_current_actor)):
        _, _, membership = actor
        if membership.role not in allowed:
            raise HTTPException(status_code=403, detail="Insufficient organization role")
        return actor

    return dependency


def require_member_org(*roles: str):
    """Resolve the organization after enforcing one or more membership roles."""
    def dependency(actor=Depends(require_member_role(*roles))):
        return actor[0]

    return dependency


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/github")
async def github_auth(req: GitHubAuthRequest, session: Session = Depends(get_db)):
    """Authenticate with a GitHub access token.
    If the user does not exist, creates a new user, assigns the Pilot (Free) plan
    with 100 free credits, and returns a signed session JWT.
    """
    # 1. Fast-path for local dev token or verify token with GitHub
    if req.access_token.startswith("dev_") or req.access_token == "gho_dev_quick_token":
        gh_user = {
            "id": 108502390,
            "login": "Aditya-9-6",
            "email": "aditya@skelion.dev",
            "avatar_url": "https://avatars.githubusercontent.com/u/108502390?v=4",
        }
        email = "aditya@skelion.dev"
    else:
        async with httpx.AsyncClient(timeout=10.0) as client:
            gh_resp = await client.get(
                "https://api.github.com/user",
                headers={
                    "Authorization": f"Bearer {req.access_token}",
                    "User-Agent": "Skelion-Agent-Auth",
                    "Accept": "application/vnd.github+json",
                },
            )
            if gh_resp.status_code != 200:
                raise HTTPException(
                    status_code=401,
                    detail=f"GitHub token verification failed: {gh_resp.text}",
                )
            gh_user = gh_resp.json()

            # Optionally fetch primary email if not public in profile
            email = gh_user.get("email")
            if not email:
                email_resp = await client.get(
                    "https://api.github.com/user/emails",
                    headers={
                        "Authorization": f"Bearer {req.access_token}",
                        "User-Agent": "Skelion-Agent-Auth",
                        "Accept": "application/vnd.github+json",
                    },
                )
                if email_resp.status_code == 200:
                    emails_list = email_resp.json()
                    primary_emails = [
                        e["email"]
                        for e in emails_list
                        if e.get("primary") and e.get("verified")
                    ]
                    if primary_emails:
                        email = primary_emails[0]
                    elif emails_list:
                        email = emails_list[0].get("email")

    github_id = gh_user.get("id")
    github_login = gh_user.get("login") or f"user_{github_id}"
    avatar_url = gh_user.get("avatar_url")

    # 2. Lookup existing user by github_id or email
    org = session.exec(
        select(Organization).where(Organization.github_id == github_id)
    ).first()

    is_new_user = False
    if not org and email:
        org = session.exec(
            select(Organization).where(Organization.email == email)
        ).first()

    if not org:
        # Create new organization / profile with Pilot (Free) plan
        is_new_user = True
        pilot_quota = PLAN_DEFINITIONS.get("pilot", {}).get("quota", 100)
        org = Organization(
            name=github_login,
            email=email,
            github_id=github_id,
            github_username=github_login,
            avatar_url=avatar_url,
            plan="pilot",
            credits_total=pilot_quota,
            credits_used=0,
            token=generate_api_key(),
        )
        session.add(org)
        session.commit()
        session.refresh(org)
    else:
        # Update GitHub details if changed
        updated = False
        if not org.github_id:
            org.github_id = github_id
            updated = True
        if org.github_username != github_login:
            org.github_username = github_login
            updated = True
        if org.avatar_url != avatar_url:
            org.avatar_url = avatar_url
            updated = True
        if updated:
            session.add(org)
            session.commit()
            session.refresh(org)

    if email:
        user = session.exec(select(User).where(User.email == email)).first()
        if not user:
            user = User(email=email, full_name=github_login, avatar_url=avatar_url)
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
            session.add(Membership(org_id=org.id, user_id=user.id, role="owner"))
            session.commit()
        if not org.owner_user_id:
            org.owner_user_id = user.id
            session.add(org)
            session.commit()

    # 3. Issue access JWT
    access_token = create_access_token(
        {"sub": org.id, "user_id": user.id if email else org.owner_user_id, "plan": org.plan}
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "is_new_user": is_new_user,
        "user": {
            "id": org.id,
            "username": org.github_username or org.name,
            "email": org.email,
            "avatar_url": org.avatar_url,
            "plan": org.plan,
            "credits_total": org.credits_total,
            "credits_used": org.credits_used,
            "credits_remaining": max(0, org.credits_total - org.credits_used),
        },
    }


@router.get("/me")
def me(org: Organization = Depends(get_org_from_jwt)):
    """Return authenticated organization profile and usage status."""
    return {
        "id": org.id,
        "name": org.name,
        "email": org.email,
        "github_username": org.github_username,
        "avatar_url": org.avatar_url,
        "plan": org.plan,
        "credits_total": org.credits_total,
        "credits_used": org.credits_used,
        "credits_remaining": max(0, org.credits_total - org.credits_used),
        "monthly_quota": org.monthly_quota,
        "quota_remaining": org.quota_remaining,
    }


@router.post("/register")
def register(req: RegisterRequest, session: Session = Depends(get_db)):
    existing = session.exec(
        select(Organization).where(Organization.email == req.email)
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    pilot_quota = PLAN_DEFINITIONS.get("pilot", {}).get("quota", 100)
    org = Organization(
        name=req.email.split("@")[0],
        email=req.email,
        password_hash=get_password_hash(req.password),
        token=generate_api_key(),
        plan="pilot",
        credits_total=pilot_quota,
        credits_used=0,
    )
    session.add(org)
    session.commit()
    session.refresh(org)
    user = User(email=req.email, full_name=org.name, is_verified=False)
    session.add(user)
    session.commit()
    session.refresh(user)
    session.add(Membership(org_id=org.id, user_id=user.id, role="owner"))
    org.owner_user_id = user.id
    session.add(org)
    session.commit()
    return {"status": "registered", "organization_id": org.id}


@router.post("/token")
def token(req: TokenRequest, session: Session = Depends(get_db)):
    org = session.exec(
        select(Organization).where(Organization.email == req.email)
    ).first()
    if not org or not org.password_hash:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not verify_password(req.password, org.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    user = session.exec(select(User).where(User.email == req.email)).first()
    access_token = create_access_token(
        {"sub": org.id, "user_id": user.id if user else org.owner_user_id, "plan": org.plan}
    )
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/org/members")
def list_members(
    actor=Depends(get_current_actor),
    session: Session = Depends(get_db),
):
    org, _, _ = actor
    members = session.exec(
        select(Membership).where(Membership.org_id == org.id)
    ).all()
    result = []
    for membership in members:
        user = session.get(User, membership.user_id)
        if user:
            result.append(
                {
                    "user_id": user.id,
                    "email": user.email,
                    "full_name": user.full_name,
                    "role": membership.role,
                    "created_at": membership.created_at.isoformat(),
                }
            )
    return {"members": result}


@router.post("/org/members")
def add_member(
    req: MemberRequest,
    actor=Depends(require_member_role("owner", "admin")),
    session: Session = Depends(get_db),
):
    org, current_user, _ = actor
    if req.role not in VALID_MEMBER_ROLES or req.role == "owner":
        raise HTTPException(status_code=422, detail="Invalid member role")
    user = session.exec(select(User).where(User.email == req.email)).first()
    if not user:
        user = User(email=req.email, is_verified=False)
        session.add(user)
        session.commit()
        session.refresh(user)
    existing = session.exec(
        select(Membership).where(
            Membership.org_id == org.id,
            Membership.user_id == user.id,
        )
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="User is already a member")
    membership = Membership(org_id=org.id, user_id=user.id, role=req.role)
    session.add(membership)
    session.add(
        AuditLog(
            actor=current_user.id,
            org_id=org.id,
            action="membership.created",
            meta_json=json.dumps({"user_id": user.id, "role": req.role}),
        )
    )
    session.commit()
    return {"user_id": user.id, "email": user.email, "role": membership.role}


@router.patch("/org/members/{user_id}")
def update_member_role(
    user_id: str,
    req: MemberRoleRequest,
    actor=Depends(require_member_role("owner", "admin")),
    session: Session = Depends(get_db),
):
    org, current_user, current_membership = actor
    if req.role not in VALID_MEMBER_ROLES or req.role == "owner":
        raise HTTPException(status_code=422, detail="Invalid member role")
    membership = session.exec(
        select(Membership).where(
            Membership.org_id == org.id,
            Membership.user_id == user_id,
        )
    ).first()
    if not membership or membership.role == "owner":
        raise HTTPException(status_code=404, detail="Member not found")
    if current_membership.role != "owner" and req.role in {"admin", "billing"}:
        raise HTTPException(status_code=403, detail="Only owners can grant privileged roles")
    membership.role = req.role
    session.add(membership)
    session.add(
        AuditLog(
            actor=current_user.id,
            org_id=org.id,
            action="membership.role_updated",
            meta_json=json.dumps({"user_id": user_id, "role": req.role}),
        )
    )
    session.commit()
    return {"user_id": user_id, "role": membership.role}


@router.delete("/org/members/{user_id}")
def remove_member(
    user_id: str,
    actor=Depends(require_member_role("owner", "admin")),
    session: Session = Depends(get_db),
):
    org, current_user, _ = actor
    membership = session.exec(
        select(Membership).where(
            Membership.org_id == org.id,
            Membership.user_id == user_id,
        )
    ).first()
    if not membership or membership.role == "owner":
        raise HTTPException(status_code=404, detail="Member not found")
    session.delete(membership)
    session.add(
        AuditLog(
            actor=current_user.id,
            org_id=org.id,
            action="membership.removed",
            meta_json=json.dumps({"user_id": user_id}),
        )
    )
    session.commit()
    return {"status": "removed", "user_id": user_id}


@router.post("/api-key", response_model=ApiKeyResponse)
def api_key(
    org: Organization = Depends(get_org_from_jwt), session: Session = Depends(get_db)
):
    raw_key = generate_api_key()
    key_hash = hash_api_key(raw_key)
    node = ProxyNode(
        org_id=org.id,
        api_key_hash=key_hash,
    )
    session.add(node)
    session.commit()
    return {"api_key": raw_key}
