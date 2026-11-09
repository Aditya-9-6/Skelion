# tests/test_pr_review_ingest.py
"""
Comprehensive Unit Tests for PR Review Data & Ingest Pipeline.
Covers:
1. SQLModel models (12 models, constraints, JSON columns, FKs)
2. .skelion.yml schema definition, unknown key rejection, and sha calculation
3. GitHub HMAC SHA-256 signature verification (X-Hub-Signature-256)
4. Strict idempotency and deduplication via X-GitHub-Delivery
5. Supersession logic (in-flight runs cancelled and superseded_by recorded)
6. Installation lifecycle and kill switch enforcement
7. Slash command parsing and ingestion (/skelion review, /skelion fix)
8. Auxiliary API endpoints (/v1/pr_reviews/{id}, /v1/pr_reviews/validate_config)
"""

import hashlib
import hmac
import json
import os
import random
import uuid
import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from sqlmodel import Session, select
from sqlalchemy.exc import IntegrityError

import skelion_agent.database as db_module
from skelion_agent.control_plane import app
from skelion_agent.pr_review_models import (
    Installation,
    Repository,
    PullRequest,
    ReviewRun,
    Finding,
    Evidence,
    Fix,
    Feedback,
    Suppression,
    LLMCache,
    Command,
    WebhookDelivery,
    utc_now,
)
from skelion_agent.pr_review_config import (
    SkelionConfig,
    validate_config,
    compute_config_sha,
    ConfigValidationError,
    SeverityLevel,
    ConfidenceLevel,
    FixMode,
)
from skelion_agent.pr_review_routes import (
    verify_github_signature,
    supersede_in_flight_runs,
    parse_slash_command,
)

TEST_SECRET = "test_webhook_secret_key_12345"


def rand_id() -> int:
    """Generate a random int id to avoid cross-test unique constraint collisions."""
    return random.randint(1_000_000, 999_999_999)


@pytest.fixture(autouse=True)
def setup_webhook_secret(monkeypatch):
    """Ensure GITHUB_WEBHOOK_SECRET is set for tests."""
    monkeypatch.setenv("GITHUB_WEBHOOK_SECRET", TEST_SECRET)


@pytest.fixture
def client():
    """Test client bound to control_plane app."""
    return TestClient(app)


@pytest.fixture
def db_session():
    """Provides a clean database session for test verification."""
    with Session(db_module.engine) as session:
        yield session


def compute_test_signature(body: bytes, secret: str = TEST_SECRET) -> str:
    """Helper to compute valid X-Hub-Signature-256 header."""
    sig = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return f"sha256={sig}"


# ===========================================================================
# 1. Database Model Tests
# ===========================================================================

def test_all_12_models_instantiation_and_persistence(db_session: Session):
    """Test that all 12 SQLModel tables can be instantiated, inserted, and retrieved."""
    inst_id = rand_id()
    repo_id = rand_id()

    # 1. Installation
    inst = Installation(
        github_installation_id=inst_id,
        account_login=f"org-{inst_id}",
        status="active",
        kill_switch=False,
    )
    db_session.add(inst)
    db_session.commit()
    db_session.refresh(inst)
    assert inst.id is not None
    assert inst.github_installation_id == inst_id

    # 2. Repository
    repo = Repository(
        installation_id=inst.id,
        github_repo_id=repo_id,
        full_name=f"org-{inst_id}/repo-{repo_id}",
        default_branch="main",
        protected_branches=["main", "release/*"],
        config={"version": 1},
        plan_tier="pro",
        fix_mode="branch",
    )
    db_session.add(repo)
    db_session.commit()
    db_session.refresh(repo)
    assert repo.protected_branches == ["main", "release/*"]
    assert repo.config == {"version": 1}

    # 3. PullRequest
    pr = PullRequest(
        repository_id=repo.id,
        number=101,
        title_hash="hash123",
        base_sha="base_sha_abc",
        head_sha="head_sha_def",
        state="open",
    )
    db_session.add(pr)
    db_session.commit()
    db_session.refresh(pr)
    assert pr.number == 101

    # 4. ReviewRun
    run = ReviewRun(
        pull_request_id=pr.id,
        head_sha="head_sha_def",
        base_sha="base_sha_abc",
        config_sha="cfg_sha_123",
        status="queued",
        lanes=["ruff", "semgrep", "gitleaks"],
        credits_estimated_milli=50,
        credits_used_milli=25,
    )
    db_session.add(run)
    db_session.commit()
    db_session.refresh(run)
    assert run.lanes == ["ruff", "semgrep", "gitleaks"]

    # 5. Finding
    finding = Finding(
        review_run_id=run.id,
        pull_request_id=pr.id,
        fingerprint=f"fp_injection_{rand_id()}",
        lane="semgrep",
        rule_id="python.lang.security.injection",
        category="security",
        file_path="src/query.py",
        start_line=12,
        end_line=15,
        severity="high",
        confidence="high",
        impact_factor=1.5,
        status="open",
    )
    db_session.add(finding)
    db_session.commit()
    db_session.refresh(finding)
    assert "fp_injection" in finding.fingerprint

    # 6. Evidence
    evidence = Evidence(
        finding_id=finding.id,
        type="sarif",
        ref="rule:python.lang.security.injection",
        redacted_payload={"snippet": "db.execute(query)"},
        sha256="sha256_mock_evidence",
    )
    db_session.add(evidence)
    db_session.commit()
    db_session.refresh(evidence)
    assert evidence.redacted_payload == {"snippet": "db.execute(query)"}

    # 7. Fix
    fix = Fix(
        finding_id=finding.id,
        fix_type="patch",
        diff_sha256="diff_sha_123",
        status="proposed",
        verdict_reason="Parameterized query applied",
        branch="skelion-fix/query-sql",
        commit_sha="commit_sha_fix_1",
        evidence_bundle={"verification_passed": True},
    )
    db_session.add(fix)
    db_session.commit()
    db_session.refresh(fix)
    assert fix.evidence_bundle == {"verification_passed": True}

    # 8. Feedback
    fb = Feedback(
        finding_id=finding.id,
        actor_id="dev-user-1",
        kind="thumbs_up",
        reason="Helpful catch",
    )
    db_session.add(fb)
    db_session.commit()
    db_session.refresh(fb)
    assert fb.kind == "thumbs_up"

    # 9. Suppression
    supp = Suppression(
        repository_id=repo.id,
        rule_id="python.lang.security.injection",
        path_pattern="tests/**",
        reason="Mock tests use raw strings",
        owner="sec-team",
    )
    db_session.add(supp)
    db_session.commit()
    db_session.refresh(supp)
    assert supp.rule_id == "python.lang.security.injection"

    # 10. LLMCache
    chunk_hash = hashlib.sha256(f"chunk content {rand_id()}".encode("utf-8")).hexdigest()
    cache_item = LLMCache(
        chunk_sha256=chunk_hash,
        model="gpt-4o",
        rate_card_version="v1",
        output={"summary": "Safe code"},
    )
    db_session.add(cache_item)
    db_session.commit()
    db_session.refresh(cache_item)
    assert cache_item.output == {"summary": "Safe code"}

    # 11. Command
    cmd = Command(
        repository_id=repo.id,
        pull_request_id=pr.id,
        actor_id="dev-user-2",
        command="fix",
        args={"mode": "branch"},
        status="pending",
    )
    db_session.add(cmd)
    db_session.commit()
    db_session.refresh(cmd)
    assert cmd.command == "fix"
    assert cmd.args == {"mode": "branch"}

    # 12. WebhookDelivery
    deliv_id = f"delivery_uuid_{rand_id()}"
    deliv = WebhookDelivery(
        delivery_id=deliv_id,
        event="pull_request",
        received_at=utc_now(),
    )
    db_session.add(deliv)
    db_session.commit()
    db_session.refresh(deliv)
    assert deliv.delivery_id == deliv_id


