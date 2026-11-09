# tests/test_pr_review_lanes.py — Comprehensive PR Review Lanes & Security Tests
"""
Comprehensive test suite verifying:
1. Base lane lifecycle, statuses ('ran', 'skipped: <reason>', 'failed: <reason>'), durations, versions.
2. L1 Quality adapter (Ruff, ESLint, tsc, mypy, AST checks).
3. L2 Security adapter (Semgrep, local_rules.yaml, Gitleaks, pre-prompt secret redaction).
4. L3 Dependencies adapter (OSV-Scanner, licensing, typosquat heuristics).
5. L7 Performance adapter (N+1 queries, blocking calls in async handlers, unbounded loops/queries).
6. L9 Runtime adapter (mapping routes/traffic/incidents, 'skipped: no runtime data').
7. L10 AI Sanity adapter (hallucinated imports, non-existent methods on types, duplicate blocks).
8. SARIF 2.1.0 Normalizer & stable fingerprint calculation.
9. Citation Filter & Ranker: diff line filtering, evidence requirement, scoring formula, inline capping.
"""

import json
import os
import tempfile
import pytest

from skelion_agent.pr_review_lanes import (
    BaseLane,
    Evidence,
    Finding,
    LaneResult,
    compute_fingerprint,
    DiffParser,
    SarifNormalizer,
    CitationFilterAndRanker,
    filter_and_rank_findings,
    L1QualityLane,
    L2SecurityLane,
    L3DependenciesLane,
    L7PerformanceLane,
    L9RuntimeLane,
    L10AiSanityLane,
    SecretRedactor,
    redact_prompt,
    detect_and_redact_secrets,
    check_typosquatting,
)


# ===========================================================================
# 1. BaseLane Lifecycle & Status Tests
# ===========================================================================

class DummyWorkingLane(BaseLane):
    def __init__(self):
        super().__init__(lane_id="dummy_work", name="Dummy Working Lane", category="quality")

    def get_tool_version(self):
        return "dummy-tool 2.1.0"

    def execute(self, repo_path, diff=None, context=None):
        return [Finding(rule_id="TEST/001", category="quality", title="Test", message="Msg", file_path="a.py", line_number=1, evidence=[Evidence(description="valid")])]


class DummySkippingLane(BaseLane):
    def __init__(self):
        super().__init__(lane_id="dummy_skip", name="Dummy Skipping Lane", category="quality")

    def get_tool_version(self):
        return "dummy-tool 1.0.0"

    def check_prerequisites(self, repo_path, diff=None, context=None):
        return "missing configuration file"

    def execute(self, repo_path, diff=None, context=None):
        return []


class DummyFailingLane(BaseLane):
    def __init__(self):
        super().__init__(lane_id="dummy_fail", name="Dummy Failing Lane", category="quality")

    def get_tool_version(self):
        return "dummy-tool 1.0.0"

    def execute(self, repo_path, diff=None, context=None):
        raise RuntimeError("Fatal tool crash during execution")


def test_base_lane_status_and_lifecycle():
    with tempfile.TemporaryDirectory() as tmpdir:
        # 1. Ran status
        lane_work = DummyWorkingLane()
        res_work = lane_work.run(repo_path=tmpdir)
        assert res_work.status == "ran"
        assert res_work.duration_seconds >= 0.0
        assert res_work.tool_version == "dummy-tool 2.1.0"
        assert len(res_work.findings) == 1

        # 2. Skipped status with reason
        lane_skip = DummySkippingLane()
        res_skip = lane_skip.run(repo_path=tmpdir)
        assert res_skip.status == "skipped: missing configuration file"
        assert res_skip.duration_seconds >= 0.0
        assert len(res_skip.findings) == 0

        # 3. Failed status with reason
        lane_fail = DummyFailingLane()
        res_fail = lane_fail.run(repo_path=tmpdir)
        assert res_fail.status.startswith("failed: Fatal tool crash")
        assert res_fail.duration_seconds >= 0.0
        assert res_fail.error is not None
        assert len(res_fail.findings) == 0


# ===========================================================================
# 2. L1 Quality Adapter Tests
# ===========================================================================

