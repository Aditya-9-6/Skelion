# license/issuer.py — Server-Side Ed25519 Offline License Signer & Issuer

import base64
import json
import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional, Tuple

from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization

from core.entitlements import PLAN_ENTITLEMENTS

DEFAULT_KID = "skelion_root_2026_v1"

# Fixed development 32-byte seed for deterministic offline verification across processes
DEV_SEED = b"skelion_dev_root_signing_key_32b"
_DEV_PRIVATE_KEY: Optional[ed25519.Ed25519PrivateKey] = None


def get_private_key() -> Tuple[ed25519.Ed25519PrivateKey, str]:
    """Retrieve private key from environment or deterministic dev seed."""
    global _DEV_PRIVATE_KEY
    env_key = os.getenv("SKELION_LICENSE_SIGNING_KEY")
    if env_key:
        raw = base64.b64decode(env_key)
        return ed25519.Ed25519PrivateKey.from_private_bytes(raw), DEFAULT_KID

    if _DEV_PRIVATE_KEY is None:
        _DEV_PRIVATE_KEY = ed25519.Ed25519PrivateKey.from_private_bytes(DEV_SEED)
    return _DEV_PRIVATE_KEY, DEFAULT_KID


def get_public_key_hex(private_key: Optional[ed25519.Ed25519PrivateKey] = None) -> str:
    """Return hex-encoded public key bytes for registration in verifier."""
    priv, _ = get_private_key() if private_key is None else (private_key, DEFAULT_KID)
    pub = priv.public_key()
    pub_bytes = pub.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    return pub_bytes.hex()


def issue_license(
    org_id: str,
    customer_name: str,
    customer_email: str,
    plan_id: str = "local_team",
    duration_days: int = 365,
    custom_limits: Optional[Dict[str, Any]] = None,
    grace_days: int = 7,
) -> Dict[str, Any]:
    """Issue and sign an offline-verifiable license file for Skelion Local."""
    plan_data = PLAN_ENTITLEMENTS.get(plan_id, PLAN_ENTITLEMENTS.get("local_team"))
    features = plan_data.get("features", [])
    limits = custom_limits or plan_data.get("limits", {})

    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(days=duration_days)

    payload = {
        "v": 1,
        "license_id": f"lic_{uuid.uuid4().hex[:12]}",
        "org_id": org_id,
        "sku": "local",
        "plan": plan_id,
        "limits": limits,
        "features": features,
        "issued_at": now.isoformat(),
        "expires_at": expires_at.isoformat(),
        "grace_days": grace_days,
        "customer": {
            "name": customer_name,
            "email": customer_email,
        },
    }

    # Canonical JSON serialization for reproducible signing
    canonical_bytes = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )

    priv_key, kid = get_private_key()
    signature_bytes = priv_key.sign(canonical_bytes)

    signed_license = {
        "license_format": "skelion-ed25519-v1",
        "kid": kid,
        "payload": payload,
        "signature": signature_bytes.hex(),
    }

    return signed_license