def test_pull_request_unique_constraint(db_session: Session):
    """Test unique(repository_id, number) on pull_requests."""
    repo = Repository(
        github_repo_id=rand_id(),
        full_name="org/unique-test",
    )
    db_session.add(repo)
    db_session.commit()

    pr1 = PullRequest(
        repository_id=repo.id,
        number=55,
        base_sha="base1",
        head_sha="head1",
    )
    db_session.add(pr1)
    db_session.commit()

    pr2 = PullRequest(
        repository_id=repo.id,
        number=55,
        base_sha="base2",
        head_sha="head2",
    )
    db_session.add(pr2)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_review_run_unique_constraint(db_session: Session):
    """Test unique(pull_request_id, head_sha, config_sha) on review_runs."""
    repo = Repository(github_repo_id=rand_id(), full_name="org/run-unique")
    db_session.add(repo)
    db_session.commit()

    pr = PullRequest(repository_id=repo.id, number=1, base_sha="b", head_sha="h")
    db_session.add(pr)
    db_session.commit()

    r1 = ReviewRun(
        pull_request_id=pr.id,
        head_sha="sha_common",
        base_sha="base_common",
        config_sha="config_common",
    )
    db_session.add(r1)
    db_session.commit()

    r2 = ReviewRun(
        pull_request_id=pr.id,
        head_sha="sha_common",
        base_sha="base_common",
        config_sha="config_common",
    )
    db_session.add(r2)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_findings_unique_constraint(db_session: Session):
    """Test unique(pull_request_id, fingerprint) on findings."""
    repo = Repository(github_repo_id=rand_id(), full_name="org/findings-unique")
    db_session.add(repo)
    db_session.commit()

    pr = PullRequest(repository_id=repo.id, number=2, base_sha="b", head_sha="h")
    db_session.add(pr)
    db_session.commit()

    run = ReviewRun(pull_request_id=pr.id, head_sha="h", base_sha="b")
    db_session.add(run)
    db_session.commit()

    fp = f"fingerprint_sec_{rand_id()}"
    f1 = Finding(
        review_run_id=run.id,
        pull_request_id=pr.id,
        fingerprint=fp,
        lane="ruff",
        rule_id="E501",
        file_path="main.py",
        start_line=1,
        end_line=1,
    )
    db_session.add(f1)
    db_session.commit()

    f2 = Finding(
        review_run_id=run.id,
        pull_request_id=pr.id,
        fingerprint=fp,
        lane="ruff",
        rule_id="E501",
        file_path="main.py",
        start_line=1,
        end_line=1,
    )
    db_session.add(f2)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_review_run_superseded_by_foreign_key(db_session: Session):
    """Test self-referencing superseded_by FK in review_runs."""
    repo = Repository(github_repo_id=rand_id(), full_name="org/superseded-fk")
    db_session.add(repo)
    db_session.commit()

    pr = PullRequest(repository_id=repo.id, number=3, base_sha="b", head_sha="h1")
    db_session.add(pr)
    db_session.commit()

    run1 = ReviewRun(pull_request_id=pr.id, head_sha="h1", base_sha="b", status="queued")
    db_session.add(run1)
    db_session.commit()

    run2 = ReviewRun(pull_request_id=pr.id, head_sha="h2", base_sha="b", status="queued")
    db_session.add(run2)
    db_session.commit()

    run1.status = "superseded"
    run1.superseded_by = run2.id
    db_session.add(run1)
    db_session.commit()

    reloaded_run1 = db_session.get(ReviewRun, run1.id)
    assert reloaded_run1.superseded_by == run2.id
    assert reloaded_run1.status == "superseded"


# ===========================================================================
# 2. .skelion.yml Schema & Validator Tests
# ===========================================================================

