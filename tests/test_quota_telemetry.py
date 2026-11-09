# tests/test_quota_telemetry.py — Tests for Request Telemetry and Quota Enforcement

import pytest
from datetime import datetime, timezone, timedelta
from fastapi import HTTPException
from sqlmodel import Session, SQLModel, create_engine

from skelion_agent.models import Organization
from skelion_agent.limits_service import track_request, get_token_status, deduct_coding_tokens


@pytest.fixture
def test_db():
    engine = create_engine("sqlite:///:memory:", echo=False)
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        org = Organization(
            id="org_quota_test",
            name="Quota Corp",
            token="skl_live_quota_test_token",
            plan="pilot",
            monthly_quota=10,
            quota_remaining=10,
            requests_total=0,
            requests_today=0,
            credits_total=100,
            credits_used=0,
        )
        session.add(org)
        session.commit()
        session.refresh(org)
        yield session


def test_track_request_increments_and_deducts_quota(test_db):
    org = test_db.get(Organization, "org_quota_test")
    assert org.requests_total == 0
    assert org.quota_remaining == 10

    res = track_request(org, test_db, cost=2)
    assert res["requests_total"] == 1
    assert res["requests_today"] == 1
    assert res["quota_remaining"] == 8

    status = get_token_status(org)
    assert "telemetry" in status
    assert status["telemetry"]["requests_total"] == 1
    assert status["telemetry"]["requests_today"] == 1
    assert status["telemetry"]["quota_remaining"] == 8
    assert status["telemetry"]["monthly_quota"] == 10


def test_quota_exhaustion_raises_http_429(test_db):
    org = test_db.get(Organization, "org_quota_test")
    org.quota_remaining = 1
    test_db.add(org)
    test_db.commit()

    # Track 1 request succeeds
    track_request(org, test_db, cost=1)
    assert org.quota_remaining == 0

    # Next request should raise 429
    with pytest.raises(HTTPException) as exc_info:
        track_request(org, test_db, cost=1)
    assert exc_info.value.status_code == 429
    assert "quota exhausted" in exc_info.value.detail.lower()


def test_day_transition_resets_today_counter(test_db):
    org = test_db.get(Organization, "org_quota_test")
    yesterday = datetime.now(timezone.utc) - timedelta(days=1)
    org.requests_today = 42
    org.last_request_at = yesterday
    test_db.add(org)
    test_db.commit()

    track_request(org, test_db, cost=1)
    assert org.requests_today == 1  # Reset to 1 for new day
    assert org.requests_total == 1
