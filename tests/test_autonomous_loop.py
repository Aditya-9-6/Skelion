# tests/test_autonomous_loop.py — Comprehensive Automated Test for Autonomous Loop
import json
import pytest
from unittest.mock import patch
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
            {"author": {"login": "Aditya-9-6"}, "body": "looks great, accepted"}
        ],
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
                "body": "Need more clarification before approving",
            }
        ],
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
        from skelion_agent.models import CreditLedger
        for row in db.exec(select(CreditLedger).where(CreditLedger.org_id == test_org_id)).all():
            db.delete(row)
        existing = db.get(Organization, test_org_id)
        if not existing:
            org = Organization(
                id=test_org_id,
                name="Autonomous Loop Org",
                token="skl_live_test_auto_ledger_key",
                plan="pro",
                autofix_tokens_total=10000,
                autofix_tokens_used=1000,
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
        org_id=test_org_id, token_cost=250, task_id="issue_test_101"
    )
    assert ok is True
    assert rem == 8750  # (10000 - 1000 - 250)

    # Verify zero double deduction: used should be exactly 1250 (not 1500)
    with Session(engine) as db:
        org_check = db.get(Organization, test_org_id)
        assert org_check.autofix_tokens_used == 1250

    # Verify AgentRun & Incident in DB
    with Session(engine) as db:
        agent_runs = db.exec(
            select(AgentRun).where(AgentRun.org_id == test_org_id)
        ).all()
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
                autofix_tokens_used=100,
            )
            db.add(org)
            db.commit()

    ok, rem, msg = test_engine_instance.deduct_task_tokens(
        org_id=broke_org_id, token_cost=250, task_id="issue_test_insufficient"
    )
    assert ok is False
    assert rem == 0
    assert "Insufficient" in msg


def test_scan_repo_for_plan_tasks(test_engine_instance):
    tasks = test_engine_instance.scan_repo_for_plan_tasks()
    assert isinstance(tasks, list)
    if tasks:
        first = tasks[0]
        assert "task_number" in first
        assert "title" in first
        assert "spec" in first
        assert "target_path" in first


def test_batch_dual_engine_accept_comment_detection():
    from scripts.gossipmesh.batch_dual_engine import check_issue_accepted_by_comment

    mock_accepted_res = {
        "comments": [
            {"author": {"login": "maintainer1"}, "body": "This looks ready to implement. accept"}
        ]
    }
    with patch("scripts.gossipmesh.batch_dual_engine.run_cmd") as mock_cmd:
        from subprocess import CompletedProcess
        mock_cmd.return_value = CompletedProcess(
            args=["gh", "issue", "view"], returncode=0, stdout=json.dumps(mock_accepted_res)
        )
        is_acc, author = check_issue_accepted_by_comment("42")
        assert is_acc is True
        assert author == "maintainer1"

    mock_unaccepted_res = {
        "comments": [
            {"author": {"login": "user2"}, "body": "Need more context on this issue"}
        ]
    }
    with patch("scripts.gossipmesh.batch_dual_engine.run_cmd") as mock_cmd:
        mock_cmd.return_value = CompletedProcess(
            args=["gh", "issue", "view"], returncode=0, stdout=json.dumps(mock_unaccepted_res)
        )
        is_acc, author = check_issue_accepted_by_comment("43")
        assert is_acc is False
        assert author is None


def test_batch_dual_engine_token_deduction():
    from scripts.gossipmesh.batch_dual_engine import deduct_issue_tokens
    from skelion_agent.credit_ledger import get_ledger_balances

    engine = get_engine()
    test_org_id = "test_dual_org"
    with Session(engine) as db:
        from skelion_agent.models import CreditLedger
        for row in db.exec(select(CreditLedger).where(CreditLedger.ref_id == "99")).all():
            db.delete(row)
        org = db.get(Organization, test_org_id)
        if not org:
            org = Organization(
                id=test_org_id,
                name="Dual Engine Org",
                token="skl_live_dual_engine_token",
                plan="team",
                autofix_tokens_total=5000,
                autofix_tokens_used=500,
            )
            db.add(org)
            db.commit()
        else:
            org.autofix_tokens_total = 5000
            org.autofix_tokens_used = 500
            db.add(org)
            db.commit()

    ok, msg = deduct_issue_tokens("99", token_cost=250, org_id=test_org_id)
    assert ok is True
    assert "Deducted 250 tokens" in msg or "Dev Mode" in msg


