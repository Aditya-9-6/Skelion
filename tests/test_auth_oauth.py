# tests/test_auth_oauth.py
import os
import hashlib
from datetime import datetime, timezone, timedelta
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select
import httpx

from admin_api.main import app, SESSION_COOKIE, sign_session_token
from admin_api.models import AdminSession, get_engine

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_db(tmp_path):
    db_path = tmp_path / "admin_test.db"
    os.environ["ADMIN_DATABASE_URL"] = f"sqlite:///{db_path}"
    os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"
    os.environ["ADMIN_GITHUB_CLIENT_ID"] = "mock_client_id"
    os.environ["ADMIN_GITHUB_SECRET"] = "mock_secret"
    os.environ["ADMIN_GITHUB_IDS"] = "123456,789012"
    from sqlmodel import SQLModel
    engine = get_engine()
    SQLModel.metadata.create_all(engine)
    yield

def test_github_login_redirect():
    response = client.get("/auth/github", follow_redirects=False)
    assert response.status_code == 303
    assert "github.com/login/oauth/authorize" in response.headers["location"]
    assert "client_id=mock_client_id" in response.headers["location"]

def test_github_callback_success(monkeypatch):
    class MockResponse:
        def __init__(self, status_code, json_data, text=""):
            self.status_code = status_code
            self._json_data = json_data
            self.text = text or str(json_data)
        def json(self):
            return self._json_data

    async def mock_post(self, url, *args, **kwargs):
        if "access_token" in url:
            return MockResponse(200, {"access_token": "gho_mock_token_123"})
        return MockResponse(404, {})

    async def mock_get(self, url, *args, **kwargs):
        if "api.github.com/user" in url:
            return MockResponse(200, {"id": 123456, "login": "admin_user", "email": "admin@skelion.dev"})
        return MockResponse(404, {})

    monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)
    monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

    response = client.get("/auth/github/callback?code=test_code", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/dashboard"
    assert SESSION_COOKIE in response.cookies

    # Verify session stored in DB
    engine = get_engine()
    with Session(engine) as db:
        session_row = db.exec(select(AdminSession).where(AdminSession.github_user_id == 123456)).first()
        assert session_row is not None
        assert session_row.github_user_id == 123456

def test_github_callback_forbidden_id(monkeypatch):
    class MockResponse:
        def __init__(self, status_code, json_data, text=""):
            self.status_code = status_code
            self._json_data = json_data
            self.text = text or str(json_data)
        def json(self):
            return self._json_data

    async def mock_post(self, url, *args, **kwargs):
        return MockResponse(200, {"access_token": "gho_mock_token_456"})

    async def mock_get(self, url, *args, **kwargs):
        return MockResponse(200, {"id": 999999, "login": "unauthorized_user"})

    monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)
    monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

    response = client.get("/auth/github/callback?code=test_code", follow_redirects=False)
    assert response.status_code == 403
    assert "not authorized" in response.json()["detail"]

def test_dashboard_access_flow():
    engine = get_engine()
    raw_token = "test_raw_session_token_789"
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    with Session(engine) as db:
        sess = AdminSession(
            github_user_id=123456,
            session_token_hash=token_hash,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        )
        db.add(sess)
        db.commit()

    signed_cookie = sign_session_token(raw_token)
    client.cookies.set(SESSION_COOKIE, signed_cookie)

    # Access dashboard with Cloudflare header and session cookie -> 200
    resp = client.get("/dashboard", headers={"CF-Access-Authenticated-User-Email": "admin@skelion.dev"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["github_user_id"] == 123456
    assert "kpis" in data

    # Access dashboard without Cloudflare header -> 403
    client.cookies.clear()
    resp = client.get("/dashboard")
    assert resp.status_code == 403
