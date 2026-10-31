# skelion_agent/license_routes.py — License Issuance & Offline Download Endpoints

import json
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel
from sqlmodel import Session, select

from skelion_agent.auth_routes import get_org_from_jwt
from skelion_agent.database import get_db
from skelion_agent.models import Organization, License
from license.issuer import issue_license
from license.verifier import verify_license_offline

router = APIRouter(prefix="/v1/licenses", tags=["Licenses"])


class IssueLicenseRequest(BaseModel):
    plan_id: str = "local_team"
    customer_name: str
    customer_email: str
    duration_days: int = 365
    grace_days: int = 7


@router.post("/issue")
def create_new_license(
    req: IssueLicenseRequest,
    org: Organization = Depends(get_org_from_jwt),
    db: Session = Depends(get_db),
):
    """Issue and sign an offline Ed25519 license file for the customer."""
    signed_lic = issue_license(
        org_id=org.id,
        customer_name=req.customer_name,
        customer_email=req.customer_email,
        plan_id=req.plan_id,
        duration_days=req.duration_days,
        grace_days=req.grace_days,
    )

    lic_payload = signed_lic["payload"]
    lic_record = License(
        id=lic_payload["license_id"],
        org_id=org.id,
        sku="local",
        plan_id=req.plan_id,
        limits_json=json.dumps(lic_payload.get("limits", {})),
        features_json=json.dumps(lic_payload.get("features", [])),
        signature=signed_lic["signature"],
        customer_name=req.customer_name,
        customer_email=req.customer_email,
        issued_at=datetime.fromisoformat(lic_payload["issued_at"]),
        expires_at=datetime.fromisoformat(lic_payload["expires_at"]),
        grace_days=req.grace_days,
        active=True,
    )
    db.add(lic_record)
    db.commit()

    return {
        "status": "issued",
        "license_id": lic_record.id,
        "plan": req.plan_id,
        "signed_license": signed_lic,
    }


@router.get("")
def list_licenses(
    org: Organization = Depends(get_org_from_jwt),
    db: Session = Depends(get_db),
):
    """List all licenses issued to this organization."""
    licenses = db.exec(select(License).where(License.org_id == org.id)).all()
    return {"licenses": licenses}


@router.get("/{license_id}/download")
def download_license(
    license_id: str,
    org: Organization = Depends(get_org_from_jwt),
    db: Session = Depends(get_db),
):
    """Download signed license file for offline installation."""
    lic = db.get(License, license_id)
    if not lic or lic.org_id != org.id:
        raise HTTPException(status_code=404, detail="License not found")

    signed_format = {
        "license_format": "skelion-ed25519-v1",
        "kid": "skelion_root_2026_v1",
        "payload": {
            "v": 1,
            "license_id": lic.id,
            "org_id": lic.org_id,
            "sku": lic.sku,
            "plan": lic.plan_id,
            "limits": json.loads(lic.limits_json),
            "features": json.loads(lic.features_json),
            "issued_at": lic.issued_at.isoformat(),
            "expires_at": lic.expires_at.isoformat(),
            "grace_days": lic.grace_days,
            "customer": {
                "name": lic.customer_name,
                "email": lic.customer_email,
            },
        },
        "signature": lic.signature,
    }

    content = json.dumps(signed_format, indent=2)
    return Response(
        content=content,
        media_type="application/json",
        headers={
            "Content-Disposition": f"attachment; filename=skelion-{lic.id}.license"
        },
    )


@router.post("/verify-offline")
def test_verify_license_file(license_data: Dict[str, Any]):
    """Offline verification helper for inspecting uploaded license files."""
    return verify_license_offline(license_data)
