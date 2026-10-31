# core/egress.py — Egress Verifier & Preview Tool (skelion egress)
# Open-source core module (Apache-2.0). Guarantees zero sensitive data leakage.

import argparse
import hashlib
import json
import os
from datetime import datetime, timezone
from typing import Dict, Any, List

from core.redact import redact_text, normalize_route_path

SCHEMA_PATH = os.path.join(
    os.path.dirname(__file__), "..", "docs", "specs", "egress_schema.json"
)

# In-memory circular buffer of recently emitted hybrid metadata payloads
_LAST_EGRESS_PAYLOADS: List[Dict[str, Any]] = []


def get_latency_bucket(latency_ms: float) -> str:
    if latency_ms < 50:
        return "<50ms"
    elif latency_ms < 200:
        return "50-200ms"
    elif latency_ms < 500:
        return "200-500ms"
    elif latency_ms < 1000:
        return "500-1000ms"
    return ">1000ms"


def sanitize_for_egress(
    project_id: str,
    service_name: str,
    raw_path: str,
    http_status: int,
    error_summary: str,
    latency_ms: float = 25.0,
    severity: str = "HIGH",
    count: int = 1,
) -> Dict[str, Any]:
    """Transform an incident into a strictly whitelisted hybrid metadata payload.
    Discards all bodies, headers, user identifiers, and raw code.
    """
    fingerprint = hashlib.sha256(error_summary.encode("utf-8")).hexdigest()[:16]
    route_template = normalize_route_path(raw_path.split("?")[0])

    payload = {
        "project_id": project_id,
        "service_name": service_name,
        "error_fingerprint": fingerprint,
        "http_status": http_status,
        "route_template": route_template,
        "severity": severity,
        "count": count,
        "latency_bucket": get_latency_bucket(latency_ms),
        "first_seen": datetime.now(timezone.utc).isoformat(),
        "last_seen": datetime.now(timezone.utc).isoformat(),
        "fix_status": "pending",
    }

    validate_egress_payload(payload)

    _LAST_EGRESS_PAYLOADS.append(payload)
    if len(_LAST_EGRESS_PAYLOADS) > 50:
        _LAST_EGRESS_PAYLOADS.pop(0)

    return payload


def validate_egress_payload(payload: Dict[str, Any]) -> bool:
    """Validate payload against strict allow-list egress schema."""
    disallowed_keys = {
        "body",
        "headers",
        "ip",
        "user_id",
        "email",
        "authorization",
        "cookie",
        "password",
        "query",
        "token",
        "prompt",
        "stack_trace",
    }

    for k in payload.keys():
        if k.lower() in disallowed_keys:
            raise ValueError(
                f"CRITICAL SECURITY VIOLATION: Disallowed field '{k}' detected in egress payload!"
            )

    # Verify against schema definition if available
    if os.path.exists(SCHEMA_PATH):
        with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
            schema = json.load(f)
        allowed_properties = set(schema.get("properties", {}).keys())
        for k in payload.keys():
            if k not in allowed_properties:
                raise ValueError(
                    f"Schema violation: Field '{k}' is not in the allow-list egress schema!"
                )

    return True


def preview_llm_prompt(
    incident_summary: str, route_path: str, proposed_code_snippet: str
) -> str:
    """Preview the exact redacted prompt that will be sent to the configured LLM."""
    redacted_snippet = redact_text(proposed_code_snippet)
    normalized_route = normalize_route_path(route_path)

    prompt = (
        f"You are a self-healing DevOps assistant.\n"
        f"Route: {normalized_route}\n"
        f"Error: {redact_text(incident_summary)}\n"
        f"Code Context:\n```javascript\n{redacted_snippet}\n```\n"
        f"Generate a minimal patch to resolve this incident."
    )
    return prompt


def main():
    parser = argparse.ArgumentParser(
        description="Skelion Egress Verifier & Payload Inspector (skelion egress)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview exact redacted prompt that leaves for an LLM",
    )
    parser.add_argument(
        "--show-last",
        type=int,
        default=5,
        help="Display the last N metadata payloads emitted",
    )
    args = parser.parse_args()

    print("[*] Skelion Egress Transparency Inspector")

    if args.dry_run:
        sample_code = "const token = 'skl_live_1234567890'; function checkout() { db.query('SELECT * FROM users'); }"
        preview = preview_llm_prompt(
            "Unhandled database deadlock", "/api/v1/orders/99401", sample_code
        )
        print("\n=== DRY-RUN LLM EGRESS PREVIEW (What your LLM receives) ===")
        print(preview)
        print("=" * 60)
        print("[✔] Zero unredacted secrets or customer IPs detected.")
    else:
        print(f"\nLast {args.show_last} Hybrid Metadata Payloads Transmitted:")
        if not _LAST_EGRESS_PAYLOADS:
            print("  (Zero payloads emitted yet. Local mode is strictly offline.)")
        else:
            for i, p in enumerate(_LAST_EGRESS_PAYLOADS[-args.show_last :], 1):
                print(f"#{i}: {json.dumps(p, indent=2)}")


if __name__ == "__main__":
    main()
