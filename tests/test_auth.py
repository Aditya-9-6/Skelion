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
