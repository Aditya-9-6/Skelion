# skelion_agent/api_key_service.py — Scoped API Key Management & Ingress Authentication

import os
import hashlib
import secrets
from typing import Optional, Tuple
from datetime import datetime, timezone
from fastapi import Header, HTTPException, Depends, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlmodel import Session, select

from skelion_agent.database import get_db
from skelion_agent.models import Organization, ApiKey, utc_now

security = HTTPBearer(auto_error=False)


def hash_api_key(raw_key: str) -> str:
    """Return SHA-256 hash of API key for safe database storage."""
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def generate_scoped_api_key(prefix: str = "skl_live_") -> Tuple[str, str, str]:
    """
    Generate a new API key.
    Returns: (raw_key, key_prefix, key_hash)
    """
    random_part = secrets.token_hex(20)  # 40 chars
    raw_key = f"{prefix}{random_part}"
    key_hash = hash_api_key(raw_key)
    return raw_key, prefix, key_hash


async def get_org_from_api_key_or_jwt(
    auth_header: Optional[HTTPAuthorizationCredentials] = Security(security),
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    db: Session = Depends(get_db),
) -> Organization:
    """
    Authenticate request via:
    1. Authorization: Bearer skl_live_... (or skl_test_...)
    2. X-API-Key: skl_live_...
    3. Authorization: Bearer <jwt_or_dev_token>
    """
    token_str = None
    if auth_header and auth_header.credentials:
        token_str = auth_header.credentials.strip()
    elif x_api_key:
        token_str = x_api_key.strip()

    if not token_str:
        if os.getenv("SKELION_ALLOW_DEV_FALLBACK", "false").lower() in ("true", "1"):
            dev_org = db.exec(select(Organization).where(Organization.github_username == "Aditya-9-6")).first()
            if dev_org:
                return dev_org
            default_org = db.exec(select(Organization)).first()
            if default_org:
                return default_org
        raise HTTPException(status_code=401, detail="API Key or Bearer Token required")

    # 1. Check if token is an API key (starts with skl_)
    if token_str.startswith("skl_live_") or token_str.startswith("skl_test_") or token_str.startswith("skl_"):
        key_hash = hash_api_key(token_str)
        api_key = db.exec(
            select(ApiKey).where(ApiKey.key_hash == key_hash, ApiKey.is_active == True)
        ).first()

        if not api_key:
            # Check legacy organization.token format
            legacy_org = db.exec(
                select(Organization).where(Organization.token == token_str)
            ).first()
            if legacy_org:
                return legacy_org
            raise HTTPException(status_code=401, detail="Invalid or revoked Skelion API key")

        # Update last used timestamp
        api_key.last_used_at = utc_now()
        db.add(api_key)
        db.commit()

        org = db.get(Organization, api_key.org_id)
        if not org:
            raise HTTPException(status_code=401, detail="Organization associated with API key not found")
        return org

    # 2. Check if token is dev/default
    if token_str in ("dev", "default", "test"):
        dev_org = db.exec(select(Organization).where(Organization.github_username == "Aditya-9-6")).first()
        if dev_org:
            return dev_org
        first_org = db.exec(select(Organization)).first()
        if first_org:
            return first_org

    # 3. Fall back to standard JWT auth
    from skelion_agent.auth_routes import get_org_from_jwt
    return get_org_from_jwt(auth_header, db)