def test_plan_advancement_engine_formatting():
    from pathlib import Path
    from scripts.gossipmesh.plan_advancement_engine import (
        PlanTask,
        format_issue_content,
        find_implementation_plans,
    )

    dummy_task = PlanTask(
        num=99,
        name="Build Epoll Edge Loop",
        phase="Phase 1",
        header="Task 99 — Build Epoll Edge Loop",
        spec="Implement non-blocking edge reactor.",
    )
    title, body = format_issue_content(dummy_task, repo="Aditya-9-6/Skelion")
    assert "Task 99 — Build Epoll Edge Loop" in title
    assert "https://github.com/Aditya-9-6/Skelion" in body
    assert "accept" in body.lower()
    assert "Maintainer Approval" in body

    plans = find_implementation_plans(Path("."))
    assert isinstance(plans, list)
    assert len(plans) > 0


def test_check_issue_accepted_negation_guarded(test_engine_instance):
    mock_gh_data = {
        "state": "OPEN",
        "title": "feat(plan): Implement Async Channel Tracker",
        "comments": [
            {"author": {"login": "lead_dev"}, "body": "Please do not accept this yet, waiting for security review."}
        ],
    }
    with patch("skelion_agent.autonomous_engine.run_cmd") as mock_run:
        mock_run.return_value = (0, json.dumps(mock_gh_data), "")
        is_acc, author, target = test_engine_instance.check_issue_accepted(105)
        assert is_acc is False
        assert author is None


def test_batch_dual_engine_accept_comment_negation():
    from scripts.gossipmesh.batch_dual_engine import check_issue_accepted_by_comment
    from subprocess import CompletedProcess

    mock_neg_res = {
        "comments": [
            {"author": {"login": "reviewer"}, "body": "I cannot accept this implementation until we fix memory leaks."}
        ]
    }
    with patch("scripts.gossipmesh.batch_dual_engine.run_cmd") as mock_cmd:
        mock_cmd.return_value = CompletedProcess(
            args=["gh", "issue", "view"], returncode=0, stdout=json.dumps(mock_neg_res)
        )
        is_acc, author = check_issue_accepted_by_comment("55")
        assert is_acc is False
        assert author is None


def test_batch_dual_engine_unaccepted_advancement_is_not_auto_approved():
    from scripts.gossipmesh.batch_dual_engine import process_single_issue
    from subprocess import CompletedProcess

    unaccepted_plan_issue = {
        "number": 120,
        "title": "feat(plan): Task 15 — Build Distributed Ring Buffer",
        "body": "Specification content",
        "labels": [{"name": "advancement"}, {"name": "enterprise-plan"}],
    }

    # Mock check_issue_accepted_by_comment returning no acceptance
    mock_comments_res = {"comments": [{"author": {"login": "user"}, "body": "Initial discussion"}]}
    with patch("scripts.gossipmesh.batch_dual_engine.run_cmd") as mock_cmd:
        mock_cmd.return_value = CompletedProcess(
            args=["gh", "issue", "view"], returncode=0, stdout=json.dumps(mock_comments_res)
        )
        task_type, item_id, status, details = process_single_issue(unaccepted_plan_issue)
        assert task_type == "ISSUE"
        assert item_id == "120"
        assert status == "AWAITING_ACCEPTANCE"
        assert "Awaiting maintainer 'accept' comment" in details


def test_batch_dual_engine_deterministic_idempotency():
    from scripts.gossipmesh.batch_dual_engine import deduct_issue_tokens

    engine = get_engine()
    test_org_id = "test_idempotent_org"
    with Session(engine) as db:
        from skelion_agent.models import CreditLedger
        for row in db.exec(select(CreditLedger).where(CreditLedger.ref_id == "202")).all():
            db.delete(row)
        org = db.get(Organization, test_org_id)
        if not org:
            org = Organization(
                id=test_org_id,
                name="Idempotent Org",
                token="skl_live_idempotent_token",
                plan="team",
                autofix_tokens_total=5000,
                autofix_tokens_used=0,
            )
            db.add(org)
            db.commit()
        else:
            org.autofix_tokens_total = 5000
            org.autofix_tokens_used = 0
            db.add(org)
            db.commit()

    # First deduction: should deduct 250
    ok1, msg1 = deduct_issue_tokens("202", token_cost=250, org_id=test_org_id)
    assert ok1 is True
    assert "Deducted 250" in msg1

    # Second deduction for same issue: MUST be idempotent and NOT deduct again
    ok2, msg2 = deduct_issue_tokens("202", token_cost=250, org_id=test_org_id)
    assert ok2 is True
    assert "idempotent" in msg2.lower()

    # Verify database: used should still be 250, not 500
    with Session(engine) as db:
        org = db.get(Organization, test_org_id)
        assert org.autofix_tokens_used == 250