def test_skelion_config_valid_full():
    """Test validating a fully-specified valid .skelion.yml file."""
    yaml_text = """
    version: 1
    lanes:
      ruff:
        enabled: true
        config_file: "pyproject.toml"
        extra_args: ["--isolated"]
      semgrep:
        enabled: true
        rules: ["p/security-audit"]
      gitleaks:
        enabled: true
      osv_scanner:
        enabled: false
    fix:
      enabled: true
      mode: branch
      max_fixes: 5
      verification: true
    rules:
      ignore:
        - "tests/**"
        - "docs/**"
      severity_threshold: high
      confidence_threshold: medium
    suppressions:
      - rule_id: "python.lang.security.injection"
        path: "tests/mock.py"
        reason: "Test only"
    review:
      comment_on_pr: true
      summary_table: true
      inline_comments: true
      max_comments: 10
    limits:
      max_files: 200
      timeout_sec: 180
    """
    config = validate_config(yaml_text)
    assert config.version == 1
    assert config.lanes["ruff"].enabled is True
    assert config.lanes["ruff"].extra_args == ["--isolated"]
    assert config.lanes["semgrep"].rules == ["p/security-audit"]
    assert config.fix.mode == FixMode.BRANCH
    assert config.fix.max_fixes == 5
    assert config.rules.severity_threshold == SeverityLevel.HIGH
    assert len(config.suppressions) == 1
    assert config.review.max_comments == 10
    assert config.limits.max_files == 200


def test_skelion_config_lanes_list_format():
    """Test validating lanes provided as a simple list of strings."""
    yaml_text = """
    version: 1
    lanes:
      - ruff
      - semgrep
      - gitleaks
    """
    config = validate_config(yaml_text)
    assert "ruff" in config.lanes
    assert config.lanes["ruff"].enabled is True
    assert "semgrep" in config.lanes
    assert "gitleaks" in config.lanes


def test_skelion_config_rejects_unknown_top_level_keys():
    """Test that unknown top-level keys raise ConfigValidationError with a clear error."""
    yaml_text = """
    version: 1
    unsupported_top_level_key: "danger"
    """
    with pytest.raises(ConfigValidationError) as exc_info:
        validate_config(yaml_text)
    err = str(exc_info.value)
    assert "Unknown key 'unsupported_top_level_key'" in err
    assert "is not allowed in .skelion.yml" in err


def test_skelion_config_rejects_unknown_nested_keys():
    """Test that unknown nested keys in sub-models raise ConfigValidationError."""
    yaml_text = """
    version: 1
    lanes:
      ruff:
        enabled: true
        illegal_sub_key: 123
    """
    with pytest.raises(ConfigValidationError) as exc_info:
        validate_config(yaml_text)
    err = str(exc_info.value)
    assert "Unknown key 'illegal_sub_key'" in err


def test_skelion_config_invalid_yaml():
    """Test invalid YAML syntax produces ConfigValidationError."""
    invalid_yaml = "version: 1\nlanes: [unclosed"
    with pytest.raises(ConfigValidationError) as exc_info:
        validate_config(invalid_yaml)
    assert "Invalid YAML syntax" in str(exc_info.value)


def test_skelion_config_non_dict_yaml():
    """Test that YAML parsing to a list or primitive raises ConfigValidationError."""
    with pytest.raises(ConfigValidationError) as exc_info:
        validate_config("- item 1\n- item 2")
    assert "must be a mapping/dictionary" in str(exc_info.value)


def test_skelion_config_empty_returns_defaults():
    """Test empty configuration string returns default SkelionConfig."""
    config = validate_config("")
    assert config.version == 1
    assert config.fix.mode == FixMode.SUGGEST


def test_compute_config_sha():
    """Test compute_config_sha is deterministic."""
    sha1 = compute_config_sha("version: 1\n")
    sha2 = compute_config_sha("version: 1\n")
    assert sha1 == sha2
    assert len(sha1) == 64


# ===========================================================================
# 3. HMAC SHA-256 Webhook Signature Verification Tests
# ===========================================================================

def test_signature_verification_helper():
    """Test verify_github_signature helper directly."""
    body = b'{"action": "opened"}'
    valid_sig = compute_test_signature(body, TEST_SECRET)

    assert verify_github_signature(body, valid_sig, TEST_SECRET) is True
    assert verify_github_signature(body, "sha256=invalidhex", TEST_SECRET) is False
    assert verify_github_signature(body, None, TEST_SECRET) is False
    assert verify_github_signature(body, "invalidscheme=123", TEST_SECRET) is False
    assert verify_github_signature(b'{"different": 1}', valid_sig, TEST_SECRET) is False


def test_webhook_route_rejects_missing_signature(client: TestClient):
    """Test route returns 401 when signature header is missing."""
    delivery_id = str(uuid.uuid4())
    resp = client.post(
        "/v1/webhooks/github",
        json={"action": "opened"},
        headers={"X-GitHub-Delivery": delivery_id, "X-GitHub-Event": "pull_request"},
    )
    assert resp.status_code == 401
    assert "signature" in resp.json()["detail"].lower()


def test_webhook_route_rejects_invalid_signature(client: TestClient):
    """Test route returns 401 when signature does not match payload."""
    delivery_id = str(uuid.uuid4())
    resp = client.post(
        "/v1/webhooks/github",
        json={"action": "opened"},
        headers={
            "X-GitHub-Delivery": delivery_id,
            "X-GitHub-Event": "pull_request",
            "X-Hub-Signature-256": "sha256=0000000000000000000000000000000000000000000000000000000000000000",
        },
    )
    assert resp.status_code == 401
    assert "signature" in resp.json()["detail"].lower()


