# tests/test_redact.py — Comprehensive Redaction Acceptance Tests

import pytest
from core.redact import (
    redact_text,
    redact_headers,
    redact_json_structure,
    normalize_route_path,
    is_luhn_valid,
)


def test_credit_card_scrubbing_with_luhn():
    # Valid Visa card (Luhn passes)
    valid_visa = "4532015112830366"
    assert is_luhn_valid(valid_visa) is True
    res = redact_text(f"Customer card is {valid_visa}")
    assert "[REDACTED_CREDIT_CARD]" in res
    assert valid_visa not in res

    # Invalid sequence of 16 digits (Luhn fails)
    invalid_num = "1234567812345678"
    assert is_luhn_valid(invalid_num) is False
    res2 = redact_text(f"Random number is {invalid_num}")
    assert "[REDACTED_CREDIT_CARD]" not in res2


def test_api_keys_and_tokens_scrubbing():
    # JWT token
    jwt = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgN_p_placeholder_secret"
    res = redact_text(f"Token is {jwt}")
    assert "[REDACTED_JWT]" in res
    assert jwt not in res

    # Skelion API key
    skelion_key = "skl_live_a1b2c3d4e5f6789012345678"
    res2 = redact_text(f"Connect using {skelion_key}")
    assert "[REDACTED_SKELION_KEY]" in res2
    assert skelion_key not in res2

    # OpenAI API key
    openai_key = "sk-proj-abc1234567890def1234567890"
    res3 = redact_text(f"Key={openai_key}")
    assert "[REDACTED_API_KEY]" in res3

    # AWS Access Key
    aws_key = "AKIAIOSFODNN7EXAMPLE"
    res4 = redact_text(f"AWS ID {aws_key}")
    assert "[REDACTED_AWS_KEY]" in res4


def test_pii_and_indian_ids():
    # Email and phone
    text = "Contact founder at ceo@startup.io or call +1-555-123-4567"
    res = redact_text(text)
    assert "[REDACTED_EMAIL]" in res
    assert "ceo@startup.io" not in res
    assert "[REDACTED_PHONE]" in res

    # Indian PAN Card
    pan = "ABCDE1234F"
    res_pan = redact_text(f"Tax PAN is {pan}")
    assert "[REDACTED_PAN]" in res_pan
    assert pan not in res_pan

    # Indian Aadhaar pattern
    aadhaar = "9876 5432 1098"
    res_aadhaar = redact_text(f"UID is {aadhaar}")
    assert "[REDACTED_AADHAAR]" in res_aadhaar


def test_route_normalization():
    # Normalizes UUIDs and numeric IDs to template
    path1 = "/api/v1/orders/a1b2c3d4-e5f6-7890-abcd-ef1234567890/status"
    assert normalize_route_path(path1) == "/api/v1/orders/:id/status"

    path2 = "/users/10492/profile"
    assert normalize_route_path(path2) == "/users/:id/profile"


def test_header_allow_list():
    raw_headers = {
        "User-Agent": "Mozilla/5.0",
        "Content-Type": "application/json",
        "Authorization": "Bearer skl_live_dummytoken123456789",
        "Cookie": "session=secret1234",
        "X-Internal-Secret": "sensitive-data",
    }
    cleaned = redact_headers(raw_headers)
    assert "user-agent" in cleaned
    assert "content-type" in cleaned
    assert cleaned["authorization"] == "[REDACTED]"
    assert cleaned["cookie"] == "[REDACTED]"
    # Disallowed header discarded completely
    assert "x-internal-secret" not in cleaned
