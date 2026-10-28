# core/doctor.py — Skelion Self-Diagnostic Health Check (skelion doctor)

import json
import os
import sys
import urllib.request
from typing import Dict, Any

from core.llm_adapter import LLMAdapter, LLMConfig
from license.verifier import verify_license_offline


def run_diagnostics(config: Optional[LLMConfig] = None) -> Dict[str, Any]:
    """Execute complete self-test of local environment, daemon, LLM connectivity, and license."""
    cfg = config or LLMConfig()
    results = {
        "status": "healthy",
        "checks": {},
        "enabled_features": [],
    }

    # 1. Local Database & Incident Store Check
    try:
        from skelion_agent.database import get_engine
        from sqlmodel import Session, select
        from skelion_agent.models import Organization
        with Session(get_engine()) as session:
            count = len(session.exec(select(Organization)).all())
        results["checks"]["database"] = {"status": "ok", "message": f"SQLite incident store operational ({count} orgs)"}
    except Exception as e:
        results["checks"]["database"] = {"status": "error", "message": str(e)}
        results["status"] = "degraded"

    # 2. Local License Status Check
    license_path = os.getenv("SKELION_LICENSE_FILE", "skelion.license")
    if os.path.exists(license_path):
        try:
            with open(license_path, "r", encoding="utf-8") as f:
                lic_data = json.load(f)
            lic_res = verify_license_offline(lic_data)
            results["checks"]["license"] = lic_res
            if lic_res["valid"]:
                results["enabled_features"].extend(lic_res.get("features", []))
        except Exception as e:
            results["checks"]["license"] = {"status": "degraded", "message": f"Failed reading license: {e}"}
    else:
        results["checks"]["license"] = {
            "status": "community_mode",
            "message": "No license file found. Operating under local community mode.",
        }
        results["enabled_features"].extend(["proxy_capture", "redaction", "incident_fingerprinting", "audit_cli"])

    # 3. LLM Connectivity Check
    llm = LLMAdapter(cfg)
    try:
        url = f"{cfg.base_url}/models"
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {cfg.api_key}"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            models = [m.get("id") for m in data.get("data", [])]
            results["checks"]["llm_connectivity"] = {
                "status": "ok",
                "endpoint": cfg.base_url,
                "models_available": models[:5],
                "message": f"Connected to {cfg.provider} ({len(models)} models available)",
            }
            results["enabled_features"].append("byo_llm")
    except Exception as e:
        results["checks"]["llm_connectivity"] = {
            "status": "offline_or_unreachable",
            "endpoint": cfg.base_url,
            "message": f"Could not reach LLM endpoint: {e}. Fix generation will fall back to local rule-based analysis.",
        }

    return results


def main():
    print("[*] Running Skelion System & Environment Diagnostics (skelion doctor)...")
    res = run_diagnostics()

    print("\n" + "=" * 60)
    print("SKELION SYSTEM DIAGNOSTICS REPORT")
    print("=" * 60)

    for component, check in res["checks"].items():
        status_sym = "✔" if check.get("status") in ("ok", "valid", "community_mode") else "⚠"
        print(f"[{status_sym}] {component.upper()}: {check.get('message', check.get('status'))}")

    print("\nActive Features:")
    for feat in set(res["enabled_features"]):
        print(f"  • {feat}")
    print("=" * 60)


if __name__ == "__main__":
    main()
