# tests/final_system_audit.py — Comprehensive End-to-End System Audit
import json
import os
import sys
import httpx

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

print("=====================================================")
print("   HELIOS / SKELION SYSTEM COMPREHENSIVE FINAL AUDIT ")
print("=====================================================")

BASE = "http://127.0.0.1:8003"
passed = 0
failed = 0


def record_test(name, success, details=""):
    global passed, failed
    if success:
        passed += 1
        print(f" [PASS] {name} {details}")
    else:
        failed += 1
        print(f" [FAIL] {name} {details}")


client = httpx.Client(base_url=BASE, timeout=12.0)
auth_headers = {"Authorization": "Bearer dev"}

# 1. Project Tartarus Honeypots
r = client.get("/.env")
record_test(
    "Tartarus Honeypot (/.env)",
    r.status_code == 200 and "internal-db-prod-001" in r.text,
    f"Status={r.status_code}"
)

r = client.get("/wp-admin")
record_test(
    "Tartarus Honeypot (/wp-admin)",
    r.status_code == 200 and "Tartarus Mirror" in r.text,
    f"Status={r.status_code}"
)

# 2. Ingress WAF Shield Injection Blocks
r = client.get("/v1/auth/me?q=admin%27%20or%201=1--")
record_test(
    "WAF Block SQL Injection (Query String)",
    r.status_code == 403 and "SQL_INJECTION" in r.text,
    f"Status={r.status_code}"
)

r = client.get("/v1/auth/me?file=../../../../etc/passwd")
record_test(
    "WAF Block Path Traversal (LFI)",
    r.status_code == 403 and "PATH_TRAVERSAL" in r.text,
    f"Status={r.status_code}"
)

r = client.get("/v1/auth/me?cmd=;%20/bin/bash%20-i")
record_test(
    "WAF Block Command Injection (RCE)",
    r.status_code == 403 and "COMMAND_INJECTION" in r.text,
    f"Status={r.status_code}"
)

r = client.post("/v1/waf/test-payload", json={"payload": "<script>alert('xss')</script>"})
record_test(
    "WAF Block XSS Attack (JSON Body)",
    r.status_code == 403 and "XSS_ATTACK" in r.text,
    f"Status={r.status_code}"
)

# 3. Clean Request Pass-Through
r = client.get("/v1/auth/me", headers=auth_headers)
record_test(
    "Clean Auth Request Pass-Through",
    r.status_code == 200 and "org_default" in r.text,
    f"Status={r.status_code}"
)

# 4. WAF Telemetry & Threat Events
r = client.get("/v1/waf/metrics")
record_test(
    "WAF Metrics Telemetry API",
    r.status_code == 200 and r.json().get("total_threats_blocked", 0) > 0,
    f"BlockedCount={r.json().get('total_threats_blocked')}"
)

r = client.get("/v1/waf/events?limit=5")
events = r.json().get("events", [])
record_test(
    "WAF Event Audit Log API",
    r.status_code == 200 and len(events) > 0,
    f"EventsCount={len(events)}"
)

# 5. Limits & Token Ledger
r = client.get("/v1/limits/status", headers=auth_headers)
record_test(
    "Token Limits Status API",
    r.status_code == 200 and "coding_tokens" in r.json(),
    f"Plan={r.json().get('plan')}"
)

# 6. Incidents Feed & Isolation
r = client.get("/v1/incidents", headers=auth_headers)
incidents = r.json().get("incidents", [])
waf_in_incidents = any("WAF" in inc.get("title", "") for inc in incidents)
record_test(
    "Incident Feed Isolation (Zero False Alerts)",
    r.status_code == 200 and not waf_in_incidents,
    f"IncidentsCount={len(incidents)}"
)

# 7. AI Autofix Suggestions & Patch Application
r = client.get("/v1/autofix/suggestions", headers=auth_headers)
suggestions = r.json().get("suggestions", [])
if not suggestions:
    from scripts.simulate_live_incident import simulate_incident
    simulate_incident("POST /api/v1/orders/checkout", "Audit Test: Simulated 500 error")
    r = client.get("/v1/autofix/suggestions", headers=auth_headers)
    suggestions = r.json().get("suggestions", [])

record_test(
    "Autofix Suggestions Feed",
    r.status_code == 200 and len(suggestions) > 0,
    f"SuggestionsCount={len(suggestions)}"
)

if suggestions:
    first_sug = suggestions[0]
    apply_resp = client.post(
        "/v1/autofix/apply",
        json={
            "incident_id": first_sug["incident_id"],
            "patch_code": first_sug["diff_patch"],
            "target_path": "src/autofix.js",
        },
        headers=auth_headers,
    )
    record_test(
        "Apply Autofix Self-Healing Patch",
        apply_resp.status_code == 200 and apply_resp.json().get("status") == "applied",
        f"RemainingTokens={apply_resp.json().get('autofix_tokens_remaining')}"
    )

# 8. Skelion AI Lite Streaming Chat
chat_chunks = 0
with client.stream(
    "POST",
    "/v1/chat",
    json={
        "messages": [{"role": "user", "content": "System status check"}],
        "model": "free-tier-agent",
    },
    headers=auth_headers,
) as resp:
    for line in resp.iter_lines():
        if line:
            chat_chunks += 1
record_test(
    "Skelion AI Lite Streaming Chat",
    resp.status_code == 200 and chat_chunks > 10,
    f"ChunksReceived={chat_chunks}"
)

# 9. Master Admin Dashboard UI
r = client.get("/admin")
record_test(
    "Master Admin Dashboard HTML UI",
    r.status_code == 200 and "<html" in r.text.lower(),
    f"Status={r.status_code}"
)

# 10. VS Code Extension Output File Integrity
ext_js = "skelion_vscode_extension/out/extension.js"
ext_ok = os.path.exists(ext_js) and os.path.getsize(ext_js) > 50000
record_test(
    "VS Code Extension Compiled Bundle",
    ext_ok,
    f"Size={os.path.getsize(ext_js) if ext_ok else 0} bytes"
)

print("=====================================================")
print(f"   AUDIT SUMMARY: {passed} PASSED, {failed} FAILED")
print("=====================================================")

if failed > 0:
    sys.exit(1)