def test_l1_quality_skip_on_unsupported_files():
    lane = L1QualityLane()
    diff = """diff --git a/README.md b/README.md
--- a/README.md
+++ b/README.md
@@ -1,2 +1,3 @@
 # Title
+Some docs update
"""
    with tempfile.TemporaryDirectory() as tmpdir:
        res = lane.run(repo_path=tmpdir, diff=diff)
        assert res.status == "skipped: no supported source files"


def test_l1_quality_detects_mutable_defaults_and_bare_except():
    code = """def bad_function(items=[]):
    try:
        x = items[0]
    except:
        pass
"""
    diff = """diff --git a/app.py b/app.py
--- a/app.py
+++ b/app.py
@@ -1,1 +1,6 @@
+def bad_function(items=[]):
+    try:
+        x = items[0]
+    except:
+        pass
"""
    with tempfile.TemporaryDirectory() as tmpdir:
        app_file = os.path.join(tmpdir, "app.py")
        with open(app_file, "w") as f:
            f.write(code)

        lane = L1QualityLane()
        res = lane.run(repo_path=tmpdir, diff=diff)
        assert res.status == "ran"
        rule_ids = [f.rule_id for f in res.findings]
        assert "RUFF/B006" in rule_ids  # mutable default
        assert "RUFF/E722" in rule_ids  # bare except


# ===========================================================================
# 3. L2 Security Adapter & Local Rules Tests
# ===========================================================================

def test_l2_security_detects_eval_and_sql_injection():
    py_code = """def run_query(user_id):
    eval("malicious_call()")
    session.exec(f"SELECT * FROM users WHERE id = {user_id}")
"""
    diff = """diff --git a/vuln.py b/vuln.py
--- a/vuln.py
+++ b/vuln.py
@@ -1,1 +1,4 @@
+def run_query(user_id):
+    eval("malicious_call()")
+    session.exec(f"SELECT * FROM users WHERE id = {user_id}")
"""
    with tempfile.TemporaryDirectory() as tmpdir:
        vuln_file = os.path.join(tmpdir, "vuln.py")
        with open(vuln_file, "w") as f:
            f.write(py_code)

        lane = L2SecurityLane()
        res = lane.run(repo_path=tmpdir, diff=diff)
        assert res.status == "ran"
        rule_ids = [f.rule_id for f in res.findings]
        assert "semgrep/insecure-exec-eval" in rule_ids
        assert "semgrep/sql-raw-formatting" in rule_ids
        for f in res.findings:
            assert f.category == "security"
            assert f.severity == "critical"
            assert len(f.evidence) >= 1


# ===========================================================================
# 4. Pre-Prompt Secret Detection & Redaction Tests
# ===========================================================================

def test_pre_prompt_secret_redaction_comprehensive():
    raw_prompt = """Review this pull request:
API key: sk-proj-1234567890abcdef1234567890
AWS Key: AKIAIOSFODNN7EXAMPLE
Skelion Live: skl_live_a1b2c3d4e5f6789012345678
GitHub: ghp_123456789012345678901234567890123456
JWT: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgN_secret_signature_test
Private key block:
-----BEGIN RSA PRIVATE KEY-----
MIIEowIBAAKCAQEA0Yk1...
-----END RSA PRIVATE KEY-----
"""
    redacted_text, findings = detect_and_redact_secrets(raw_prompt)

    # 1. No secrets leak into redacted prompt
    assert "sk-proj-1234567890abcdef1234567890" not in redacted_text
    assert "AKIAIOSFODNN7EXAMPLE" not in redacted_text
    assert "skl_live_a1b2c3d4e5f6789012345678" not in redacted_text
    assert "ghp_123456789012345678901234567890123456" not in redacted_text
    assert "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" not in redacted_text
    assert "MIIEowIBAAKCAQEA0Yk1" not in redacted_text

    # 2. Redacted placeholders present
    assert "[REDACTED_API_KEY]" in redacted_text
    assert "[REDACTED_AWS_KEY]" in redacted_text
    assert "[REDACTED_SKELION_KEY]" in redacted_text
    assert "[REDACTED_GITHUB_PAT]" in redacted_text
    assert "[REDACTED_JWT]" in redacted_text
    assert "[REDACTED_PRIVATE_KEY]" in redacted_text

    # 3. Findings generated with critical severity and verifiable evidence
    assert len(findings) >= 5
    for f in findings:
        assert f.severity == "critical"
        assert f.category == "security"
        assert len(f.evidence) >= 1
        assert f.evidence[0].is_verifiable()

    # 4. redact_prompt wrapper returns identical clean text
    assert redact_prompt(raw_prompt) == redacted_text


