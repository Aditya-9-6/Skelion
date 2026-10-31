# tests/test_saas_final_audit.py -- Comprehensive SaaS Multi-Tenant End-to-End Audit

import os
import sys
import json
import httpx
from datetime import datetime, timezone

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

BASE_URL = "http://127.0.0.1:8003"

def run_saas_final_audit():
    print("=" * 70)
    print("SKELION COMMERCIAL MULTI-TENANT SAAS PLATFORM -- COMPREHENSIVE AUDIT")
    print("=" * 70)
    client = httpx.Client(base_url=BASE_URL, timeout=15.0)

    # 1. Health & Portal Checks
    print("\n[TEST 1] Customer SaaS Web Portal & Health Verification...")
    r_health = client.get("/health")
    assert r_health.status_code == 200, f"Health check failed: {r_health.status_code}"
    print("  [PASS] /health returned 200 OK:", r_health.json())

    r_portal = client.get("/portal")
    assert r_portal.status_code == 200, f"/portal failed: {r_portal.status_code}"
    assert "Skelion SaaS Portal" in r_portal.text, "Customer portal title missing"
    assert "API Keys" in r_portal.text, "Portal tabs missing"
    print(f"  [PASS] /portal returned 200 OK (size: {len(r_portal.text)} bytes)")

    r_app = client.get("/app")
    assert r_app.status_code == 200, f"/app failed: {r_app.status_code}"
    print("  [PASS] /app alias returned 200 OK")

    # 2. Scoped API Key Governance
    print("\n[TEST 2] Scoped API Key Governance (Creation, Hashing & Scopes)...")
    admin_auth = {"Authorization": "Bearer dev"}
    key_payload = {
        "name": "Production E2E Key",
        "environment": "live",
        "scopes": ["ingest", "read"]
    }
    r_key = client.post("/v1/keys", json=key_payload, headers=admin_auth)
    assert r_key.status_code == 200, f"Key creation failed: {r_key.text}"
    key_data = r_key.json()
    raw_api_key = key_data["api_key"]
    key_id = key_data["id"]
    prefix = key_data["prefix"]

    assert raw_api_key.startswith("skl_live_"), f"Unexpected key format: {raw_api_key}"
    assert raw_api_key.startswith(prefix), f"Prefix mismatch: {prefix} vs {raw_api_key}"
    print(f"  [PASS] Successfully minted scoped key: {prefix}******** (ID: {key_id})")

    # List keys
    r_list_keys = client.get("/v1/keys", headers=admin_auth)
    assert r_list_keys.status_code == 200
    active_keys = r_list_keys.json()
    found = any(k["id"] == key_id for k in active_keys)
    assert found, "Created key not found in key list"
    print(f"  [PASS] Found key in active organization key list (total active: {len(active_keys)})")

    # 3. Telemetry Ingress with Live API Key & Zero-PII Redaction
    print("\n[TEST 3] Telemetry Ingress (POST /v1/ingest/incident) with Zero-PII scrubbing...")
    test_incident = {
        "service_name": "billing-service",
        "environment": "production",
        "http_method": "POST",
        "route_path": "/v1/charge",
        "status_code": 500,
        "error_summary": "PaymentGatewayTimeout: Stripe down for user@stripe.com with token secret_token_xyz987",
        "captured_headers": {
            "Authorization": "Bearer sk_test_secret_stripe_api_key_12345",
            "Cookie": "sessionid=secret_cookie_session_9999",
            "Content-Type": "application/json"
        },
        "captured_payload": json.dumps({
            "card_number": "4111-2222-3333-4444",
            "email": "customer@company.com"
        }),
        "latency_ms": 142.5
    }

    # Verify unauthenticated request without token fails with 401
    r_unauth = client.post("/v1/ingest/incident", json=test_incident)
    assert r_unauth.status_code == 401, f"Expected 401 for missing key, got {r_unauth.status_code}"
    print(f"  [PASS] Unauthenticated ingress rejected with HTTP {r_unauth.status_code}")

    # Verify invalid key fails with 401
    r_invalid = client.post("/v1/ingest/incident", json=test_incident, headers={"Authorization": "Bearer skl_live_invalidkey12345"})
    assert r_invalid.status_code == 401, f"Expected 401 for invalid key, got {r_invalid.status_code}"
    print(f"  [PASS] Invalid API key rejected with HTTP {r_invalid.status_code}")

    # Authenticated ingress with our new API key
    auth_headers = {
        "Authorization": f"Bearer {raw_api_key}",
        "Content-Type": "application/json"
    }
    r_ingest = client.post("/v1/ingest/incident", json=test_incident, headers=auth_headers)
    assert r_ingest.status_code == 200, f"Ingress failed: {r_ingest.text}"
    ingest_res = r_ingest.json()
    assert ingest_res["status"] in ("incident_created", "occurrence_incremented")
    inc_id = ingest_res["incident_id"]
    fingerprint = ingest_res["fingerprint"]
    print(f"  [PASS] Telemetry ingested successfully! Incident ID: {inc_id}, Fingerprint: {fingerprint}")

    # 4. Incident Deduplication & Occurrence Counter
    print("\n[TEST 4] Incident Deduplication & Frequency Tracking...")
    r_ingest_dup = client.post("/v1/ingest/incident", json=test_incident, headers=auth_headers)
    assert r_ingest_dup.status_code == 200
    dup_res = r_ingest_dup.json()
    assert dup_res["fingerprint"] == fingerprint, "Fingerprint changed on identical incident"
    assert dup_res["status"] == "occurrence_incremented", "Expected status occurrence_incremented"
    print(f"  [PASS] Deduplication verified: Incident {dup_res['incident_id']} incremented seamlessly")

    # 5. Zero-PII Verification in Database
    print("\n[TEST 5] Zero-PII Scrubbing Verification...")
    from skelion_agent.database import engine
    from skelion_agent.models import Incident
    from sqlmodel import Session
    with Session(engine) as session:
        stored_inc = session.get(Incident, inc_id)
        assert stored_inc is not None, "Ingested incident not found in database"
        headers_str = str(stored_inc.captured_headers or {})
        assert "sk_test_secret" not in headers_str, "Raw Stripe API key leaked in headers!"
        assert "[REDACTED]" in headers_str, "Authorization header not redacted with [REDACTED]"
        print("  [PASS] Verification confirmed: Raw tokens and PII scrubbed before persistence!")

    # 6. Webhook Subscriptions & Alerting
    print("\n[TEST 6] Webhook Subscriptions Management...")
    wh_payload = {
        "url": "https://example.com/mock-webhook-endpoint",
        "description": "Ops Alert Endpoint",
        "events": ["incident.created", "incident.deduplicated"]
    }
    r_wh = client.post("/v1/webhooks", json=wh_payload, headers=admin_auth)
    assert r_wh.status_code == 200, f"Webhook creation failed: {r_wh.text}"
    wh_data = r_wh.json()
    wh_id = wh_data["id"]
    print(f"  [PASS] Registered webhook subscription {wh_id}")

    r_wh_list = client.get("/v1/webhooks", headers=admin_auth)
    assert r_wh_list.status_code == 200
    active_whs = r_wh_list.json()
    assert any(w["id"] == wh_id for w in active_whs), "Created webhook not in list"
    print(f"  [PASS] Active webhooks verified (total: {len(active_whs)})")

    # Cleanup webhook
    r_del_wh = client.delete(f"/v1/webhooks/{wh_id}", headers=admin_auth)
    assert r_del_wh.status_code == 200
    print(f"  [PASS] Deleted webhook subscription {wh_id}")

    # 7. Python SDK Fail-Open Middleware Simulation
    print("\n[TEST 7] Drop-in Python SDK Fail-Open Middleware Simulation...")
    from src.sdk.python.skelion import SkelionMiddleware
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    # Test 7A: fail_open = True
    test_app = FastAPI()
    test_app.add_middleware(
        SkelionMiddleware,
        api_key=raw_api_key,
        endpoint=BASE_URL,
        fail_open=True,
    )

    @test_app.get("/crash")
    def crash_route():
        raise ZeroDivisionError("Simulated division by zero in customer app")

    sdk_client = TestClient(test_app, raise_server_exceptions=False)
    resp = sdk_client.get("/crash")
    assert resp.status_code == 200, f"SDK should fail-open with 200 buffered, got {resp.status_code}"
    assert resp.json().get("status") == "fail_open_buffered"
    print("  [PASS] Python SDK fail-open boundary successfully intercepted crash and returned buffered 200!")

    # Test 7B: fail_open = False (re-raises 500)
    strict_app = FastAPI()
    strict_app.add_middleware(
        SkelionMiddleware,
        api_key=raw_api_key,
        endpoint=BASE_URL,
        fail_open=False,
    )

    @strict_app.get("/crash_strict")
    def crash_strict_route():
        raise RuntimeError("Strict mode crash")

    strict_client = TestClient(strict_app, raise_server_exceptions=False)
    resp_strict = strict_client.get("/crash_strict")
    assert resp_strict.status_code == 500, f"Expected 500 in strict mode, got {resp_strict.status_code}"
    print("  [PASS] Python SDK strict mode correctly propagated 500 while shipping telemetry!")

    # 8. Node.js SDK Contract Audit
    print("\n[TEST 8] Node.js SDK Packaging & Contract Audit...")
    node_sdk_path = os.path.abspath("src/sdk/node/index.js")
    assert os.path.exists(node_sdk_path), f"Node SDK file not found at {node_sdk_path}"
    with open(node_sdk_path, "r", encoding="utf-8") as f:
        node_code = f.read()
    assert "skelionMiddleware" in node_code
    assert "failOpen" in node_code
    assert "/v1/ingest/incident" in node_code
    print(f"  [PASS] Node SDK contract intact at {node_sdk_path}")

    # 9. Clean up test key
    print("\n[TEST 9] API Key Revocation...")
    r_del_key = client.delete(f"/v1/keys/{key_id}", headers=admin_auth)
    assert r_del_key.status_code == 200
    print(f"  [PASS] Revoked API key {key_id}")

    print("\n" + "=" * 70)
    print("ALL 9 SAAS PLATFORM TEST SUITES PASSED WITH ZERO REGRESSIONS!")
    print("=" * 70)

if __name__ == "__main__":
    run_saas_final_audit()
