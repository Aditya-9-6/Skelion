# scripts/simulate_live_incident.py — Real-time Production Incident Generator
"""
Simulates a live production incident intercepted by the Skelion Fail-Open DevProxy.
Inserts an active incident with zero-PII redacted headers, status 500, AST patch,
and Replay Sandbox verification proof into the local control plane database.
"""

import sys
import os
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import uuid
from datetime import datetime, timezone
from sqlmodel import Session, select

from skelion_agent.database import get_engine
from skelion_agent.models import Incident, Organization


def simulate_incident(
    route: str = "POST /api/v1/orders/checkout",
    error_msg: str = "TypeError: Cannot read properties of undefined (reading 'payment_method_id')",
    org_id: str = None
):
    engine = get_engine()
    with Session(engine) as s:
        if not org_id:
            dev_org = s.exec(
                select(Organization).where(Organization.github_id == 108502390)
            ).first()
            if not dev_org:
                dev_org = s.exec(
                    select(Organization).where(Organization.github_username == "Aditya-9-6")
                ).first()
            if not dev_org:
                dev_org = s.exec(select(Organization).where(Organization.id == "org_default")).first()
            if not dev_org:
                dev_org = s.exec(select(Organization)).first()
            org_id = dev_org.id if dev_org else "org_default"
        org = s.get(Organization, org_id) if org_id else None

        method, path = route.split(" ", 1)
        inc_id = f"inc_{uuid.uuid4().hex[:10]}"
        fp = f"fp_{uuid.uuid4().hex[:12]}"

        diff_code = (
            f"// Skelion Autonomous Self-Healing Patch\n"
            f"// Incident: {route} -> HTTP 500\n"
            f"// DevProxy Fail-Open error boundary with zero-PII protection:\n"
            f"export function safeOrderHandler(req, res, next) {{\n"
            f"  try {{\n"
            f"    if (!req.body || !req.body.payment_method_id) {{\n"
            f"      // Fail-open buffer: preserve order draft instead of 500 crash\n"
            f"      return res.status(200).json({{ status: 'buffered_pending_payment', retry_after: 5 }});\n"
            f"    }}\n"
            f"    return next();\n"
            f"  }} catch (err) {{\n"
            f"    return res.status(200).json({{ status: 'fail_open_buffered' }});\n"
            f"  }}\n"
            f"}}\n"
        )

        inc = Incident(
            id=inc_id,
            org_id=org_id,
            fingerprint=fp,
            http_method=method,
            captured_method=method,
            route_path=path,
            status_code=500,
            error_summary=error_msg,
            occurrence_count=1,
            latency_ms=142.5,
            generated_diff=diff_code,
            last_seen_at=datetime.now(timezone.utc),
        )
        s.add(inc)
        s.commit()
        s.refresh(inc)

        print("\n" + "=" * 65)
        print("🚨 LIVE PRODUCTION INCIDENT SIMULATED SUCCESSFULLY!")
        print("=" * 65)
        print(f"• Incident ID  : {inc.id}")
        print(f"• Route        : {inc.http_method} {inc.route_path} (HTTP {inc.status_code})")
        print(f"• Error        : {inc.error_summary}")
        print(f"• Fingerprint  : {inc.fingerprint}")
        print(f"• Organization : {org.github_username if org else 'Default'}")
        print("-" * 65)
        print("👉 In your VS Code sidebar:")
        print("   1. Click 'Refresh' in the 🚨 Incidents tab to see the live edge crash.")
        print("   2. Switch to ⚡ Fixes tab to review the Replay Sandbox verification.")
        print("   3. Click '⚡ Apply Verified Fix' to auto-heal the code without downtime!")
        print("=" * 65 + "\n")
        return inc


if __name__ == "__main__":
    route_arg = sys.argv[1] if len(sys.argv) > 1 else "POST /api/v1/orders/checkout"
    err_arg = sys.argv[2] if len(sys.argv) > 2 else "TypeError: Cannot read properties of undefined (reading 'payment_method_id')"
    simulate_incident(route_arg, err_arg)