# ===========================================================================
# 5. L3 Dependencies Adapter Tests (OSV, Typosquats, Licenses)
# ===========================================================================

def test_l3_dependencies_skip_when_no_lockfiles():
    lane = L3DependenciesLane()
    diff = """diff --git a/main.py b/main.py
--- a/main.py
+++ b/main.py
@@ -1,1 +1,2 @@
+print("Hello")
"""
    with tempfile.TemporaryDirectory() as tmpdir:
        res = lane.run(repo_path=tmpdir, diff=diff)
        assert res.status == "skipped: no changed lockfiles or dependencies"


def test_l3_dependencies_detects_vuln_typosquat_and_license():
    req_content = """# Requirements
requests==2.28.0
reqeusts==1.0.0
agpl-service==0.1.0
"""
    diff = """diff --git a/requirements.txt b/requirements.txt
--- a/requirements.txt
+++ b/requirements.txt
@@ -1,1 +1,4 @@
+requests==2.28.0
+reqeusts==1.0.0
+agpl-service==0.1.0
"""
    with tempfile.TemporaryDirectory() as tmpdir:
        req_file = os.path.join(tmpdir, "requirements.txt")
        with open(req_file, "w") as f:
            f.write(req_content)

        lane = L3DependenciesLane()
        res = lane.run(repo_path=tmpdir, diff=diff)
        assert res.status == "ran"
        rule_ids = [f.rule_id for f in res.findings]

        # 1. OSV CVE vulnerability on requests 2.28.0
        assert any("OSV/CVE-2023-32681" in r for r in rule_ids)
        # 2. Typosquat risk on 'reqeusts'
        assert "DEPENDENCY/typosquat-risk" in rule_ids
        # 3. Restrictive AGPL license on 'agpl-service'
        assert "DEPENDENCY/restrictive-license" in rule_ids


def test_check_typosquatting_heuristics():
    # True positives: Levenshtein distance 1 or 2 from popular package
    assert check_typosquatting("reqeusts") == ("requests", 2)
    assert check_typosquatting("lodahs") == ("lodash", 2)
    assert check_typosquatting("colorma") == ("colorama", 1)
    assert check_typosquatting("flsak") == ("flask", 2)

    # Legitimate exact popular package
    assert check_typosquatting("requests") is None
    assert check_typosquatting("flask") is None
    assert check_typosquatting("lodash") is None


# ===========================================================================
# 6. L7 Performance Adapter Tests (N+1, Blocking Async, Unbounded)
# ===========================================================================

def test_l7_performance_detects_n_plus_one_and_blocking_async():
    perf_code = """import time
import requests

async def handle_user_request(user_ids):
    # Blocking calls in async handler
    time.sleep(2)
    resp = requests.get("https://api.example.com")

    # N+1 query in loop
    results = []
    for uid in user_ids:
        user = session.exec(f"SELECT * FROM user WHERE id = {uid}")
        results.append(user)

    # Unbounded loop
    while True:
        pass
"""
    diff = """diff --git a/handler.py b/handler.py
--- a/handler.py
+++ b/handler.py
@@ -1,1 +1,16 @@
+import time
+import requests
+async def handle_user_request(user_ids):
+    time.sleep(2)
+    resp = requests.get("https://api.example.com")
+    results = []
+    for uid in user_ids:
+        user = session.exec(f"SELECT * FROM user WHERE id = {uid}")
+        results.append(user)
+    while True:
+        pass
"""
    with tempfile.TemporaryDirectory() as tmpdir:
        h_file = os.path.join(tmpdir, "handler.py")
        with open(h_file, "w") as f:
            f.write(perf_code)

        lane = L7PerformanceLane()
        res = lane.run(repo_path=tmpdir, diff=diff)
        assert res.status == "ran"
        rule_ids = [f.rule_id for f in res.findings]

        assert "PERF/blocking-call-in-async" in rule_ids
        assert "PERF/n-plus-one-query" in rule_ids
        assert "PERF/unbounded-loop" in rule_ids