def test_webhook_route_accepts_valid_signature(client: TestClient):
    """Test route accepts request with valid HMAC SHA-256 signature."""
    delivery_id = str(uuid.uuid4())
    payload = {"zen": "Mind your words."}
    body = json.dumps(payload).encode("utf-8")
    sig = compute_test_signature(body, TEST_SECRET)

    resp = client.post(
        "/v1/webhooks/github",
        content=body,
        headers={
            "Content-Type": "application/json",
            "X-GitHub-Delivery": delivery_id,
            "X-GitHub-Event": "ping",
            "X-Hub-Signature-256": sig,
        },
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "pong"


# ===========================================================================
# 4. Strict Deduplication and Idempotency Tests
# ===========================================================================

def test_webhook_route_requires_delivery_header(client: TestClient):
    """Test route rejects requests without X-GitHub-Delivery."""
    body = b'{"zen": "hello"}'
    sig = compute_test_signature(body, TEST_SECRET)
    resp = client.post(
        "/v1/webhooks/github",
        content=body,
        headers={
            "Content-Type": "application/json",
            "X-GitHub-Event": "ping",
            "X-Hub-Signature-256": sig,
        },
    )
    assert resp.status_code == 400
    assert "Missing X-GitHub-Delivery" in resp.json()["detail"]


def test_webhook_deduplication_via_delivery_id(client: TestClient, db_session: Session):
    """Test that repeated requests with the same X-GitHub-Delivery are deduplicated."""
    delivery_id = f"dedup-test-{uuid.uuid4()}"
    repo_gh_id = rand_id()
    head_sha = f"sha_dedup_{rand_id()}"
    payload = {
        "action": "opened",
        "repository": {"id": repo_gh_id, "full_name": f"test-org/dedup-repo-{repo_gh_id}"},
        "pull_request": {
            "number": 1,
            "head": {"sha": head_sha},
            "base": {"sha": "sha_base_0"},
            "state": "open",
            "title": "Dedup Test PR",
        },
    }
    body = json.dumps(payload).encode("utf-8")
    sig = compute_test_signature(body, TEST_SECRET)
    headers = {
        "Content-Type": "application/json",
        "X-GitHub-Delivery": delivery_id,
        "X-GitHub-Event": "pull_request",
        "X-Hub-Signature-256": sig,
    }

    # First delivery: processed normally
    resp1 = client.post("/v1/webhooks/github", content=body, headers=headers)
    assert resp1.status_code == 200
    data1 = resp1.json()
    assert data1["status"] == "success"
    first_run_id = data1["run_id"]

    # Verify delivery record exists
    deliv_rec = db_session.get(WebhookDelivery, delivery_id)
    assert deliv_rec is not None
    assert deliv_rec.processed_at is not None

    # Second delivery with SAME delivery_id: returned duplicate status
    resp2 = client.post("/v1/webhooks/github", content=body, headers=headers)
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert data2["status"] == "duplicate"
    assert data2["delivery_id"] == delivery_id

    # Verify only ONE review run was created
    runs = db_session.exec(
        select(ReviewRun).where(ReviewRun.head_sha == head_sha)
    ).all()
    assert len(runs) == 1
    assert runs[0].id == first_run_id


# ===========================================================================
# 5. Supersession Logic Tests
# ===========================================================================

def test_supersede_in_flight_runs_helper(db_session: Session):
    """Test supersede_in_flight_runs helper function directly."""
    repo = Repository(github_repo_id=rand_id(), full_name="test-org/supersede-helper")
    db_session.add(repo)
    db_session.commit()

    pr = PullRequest(repository_id=repo.id, number=10, base_sha="b0", head_sha="h1")
    db_session.add(pr)
    db_session.commit()

    # Create two in-flight runs and one completed run
    run1 = ReviewRun(pull_request_id=pr.id, head_sha="h1", base_sha="b0", status="queued")
    run2 = ReviewRun(pull_request_id=pr.id, head_sha="h1_b", base_sha="b0", status="in_progress")
    run_done = ReviewRun(pull_request_id=pr.id, head_sha="h0", base_sha="b0", status="completed")
    db_session.add_all([run1, run2, run_done])
    db_session.commit()

    # Create new run
    new_run = ReviewRun(pull_request_id=pr.id, head_sha="h2", base_sha="b0", status="queued")
    db_session.add(new_run)
    db_session.commit()

    superseded = supersede_in_flight_runs(db_session, pr.id, new_run.id)
    assert len(superseded) == 2
    superseded_ids = {r.id for r in superseded}
    assert run1.id in superseded_ids
    assert run2.id in superseded_ids

    # Verify DB state
    db_session.refresh(run1)
    db_session.refresh(run2)
    db_session.refresh(run_done)
    assert run1.status == "superseded"
    assert run1.superseded_by == new_run.id
    assert run1.finished_at is not None

    assert run2.status == "superseded"
    assert run2.superseded_by == new_run.id

    # Completed run must remain completed
    assert run_done.status == "completed"
    assert run_done.superseded_by is None


def test_supersession_flow_via_webhook(client: TestClient, db_session: Session):
    """
    Test end-to-end supersession flow via GitHub Webhook:
    1. Action 'opened' creates run 1 (head_sha="sha_v1")
    2. Action 'synchronize' with newer head_sha ("sha_v2") supersedes run 1 and starts run 2
    3. Action 'synchronize' with newer head_sha ("sha_v3") supersedes run 2 and starts run 3
    """
    repo_id = rand_id()

    # Step 1: opened
    delivery_1 = f"deliv-super-1-{uuid.uuid4()}"
    payload_1 = {
        "action": "opened",
        "repository": {"id": repo_id, "full_name": f"test-org/super-flow-{repo_id}"},
        "pull_request": {
            "number": 42,
            "head": {"sha": f"sha_v1_{repo_id}"},
            "base": {"sha": "sha_base"},
            "state": "open",
            "title": "Feature Branch",
        },
    }
    body_1 = json.dumps(payload_1).encode("utf-8")
    resp_1 = client.post(
        "/v1/webhooks/github",
        content=body_1,
        headers={
            "Content-Type": "application/json",
            "X-GitHub-Delivery": delivery_1,
            "X-GitHub-Event": "pull_request",
            "X-Hub-Signature-256": compute_test_signature(body_1),
        },
    )
    assert resp_1.status_code == 200
    res_1 = resp_1.json()
    run_1_id = res_1["run_id"]
    assert res_1["superseded_count"] == 0

    # Step 2: synchronize with new head sha
    delivery_2 = f"deliv-super-2-{uuid.uuid4()}"
    payload_2 = {
        "action": "synchronize",
        "repository": {"id": repo_id, "full_name": f"test-org/super-flow-{repo_id}"},
        "pull_request": {
            "number": 42,
            "head": {"sha": f"sha_v2_{repo_id}"},
            "base": {"sha": "sha_base"},
            "state": "open",
            "title": "Feature Branch",
        },
    }
    body_2 = json.dumps(payload_2).encode("utf-8")
    resp_2 = client.post(
        "/v1/webhooks/github",
        content=body_2,
        headers={
            "Content-Type": "application/json",
            "X-GitHub-Delivery": delivery_2,
            "X-GitHub-Event": "pull_request",
            "X-Hub-Signature-256": compute_test_signature(body_2),
        },
    )
    assert resp_2.status_code == 200
    res_2 = resp_2.json()
    run_2_id = res_2["run_id"]
    assert res_2["superseded_count"] == 1
    assert run_1_id in res_2["superseded_runs"]

    # Verify run 1 in DB is superseded
    db_run_1 = db_session.get(ReviewRun, run_1_id)
    assert db_run_1.status == "superseded"
    assert db_run_1.superseded_by == run_2_id

    # Step 3: synchronize with third head sha
    delivery_3 = f"deliv-super-3-{uuid.uuid4()}"
    payload_3 = {
        "action": "synchronize",
        "repository": {"id": repo_id, "full_name": f"test-org/super-flow-{repo_id}"},
        "pull_request": {
            "number": 42,
            "head": {"sha": f"sha_v3_{repo_id}"},
            "base": {"sha": "sha_base"},
            "state": "open",
            "title": "Feature Branch",
        },
    }
    body_3 = json.dumps(payload_3).encode("utf-8")
    resp_3 = client.post(
        "/v1/webhooks/github",
        content=body_3,
        headers={
            "Content-Type": "application/json",
            "X-GitHub-Delivery": delivery_3,
            "X-GitHub-Event": "pull_request",
            "X-Hub-Signature-256": compute_test_signature(body_3),
        },
    )
    assert resp_3.status_code == 200
    res_3 = resp_3.json()
    run_3_id = res_3["run_id"]
    assert res_3["superseded_count"] == 1
    assert run_2_id in res_3["superseded_runs"]

    # Verify run 2 is now superseded by run 3
    db_run_2 = db_session.get(ReviewRun, run_2_id)
    assert db_run_2.status == "superseded"
    assert db_run_2.superseded_by == run_3_id


def test_pr_closed_cancels_in_flight_runs(client: TestClient, db_session: Session):
    """Test action 'closed' cancels in-flight review runs."""
    repo_id = rand_id()
    delivery_open = f"deliv-open-{uuid.uuid4()}"
    head_sha = f"sha_close_test_{repo_id}"
    payload_open = {
        "action": "opened",
        "repository": {"id": repo_id, "full_name": f"test-org/close-flow-{repo_id}"},
        "pull_request": {
            "number": 77,
            "head": {"sha": head_sha},
            "base": {"sha": "sha_base"},
            "state": "open",
            "title": "To be closed",
        },
    }
    b_open = json.dumps(payload_open).encode("utf-8")
    resp_open = client.post(
        "/v1/webhooks/github",
        content=b_open,
        headers={
            "Content-Type": "application/json",
            "X-GitHub-Delivery": delivery_open,
            "X-GitHub-Event": "pull_request",
            "X-Hub-Signature-256": compute_test_signature(b_open),
        },
    )
    run_id = resp_open.json()["run_id"]

    # Now send PR closed
    delivery_close = f"deliv-close-{uuid.uuid4()}"
    payload_close = {
        "action": "closed",
        "repository": {"id": repo_id, "full_name": f"test-org/close-flow-{repo_id}"},
        "pull_request": {
            "number": 77,
            "head": {"sha": head_sha},
            "base": {"sha": "sha_base"},
            "state": "closed",
        },
    }
    b_close = json.dumps(payload_close).encode("utf-8")
    resp_close = client.post(
        "/v1/webhooks/github",
        content=b_close,
        headers={
            "Content-Type": "application/json",
            "X-GitHub-Delivery": delivery_close,
            "X-GitHub-Event": "pull_request",
            "X-Hub-Signature-256": compute_test_signature(b_close),
        },
    )
    assert resp_close.status_code == 200
    assert resp_close.json()["action"] == "closed"

    db_run = db_session.get(ReviewRun, run_id)
    assert db_run.status == "cancelled"


# ===========================================================================
# 6. Installation Lifecycle & Kill Switch Tests
# ===========================================================================

def test_installation_kill_switch_skips_pr_processing(client: TestClient, db_session: Session):
    """Test that if an installation kill_switch is active, PR webhooks are skipped."""
    gh_inst_id = rand_id()
    repo_id = rand_id()
    head_sha = f"sha_ks_{rand_id()}"

    inst = Installation(
        github_installation_id=gh_inst_id,
        account_login=f"killswitch-org-{gh_inst_id}",
        status="active",
        kill_switch=True,  # Kill switch activated!
    )
    db_session.add(inst)
    db_session.commit()

    delivery = f"deliv-killswitch-{uuid.uuid4()}"
    payload = {
        "action": "opened",
        "installation": {"id": gh_inst_id, "account": {"login": f"killswitch-org-{gh_inst_id}"}},
        "repository": {"id": repo_id, "full_name": f"killswitch-org/repo-{repo_id}"},
        "pull_request": {
            "number": 1,
            "head": {"sha": head_sha},
            "base": {"sha": "sha_base"},
            "state": "open",
            "title": "PR on killed installation",
        },
    }
    body = json.dumps(payload).encode("utf-8")
    resp = client.post(
        "/v1/webhooks/github",
        content=body,
        headers={
            "Content-Type": "application/json",
            "X-GitHub-Delivery": delivery,
            "X-GitHub-Event": "pull_request",
            "X-Hub-Signature-256": compute_test_signature(body),
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "skipped"
    assert "Kill switch" in data["reason"]

    # Verify no review run was created
    runs = db_session.exec(select(ReviewRun).where(ReviewRun.head_sha == head_sha)).all()
    assert len(runs) == 0


def test_installation_suspend_and_unsuspend_events(client: TestClient, db_session: Session):
    """Test installation lifecycle events: created, suspend, unsuspend."""
    gh_inst_id = rand_id()

    # 1. Installation created
    d1 = f"deliv-inst-create-{uuid.uuid4()}"
    p1 = {
        "action": "created",
        "installation": {"id": gh_inst_id, "account": {"login": f"lifecycle-org-{gh_inst_id}"}},
    }
    b1 = json.dumps(p1).encode("utf-8")
    resp1 = client.post(
        "/v1/webhooks/github",
        content=b1,
        headers={
            "Content-Type": "application/json",
            "X-GitHub-Delivery": d1,
            "X-GitHub-Event": "installation",
            "X-Hub-Signature-256": compute_test_signature(b1),
        },
    )
    assert resp1.status_code == 200

    inst = db_session.exec(
        select(Installation).where(Installation.github_installation_id == gh_inst_id)
    ).first()
    assert inst is not None
    assert inst.status == "active"
    assert inst.kill_switch is False

    # 2. Installation suspended
    d2 = f"deliv-inst-suspend-{uuid.uuid4()}"
    p2 = {
        "action": "suspend",
        "installation": {"id": gh_inst_id},
    }
    b2 = json.dumps(p2).encode("utf-8")
    client.post(
        "/v1/webhooks/github",
        content=b2,
        headers={
            "Content-Type": "application/json",
            "X-GitHub-Delivery": d2,
            "X-GitHub-Event": "installation",
            "X-Hub-Signature-256": compute_test_signature(b2),
        },
    )
    db_session.refresh(inst)
    assert inst.status == "suspended"
    assert inst.kill_switch is True

    # 3. Installation unsuspended
    d3 = f"deliv-inst-unsuspend-{uuid.uuid4()}"
    p3 = {
        "action": "unsuspend",
        "installation": {"id": gh_inst_id},
    }
    b3 = json.dumps(p3).encode("utf-8")
    client.post(
        "/v1/webhooks/github",
        content=b3,
        headers={
            "Content-Type": "application/json",
            "X-GitHub-Delivery": d3,
            "X-GitHub-Event": "installation",
            "X-Hub-Signature-256": compute_test_signature(b3),
        },
    )
    db_session.refresh(inst)
    assert inst.status == "active"
    assert inst.kill_switch is False


# ===========================================================================
# 7. Slash Command Ingestion Tests
# ===========================================================================

def test_parse_slash_command_helper():
    """Test slash command regex parser."""
    cmd1 = parse_slash_command("/skelion review")
    assert cmd1 == {"command": "review", "raw_args": ""}

    cmd2 = parse_slash_command("  /skelion fix --mode branch --max 3  ")
    assert cmd2["command"] == "fix"
    assert "--mode branch --max 3" in cmd2["raw_args"]

    cmd3 = parse_slash_command("@skelion review")
    assert cmd3 == {"command": "review", "raw_args": ""}

    assert parse_slash_command("LGTM! Great work.") is None


def test_slash_command_webhook_flow(client: TestClient, db_session: Session):
    """Test issue_comment webhook with /skelion review command."""
    repo_id = rand_id()
    head_sha = f"sha_slash_{repo_id}"

    # First create PR
    delivery_pr = f"deliv-pr-{uuid.uuid4()}"
    payload_pr = {
        "action": "opened",
        "repository": {"id": repo_id, "full_name": f"test-org/slash-cmd-{repo_id}"},
        "pull_request": {
            "number": 5,
            "head": {"sha": head_sha},
            "base": {"sha": "sha_base"},
            "state": "open",
            "title": "PR for slash cmd",
        },
    }
    b_pr = json.dumps(payload_pr).encode("utf-8")
    client.post(
        "/v1/webhooks/github",
        content=b_pr,
        headers={
            "Content-Type": "application/json",
            "X-GitHub-Delivery": delivery_pr,
            "X-GitHub-Event": "pull_request",
            "X-Hub-Signature-256": compute_test_signature(b_pr),
        },
    )

    # Now post /skelion review comment
    delivery_comment = f"deliv-comment-{uuid.uuid4()}"
    sender_name = f"dev-{rand_id()}"
    payload_comment = {
        "action": "created",
        "repository": {"id": repo_id, "full_name": f"test-org/slash-cmd-{repo_id}"},
        "issue": {"number": 5},
        "comment": {"body": "/skelion review"},
        "sender": {"login": sender_name},
    }
    b_comment = json.dumps(payload_comment).encode("utf-8")
    resp_comment = client.post(
        "/v1/webhooks/github",
        content=b_comment,
        headers={
            "Content-Type": "application/json",
            "X-GitHub-Delivery": delivery_comment,
            "X-GitHub-Event": "issue_comment",
            "X-Hub-Signature-256": compute_test_signature(b_comment),
        },
    )
    assert resp_comment.status_code == 200
    data = resp_comment.json()
    assert data["status"] == "command_queued"
    assert data["command"] == "review"
    assert data["run_id"] is not None

    # Verify Command record in DB
    cmd = db_session.exec(
        select(Command).where(Command.actor_id == sender_name)
    ).first()
    assert cmd is not None
    assert cmd.command == "review"


# ===========================================================================
# 8. Auxiliary API Endpoints
# ===========================================================================

def test_auxiliary_review_endpoints(client: TestClient, db_session: Session):
    """Test GET /v1/pr_reviews/{id} and POST /v1/pr_reviews/validate_config."""
    repo = Repository(github_repo_id=rand_id(), full_name="test-org/aux-api")
    db_session.add(repo)
    db_session.commit()

    pr = PullRequest(repository_id=repo.id, number=9, base_sha="b", head_sha="h")
    db_session.add(pr)
    db_session.commit()

    run = ReviewRun(pull_request_id=pr.id, head_sha="h", base_sha="b")
    db_session.add(run)
    db_session.commit()

    fp = f"fp_aux_{rand_id()}"
    finding = Finding(
        review_run_id=run.id,
        pull_request_id=pr.id,
        fingerprint=fp,
        lane="ruff",
        rule_id="F401",
        file_path="foo.py",
        start_line=1,
        end_line=1,
    )
    db_session.add(finding)
    db_session.commit()

    # 1. Fetch review run
    resp_run = client.get(f"/v1/pr_reviews/{run.id}")
    assert resp_run.status_code == 200
    res_data = resp_run.json()
    assert res_data["run"]["id"] == run.id
    assert len(res_data["findings"]) == 1
    assert res_data["findings"][0]["fingerprint"] == fp

    # 2. Fetch runs by PR
    resp_pr_runs = client.get(f"/v1/pull_requests/{pr.id}/runs")
    assert resp_pr_runs.status_code == 200
    assert len(resp_pr_runs.json()["runs"]) >= 1

    # 3. Validate config endpoint (valid)
    resp_val_ok = client.post(
        "/v1/pr_reviews/validate_config",
        json={"raw_yaml": "version: 1\nlanes: [ruff]"},
    )
    assert resp_val_ok.status_code == 200
    assert resp_val_ok.json()["valid"] is True

    # 4. Validate config endpoint (invalid unknown key)
    resp_val_bad = client.post(
        "/v1/pr_reviews/validate_config",
        json={"raw_yaml": "version: 1\nillegal_key: true"},
    )
    assert resp_val_bad.status_code == 200
    assert resp_val_bad.json()["valid"] is False
    assert "Unknown key 'illegal_key'" in resp_val_bad.json()["error"]


# ===========================================================================
# 9. Edge Case & Robustness Tests (Discovered in Review)
# ===========================================================================

def test_pr_reopen_and_resync_with_same_sha_and_config(client: TestClient, db_session: Session):
    """Verify reopening PR or duplicate opened/sync events with identical (pr_id, head_sha, config_sha) do not crash with IntegrityError."""
    repo_id = rand_id()
    head_sha = f"sha_reopen_{repo_id}"
    cfg_sha = f"cfg_sha_{repo_id}"

    # Setup repo with non-null config_sha
    repo = Repository(github_repo_id=repo_id, full_name=f"org/repo-{repo_id}", config_sha=cfg_sha)
    db_session.add(repo)
    db_session.commit()

    # 1. PR opened event
    deliv_1 = f"deliv-open-{uuid.uuid4()}"
    p_open = {
        "action": "opened",
        "repository": {"id": repo_id, "full_name": f"org/repo-{repo_id}"},
        "pull_request": {
            "number": 20,
            "head": {"sha": head_sha},
            "base": {"sha": "sha_base"},
            "state": "open",
            "title": "PR to be reopened",
        },
    }
    b1 = json.dumps(p_open).encode("utf-8")
    r1 = client.post(
        "/v1/webhooks/github",
        content=b1,
        headers={
            "Content-Type": "application/json",
            "X-GitHub-Delivery": deliv_1,
            "X-GitHub-Event": "pull_request",
            "X-Hub-Signature-256": compute_test_signature(b1),
        },
    )
    assert r1.status_code == 200
    run_id = r1.json()["run_id"]

    # 2. PR closed event
    deliv_2 = f"deliv-close-{uuid.uuid4()}"
    p_close = dict(p_open, action="closed")
    b2 = json.dumps(p_close).encode("utf-8")
    r2 = client.post(
        "/v1/webhooks/github",
        content=b2,
        headers={
            "Content-Type": "application/json",
            "X-GitHub-Delivery": deliv_2,
            "X-GitHub-Event": "pull_request",
            "X-Hub-Signature-256": compute_test_signature(b2),
        },
    )
    assert r2.status_code == 200

    # 3. PR reopened event with same commit & config_sha
    deliv_3 = f"deliv-reopen-{uuid.uuid4()}"
    p_reopen = dict(p_open, action="reopened")
    b3 = json.dumps(p_reopen).encode("utf-8")
    r3 = client.post(
        "/v1/webhooks/github",
        content=b3,
        headers={
            "Content-Type": "application/json",
            "X-GitHub-Delivery": deliv_3,
            "X-GitHub-Event": "pull_request",
            "X-Hub-Signature-256": compute_test_signature(b3),
        },
    )
    assert r3.status_code == 200
    assert r3.json()["status"] == "success"
    assert r3.json()["run_id"] == run_id

    # Verify run is back to queued
    reloaded_run = db_session.get(ReviewRun, run_id)
    assert reloaded_run.status == "queued"


def test_slash_command_on_same_pr_with_same_sha_and_config(client: TestClient, db_session: Session):
    """Verify that multiple /skelion review comments on the same PR commit do not raise IntegrityError."""
    repo_id = rand_id()
    head_sha = f"sha_cmd_{repo_id}"
    cfg_sha = f"cfg_cmd_{repo_id}"

    repo = Repository(github_repo_id=repo_id, full_name=f"org/cmd-repo-{repo_id}", config_sha=cfg_sha)
    db_session.add(repo)
    db_session.commit()

    # Create PR via opened event
    deliv_pr = f"deliv-cmd-pr-{uuid.uuid4()}"
    payload_pr = {
        "action": "opened",
        "repository": {"id": repo_id, "full_name": f"org/cmd-repo-{repo_id}"},
        "pull_request": {
            "number": 33,
            "head": {"sha": head_sha},
            "base": {"sha": "sha_base"},
            "state": "open",
            "title": "PR for repeated slash commands",
        },
    }
    b_pr = json.dumps(payload_pr).encode("utf-8")
    client.post(
        "/v1/webhooks/github",
        content=b_pr,
        headers={
            "Content-Type": "application/json",
            "X-GitHub-Delivery": deliv_pr,
            "X-GitHub-Event": "pull_request",
            "X-Hub-Signature-256": compute_test_signature(b_pr),
        },
    )

    # First slash command
    deliv_c1 = f"deliv-c1-{uuid.uuid4()}"
    p_c1 = {
        "action": "created",
        "repository": {"id": repo_id, "full_name": f"org/cmd-repo-{repo_id}"},
        "issue": {"number": 33},
        "comment": {"body": "/skelion review"},
        "sender": {"login": "dev-tester-1"},
    }
    bc1 = json.dumps(p_c1).encode("utf-8")
    rc1 = client.post(
        "/v1/webhooks/github",
        content=bc1,
        headers={
            "Content-Type": "application/json",
            "X-GitHub-Delivery": deliv_c1,
            "X-GitHub-Event": "issue_comment",
            "X-Hub-Signature-256": compute_test_signature(bc1),
        },
    )
    assert rc1.status_code == 200
    assert rc1.json()["status"] == "command_queued"

    # Second slash command on same PR commit
    deliv_c2 = f"deliv-c2-{uuid.uuid4()}"
    p_c2 = {
        "action": "created",
        "repository": {"id": repo_id, "full_name": f"org/cmd-repo-{repo_id}"},
        "issue": {"number": 33},
        "comment": {"body": "Please review again:\n/review"},
        "sender": {"login": "dev-tester-2"},
    }
    bc2 = json.dumps(p_c2).encode("utf-8")
    rc2 = client.post(
        "/v1/webhooks/github",
        content=bc2,
        headers={
            "Content-Type": "application/json",
            "X-GitHub-Delivery": deliv_c2,
            "X-GitHub-Event": "issue_comment",
            "X-Hub-Signature-256": compute_test_signature(bc2),
        },
    )
    assert rc2.status_code == 200
    assert rc2.json()["status"] == "command_queued"
    assert rc2.json()["command"] == "review"


def test_slash_command_respects_installation_kill_switch(client: TestClient, db_session: Session):
    """Verify that /skelion review or /fix is rejected when installation kill switch is active."""
    inst_id = rand_id()
    repo_id = rand_id()

    inst = Installation(
        github_installation_id=inst_id,
        account_login=f"org-{inst_id}",
        status="suspended",
        kill_switch=True,
    )
    db_session.add(inst)
    db_session.commit()

    repo = Repository(
        installation_id=inst.id,
        github_repo_id=repo_id,
        full_name=f"org-{inst_id}/repo-{repo_id}",
    )
    db_session.add(repo)
    db_session.commit()

    pr = PullRequest(repository_id=repo.id, number=7, base_sha="b", head_sha="h")
    db_session.add(pr)
    db_session.commit()

    deliv_id = f"deliv-kill-{uuid.uuid4()}"
    payload = {
        "action": "created",
        "installation": {"id": inst_id},
        "repository": {"id": repo_id, "full_name": repo.full_name},
        "issue": {"number": 7},
        "comment": {"body": "/skelion review"},
        "sender": {"login": "attacker"},
    }
    b = json.dumps(payload).encode("utf-8")
    resp = client.post(
        "/v1/webhooks/github",
        content=b,
        headers={
            "Content-Type": "application/json",
            "X-GitHub-Delivery": deliv_id,
            "X-GitHub-Event": "issue_comment",
            "X-Hub-Signature-256": compute_test_signature(b),
        },
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "skipped"
    assert "Kill switch enabled" in resp.json()["reason"]


def test_parse_slash_command_multiline_and_none_input():
    """Verify parse_slash_command handles None safely and parses multiline comments."""
    assert parse_slash_command(None) is None
    assert parse_slash_command("") is None
    assert parse_slash_command("   ") is None

    # Multiline /review
    res1 = parse_slash_command("Hello team,\n/review\nThanks!")
    assert res1 is not None
    assert res1["command"] == "review"

    # Multiline /fix with args
    res2 = parse_slash_command("Addressing feedback:\n/fix 42")
    assert res2 is not None
    assert res2["command"] == "fix"
    assert res2["raw_args"].strip() == "42"


def test_compute_config_sha_none_input():
    """Verify compute_config_sha handles None input without crashing."""
    sha_none = compute_config_sha(None)
    assert isinstance(sha_none, str)
    assert len(sha_none) == 64
    assert sha_none == compute_config_sha(b"")


def test_model_plural_aliases_and_exports():
    """Verify all 12 models have singular and plural aliases registered in database.py."""
    from skelion_agent.pr_review_models import (
        Evidences,
        Feedbacks,
        FeedbackRecords,
        Installations,
        Repositories,
        PullRequests,
        ReviewRuns,
        Findings,
        Fixes,
        Suppressions,
        LLMCaches,
        Commands,
        WebhookDeliveries,
        Evidence,
        Feedback,
    )
    assert Evidences is Evidence
    assert Feedbacks is Feedback
    assert FeedbackRecords is Feedback
    assert hasattr(db_module, "Evidences")
    assert hasattr(db_module, "Feedbacks")

