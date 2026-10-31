import re
from typing import Any, Dict

SENSITIVE_KEYS = {
    "authorization",
    "cookie",
    "x-api-key",
    "api_key",
    "secret",
    "password",
    "token",
    "authorization-token",
    "set-cookie",
    "auth",
    "x-auth-token",
}


def redact_headers(headers: Dict[str, str]) -> Dict[str, str]:
    """Mask any header whose name matches a sensitive key."""
    return {
        k: ("****" if k.lower() in SENSITIVE_KEYS else v) for k, v in headers.items()
    }


def _scrub(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            k: _scrub(v) for k, v in value.items() if k.lower() not in SENSITIVE_KEYS
        }
    if isinstance(value, list):
        return [_scrub(v) for v in value]
    if isinstance(value, str):
        # mask token‑like patterns
        return re.sub(
            r"(?i)(tok[en]{2,}|secret|api[-_]key)\s*[:=]\s*\S+", r"\1=****", value
        )
    return value


def redact_json(payload: Any) -> Any:
    """Recursively remove or mask sensitive fields from JSON‑serialisable payloads."""
    return _scrub(payload)