# ===========================================================================
# 7. L10 AI Sanity Adapter Tests (Hallucinated Imports, Non-Existent Methods)
# ===========================================================================

def test_l10_ai_sanity_detects_hallucinations_and_bad_methods():
    ai_code = """import json
import imaginary_llm_hyper_package

def process_data(user_text, items_list):
    # Hallucinated JS stringify
    payload = json.stringify({"a": 1})

    # Hallucinated method on list
    d = items_list.to_dict()

    # Hallucinated reverse on str
    rev = user_text.reverse()

    return payload
"""
    diff = """diff --git a/ai_gen.py b/ai_gen.py
--- a/ai_gen.py
+++ b/ai_gen.py
@@ -1,1 +1,15 @@
+import json
+import imaginary_llm_hyper_package
+def process_data(user_text, items_list):
+    payload = json.stringify({"a": 1})
+    d = items_list.to_dict()
+    rev = user_text.reverse()
+    return payload
"""
    with tempfile.TemporaryDirectory() as tmpdir:
        ai_file = os.path.join(tmpdir, "ai_gen.py")
        with open(ai_file, "w") as f:
            f.write(ai_code)

        lane = L10AiSanityLane()
        res = lane.run(repo_path=tmpdir, diff=diff)
        assert res.status == "ran"
        rule_ids = [f.rule_id for f in res.findings]

        assert "AI/hallucinated-import" in rule_ids
        assert "AI/non-existent-method" in rule_ids


# ===========================================================================
# 8. L9 Runtime Adapter Tests ('skipped: no runtime data' & correlation)
# ===========================================================================

def test_l9_runtime_skipped_when_disconnected():
    lane = L9RuntimeLane()
    with tempfile.TemporaryDirectory() as tmpdir:
        # 1. No context at all
        res1 = lane.run(repo_path=tmpdir, diff=None, context=None)
        assert res1.status == "skipped: no runtime data"

        # 2. Context with runtime_connected=False
        res2 = lane.run(repo_path=tmpdir, diff=None, context={"runtime_connected": False})
        assert res2.status == "skipped: no runtime data"


def test_l9_runtime_correlates_symbols_and_boosts_impact():
    route_code = """def stream_chat():
    return "streaming response"
"""
    diff = """diff --git a/chat.py b/chat.py
--- a/chat.py
+++ b/chat.py
@@ -1,1 +1,2 @@
+def stream_chat():
+    return "streaming response"
"""
    context = {
        "runtime_data": {
            "routes": {
                "POST /v1/chat": {
                    "traffic_share": 0.45,
                    "error_spike_rate": 0.08,
                    "symbol_mappings": ["stream_chat"],
                }
            },
            "incidents": [
                {"route_path": "POST /v1/chat", "occurrence_count": 14}
            ],
        }
    }

    with tempfile.TemporaryDirectory() as tmpdir:
        c_file = os.path.join(tmpdir, "chat.py")
        with open(c_file, "w") as f:
            f.write(route_code)

        lane = L9RuntimeLane()
        res = lane.run(repo_path=tmpdir, diff=diff, context=context)
        assert res.status == "ran"
        assert len(res.findings) == 1

        f0 = res.findings[0]
        assert f0.rule_id == "RUNTIME/high-impact-route-modified"
        assert f0.impact_factor > 0.5  # Boosted by high traffic, error spike, and incident
        assert f0.severity in ("high", "critical")
        assert len(f0.evidence) >= 1


# ===========================================================================
# 9. SARIF Normalizer & Stable Fingerprint Tests
# ===========================================================================

