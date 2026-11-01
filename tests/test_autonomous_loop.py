# tests/test_autonomous_loop.py — Comprehensive Automated Test for Autonomous Loop
import json
import pytest
from unittest.mock import patch, MagicMock
from sqlmodel import Session, select

from skelion_agent.database import get_engine
from skelion_agent.models import Organization, AgentRun, Incident
from skelion_agent.autonomous_engine import AutonomousLoopEngine


@pytest.fixture
def test_engine_instance():
    return AutonomousLoopEngine(default_repo="Aditya-9-6/Skelion")


def test_check_issue_accepted_positive(test_engine_instance):
    mock_gh_data = {
        "state": "OPEN",
        "title": "feat(sre): Implement Epoll Edge Reactor with Bounded MPMC Circular Buffer",
        "body": "#### 🎯 Target Files\n- `skelion_agent/sre/epoll_reactor.py`",
        "comments": [
            {
                "author": {"login": "Aditya-9-6"},
                "body": "looks great, accepted"
            }
        ]
    }
    with patch("skelion_agent.autonomous_engine.run_cmd") as mock_run:
        mock_run.return_value = (0, json.dumps(mock_gh_data), "")
        is_acc, author, target = test_engine_instance.check_issue_accepted(183)
        assert is_acc is True
        assert author == "Aditya-9-6"
        assert target == "skelion_agent/sre/epoll_reactor.py"


def test_check_issue_accepted_negative(test_engine_instance):
    mock_gh_data = {
        "state": "OPEN",
        "title": "Some feature",
        "comments": [
            {
                "author": {"login": "user1"},
                "body": "Need more clarification before approving"
            }
        ]
    }
    with patch("skelion_agent.autonomous_engine.run_cmd") as mock_run:
        mock_run.return_value = (0, json.dumps(mock_gh_data), "")
        is_acc, author, target = test_engine_instance.check_issue_accepted(999)
        assert is_acc is False
        assert author is None


def test_token_deduction_and_agent_run_ledger(test_engine_instance):
    engine = get_engine()
    test_org_id = "test_auto_org_1"
    
    with Session(engine) as db:
        existing = db.get(Organization, test_org_id)
        if not existing:
            org = Organization(
                id=test_org_id,
                name="Autonomous Loop Org",
                token="skl_live_test_auto_ledger_key",
                plan="pro",
                autofix_tokens_total=10000,
                autofix_tokens_used=1000
            )
            db.add(org)
            db.commit()
        else:
            existing.autofix_tokens_total = 10000
            existing.autofix_tokens_used = 1000
            db.add(existing)
            db.commit()

    # Deduct 250 tokens
    ok, rem, msg = test_engine_instance.deduct_task_tokens(
        org_id=test_org_id,
        token_cost=250,
        task_id="issue_test_101"
    )
    assert ok is True
    assert rem == 8750  # (10000 - 1000 - 250)

    # Verify AgentRun & Incident in DB
    with Session(engine) as db:
        agent_runs = db.exec(select(AgentRun).where(AgentRun.org_id == test_org_id)).all()
        assert len(agent_runs) >= 1
        incident = db.get(Incident, "issue_test_101")
        assert incident is not None
        assert incident.org_id == test_org_id


def test_insufficient_tokens_rejection(test_engine_instance):
    engine = get_engine()
    broke_org_id = "test_broke_org"
    
    with Session(engine) as db:
        existing = db.get(Organization, broke_org_id)
        if not existing:
            org = Organization(
                id=broke_org_id,
                name="Broke Org",
                token="skl_live_test_broke_org_key",
                plan="pilot",
                autofix_tokens_total=100,
                autofix_tokens_used=100
            )
            db.add(org)
            db.commit()

    ok, rem, msg = test_engine_instance.deduct_task_tokens(
        org_id=broke_org_id,
        token_cost=250,
        task_id="issue_test_insufficient"
    )
    assert ok is False
    assert rem == 0
    assert "Insufficient" in msg