def test_autonomous_routes_entitlement_gating():
    import os
    from fastapi import HTTPException
    from skelion_agent.autonomous_routes import check_autonomous_loop_entitlement

    # Ensure not bypassed by TESTING env var
    old_test = os.environ.pop("TESTING", None)
    old_env = os.environ.pop("ENV", None)

    try:
        # Org without add-on and on pilot plan should be rejected
        unentitled_org = Organization(
            id="org_unentitled",
            name="Unentitled Org",
            token="skl_live_unentitled",
            plan="pilot",
            addon_autonomous_dev_loop=False,
        )
        with pytest.raises(HTTPException) as exc:
            check_autonomous_loop_entitlement(unentitled_org)
        assert exc.value.status_code == 403

        # Org with add-on active should pass
        entitled_org = Organization(
            id="org_entitled",
            name="Entitled Org",
            token="skl_live_entitled",
            plan="pilot",
            addon_autonomous_dev_loop=True,
        )
        check_autonomous_loop_entitlement(entitled_org)  # Should not raise
    finally:
        if old_test is not None:
            os.environ["TESTING"] = old_test
        if old_env is not None:
            os.environ["ENV"] = old_env


def test_switch_active_repo(test_engine_instance):
    test_engine_instance.set_active_repo("client-corp/production-payment-api")
    assert test_engine_instance.repo == "client-corp/production-payment-api"
    assert test_engine_instance.last_status == "SWITCHED_REPO"


def test_zero_fake_issues_generated_when_no_plans(tmp_path):
    # Empty workspace with NO plan files
    engine = AutonomousLoopEngine(workspace_root=tmp_path, default_repo="client-org/clean-repo")
    with patch("skelion_agent.autonomous_engine.run_cmd") as mock_run:
        # Mock gh issue list returning 0 issues
        mock_run.return_value = (0, "[]", "")
        # Should return None, refusing to generate catalog/fake issues
        issue = engine.generate_advancement_issue()
        assert issue is None

        # run_single_cycle should report up_to_date with 0 tasks found
        res = engine.run_single_cycle()
        assert res["status"] == "up_to_date"
        assert res["tasks_found"] == 0
        assert "Zero pending implementation plan tasks found" in res["message"]


def test_strict_deduplication_against_existing_issues_and_prs(tmp_path):
    # Workspace with a real plan markdown file containing Task 1 and Task 2
    plan_file = tmp_path / "ROADMAP.md"
    plan_file.write_text(
        """# Roadmap
## Task 1 — Implement Edge Rate Limiter
`src/ratelimit.ts`
Implement token bucket.

## Task 2 — Implement Circuit Breaker
`src/circuit.ts`
Implement circuit breaker.
""",
        encoding="utf-8",
    )

    engine = AutonomousLoopEngine(workspace_root=tmp_path, default_repo="client-org/app")

    # Mock GitHub returning Task 1 already existing in issue list
    def mock_run_cmd_side_effect(cmd, **kwargs):
        if "issue" in cmd and "list" in cmd:
            return (0, json.dumps([{"title": "feat(plan): Task 1 — Implement Edge Rate Limiter", "number": 101}]), "")
        if "pr" in cmd and "list" in cmd:
            return (0, "[]", "")
        return (0, "", "")

    with patch("skelion_agent.autonomous_engine.run_cmd", side_effect=mock_run_cmd_side_effect):
        tasks = engine.scan_repo_for_plan_tasks()
        # Task 1 must be deduplicated out; only Task 2 should remain
        assert len(tasks) == 1
        assert tasks[0]["task_number"] == 2
        assert "Circuit Breaker" in tasks[0]["title"]


def test_bounded_queue_at_three_open_issues(tmp_path):
    engine = AutonomousLoopEngine(workspace_root=tmp_path, default_repo="client-org/app")

    # Mock 3 open issues currently awaiting acceptance
    open_issues = [
        {"number": 1, "title": "feat(plan): Task 1"},
        {"number": 2, "title": "feat(plan): Task 2"},
        {"number": 3, "title": "feat(plan): Task 3"},
    ]

    with patch("skelion_agent.autonomous_engine.run_cmd") as mock_run:
        # check_issue_accepted returns False (not yet accepted)
        with patch.object(engine, "check_issue_accepted", return_value=(False, None, None)):
            mock_run.return_value = (0, json.dumps(open_issues), "")
            res = engine.run_single_cycle()
            assert res["status"] == "awaiting_user_acceptance"
            assert res["open_backlog_count"] == 3


