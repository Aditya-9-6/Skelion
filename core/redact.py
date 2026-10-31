# core/redact.py — Comprehensive Redaction Engine (Apache-2.0 Open Core)

import re
from typing import Any, Dict, List, Union

# ---------------------------------------------------------------------------
# Strict Allow-Lists
# ---------------------------------------------------------------------------

ALLOWED_HEADERS = {
    "content-type",
    "content-length",
    "accept",
    "accept-encoding",
    "user-agent",
    "host",
    "x-request-id",
    "x-correlation-id",
    "x-forwarded-proto",
    "origin",
    "referer",
    "x-ratelimit-limit",
    "x-ratelimit-remaining",
    "x-ratelimit-reset",
}

# ---------------------------------------------------------------------------
# Regex Scrubbers for High-Risk Patterns & PII
# ---------------------------------------------------------------------------

RE_EMAIL = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")
RE_PHONE = re.compile(r"\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b")
RE_IPV4 = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")

# API Keys & High-Entropy Token Prefixes
RE_JWT = re.compile(r"\beyJ[A-Za-z0-9-_]+\.eyJ[A-Za-z0-9-_]+\.[A-Za-z0-9-_]+\b")
RE_SKELION_KEY = re.compile(r"\bskl_(?:live|test)_[a-zA-Z0-9]{16,40}\b")
RE_OPENAI_KEY = re.compile(r"\bsk-(?:proj-|live-)?[a-zA-Z0-9]{20,50}\b")
RE_ANTHROPIC_KEY = re.compile(r"\bsk-ant-[a-zA-Z0-9]{20,60}\b")
RE_AWS_KEY = re.compile(r"\b(?:AKIA|ABIA|ACCA)[0-9A-Z]{16}\b")
RE_BEARER_TOKEN = re.compile(r"(?i)\bBearer\s+[a-zA-Z0-9_\-\.]{15,}\b")
RE_BASIC_AUTH = re.compile(r"(?i)\bBasic\s+[a-zA-Z0-9+/=]{15,}\b")

# Indian National ID Patterns
RE_PAN_CARD = re.compile(r"\b[A-Z]{5}[0-9]{4}[A-Z]{1}\b")
RE_AADHAAR_LIKE = re.compile(r"\b[2-9]{1}[0-9]{3}\s?[0-9]{4}\s?[0-9]{4}\b")

# Generic High Entropy Hex / Base64 Token
RE_HEX_SECRET = re.compile(
    r"\b(?:secret|token|apikey|password|passwd|key)=['\"]?([a-zA-Z0-9_=-]{16,})['\"]?",
    re.IGNORECASE,
)

# Dynamic Route Normalization (UUIDs & Integer IDs)
RE_UUID = re.compile(
    r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b"
)
RE_NUMERIC_ID = re.compile(r"(?<=/)\d{2,}(?=(/|$|\?))")


# ---------------------------------------------------------------------------
# Luhn Algorithm for Credit Card Validation
# ---------------------------------------------------------------------------


def is_luhn_valid(card_num: str) -> bool:
    digits = [int(d) for d in card_num if d.isdigit()]
    if len(digits) < 13 or len(digits) > 19:
        return False
    checksum = 0
    reverse_digits = digits[::-1]
    for i, d in enumerate(reverse_digits):
        if i % 2 == 1:
            d = d * 2
            if d > 9:
                d = d - 9
        checksum += d
    return checksum % 10 == 0


RE_CARD_CANDIDATE = re.compile(r"\b(?:\d{4}[-\s]?){3}\d{4}\b|\b\d{13,19}\b")


def scrub_credit_cards(text: str) -> str:
    """Detect and mask valid credit card numbers using Luhn checksum."""

    def replacer(match):
        raw = match.group(0)
        cleaned = re.sub(r"[-\s]", "", raw)
        if is_luhn_valid(cleaned):
            return "[REDACTED_CREDIT_CARD]"
        return raw

    return RE_CARD_CANDIDATE.sub(replacer, text)


# ---------------------------------------------------------------------------
# Redaction Functions
# ---------------------------------------------------------------------------


def normalize_route_path(path: str) -> str:
    """Normalize dynamic segments in route paths into generic templates (e.g., /users/:id)."""
    if not path:
        return "/"
    p = RE_UUID.sub(":id", path)
    p = RE_NUMERIC_ID.sub(":id", p)
    return p


def redact_text(text: str) -> str:
    """Scrub PII, auth credentials, tokens, and cards from free-form text or bodies."""
    if not text:
        return ""

    out = text
    # 1. Credit Cards via Luhn
    out = scrub_credit_cards(out)

    # 2. Auth Credentials & Keys
    out = RE_JWT.sub("[REDACTED_JWT]", out)
    out = RE_SKELION_KEY.sub("[REDACTED_SKELION_KEY]", out)
    out = RE_OPENAI_KEY.sub("[REDACTED_API_KEY]", out)
    out = RE_ANTHROPIC_KEY.sub("[REDACTED_API_KEY]", out)
    out = RE_AWS_KEY.sub("[REDACTED_AWS_KEY]", out)
    out = RE_BEARER_TOKEN.sub("Bearer [REDACTED_TOKEN]", out)
    out = RE_BASIC_AUTH.sub("Basic [REDACTED_AUTH]", out)
    out = RE_HEX_SECRET.sub(r"\1=[REDACTED_SECRET]", out)

    # 3. PII & National IDs
    out = RE_PAN_CARD.sub("[REDACTED_PAN]", out)
    out = RE_AADHAAR_LIKE.sub("[REDACTED_AADHAAR]", out)
    out = RE_EMAIL.sub("[REDACTED_EMAIL]", out)
    out = RE_PHONE.sub("[REDACTED_PHONE]", out)
    out = RE_IPV4.sub("[REDACTED_IP]", out)

    return out


def redact_headers(headers: Dict[str, Any]) -> Dict[str, str]:
    """Apply strict allow-list approach to HTTP headers.
    Headers not in ALLOWED_HEADERS are completely discarded.
    """
    clean = {}
    for k, v in headers.items():
        k_lower = k.lower().strip()
        if k_lower in ALLOWED_HEADERS:
            clean[k_lower] = redact_text(str(v))
        elif k_lower in (
            "authorization",
            "cookie",
            "set-cookie",
            "proxy-authorization",
            "x-api-key",
        ):
            clean[k_lower] = "[REDACTED]"
    return clean


def redact_json_structure(data: Union[Dict, List, Any]) -> Any:
    """Recursively scrub values inside JSON structures while masking sensitive field names."""
    SENSITIVE_KEYS = {
        "password",
        "passwd",
        "secret",
        "token",
        "access_token",
        "refresh_token",
        "api_key",
        "apikey",
        "private_key",
        "authorization",
        "auth",
        "cvv",
        "pan",
        "aadhaar",
    }

    if isinstance(data, dict):
        clean_dict = {}
        for k, v in data.items():
            if k.lower() in SENSITIVE_KEYS:
                clean_dict[k] = "[REDACTED]"
            elif isinstance(v, (dict, list)):
                clean_dict[k] = redact_json_structure(v)
            elif isinstance(v, str):
                clean_dict[k] = redact_text(v)
            else:
                clean_dict[k] = v
        return clean_dict
    elif isinstance(data, list):
        return [redact_json_structure(item) for item in data]
    elif isinstance(data, str):
        return redact_text(data)
    return data