def test_sarif_normalizer_generates_valid_findings_and_fingerprints():
    sarif_json = json.dumps({
        "version": "2.1.0",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "Ruff",
                        "version": "0.3.0",
                        "rules": [
                            {
                                "id": "F401",
                                "name": "unused-import",
                                "shortDescription": {"text": "imported but unused"},
                                "defaultConfiguration": {"level": "warning"}
                            }
                        ]
                    }
                },
                "results": [
                    {
                        "ruleId": "F401",
                        "message": {"text": "'os' imported but unused"},
                        "locations": [
                            {
                                "physicalLocation": {
                                    "artifactLocation": {"uri": "src/utils.py"},
                                    "region": {
                                        "startLine": 5,
                                        "startColumn": 1,
                                        "snippet": {"text": "import os"}
                                    }
                                },
                                "logicalLocations": [
                                    {"name": "setup_environment"}
                                ]
                            }
                        ]
                    }
                ]
            }
        ]
    })

    findings = SarifNormalizer.normalize(sarif_json, default_category="quality")
    assert len(findings) == 1
    f = findings[0]

    assert f.rule_id == "RUFF/F401"
    assert f.file_path == "src/utils.py"
    assert f.line_number == 5
    assert f.severity == "medium"
    assert f.enclosing_symbol == "setup_environment"
    assert f.fingerprint != ""

    # Verify stable fingerprint calculation
    expected_fp = compute_fingerprint(
        rule_id_or_category="RUFF/F401",
        normalized_code_snippet="import os",
        enclosing_symbol="setup_environment",
        file_path="src/utils.py",
    )
    assert f.fingerprint == expected_fp


def test_stable_fingerprint_normalization_determinism():
    # Variations in whitespace and path slashes must yield exact same fingerprint
    fp1 = compute_fingerprint(
        rule_id_or_category="RUFF/B006",
        normalized_code_snippet="def foo(a=[]): pass",
        enclosing_symbol="foo",
        file_path="src/app.py",
    )
    fp2 = compute_fingerprint(
        rule_id_or_category="RUFF/B006",
        normalized_code_snippet="   def   foo(a=[]): \n   pass  ",
        enclosing_symbol="foo",
        file_path="src\\app.py",
    )
    assert fp1 == fp2


# ===========================================================================
# 10. Citation Filter & Ranker Tests (Diff, Evidence, Scoring, Capping)
# ===========================================================================

def test_citation_filter_drops_findings_outside_diff():
    diff = """diff --git a/service.py b/service.py
--- a/service.py
+++ b/service.py
@@ -10,3 +10,4 @@ def existing_method():
 context line
+added line at 11
+added line at 12
 context line
"""
    f_inside = Finding(
        rule_id="RULE/INSIDE",
        category="quality",
        file_path="service.py",
        line_number=11,
        evidence=[Evidence(description="Found in diff line 11", snippet="added line at 11")],
    )
    f_outside = Finding(
        rule_id="RULE/OUTSIDE",
        category="quality",
        file_path="service.py",
        line_number=2,  # Line 2 was NOT modified
        evidence=[Evidence(description="Found in line 2", snippet="old line")],
    )
    f_other_file = Finding(
        rule_id="RULE/OTHER_FILE",
        category="quality",
        file_path="unrelated.py",
        line_number=11,
        evidence=[Evidence(description="Found in unrelated file")],
    )

    result = filter_and_rank_findings([f_inside, f_outside, f_other_file], diff_text=diff)

    assert result.total_input_count == 3
    assert result.total_surviving_count == 1
    assert result.dropped_out_of_diff_count == 2
    assert result.inline_findings[0].rule_id == "RULE/INSIDE"


def test_citation_filter_drops_findings_lacking_verifiable_evidence():
    diff = """diff --git a/test.py b/test.py
--- a/test.py
+++ b/test.py
@@ -1,1 +1,3 @@
+line 1
+line 2
"""
    f_with_evidence = Finding(
        rule_id="VALID/01",
        category="security",
        file_path="test.py",
        line_number=1,
        evidence=[Evidence(type="ast", description="Non-empty AST evidence", snippet="line 1")],
    )
    f_empty_evidence = Finding(
        rule_id="INVALID/01",
        category="security",
        file_path="test.py",
        line_number=2,
        evidence=[],  # No evidence
    )
    f_blank_evidence = Finding(
        rule_id="INVALID/02",
        category="security",
        file_path="test.py",
        line_number=2,
        evidence=[Evidence(description="   ")],  # Blank description
    )

    result = filter_and_rank_findings([f_with_evidence, f_empty_evidence, f_blank_evidence], diff_text=diff)

    assert result.total_surviving_count == 1
    assert result.dropped_no_evidence_count == 2
    assert result.inline_findings[0].rule_id == "VALID/01"


