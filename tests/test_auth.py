# tests/test_auth.py – Verify authentication endpoints

import os
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

# Ensure the test uses the same app instance
from skelion_agent.control_plane import app
from skelion_agent.database import get_session, init_db
from skelion_agent.models import ApiKey, Membership, Organization, ProxyNode, utc_now

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_db(tmp_path):
    # Use a temporary SQLite file for isolation
    db_path = tmp_path / "test.db"
    os.environ["DATABASE_URI"] = f"sqlite:///{db_path}"
    # Re‑initialize the DB schema
    init_db()
    yield
    # Cleanup – the temporary directory is removed automatically


def test_register_and_login():
    import uuid

    email = f"alice_{uuid.uuid4().hex[:6]}@example.com"
    password = "strongpassword"

    # Register
    resp = client.post("/v1/auth/register", json={"email": email, "password": password})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "registered"
    org_id = data["organization_id"]

    # Verify org exists in DB
    with Session(get_session()) as s:
        org = s.exec(select(Organization).where(Organization.id == org_id)).first()
        assert org is not None
        assert org.email == email
        membership = s.exec(
            select(Membership).where(Membership.org_id == org_id)
        ).first()
        assert membership is not None
        assert membership.role == "owner"

    # Token (login)
    resp = client.post("/v1/auth/token", json={"email": email, "password": password})
    assert resp.status_code == 200
    token_data = resp.json()
    assert "access_token" in token_data
    bearer = f"Bearer {token_data['access_token']}"

    member_resp = client.post(
        "/v1/auth/org/members",
        headers={"Authorization": bearer},
        json={"email": "developer@example.com", "role": "developer"},
    )
    assert member_resp.status_code == 200
    member_id = member_resp.json()["user_id"]
    members_resp = client.get(
        "/v1/auth/org/members", headers={"Authorization": bearer}
    )
    assert members_resp.status_code == 200
    assert any(member["user_id"] == member_id for member in members_resp.json()["members"])
    role_resp = client.patch(
        f"/v1/auth/org/members/{member_id}",
        headers={"Authorization": bearer},
        json={"role": "viewer"},
    )
    assert role_resp.status_code == 200

    sso_resp = client.put(
        "/v1/org/sso",
        headers={"Authorization": bearer},
        json={
            "provider": "oidc",
            "issuer_url": "https://idp.example.com",
            "client_id": "skelion-client",
            "enabled": True,
        },
    )
    assert sso_resp.status_code == 200
    scim_token_resp = client.post(
        "/v1/org/scim-tokens",
        headers={"Authorization": bearer},
        json={"label": "directory sync", "expires_in_days": 30},
    )
    assert scim_token_resp.status_code == 200
    scim_token_id = scim_token_resp.json()["id"]
    token_list_resp = client.get(
        "/v1/org/scim-tokens", headers={"Authorization": bearer}
    )
    assert token_list_resp.status_code == 200
    assert any(item["id"] == scim_token_id for item in token_list_resp.json()["tokens"])
    scim_bearer = {"Authorization": f"Bearer {scim_token_resp.json()['token']}"}
    scim_user_resp = client.post(
        "/scim/v2.0/Users",
        headers=scim_bearer,
        json={"userName": "scim-user@example.com", "displayName": "SCIM User"},
    )
    assert scim_user_resp.status_code == 200
    scim_user_id = scim_user_resp.json()["id"]
    filtered_users_resp = client.get(
        "/scim/v2.0/Users",
        headers=scim_bearer,
        params={"filter": 'userName eq "scim-user@example.com"'},
    )
    assert filtered_users_resp.status_code == 200
    assert filtered_users_resp.json()["totalResults"] == 1
    scim_patch_resp = client.patch(
        f"/scim/v2.0/Users/{scim_user_id}",
        headers=scim_bearer,
        json={"Operations": [{"op": "replace", "path": "active", "value": False}]},
    )
    assert scim_patch_resp.status_code == 200
    assert scim_patch_resp.json()["active"] is False
    assert client.delete(
        f"/scim/v2.0/Users/{scim_user_id}", headers=scim_bearer
    ).status_code == 204
    rotate_resp = client.post(
        f"/v1/org/scim-tokens/{scim_token_id}/rotate",
        headers={"Authorization": bearer},
        json={"expires_in_days": 30},
    )
    assert rotate_resp.status_code == 200
    assert client.get(
        "/scim/v2.0/Users", headers=scim_bearer
    ).status_code == 401
    evidence_resp = client.get(
        "/v1/compliance/evidence", headers={"Authorization": bearer}
    )
    assert evidence_resp.status_code == 200
    assert evidence_resp.json()["controls"]["sso_configured"] is True

    read_key_resp = client.post(
        "/v1/keys",
        headers={"Authorization": bearer},
        json={"name": "Read only", "scopes": ["read"]},
    )
    assert read_key_resp.status_code == 200
    ingest_resp = client.post(
        "/v1/ingest/incident",
        headers={"X-API-Key": read_key_resp.json()["api_key"]},
        json={"error_summary": "scope check"},
    )
    assert ingest_resp.status_code == 403

    # Generate API key (machine token)
    resp = client.post("/v1/auth/api-key", headers={"Authorization": bearer})
    assert resp.status_code == 200
    api_key = resp.json()["api_key"]
    assert api_key.startswith("skl_live_")

    # Verify ProxyNode created
    with Session(get_session()) as s:
        node = s.exec(select(ProxyNode).where(ProxyNode.org_id == org_id)).first()
        assert node is not None
        from skelion_agent.control_plane import hash_api_key

        expected_hash = hash_api_key(api_key)
        assert node.api_key_hash == expected_hash


def test_production_rejects_anonymous_org_resolution(monkeypatch):
    from fastapi import HTTPException
    from skelion_agent.auth_routes import get_org_from_jwt

    monkeypatch.setenv("ENVIRONMENT", "production")
    with Session(get_session()) as s:
        with pytest.raises(HTTPException) as exc_info:
            get_org_from_jwt(authorization=None, x_organization_id=None, session=s)
    assert exc_info.value.status_code == 401


def test_expired_scoped_api_key_is_rejected():
    import asyncio
    from datetime import timedelta
    from skelion_agent.api_key_service import (
        generate_scoped_api_key,
        get_org_from_api_key_or_jwt,
    )

    with Session(get_session()) as s:
        org = s.exec(select(Organization)).first()
        raw_key, prefix, key_hash = generate_scoped_api_key()
        s.add(
            ApiKey(
                org_id=org.id,
                name="expired",
                key_prefix=prefix,
                key_hash=key_hash,
                scopes="ingest",
                expires_at=utc_now() - timedelta(seconds=1),
            )
        )
        s.commit()
        with pytest.raises(Exception) as exc_info:
            asyncio.run(
                get_org_from_api_key_or_jwt(
                    auth_header=type(
                        "Credentials", (), {"credentials": raw_key}
                    )(),
                    x_api_key=None,
                    db=s,
                )
            )
        assert getattr(exc_info.value, "status_code", None) == 401
