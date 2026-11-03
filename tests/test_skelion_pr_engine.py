# tests/test_skelion_pr_engine.py — Tests for Skelion Autonomous PR Engine
import pytest
from fastapi.testclient import TestClient
from fastapi import FastAPI
from skelion_agent.github_pr_engine import SkelionPREngine
from skelion_agent.pr_comment_bot import router

app = FastAPI()
app.include_router(router)
client = TestClient(app)


def test_skelion_pr_engine_initialization():
    engine = SkelionPREngine()
    assert engine.repo == "Aditya-9-6/Skelion"
    assert engine.author_name == "Dahale Aditya Dnyaneshwar"
    assert engine.author_email == "adityadahale96@gmail.com"


def test_skelion_pr_engine_jules_timeline(monkeypatch):
    engine = SkelionPREngine()

    # Mock _request to return clean PR and check data
    def mock_request(endpoint, method="GET", data=None):
        if "check-runs" in endpoint:
            return 200, {
                "total_count": 4,
                "check_runs": [
                    {"name": "build", "status": "completed", "conclusion": "success"},
                    {"name": "test-unit", "status": "completed", "conclusion": "success"},
                    {"name": "lint", "status": "in_progress"},
                    {"name": "typecheck", "status": "queued"}
                ]
            }
        elif "comments" in endpoint:
            return 200, [
                {"id": 1, "body": "Please add docstring", "path": "p2p/congestion.py", "line": 260, "user": {"login": "reviewer"}}
            ]
        elif "pulls" in endpoint:
            return 200, {
                "number": 190,
                "head": {"sha": "c8d914ff"},
                "mergeable": True,
                "mergeable_state": "clean"
            }
        return 404, {}

    monkeypatch.setattr(engine, "_request", mock_request)

    timeline = engine.get_jules_timeline(190)
    assert timeline["pr_number"] == 190
    assert len(timeline["stages"]) == 5

    stages = {s["id"]: s for s in timeline["stages"]}
    assert stages["branch_created"]["status"] == "done"
    assert stages["ci_checks"]["status"] == "running"
    assert "2/4" in stages["ci_checks"]["detail"]
    assert stages["merge_conflicts"]["status"] == "done"
    assert stages["review_comments"]["status"] == "running"
    assert stages["ready_to_merge"]["status"] == "pending"


def test_skelion_pr_engine_ready_to_merge(monkeypatch):
    engine = SkelionPREngine()

    def mock_request(endpoint, method="GET", data=None):
        if "check-runs" in endpoint:
            return 200, {
                "total_count": 2,
                "check_runs": [
                    {"name": "build", "status": "completed", "conclusion": "success"},
                    {"name": "test", "status": "completed", "conclusion": "success"}
                ]
            }
        elif "comments" in endpoint:
            return 200, []
        elif "pulls" in endpoint:
            return 200, {
                "number": 190,
                "head": {"sha": "c8d914ff"},
                "mergeable": True,
                "mergeable_state": "clean"
            }
        return 404, {}

    monkeypatch.setattr(engine, "_request", mock_request)

    timeline = engine.get_jules_timeline(190)
    assert timeline["is_ready_to_merge"] is True
    stages = {s["id"]: s for s in timeline["stages"]}
    assert stages["ci_checks"]["status"] == "done"
    assert stages["merge_conflicts"]["status"] == "done"
    assert stages["review_comments"]["status"] == "done"
    assert stages["ready_to_merge"]["status"] == "done"


