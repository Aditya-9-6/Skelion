"""Fail-closed SAML response validation.

The IdP certificate is supplied by deployment configuration and never accepted
from the incoming response. Validation covers XML signature, issuer, audience,
recipient, request correlation, and assertion time bounds.
"""

import base64
from datetime import datetime, timezone
from typing import Optional
from xml.etree import ElementTree as ET


SAML_NS = "urn:oasis:names:tc:SAML:2.0:assertion"
PROTOCOL_NS = "urn:oasis:names:tc:SAML:2.0:protocol"


class SamlValidationError(ValueError):
    pass


def validate_saml_response(
    encoded_response: str,
    *,
    certificate_pem: str,
    expected_issuer: str,
    expected_audience: str,
    expected_recipient: str,
    request_id: Optional[str] = None,
    now: Optional[datetime] = None,
    clock_skew_seconds: int = 120,
) -> dict[str, str]:
    try:
        from lxml import etree
        from signxml import XMLVerifier, SignatureConfiguration
    except ImportError as exc:
        raise SamlValidationError(
            "SAML verification dependencies are not installed"
        ) from exc
    try:
        raw = base64.b64decode(encoded_response, validate=True)
        document = etree.fromstring(raw)
        XMLVerifier().verify(
            document,
            x509_cert=certificate_pem,
            expect_config=SignatureConfiguration(require_x509=True),
        )
    except Exception as exc:
        raise SamlValidationError("SAML XML signature verification failed") from exc

    root = ET.fromstring(raw)
    issuer = root.find(f"{{{SAML_NS}}}Issuer")
    if issuer is None or issuer.text != expected_issuer:
        raise SamlValidationError("SAML response issuer mismatch")
    if request_id and root.get("InResponseTo") != request_id:
        raise SamlValidationError("SAML response request correlation failed")
    status = root.find(f"{{{PROTOCOL_NS}}}Status/{{{PROTOCOL_NS}}}StatusCode")
    if status is None or status.get("Value") != "urn:oasis:names:tc:SAML:2.0:status:Success":
        raise SamlValidationError("SAML response status is not success")
    assertion = root.find(f"{{{SAML_NS}}}Assertion")
    if assertion is None:
        raise SamlValidationError("SAML assertion is missing")
    assertion_issuer = assertion.find(f"{{{SAML_NS}}}Issuer")
    if assertion_issuer is None or assertion_issuer.text != expected_issuer:
        raise SamlValidationError("SAML assertion issuer mismatch")
    conditions = assertion.find(f"{{{SAML_NS}}}Conditions")
    if conditions is None:
        raise SamlValidationError("SAML assertion conditions are missing")
    current = now or datetime.now(timezone.utc)

    def parse_time(name: str) -> Optional[datetime]:
        value = conditions.get(name)
        if not value:
            return None
        return datetime.fromisoformat(value.replace("Z", "+00:00"))

    not_before = parse_time("NotBefore")
    not_on_or_after = parse_time("NotOnOrAfter")
    from datetime import timedelta

    skew = timedelta(seconds=clock_skew_seconds)
    if not_before and current + skew < not_before:
        raise SamlValidationError("SAML assertion is not yet valid")
    if not_on_or_after and current - skew >= not_on_or_after:
        raise SamlValidationError("SAML assertion has expired")
    audience = assertion.find(
        f"{{{SAML_NS}}}Conditions/{{{SAML_NS}}}AudienceRestriction/{{{SAML_NS}}}Audience"
    )
    if audience is None or audience.text != expected_audience:
        raise SamlValidationError("SAML audience mismatch")
    subject_confirmation = assertion.find(
        f"{{{SAML_NS}}}Subject/{{{SAML_NS}}}SubjectConfirmation"
    )
    if subject_confirmation is None:
        raise SamlValidationError("SAML subject confirmation is missing")
    confirmation_data = subject_confirmation.find(f"{{{SAML_NS}}}SubjectConfirmationData")
    if confirmation_data is None or confirmation_data.get("Recipient") != expected_recipient:
        raise SamlValidationError("SAML recipient mismatch")
    name_id = assertion.find(f"{{{SAML_NS}}}Subject/{{{SAML_NS}}}NameID")
    if name_id is None or not name_id.text:
        raise SamlValidationError("SAML subject identity is missing")
    return {"name_id": name_id.text, "issuer": expected_issuer}