def test_scoring_and_ranking_formula_descending():
    # score = severity_weight * confidence * (1 + impact_factor) * evidence_strength
    # Critical (weight 5.0), conf 1.0, impact 0.5, ev_str 1.0 => 5.0 * 1.0 * 1.5 * 1.0 = 7.5
    f_critical = Finding(
        rule_id="CRIT/01",
        category="security",
        severity="critical",
        confidence=1.0,
        impact_factor=0.5,
        evidence_strength=1.0,
        evidence=[Evidence(description="Crit evidence")],
    )
    # High (weight 4.0), conf 1.0, impact 0.0, ev_str 1.0 => 4.0 * 1.0 * 1.0 * 1.0 = 4.0
    f_high = Finding(
        rule_id="HIGH/01",
        category="quality",
        severity="high",
        confidence=1.0,
        impact_factor=0.0,
        evidence_strength=1.0,
        evidence=[Evidence(description="High evidence")],
    )
    # Low (weight 2.0), conf 0.5, impact 0.0, ev_str 1.0 => 2.0 * 0.5 * 1.0 * 1.0 = 1.0
    f_low = Finding(
        rule_id="LOW/01",
        category="quality",
        severity="low",
        confidence=0.5,
        impact_factor=0.0,
        evidence_strength=1.0,
        evidence=[Evidence(description="Low evidence")],
    )

    ranker = CitationFilterAndRanker(max_inline=10)
    result = ranker.filter_and_rank([f_low, f_critical, f_high], diff_text=None)

    assert result.total_surviving_count == 3
    # Check exact score calculation
    assert pytest.approx(result.all_ranked_findings[0].score, 0.01) == 7.5
    assert pytest.approx(result.all_ranked_findings[1].score, 0.01) == 4.0
    assert pytest.approx(result.all_ranked_findings[2].score, 0.01) == 1.0

    # Sorted descending by score
    assert result.all_ranked_findings[0].rule_id == "CRIT/01"
    assert result.all_ranked_findings[1].rule_id == "HIGH/01"
    assert result.all_ranked_findings[2].rule_id == "LOW/01"


def test_inline_cap_maximum_10_overflow_to_summary():
    # Create 14 valid findings with different scores
    findings = []
    for i in range(14):
        f = Finding(
            rule_id=f"RULE/{i:02d}",
            category="quality",
            severity="medium",
            confidence=1.0,
            evidence_strength=1.0,
            impact_factor=float(i) * 0.1,  # higher i gets higher score
            evidence=[Evidence(description=f"Evidence {i}")],
        )
        findings.append(f)

    # Filter and rank with default max_inline=10
    result = filter_and_rank_findings(findings, diff_text=None, max_inline=10)

    assert result.total_surviving_count == 14
    assert len(result.inline_findings) == 10
    assert len(result.summary_findings) == 4

    # Top 10 have is_inline=True, overflowed_to_summary=False
    for f in result.inline_findings:
        assert f.is_inline is True
        assert f.overflowed_to_summary is False

    # Remaining 4 have is_inline=False, overflowed_to_summary=True
    for f in result.summary_findings:
        assert f.is_inline is False
        assert f.overflowed_to_summary is True

    # Test custom max_inline=3
    result_cap3 = filter_and_rank_findings(findings, diff_text=None, max_inline=3)
    assert len(result_cap3.inline_findings) == 3
    assert len(result_cap3.summary_findings) == 11


# ===========================================================================
# 11. Edge Cases & Boundary Tests
# ===========================================================================

def test_diff_parser_deletions_only():
    del_diff = """diff --git a/deleted.py b/deleted.py
--- a/deleted.py
+++ b/deleted.py
@@ -1,5 +1,0 @@
-line 1
-line 2
-line 3
-line 4
-line 5
"""
    parsed = DiffParser.parse(del_diff)
    assert "deleted.py" in parsed
    assert len(parsed["deleted.py"]) == 0  # No lines added

    # Finding on line 1 should be dropped since line was only deleted
    f = Finding(
        rule_id="RULE/DEL",
        category="quality",
        file_path="deleted.py",
        line_number=1,
        evidence=[Evidence(description="line 1")],
    )
    res = filter_and_rank_findings([f], diff_text=del_diff)
    assert res.total_surviving_count == 0
    assert res.dropped_out_of_diff_count == 1


