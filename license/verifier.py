# license/verifier.py — Offline Ed25519 License Verifier & Graceful Degradation

import json
from datetime import datetime, timezone
from typing import Dict, Any

from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.exceptions import InvalidSignature

from core.entitlements import PLAN_ENTITLEMENTS
from license.issuer import get_public_key_hex

# Trusted public keys by key ID (kid) for offline rotation
TRUSTED_PUBLIC_KEYS: Dict[str, str] = {
    # Dynamically registered development root key
    "skelion_root_2026_v1": get_public_key_hex(),
}


def register_trusted_key(kid: str, public_key_hex: str):
    """Register or rotate an offline public key."""
    TRUSTED_PUBLIC_KEYS[kid] = public_key_hex


def verify_license_offline(license_data: Dict[str, Any]) -> Dict[str, Any]:
    """Verify an offline license file without any network calls.
    Return status:
    - 'valid': Cryptographically authentic, within active subscription period.
    - 'grace_period': Expired within grace period. Features remain active + warning notice.
    - 'degraded': Expired past grace period or invalid signature.
      CRITICAL REQUIREMENT: Degrades to 'local_community' features; NEVER breaks traffic or stops the proxy!
    """
    community_fallback = {
        "status": "degraded",
        "valid": False,
        "plan": "local_community",
        "features": PLAN_ENTITLEMENTS["local_community"]["features"],
        "limits": PLAN_ENTITLEMENTS["local_community"]["limits"],
        "message": "License invalid or missing. Operating under local community free mode.",
    }

    try:
        kid = license_data.get("kid")
        payload = license_data.get("payload")
        signature_hex = license_data.get("signature")

        if not kid or not payload or not signature_hex:
            community_fallback["reason"] = "Malformed license structure"
            return community_fallback

        pub_hex = TRUSTED_PUBLIC_KEYS.get(kid)
        if not pub_hex:
            community_fallback["reason"] = f"Untrusted key id: {kid}"
            return community_fallback

        # Re-construct canonical bytes
        canonical_bytes = json.dumps(
            payload, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        sig_bytes = bytes.fromhex(signature_hex)
        pub_bytes = bytes.fromhex(pub_hex)

        public_key = ed25519.Ed25519PublicKey.from_public_bytes(pub_bytes)
        public_key.verify(sig_bytes, canonical_bytes)

        # Signature is authentic! Now check lifecycle dates
        now = datetime.now(timezone.utc)
        expires_at = datetime.fromisoformat(payload["expires_at"])
        grace_days = payload.get("grace_days", 7)

        if now <= expires_at:
            return {
                "status": "valid",
                "valid": True,
                "plan": payload.get("plan", "local_team"),
                "features": payload.get("features", []),
                "limits": payload.get("limits", {}),
                "expires_at": payload["expires_at"],
                "customer": payload.get("customer", {}),
                "message": "License is valid and active.",
            }
        else:
            # Check if within grace period
            days_expired = (now - expires_at).total_seconds() / 86400.0
            if days_expired <= grace_days:
                return {
                    "status": "grace_period",
                    "valid": True,
                    "plan": payload.get("plan", "local_team"),
                    "features": payload.get("features", []),
                    "limits": payload.get("limits", {}),
                    "expires_at": payload["expires_at"],
                    "grace_days_remaining": round(grace_days - days_expired, 1),
                    "message": f"License expired on {payload['expires_at']}. Grace period active ({round(grace_days - days_expired, 1)} days remaining). Please renew your license.",
                }
            else:
                # Expired past grace period -> Graceful degradation to local_community!
                return {
                    "status": "degraded",
                    "valid": False,
                    "plan": "local_community",
                    "features": PLAN_ENTITLEMENTS["local_community"]["features"],
                    "limits": PLAN_ENTITLEMENTS["local_community"]["limits"],
                    "reason": f"License expired on {payload['expires_at']} (grace period ended)",
                    "message": "Subscription expired. Advanced features (fix generation, PR bot, MCP) degraded to community mode. Proxy traffic is completely unaffected.",
                }

    except InvalidSignature:
        community_fallback["reason"] = (
            "Cryptographic signature verification failed (tampered license)"
        )
        return community_fallback
    except Exception as e:
        community_fallback["reason"] = f"Verification exception: {str(e)}"
        return community_fallback
