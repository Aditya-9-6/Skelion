# scripts/issue_license.py — Enterprise Ed25519 Offline Airgap License CLI
"""
Issues and verifies signed .skelion-license files for 100% airgapped enterprise deployments.
Uses cryptographic Ed25519 signatures with zero external data egress.
"""

import argparse
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from license.issuer import issue_license
from license.verifier import verify_license_offline


def main():
    parser = argparse.ArgumentParser(
        description="Skelion Enterprise Offline License Generator"
    )
    parser.add_argument("--org", default="org_enterprise_01", help="Organization ID")
    parser.add_argument(
        "--customer",
        default="Aditya Enterprise Labs",
        help="Customer Organization Name",
    )
    parser.add_argument(
        "--email", default="admin@aditya-enterprise.io", help="Customer Admin Email"
    )
    parser.add_argument(
        "--plan",
        default="local_team",
        choices=["local_solo", "local_team", "local_enterprise"],
        help="Airgap Plan Tier",
    )
    parser.add_argument(
        "--days", type=int, default=365, help="License validity duration in days"
    )
    parser.add_argument(
        "--output",
        default="skelion.license",
        help="Destination path for signed license file",
    )

    args = parser.parse_args()

    # 1. Issue signed license
    signed_license = issue_license(
        org_id=args.org,
        customer_name=args.customer,
        customer_email=args.email,
        plan_id=args.plan,
        duration_days=args.days,
    )

    # 2. Verify 100% offline
    verification = verify_license_offline(signed_license)

    # 3. Save to output file
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(signed_license, f, indent=2)

    # 4. Print clean report
    print("\n" + "=" * 70)
    print("🔒 SKELION ENTERPRISE OFFLINE LICENSE ISSUED & VERIFIED")
    print("=" * 70)
    print(f"• License ID   : {signed_license['payload']['license_id']}")
    print(
        f"• Customer     : {signed_license['payload']['customer']['name']} ({signed_license['payload']['customer']['email']})"
    )
    print(
        f"• Plan Tier    : {signed_license['payload']['plan'].upper()} (100% Airgap / Zero Egress)"
    )
    print(
        f"• Valid Until  : {signed_license['payload']['expires_at'][:10]} ({args.days} days)"
    )
    print(f"• Key ID (KID) : {signed_license['kid']}")
    print(
        f"• Signature    : {signed_license['signature'][:32]}... [Ed25519 Cryptographic Proof]"
    )
    print("-" * 70)
    print("🧪 Offline Airgap Verification Check:")
    print(
        f"• Status       : {'✅ ' + verification['status'].upper() if verification['valid'] else '❌ DEGRADED'}"
    )
    print(f"• Features     : {', '.join(verification.get('features', []))}")
    print(f"• License File : Saved to '{args.output}'")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