def test_pr_timeline_api_endpoints(monkeypatch):
    # Mock engine inside endpoint
    mock_timeline = {
        "pr_number": 190,
        "repo": "Aditya-9-6/Skelion",
        "stages": [
            {"id": "branch_created", "label": "PR Branch Created", "status": "done", "detail": "open"},
            {"id": "ci_checks", "label": "CI / GitHub Actions Checks", "status": "done", "detail": "passed"},
            {"id": "merge_conflicts", "label": "Merge Conflict Verification", "status": "done", "detail": "clean"},
            {"id": "review_comments", "label": "Review Feedback Ingestion", "status": "done", "detail": "clean"},
            {"id": "ready_to_merge", "label": "Merge Readiness", "status": "done", "detail": "ready"}
        ],
        "is_ready_to_merge": True
    }

    monkeypatch.setattr(
        SkelionPREngine,
        "get_jules_timeline",
        lambda self, pr: mock_timeline
    )
    monkeypatch.setattr(
        SkelionPREngine,
        "run_autonomous_cycle",
        lambda self, pr: {"pr_number": pr, "timeline": mock_timeline, "actions_taken": []}
    )

    res = client.get("/v1/github/pr-timeline/190")
    assert res.status_code == 200
    data = res.json()
    assert data["pr_number"] == 190
    assert len(data["stages"]) == 5
    assert data["is_ready_to_merge"] is True

    post_res = client.post("/v1/github/pr-cycle/190")
    assert post_res.status_code == 200
    cycle_data = post_res.json()
    assert cycle_data["pr_number"] == 190
    assert "timeline" in cycle_data


def test_skelion_pr_engine_merge_pr(monkeypatch):
    engine = SkelionPREngine()

    def mock_request(endpoint, method="GET", data=None):
        if "merge" in endpoint and method == "PUT":
            return 200, {
                "sha": "9fdc9432e6321d6102ddc66c3d305d785cbfacbf",
                "merged": True,
                "message": "Pull Request successfully merged"
            }
        return 404, {}

    monkeypatch.setattr(engine, "_request", mock_request)

    res = engine.merge_pr(190, commit_title="Merge PR #190", commit_message="Merged cleanly")
    assert res["status"] == "ok"
    assert res["merged"] is True
    assert res["sha"] == "9fdc9432e6321d6102ddc66c3d305d785cbfacbf"

    # Test the API endpoint
    monkeypatch.setattr(SkelionPREngine, "merge_pr", lambda self, pr, commit_title=None, commit_message=None, merge_method="merge": {
        "status": "ok",
        "merged": True,
        "sha": "9fdc9432e6321d6102ddc66c3d305d785cbfacbf",
        "message": "Pull Request successfully merged"
    })

    api_res = client.post("/v1/github/pr-merge/190", json={"commit_title": "Merge PR #190"})
    assert api_res.status_code == 200
    assert api_res.json()["merged"] is True


def test_skelion_pr_engine_autonomous_repair_cycle(monkeypatch):
    engine = SkelionPREngine()
    replies_posted = []

    def mock_request(endpoint, method="GET", data=None):
        if "check-runs" in endpoint:
            return 200, {
                "total_count": 2,
                "check_runs": [
                    {"name": "build", "status": "completed", "conclusion": "failure"},
                    {"name": "test", "status": "completed", "conclusion": "success"}
                ]
            }
        elif "comments" in endpoint and method == "GET":
            return 200, [
                {"id": 42, "body": "Handle negative rate limit window", "path": "p2p/congestion.py", "line": 150, "user": {"login": "architect"}}
            ]
        elif "replies" in endpoint or ("comments" in endpoint and method == "POST"):
            replies_posted.append(data)
            return 201, {"id": 99, "body": data.get("body", "")}
        elif "pulls" in endpoint and method == "GET":
            return 200, {
                "number": 190,
                "head": {"sha": "c8d914ff"},
                "mergeable": True,
                "mergeable_state": "clean"
            }
        return 200, {}

    monkeypatch.setattr(engine, "_request", mock_request)

    cycle_res = engine.run_autonomous_cycle(190, auto_reply_comments=True)
    assert cycle_res["pr_number"] == 190
    assert len(cycle_res["actions_taken"]) >= 2
    assert any("CI repair analysis triggered" in act for act in cycle_res["actions_taken"])
    assert any("Scanned 1 review comments" in act for act in cycle_res["actions_taken"])
    assert any("Replied to review thread #42" in act for act in cycle_res["actions_taken"])
    assert len(replies_posted) == 1
    assert "Replay Sandbox: 120/120 transactions" in replies_posted[0]["body"]
