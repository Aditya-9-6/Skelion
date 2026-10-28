from sqlmodel import Session, select
from skelion_agent.database import get_engine
from skelion_agent.models import Incident, Organization

engine = get_engine()
with Session(engine) as s:
    org = s.exec(select(Organization)).first()
    org_id = org.id if org else "org_default"

    incidents_data = [
        {
            "id": "inc_prod_500_checkout",
            "org_id": org_id,
            "fingerprint": "fp_checkout_null_pointer",
            "http_method": "POST",
            "route_path": "/api/checkout/process",
            "status_code": 500,
            "error_summary": "TypeError: Cannot read properties of undefined (reading 'payment_method_id')",
            "occurrence_count": 14,
            "latency_ms": 184.2,
            "generated_diff": """--- a/src/services/checkout.ts
+++ b/src/services/checkout.ts
@@ -42,3 +42,7 @@
+  // Guard against missing payment method in payload
+  if (!req.body || !req.body.payment_method_id) {
+    return res.status(400).json({ error: 'Missing payment_method_id' });
+  }
""",
        },
        {
            "id": "inc_prod_502_telemetry",
            "org_id": org_id,
            "fingerprint": "fp_telemetry_502_timeout",
            "http_method": "POST",
            "route_path": "/v1/telemetry/event",
            "status_code": 502,
            "error_summary": "Upstream Gateway Timeout under load (DevProxy buffer intercepted)",
            "occurrence_count": 42,
            "latency_ms": 5020.0,
            "generated_diff": """--- a/src/routes/telemetry.ts
+++ b/src/routes/telemetry.ts
@@ -18,2 +18,6 @@
+  // DevProxy Fail-Open Resilience Buffer
+  queue.enqueueAsync(req.body).catch(err => {
+    logger.warn('Telemetry buffered in memory fallback:', err.message);
+  });
+  return res.status(202).json({ status: 'buffered' });
""",
        },
        {
            "id": "inc_prod_429_llm_storm",
            "org_id": org_id,
            "fingerprint": "fp_llm_429_rate_storm",
            "http_method": "POST",
            "route_path": "/v1/ai/completions",
            "status_code": 429,
            "error_summary": "Rate Limit Exceeded: Upstream provider 429 storm intercepted by Skelion key-pool",
            "occurrence_count": 89,
            "latency_ms": 45.0,
            "generated_diff": """--- a/src/ai/client.ts
+++ b/src/ai/client.ts
@@ -30,2 +30,5 @@
+  // Automatic failover to next healthy key pool slot
+  const key = await keyPool.getNextAvailableSlot();
+  return executeWithRetry(req, key, { maxBackoffMs: 2000 });
""",
        },
        {
            "id": "inc_prod_500_user_profile",
            "org_id": org_id,
            "fingerprint": "fp_user_profile_key_error",
            "http_method": "GET",
            "route_path": "/api/v1/user/profile",
            "status_code": 500,
            "error_summary": "KeyError: 'subscription_status' in profile serializer",
            "occurrence_count": 8,
            "latency_ms": 78.4,
            "generated_diff": """--- a/src/serializers/user.py
+++ b/src/serializers/user.py
@@ -15,1 +15,1 @@
-    'subscription': user.subscription['status'],
+    'subscription': user.subscription.get('status', 'pilot'),
""",
        },
    ]

    for item in incidents_data:
        inc = s.get(Incident, item["id"])
        if not inc:
            inc = Incident(
                id=item["id"],
                org_id=item["org_id"],
                fingerprint=item["fingerprint"],
                http_method=item["http_method"],
                captured_method=item["http_method"],
                route_path=item["route_path"],
                status_code=item["status_code"],
                error_summary=item["error_summary"],
                occurrence_count=item["occurrence_count"],
                latency_ms=item["latency_ms"],
                generated_diff=item["generated_diff"],
                status="analyzing",
            )
            s.add(inc)
        else:
            inc.error_summary = item["error_summary"]
            inc.occurrence_count = item["occurrence_count"]
            inc.generated_diff = item["generated_diff"]
            s.add(inc)
    s.commit()
    print("Successfully seeded 4 production incidents with replay diffs!")
