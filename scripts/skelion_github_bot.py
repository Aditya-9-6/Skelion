#!/usr/bin/env python3
"""
scripts/skelion_github_bot.py — Skelion GitHub Agent Bot CLI Runner

Autonomous DevOps bot that monitors production incidents, executes Replay Sandbox
verifications, and opens GitHub Pull Requests with 0 regressions.
"""

import sys
import os
import argparse
import requests

CONTROL_PLANE_URL = os.getenv("SKELION_URL", "http://127.0.0.1:8003")


def main():
    parser = argparse.ArgumentParser(description="Skelion GitHub Agent Bot")
    parser.add_argument("--repo", default=os.getenv("GITHUB_REPOSITORY", "adity/helios"), help="Target GitHub repo (owner/repo)")
    parser.add_argument("--route", default="/api/v1/orders/checkout", help="Route path of incident to heal")
    parser.add_argument("--method", default="POST", help="HTTP method")
    parser.add_argument("--incident-id", default=None, help="Specific incident ID")
    parser.add_argument("--simulate", action="store_true", help="Simulate runtime crash before triggering bot")
    args = parser.parse_args()

    print(f"[BOT] Initializing Skelion Agent Bot for repo: {args.repo}...")

    # Optional: Simulate runtime edge crash
    if args.simulate:
        print(f"[BOT] Simulating live edge incident on {args.method} {args.route}...")
        try:
            sim_res = requests.post(
                f"{CONTROL_PLANE_URL}/v1/telemetry",
                json={
                    "route": args.route,
                    "method": args.method,
                    "status_code": 500,
                    "error_summary": "Simulated NullPointerException in checkout controller",
                    "latency_ms": 142.5,
                },
                timeout=5.0,
            )
            print(f"[BOT] Telemetry logged: {sim_res.status_code}")
        except Exception as e:
            print(f"[BOT] Could not simulate telemetry: {e}")

    # Fetch suggestions / open incidents
    print(f"[BOT] Querying active incidents from {CONTROL_PLANE_URL}/v1/autofix/suggestions...")
    try:
        sugg_res = requests.get(f"{CONTROL_PLANE_URL}/v1/autofix/suggestions", timeout=5.0)
        sugg_data = sugg_res.json()
        suggestions = sugg_data.get("suggestions", [])
        remaining = sugg_data.get("autofix_tokens_remaining", 50000)
        print(f"[BOT] Active unresolved incidents: {len(suggestions)} (Autofix tokens: {remaining:,})")
    except Exception as e:
        print(f"[BOT] Error querying suggestions: {e}")
        suggestions = []

    target_inc_id = args.incident_id
    if not target_inc_id and suggestions:
        target_inc_id = suggestions[0].get("incident_id")
    elif not target_inc_id:
        target_inc_id = "inc_bot_standalone"

    # Trigger Automated PR Creation via Bot API
    print(f"[BOT] Triggering Skelion Bot PR creation for incident: {target_inc_id}...")
    try:
        pr_res = requests.post(
            f"{CONTROL_PLANE_URL}/v1/github/create-autofix-pr",
            json={
                "incident_id": target_inc_id,
                "repo": args.repo,
                "target_path": "src/autofix_resilience.js",
            },
            timeout=10.0,
        )
        if pr_res.status_code == 200:
            result = pr_res.json()
            print("\n" + "=" * 60)
            print("🚀 SKELION GITHUB BOT: AUTONOMOUS PR CREATED SUCCESSFULLY!")
            print("=" * 60)
            print(f"• Pull Request: {result.get('pr_url')}")
            print(f"• Dedicated Branch: {result.get('branch')}")
            print(f"• Incident Status: {result.get('incident_status')} (committed to DB)")
            print(f"• Tokens Deducted: {result.get('tokens_deducted')} (Remaining: {result.get('autofix_tokens_remaining'):,})")
            print("=" * 60)
            print("\nPR Diagnostic Card Preview:\n")
            print(result.get("diagnostic_card", ""))
        else:
            print(f"[BOT] PR creation returned status {pr_res.status_code}: {pr_res.text}")
    except Exception as e:
        print(f"[BOT] Failed to connect to Skelion Control Plane: {e}")


if __name__ == "__main__":
    main()