def test_diff_parser_multiple_hunks_and_files():
    multi_diff = """diff --git a/src/a.py b/src/a.py
--- a/src/a.py
+++ b/src/a.py
@@ -5,2 +5,3 @@
 ctx
+new line 6
 ctx
@@ -20,2 +21,3 @@
 ctx
+new line 22
 ctx
diff --git a/src/b.py b/src/b.py
--- a/src/b.py
+++ b/src/b.py
@@ -1,2 +1,3 @@
+new line 1 in b
 ctx
"""
    parsed = DiffParser.parse(multi_diff)
    assert parsed["src/a.py"] == {6, 22}
    assert parsed["src/b.py"] == {1}


def test_sarif_normalizer_malformed_and_empty():
    # Empty string
    assert SarifNormalizer.normalize("") == []
    # Invalid JSON
    assert SarifNormalizer.normalize("{not valid json") == []
    # Empty run
    assert SarifNormalizer.normalize({"runs": []}) == []
    # Run without results
    assert SarifNormalizer.normalize({"runs": [{"tool": {"driver": {"name": "EmptyTool"}}}]}) == []
    # Malformed result without locations
    malformed_sarif = {
        "runs": [
            {
                "tool": {"driver": {"name": "TestTool"}},
                "results": [
                    {"ruleId": "TEST_NO_LOC", "message": {"text": "No location"}}
                ]
            }
        ]
    }
    findings = SarifNormalizer.normalize(malformed_sarif)
    assert len(findings) == 1
    assert findings[0].rule_id == "TEST_NO_LOC"
    assert findings[0].file_path == ""
    assert findings[0].line_number is None


def test_unbounded_query_bounded_vs_unbounded():
    code = """def fetch_users():
    # Bounded query
    u1 = session.exec(select(User).limit(10)).all()
    # Unbounded query
    u2 = session.exec(select(User)).all()
"""
    lane = L7PerformanceLane()
    with tempfile.TemporaryDirectory() as tmpdir:
        fpath = os.path.join(tmpdir, "queries.py")
        with open(fpath, "w") as f:
            f.write(code)

        diff = """diff --git a/queries.py b/queries.py
--- a/queries.py
+++ b/queries.py
@@ -1,1 +1,5 @@
+def fetch_users():
+    u1 = session.exec(select(User).limit(10)).all()
+    u2 = session.exec(select(User)).all()
"""
        res = lane.run(repo_path=tmpdir, diff=diff)
        assert res.status == "ran"
        unbounded_findings = [f for f in res.findings if f.rule_id == "PERF/unbounded-query"]
        assert len(unbounded_findings) == 1
        assert "limit(10)" not in unbounded_findings[0].code_snippet


def test_fingerprint_uniqueness_across_different_rules():
    fp_rule1 = compute_fingerprint("RULE_A", "snippet", "my_func", "a.py")
    fp_rule2 = compute_fingerprint("RULE_B", "snippet", "my_func", "a.py")
    fp_sym1 = compute_fingerprint("RULE_A", "snippet", "other_func", "a.py")
    fp_file1 = compute_fingerprint("RULE_A", "snippet", "my_func", "b.py")

    assert fp_rule1 != fp_rule2
    assert fp_rule1 != fp_sym1
    assert fp_rule1 != fp_file1


def test_custom_severity_weights_ranking():
    custom_weights = {"critical": 100.0, "high": 50.0, "medium": 10.0, "low": 1.0}
    f1 = Finding(rule_id="R1", category="quality", severity="critical", evidence=[Evidence(description="e1")])
    f2 = Finding(rule_id="R2", category="quality", severity="low", evidence=[Evidence(description="e2")])

    ranker = CitationFilterAndRanker(max_inline=10, severity_weights=custom_weights)
    res = ranker.filter_and_rank([f2, f1], diff_text=None)

    assert res.all_ranked_findings[0].rule_id == "R1"
    assert res.all_ranked_findings[0].score == 100.0
    assert res.all_ranked_findings[1].rule_id == "R2"
    assert res.all_ranked_findings[1].score == 1.0

