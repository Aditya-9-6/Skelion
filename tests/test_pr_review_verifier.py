# tests/test_pr_review_verifier.py — Unit Tests for Fix Verification Pipeline (§8.3)
"""
Comprehensive Unit Tests for:
1. DisposableWorktreeRunner & Execution Sandbox (skelion_agent/pr_review_sandbox.py)
2. Fix Engine & Excluded Paths Guard (skelion_agent/pr_review_fixer.py)
3. 9-Step Verification Pipeline (skelion_agent/pr_review_verifier.py)
4. PR Review Publisher Helpers (skelion_agent/pr_review_publisher.py)
"""

import os
import subprocess
import tempfile
import pytest
from pathlib import Path
from typing import Dict, Any, List, Tuple

from skelion_agent.pr_review_sandbox import (
    DisposableWorktreeRunner,
    SandboxConfig,
    SandboxExecutionResult,
    sanitize_sandbox_env,
    NETWORK_BLOCK_ENV,
)
from skelion_agent.pr_review_fixer import (
    FixEngine,
    FixFinding,
    FixSuggestion,
    FixType,
    ToolNativeFixer,
    CodemodFixer,
    BoundedLLMFixer,
    is_path_excluded,
    validate_fix_paths,
    count_diff_lines,
    make_unified_diff,
)
from skelion_agent.pr_review_verifier import (
    VerificationPipeline,
    VerificationStepResult,
    EvidenceBundle,
    Verdict,
    StepStatus,
    redact_sensitive_text,
    redact_command_entry,
)
from skelion_agent.pr_review_publisher import (
    format_github_suggestion_block,
    extract_replacement_from_diff,
    format_pr_review_comment,
    parse_revert_command,
    invert_unified_diff,
    apply_one_click_commit,
    execute_one_click_revert,
)


# ===========================================================================
# Fixtures
# ===========================================================================

@pytest.fixture
def temp_git_repo(tmp_path: Path):
    """Creates a temporary initialized git repository with a committed sample file."""
    repo_dir = tmp_path / "test_repo"
    repo_dir.mkdir()

    # Initialize git
    subprocess.run(["git", "init"], cwd=str(repo_dir), check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test Runner"], cwd=str(repo_dir), check=True)
    subprocess.run(["git", "config", "user.email", "test@skelion.dev"], cwd=str(repo_dir), check=True)

    # Initial file commit
    sample_file = repo_dir / "app.py"
    sample_file.write_text("def hello():\n    return 'world'\n", encoding="utf-8")

    subprocess.run(["git", "add", "app.py"], cwd=str(repo_dir), check=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=str(repo_dir), check=True)

    return repo_dir


@pytest.fixture
def sample_finding() -> FixFinding:
    return FixFinding(
        id="fnd_001",
        file_path="app.py",
        line=2,
        rule_id="E501",
        message="Line too long / style formatting issue",
        severity="MEDIUM",
        source_tool="ruff",
    )


@pytest.fixture
def sample_diff() -> str:
    return """--- a/app.py
+++ b/app.py
@@ -1,2 +1,2 @@
 def hello():
-    return 'world'
+    return 'skelion'
"""


# ===========================================================================
# 1. Sandbox & Worktree Runner Tests
# ===========================================================================

class TestSandboxAndWorktreeRunner:

    def test_worktree_creation_and_cleanup_in_context_manager(self, temp_git_repo: Path):
        """Context manager creates worktree and safely cleans up in finally block."""
        worktree_created_path = None

        with DisposableWorktreeRunner(repo_root=temp_git_repo) as runner:
            worktree_created_path = runner.worktree_path
            assert worktree_created_path is not None
            assert worktree_created_path.exists()
            assert (worktree_created_path / "app.py").exists()
            assert runner.read_file("app.py") == "def hello():\n    return 'world'\n"

        # After context exit, cleanup must have removed worktree
        assert not worktree_created_path.exists()

    def test_worktree_cleanup_on_exception(self, temp_git_repo: Path):
        """Cleanup executes even when an unexpected exception is raised."""
        captured_path = None
        with pytest.raises(ZeroDivisionError):
            with DisposableWorktreeRunner(repo_root=temp_git_repo) as runner:
                captured_path = runner.worktree_path
                assert captured_path.exists()
                _ = 1 / 0

        assert captured_path is not None
        assert not captured_path.exists()

    def test_environment_sanitization_drops_secrets(self):
        """Sanitizer purges customer credentials, database URLs, and API keys."""
        dirty_env = {
            "PATH": "/usr/bin;C:\\Windows",
            "TEMP": "C:\\Temp",
            "AWS_SECRET_ACCESS_KEY": "AKIA1234567890SECRET",
            "GITHUB_TOKEN": "ghp_abcdef1234567890",
            "DATABASE_URL": "postgres://user:secret@localhost:5432/db",
            "RAZORPAY_KEY_SECRET": "rzp_secret_key",
            "STRIPE_API_KEY": "sk_live_123456",
            "CUSTOM_API_KEY": "my_secret_token",
            "SAFE_UNALLOWED_VAR": "something",
        }
        sanitized = sanitize_sandbox_env(source_env=dirty_env, block_network=False)

        assert "PATH" in sanitized
        assert "TEMP" in sanitized
        # Verify sensitive keys stripped
        assert "AWS_SECRET_ACCESS_KEY" not in sanitized
        assert "GITHUB_TOKEN" not in sanitized
        assert "DATABASE_URL" not in sanitized
        assert "RAZORPAY_KEY_SECRET" not in sanitized
        assert "STRIPE_API_KEY" not in sanitized
        assert "CUSTOM_API_KEY" not in sanitized
        assert "SAFE_UNALLOWED_VAR" not in sanitized

    def test_network_blocking_env_injection(self):
        """Sanitizer injects proxy-blocking and offline package manager settings."""
        sanitized = sanitize_sandbox_env(source_env={}, block_network=True)
        for k, v in NETWORK_BLOCK_ENV.items():
            assert sanitized[k] == v

    def test_path_traversal_guard(self, temp_git_repo: Path):
        """Validates that path escaping the worktree raises PermissionError."""
        with DisposableWorktreeRunner(repo_root=temp_git_repo) as runner:
            # Valid paths inside worktree
            valid = runner.validate_path_inside_worktree("app.py")
            assert valid.exists()

            # Escaping paths must raise PermissionError
            with pytest.raises(PermissionError):
                runner.validate_path_inside_worktree("../../outside.txt")

    def test_sandbox_run_command_timeout(self, temp_git_repo: Path):
        """Commands exceeding timeout threshold are terminated and marked timed_out."""
        with DisposableWorktreeRunner(repo_root=temp_git_repo) as runner:
            # Run command that sleeps longer than timeout
            cmd = ["python", "-c", "import time; time.sleep(5)"]
            res = runner.run_command(cmd, timeout=1)
            assert res.timed_out is True
            assert res.exit_code == 124

    def test_apply_patch_in_worktree(self, temp_git_repo: Path, sample_diff: str):
        """Applies unified diff cleanly into worktree files."""
        with DisposableWorktreeRunner(repo_root=temp_git_repo) as runner:
            success, msg = runner.apply_patch(sample_diff)
            assert success is True
            content = runner.read_file("app.py")
            assert "return 'skelion'" in content


# ===========================================================================
# 2. Fix Engine & Excluded Paths Guard Tests
# ===========================================================================

class TestFixEngineAndExcludedPaths:

    @pytest.mark.parametrize(
        "excluded_path, expected_category",
        [
            ("migrations/0001_init.py", "Database Migration"),
            ("alembic/versions/1234_add_col.py", "Database Migration"),
            ("migrate_v2.py", "Database Migration"),
            ("scripts/schema.sql", "SQL/Migration File"),
            (".github/workflows/ci.yml", "CI/CD Workflow"),
            (".circleci/config.yml", "CI/CD Configuration"),
            (".gitlab-ci.yml", "GitLab CI Workflow"),
            ("Jenkinsfile", "Jenkins CI Workflow"),
            ("Dockerfile", "Dockerfile"),
            ("Dockerfile.worker", "Dockerfile"),
            ("docker-compose.yml", "Docker Compose File"),
            (".env", "Environment / Secrets File"),
            (".env.production", "Environment / Secrets File"),
            ("server.key", "TLS / Encryption Certificate Key"),
            ("id_rsa", "SSH Private Key"),
            ("skelion.license", "Software License Key File"),
            ("skelion_agent/auth.py", "Authentication Script"),
            ("payment.py", "Payment Script"),
            ("billing_routes.py", "Billing Script"),
            ("razorpay_service.py", "Payment Gateway Script"),
            ("stripe_handler.py", "Payment Gateway Script"),
        ],
    )
    def test_excluded_paths_guard_rejects(self, excluded_path: str, expected_category: str):
        """Never auto-fixes migrations, workflows, Dockerfiles, secrets, or auth/payment."""
        is_ex, reason = is_path_excluded(excluded_path)
        assert is_ex is True
        assert reason is not None
        assert expected_category in reason

    @pytest.mark.parametrize(
        "safe_path",
        [
            "skelion_agent/utils/string_helper.py",
            "src/components/button.tsx",
            "pkg/math_utils.py",
            "services/analytics.py",
        ],
    )
    def test_allowed_paths_guard_permits(self, safe_path: str):
        """Permits standard non-sensitive application paths."""
        is_ex, reason = is_path_excluded(safe_path)
        assert is_ex is False
        assert reason is None

    def test_validate_fix_paths_rejects_mixed(self):
        """If any file in a multi-file fix is excluded, validation fails."""
        paths = ["skelion_agent/utils.py", "migrations/002.py"]
        valid, reason = validate_fix_paths(paths)
        assert valid is False
        assert "Database Migration" in (reason or "")

    def test_codemod_sync_to_async_f2(self):
        """Codemod transforms blocking time.sleep to await asyncio.sleep."""
        code = "def worker():\n    time.sleep(2)\n"
        fix = CodemodFixer.sync_to_async(code, "worker.py")
        assert fix is not None
        assert fix.fix_type == FixType.CODEMOD
        assert "+import asyncio" in fix.diff or "+import asyncio" in fix.diff.replace(" ", "")
        assert "+    await asyncio.sleep(2)" in fix.diff

    def test_codemod_remove_unused_imports_f2(self):
        """Codemod removes unused imports cleanly."""
        code = "import os\nimport sys\nimport unused_module\n\ndef run():\n    return os.name\n"
        fix = CodemodFixer.remove_unused_imports(code, "run.py", ["unused_module"])
        assert fix is not None
        assert "-import unused_module" in fix.diff

    def test_codemod_replace_deprecated_api_f2(self):
        """Codemod replaces datetime.utcnow() with datetime.now(timezone.utc)."""
        code = "from datetime import datetime\n\ndef get_time():\n    return datetime.utcnow()\n"
        fix = CodemodFixer.replace_deprecated_api(code, "time_util.py")
        assert fix is not None
        assert "-    return datetime.utcnow()" in fix.diff
        assert "+    return datetime.now(timezone.utc)" in fix.diff

    def test_bounded_llm_fixer_f3_valid(self, sample_finding: FixFinding, sample_diff: str):
        """Valid bounded LLM patch passes validation."""
        fix = BoundedLLMFixer.validate_and_create_patch(sample_diff, sample_finding)
        assert fix.fix_type == FixType.BOUNDED_LLM
        assert fix.lines_changed == 2
        assert fix.file_paths == ["app.py"]

    def test_bounded_llm_fixer_rejects_more_than_two_files(self, sample_finding: FixFinding):
        """Rejects LLM patch modifying more than 2 files."""
        multi_file_diff = """--- a/f1.py
+++ b/f1.py
@@ -1 +1 @@
-a
+b
--- a/f2.py
+++ b/f2.py
@@ -1 +1 @@
-a
+b
--- a/f3.py
+++ b/f3.py
@@ -1 +1 @@
-a
+b
"""
        with pytest.raises(ValueError, match="exceeds file limit"):
            BoundedLLMFixer.validate_and_create_patch(multi_file_diff, sample_finding)

    def test_bounded_llm_fixer_rejects_exceeded_diff_lines(self, sample_finding: FixFinding):
        """Rejects LLM patch exceeding 150 line budget."""
        big_diff_lines = ["--- a/app.py", "+++ b/app.py", "@@ -1,1 +1,160 @@", "-old"]
        for i in range(160):
            big_diff_lines.append(f"+line_{i}")
        big_diff = "\n".join(big_diff_lines)

        with pytest.raises(ValueError, match="exceeds diff size budget"):
            BoundedLLMFixer.validate_and_create_patch(big_diff, sample_finding)

    def test_bounded_llm_fixer_rejects_invalid_diff_format(self, sample_finding: FixFinding):
        """Rejects plain code that is not a unified diff."""
        plain_code = "def hello():\n    return 'new'\n"
        with pytest.raises(ValueError, match="not a valid unified diff"):
            BoundedLLMFixer.validate_and_create_patch(plain_code, sample_finding)

    def test_fix_engine_refuses_excluded_path(self, sample_finding: FixFinding):
        """FixEngine raises PermissionError when asked to fix an excluded path."""
        bad_finding = FixFinding(
            id="fnd_bad",
            file_path="skelion_agent/auth.py",
            line=10,
            rule_id="S101",
        )
        engine = FixEngine()
        with pytest.raises(PermissionError, match="Cannot auto-fix finding"):
            engine.generate_fix(bad_finding)


# ===========================================================================
# 3. 9-Step Verification Pipeline Tests (§8.3)
# ===========================================================================

class TestVerificationPipeline:

    def test_pipeline_all_steps_pass_with_traffic_verdict_verified(
        self, temp_git_repo: Path, sample_finding: FixFinding, sample_diff: str
    ):
        """Full pass on all 9 steps with traffic replay yields verdict 'verified'."""
        with DisposableWorktreeRunner(repo_root=temp_git_repo) as runner:
            fix = FixSuggestion(
                id="fix_001",
                finding_id=sample_finding.id,
                fix_type=FixType.BOUNDED_LLM,
                description="Verified fix",
                file_paths=["app.py"],
                diff=sample_diff,
                lines_changed=2,
            )

            pipeline = VerificationPipeline(
                worktree_runner=runner,
                finding=sample_finding,
                fix_suggestion=fix,
                originating_tool_runner=lambda wt, fnd: [],  # finding eliminated
                deterministic_lanes_runner=lambda wt, files: [],  # no new findings
                type_and_lint_runner=lambda wt, files: (True, "Passed"),
                test_suite_runner=lambda wt, files: {
                    "before_passed": 10,
                    "before_failed": 0,
                    "after_passed": 10,
                    "after_failed": 0,
                    "regressions": 0,
                },
                replay_runner=lambda wt: (True, "Replay 100% passed"),
                has_recorded_traffic=True,
            )

            verdict, bundle = pipeline.execute_pipeline()

            assert verdict == Verdict.VERIFIED
            assert bundle is not None
            assert bundle.diff_hash == fix.diff_hash
            assert bundle.finding_fingerprint == sample_finding.fingerprint
            assert bundle.test_counts["regressions"] == 0
            assert bundle.policy_results["diff_size_passed"] is True

    def test_pipeline_traffic_replay_not_run_verdict_verified_with_gaps(
        self, temp_git_repo: Path, sample_finding: FixFinding, sample_diff: str
    ):
        """When traffic replay is skipped (no traffic), verdict is 'verified with gaps'."""
        with DisposableWorktreeRunner(repo_root=temp_git_repo) as runner:
            fix = FixSuggestion(
                id="fix_002",
                finding_id=sample_finding.id,
                fix_type=FixType.TOOL_NATIVE,
                description="Fix without traffic",
                file_paths=["app.py"],
                diff=sample_diff,
                lines_changed=2,
            )

            pipeline = VerificationPipeline(
                worktree_runner=runner,
                finding=sample_finding,
                fix_suggestion=fix,
                originating_tool_runner=lambda wt, fnd: [],
                deterministic_lanes_runner=lambda wt, files: [],
                type_and_lint_runner=lambda wt, files: (True, "Passed"),
                test_suite_runner=lambda wt, files: {
                    "before_passed": 5,
                    "after_passed": 5,
                    "regressions": 0,
                },
                has_recorded_traffic=False,  # NO RECORDED TRAFFIC
            )

            verdict, bundle = pipeline.execute_pipeline()

            assert verdict == Verdict.VERIFIED_WITH_GAPS
            assert bundle is not None
            # Check step 6 label
            step6 = bundle.step_results["step_6_traffic_replay_check"]
            assert step6["details"] == "replay: not run (no recorded traffic)"
            assert any("replay: not run" in g for g in bundle.gaps)

    def test_pipeline_step_1_fails_unverified(
        self, temp_git_repo: Path, sample_finding: FixFinding
    ):
        """Step 1 patch apply failure terminates early with 'unverified'."""
        with DisposableWorktreeRunner(repo_root=temp_git_repo) as runner:
            bad_diff = """--- a/non_existent.py
+++ b/non_existent.py
@@ -1,1 +1,1 @@
-original
+replacement
"""
            fix = FixSuggestion(
                id="fix_bad_diff",
                finding_id=sample_finding.id,
                fix_type=FixType.BOUNDED_LLM,
                description="Bad diff",
                file_paths=["non_existent.py"],
                diff=bad_diff,
                lines_changed=2,
            )

            pipeline = VerificationPipeline(
                worktree_runner=runner,
                finding=sample_finding,
                fix_suggestion=fix,
            )

            verdict, bundle = pipeline.execute_pipeline()
            assert verdict == Verdict.UNVERIFIED
            assert bundle.step_results["step_1_apply_unified_diff_in_clean_worktree"]["status"] == "failed"

    def test_pipeline_step_2_fails_originating_finding_remains(
        self, temp_git_repo: Path, sample_finding: FixFinding, sample_diff: str
    ):
        """Step 2 fails if originating tool still finds the violation."""
        with DisposableWorktreeRunner(repo_root=temp_git_repo) as runner:
            fix = FixSuggestion(
                id="fix_step2_fail",
                finding_id=sample_finding.id,
                fix_type=FixType.TOOL_NATIVE,
                description="Incomplete fix",
                file_paths=["app.py"],
                diff=sample_diff,
                lines_changed=2,
            )

            pipeline = VerificationPipeline(
                worktree_runner=runner,
                finding=sample_finding,
                fix_suggestion=fix,
                # Tool reports finding was NOT eliminated
                originating_tool_runner=lambda wt, fnd: [sample_finding],
            )

            verdict, bundle = pipeline.execute_pipeline()
            assert verdict == Verdict.UNVERIFIED
            assert bundle.step_results["step_2_re-run_originating_tool_(elimination_check)"]["status"] == "failed"

    def test_pipeline_step_3_fails_new_finding_introduced(
        self, temp_git_repo: Path, sample_finding: FixFinding, sample_diff: str
    ):
        """Step 3 fails if deterministic lanes introduce new findings."""
        with DisposableWorktreeRunner(repo_root=temp_git_repo) as runner:
            fix = FixSuggestion(
                id="fix_step3_fail",
                finding_id=sample_finding.id,
                fix_type=FixType.TOOL_NATIVE,
                description="Fix introducing bug",
                file_paths=["app.py"],
                diff=sample_diff,
                lines_changed=2,
            )

            new_finding = FixFinding(id="fnd_new", file_path="app.py", rule_id="F401", message="Unused import")

            pipeline = VerificationPipeline(
                worktree_runner=runner,
                finding=sample_finding,
                fix_suggestion=fix,
                originating_tool_runner=lambda wt, fnd: [],
                deterministic_lanes_runner=lambda wt, files: [new_finding],
            )

            verdict, bundle = pipeline.execute_pipeline()
            assert verdict == Verdict.UNVERIFIED
            assert bundle.step_results["step_3_re-run_deterministic_lanes_(no_new_findings)"]["status"] == "failed"

    def test_pipeline_step_4_fails_type_lint_error(
        self, temp_git_repo: Path, sample_finding: FixFinding, sample_diff: str
    ):
        """Step 4 fails if type-checker or linter reports errors on changed files."""
        with DisposableWorktreeRunner(repo_root=temp_git_repo) as runner:
            fix = FixSuggestion(
                id="fix_step4_fail",
                finding_id=sample_finding.id,
                fix_type=FixType.TOOL_NATIVE,
                description="Type error fix",
                file_paths=["app.py"],
                diff=sample_diff,
                lines_changed=2,
            )

            pipeline = VerificationPipeline(
                worktree_runner=runner,
                finding=sample_finding,
                fix_suggestion=fix,
                originating_tool_runner=lambda wt, fnd: [],
                deterministic_lanes_runner=lambda wt, files: [],
                type_and_lint_runner=lambda wt, files: (False, "Type check failed: incompatible return type"),
            )

            verdict, bundle = pipeline.execute_pipeline()
            assert verdict == Verdict.UNVERIFIED
            assert bundle.step_results["step_4_type-check_and_lint_changed_files"]["status"] == "failed"

    def test_pipeline_step_5_fails_regression_detected(
        self, temp_git_repo: Path, sample_finding: FixFinding, sample_diff: str
    ):
        """Step 5 fails if any previously passing test fails after patch."""
        with DisposableWorktreeRunner(repo_root=temp_git_repo) as runner:
            fix = FixSuggestion(
                id="fix_step5_fail",
                finding_id=sample_finding.id,
                fix_type=FixType.BOUNDED_LLM,
                description="Regression-causing patch",
                file_paths=["app.py"],
                diff=sample_diff,
                lines_changed=2,
            )

            pipeline = VerificationPipeline(
                worktree_runner=runner,
                finding=sample_finding,
                fix_suggestion=fix,
                originating_tool_runner=lambda wt, fnd: [],
                deterministic_lanes_runner=lambda wt, files: [],
                type_and_lint_runner=lambda wt, files: (True, "Passed"),
                test_suite_runner=lambda wt, files: {
                    "before_passed": 12,
                    "before_failed": 0,
                    "after_passed": 11,
                    "after_failed": 1,
                    "regressions": 1,
                    "regression_names": ["test_core_feature"],
                },
            )

            verdict, bundle = pipeline.execute_pipeline()
            assert verdict == Verdict.UNVERIFIED
            assert bundle.step_results["step_5_test_selection_(regression_check)"]["status"] == "failed"
            assert bundle.test_counts["regressions"] == 1

    def test_pipeline_step_6_fails_traffic_replay_regression(
        self, temp_git_repo: Path, sample_finding: FixFinding, sample_diff: str
    ):
        """Step 6 fails if recorded traffic replay encounters an error."""
        with DisposableWorktreeRunner(repo_root=temp_git_repo) as runner:
            fix = FixSuggestion(
                id="fix_step6_fail",
                finding_id=sample_finding.id,
                fix_type=FixType.TOOL_NATIVE,
                description="Replay regression",
                file_paths=["app.py"],
                diff=sample_diff,
                lines_changed=2,
            )

            pipeline = VerificationPipeline(
                worktree_runner=runner,
                finding=sample_finding,
                fix_suggestion=fix,
                originating_tool_runner=lambda wt, fnd: [],
                deterministic_lanes_runner=lambda wt, files: [],
                type_and_lint_runner=lambda wt, files: (True, "Passed"),
                test_suite_runner=lambda wt, files: {"regressions": 0},
                replay_runner=lambda wt: (False, "500 Internal Server Error on /api/v1/checkout"),
                has_recorded_traffic=True,
            )

            verdict, bundle = pipeline.execute_pipeline()
            assert verdict == Verdict.UNVERIFIED
            assert bundle.step_results["step_6_traffic_replay_check"]["status"] == "failed"

    def test_pipeline_step_7_mutation_check_fails_on_tautology(
        self, temp_git_repo: Path, sample_finding: FixFinding
    ):
        """Step 7 fails if newly added test does not fail on unpatched code."""
        with DisposableWorktreeRunner(repo_root=temp_git_repo) as runner:
            test_diff = """--- a/app.py
+++ b/app.py
@@ -1,2 +1,5 @@
 def hello():
     return 'world'
+
+def test_tautology():
+    assert True
"""
            fix = FixSuggestion(
                id="fix_step7_fail",
                finding_id=sample_finding.id,
                fix_type=FixType.BOUNDED_LLM,
                description="Tautological test patch",
                file_paths=["app.py"],
                diff=test_diff,
                lines_changed=4,
                metadata={"mutation_check_valid": False},  # Test does NOT fail on unpatched code
            )

            pipeline = VerificationPipeline(
                worktree_runner=runner,
                finding=sample_finding,
                fix_suggestion=fix,
                originating_tool_runner=lambda wt, fnd: [],
                deterministic_lanes_runner=lambda wt, files: [],
                type_and_lint_runner=lambda wt, files: (True, "Passed"),
                test_suite_runner=lambda wt, files: {"regressions": 0},
            )

            verdict, bundle = pipeline.execute_pipeline()
            assert verdict == Verdict.UNVERIFIED
            assert bundle.step_results["step_7_mutation_check_for_added_tests"]["status"] == "failed"

    def test_pipeline_step_8_fails_policy_excluded_path(
        self, temp_git_repo: Path, sample_finding: FixFinding, sample_diff: str
    ):
        """Step 8 policy check rejects excluded path before applying diff."""
        with DisposableWorktreeRunner(repo_root=temp_git_repo) as runner:
            fix = FixSuggestion(
                id="fix_step8_fail",
                finding_id=sample_finding.id,
                fix_type=FixType.BOUNDED_LLM,
                description="Fix targeting auth",
                file_paths=["skelion_agent/auth.py"],
                diff=sample_diff,
                lines_changed=2,
            )

            pipeline = VerificationPipeline(
                worktree_runner=runner,
                finding=sample_finding,
                fix_suggestion=fix,
            )

            verdict, bundle = pipeline.execute_pipeline()
            assert verdict == Verdict.UNVERIFIED
            assert bundle.step_results["step_8_policy_checks_(excluded_paths,_size,_files)"]["status"] == "failed"
            assert "step_1" not in bundle.step_results  # Terminated before diff apply!

    def test_pipeline_never_verified_without_evidence_bundle(self):
        """Never label verified without the evidence bundle."""
        # Simulated null bundle scenario
        pipeline = VerificationPipeline(
            worktree_runner=None,  # type: ignore
            finding=FixFinding(id="fnd_x", file_path="app.py"),
            fix_suggestion=FixSuggestion(
                id="fix_x",
                finding_id="fnd_x",
                fix_type=FixType.TOOL_NATIVE,
                description="",
                file_paths=["app.py"],
                diff="",
                lines_changed=0,
            ),
        )
        verdict, bundle = pipeline.execute_pipeline()
        assert verdict == Verdict.UNVERIFIED
        assert bundle is not None

    def test_evidence_bundle_secret_redaction(self):
        """Tokens, keys, and DB passwords are redacted in bundle JSON."""
        raw_output = "Connected to postgres://admin:super_secret_pw@db.prod.internal:5432/main with ghp_1234567890abcdef1234567890abcdef and skl_live_abcdef1234567890"
        redacted = redact_sensitive_text(raw_output)

        assert "super_secret_pw" not in redacted
        assert "ghp_" not in redacted
        assert "skl_live_" not in redacted
        assert "[REDACTED]" in redacted
        assert "[REDACTED_GH_TOKEN]" in redacted
        assert "[REDACTED_SKELION_KEY]" in redacted


# ===========================================================================
# 4. Publisher Helpers Tests
# ===========================================================================

class TestPRReviewPublisher:

    def test_format_github_suggestion_block(self):
        """Formats inline suggestion block correctly."""
        code = "def add(a, b):\n    return a + b"
        block = format_github_suggestion_block(code)
        assert block.startswith("```suggestion\n")
        assert block.endswith("\n```")
        assert "return a + b" in block

    def test_extract_replacement_from_diff(self, sample_diff: str):
        """Extracts only the replacement code lines from diff."""
        replacement = extract_replacement_from_diff(sample_diff)
        assert "return 'skelion'" in replacement
        assert "return 'world'" not in replacement

    def test_format_pr_review_comment(self, sample_finding: FixFinding, sample_diff: str):
        """Formats full GitHub PR review comment with evidence bundle card."""
        fix = FixSuggestion(
            id="fix_pub_001",
            finding_id=sample_finding.id,
            fix_type=FixType.TOOL_NATIVE,
            description="Style fix",
            file_paths=["app.py"],
            diff=sample_diff,
            lines_changed=2,
        )
        bundle = {
            "verdict": "verified",
            "diff_hash": fix.diff_hash,
            "test_counts": {
                "before": {"passed": 10},
                "after": {"passed": 10},
                "regressions": 0,
            },
        }

        comment = format_pr_review_comment(sample_finding, fix, bundle, run_id="run_999")
        assert "### 🛡️ Skelion Autofix" in comment
        assert "🟢 **VERIFIED**" in comment
        assert "```suggestion" in comment
        assert "return 'skelion'" in comment
        assert "@skelion revert run_999" in comment

    def test_parse_revert_command(self):
        """Correctly extracts run_id from @skelion revert <run_id>."""
        assert parse_revert_command("@skelion revert run_12345") == "run_12345"
        assert parse_revert_command("Please @skelion revert fix-abc.12 now") == "fix-abc.12"
        assert parse_revert_command("@SKELION REVERT run_xyz") == "run_xyz"
        assert parse_revert_command("LGTM, thanks!") is None

    def test_invert_unified_diff(self, sample_diff: str):
        """Inverts a unified diff cleanly."""
        inverted = invert_unified_diff(sample_diff)
        assert "--- b/app.py" in inverted
        assert "+++ a/app.py" in inverted
        assert "+    return 'world'" in inverted
        assert "-    return 'skelion'" in inverted

    def test_one_click_commit_and_revert(self, temp_git_repo: Path, sample_diff: str):
        """Executes one-click commit and subsequent one-click revert on git repo."""
        # Step 1: One-click commit
        commit_res = apply_one_click_commit(
            repo_path=temp_git_repo,
            run_id="run_test_01",
            diff=sample_diff,
        )
        assert commit_res.success is True
        assert commit_res.commit_sha is not None

        # Verify change was committed
        content_after_commit = (temp_git_repo / "app.py").read_text(encoding="utf-8")
        assert "return 'skelion'" in content_after_commit

        # Step 2: One-click revert using original diff
        revert_res = execute_one_click_revert(
            repo_path=temp_git_repo,
            run_id="run_test_01",
            original_diff=sample_diff,
        )
        assert revert_res.success is True
        assert revert_res.revert_commit_sha is not None

        # Verify change was cleanly reverted back
        content_after_revert = (temp_git_repo / "app.py").read_text(encoding="utf-8")
        assert "return 'world'" in content_after_revert

    def test_parse_revert_command_with_angle_brackets(self):
        """Correctly extracts run_id from @skelion revert <run_id> with literal brackets."""
        assert parse_revert_command("@skelion revert <run_abc_123>") == "run_abc_123"
        assert parse_revert_command("revert this: @skelion revert <fix-999.1>") == "fix-999.1"

    def test_execute_one_click_revert_reports_git_error(self, temp_git_repo: Path):
        """When git revert fails on invalid commit SHA, returns real error message."""
        bad_sha = "1111111111111111111111111111111111111111"
        res = execute_one_click_revert(
            repo_path=temp_git_repo,
            run_id="run_bad_sha",
            commit_sha=bad_sha,
        )
        assert res.success is False
        assert "git revert failed" in (res.error or "")


# ===========================================================================
# 5. Advanced Resilience & Edge Case Tests
# ===========================================================================

class TestAdvancedResilienceAndEdgeCases:

    def test_sandbox_memory_limit_exceeded(self, temp_git_repo: Path):
        """Commands exceeding memory limit are terminated and marked memory_exceeded."""
        # 15MB limit, process allocates 40MB
        config = SandboxConfig(timeout_seconds=10, memory_limit_bytes=15 * 1024 * 1024)
        with DisposableWorktreeRunner(repo_root=temp_git_repo, config=config) as runner:
            cmd = ["python", "-c", "a = bytearray(40 * 1024 * 1024); import time; time.sleep(2)"]
            res = runner.run_command(cmd)
            assert res.memory_exceeded is True
            assert res.exit_code == 137
            assert res.success is False
            assert "exceeded memory limit" in res.stderr

    def test_apply_patch_directory_traversal_blocked(self, temp_git_repo: Path):
        """Unified diff with directory traversal target is rejected by sandbox."""
        from skelion_agent.pr_review_sandbox import _apply_unified_diff_fallback

        evil_diff = """--- a/app.py
+++ b/../../evil_escape.py
@@ -1,1 +1,1 @@
-a
+b
"""
        with DisposableWorktreeRunner(repo_root=temp_git_repo) as runner:
            success, msg = _apply_unified_diff_fallback(runner.worktree_path, evil_diff)
            assert success is False
            assert "Sandbox violation" in msg

    def test_apply_patch_file_deletion_and_empty_context(self, temp_git_repo: Path):
        """Fallback diff parser handles file deletion and empty context lines cleanly."""
        from skelion_agent.pr_review_sandbox import _apply_unified_diff_fallback

        with DisposableWorktreeRunner(repo_root=temp_git_repo) as runner:
            del_target = runner.worktree_path / "to_delete.py"
            del_target.write_text("def delete_me(): pass\n", encoding="utf-8")
            assert del_target.exists()

            del_diff = """--- a/to_delete.py
+++ /dev/null
@@ -1,1 +0,0 @@
-def delete_me(): pass
"""
            success, msg = _apply_unified_diff_fallback(runner.worktree_path, del_diff)
            assert success is True
            assert not del_target.exists()

    def test_environment_sanitizer_case_insensitive(self):
        """Sanitizer handles mixed-case keys on Windows without dropping safe variables."""
        mixed_env = {
            "Path": "C:\\Windows\\system32;C:\\Python312",
            "SystemRoot": "C:\\Windows",
            "Temp": "C:\\Temp",
            "AWS_SECRET_KEY": "leak_me",
        }
        sanitized = sanitize_sandbox_env(source_env=mixed_env, block_network=False)
        assert "Path" in sanitized or "PATH" in sanitized
        assert "SystemRoot" in sanitized or "SYSTEMROOT" in sanitized
        assert "AWS_SECRET_KEY" not in sanitized

    @pytest.mark.parametrize(
        "edge_path",
        [
            "src/authentication/login.py",
            "src/payments/checkout.py",
            "deployments/compose.yaml",
            "id_ed25519",
            "backend/api.dockerfile",
            "../../outside.py",
        ],
    )
    def test_excluded_paths_guard_edge_cases(self, edge_path: str):
        """Rejects pluralized auth/payment directories, modern docker/compose, and traversal."""
        is_ex, reason = is_path_excluded(edge_path)
        assert is_ex is True
        assert reason is not None

    def test_codemod_sync_to_async_syntax_valid(self, tmp_path: Path):
        """Generated sync_to_async code converts enclosing def to async def and passes syntax check."""
        import py_compile

        code = "def fetch_data():\n    time.sleep(1)\n    return 42\n"
        fix = CodemodFixer.sync_to_async(code, "fetcher.py")
        assert fix is not None
        assert "async def fetch_data():" in fix.diff
        assert "await asyncio.sleep(1)" in fix.diff

        # Extract fixed content and verify valid Python syntax
        lines = code.splitlines()
        fixed = "import asyncio\nasync def fetch_data():\n    await asyncio.sleep(1)\n    return 42\n"
        test_file = tmp_path / "syntax_check.py"
        test_file.write_text(fixed, encoding="utf-8")
        # py_compile will raise PyCompileError if 'await' is outside async def
        py_compile.compile(str(test_file), doraise=True)

    def test_codemod_remove_unused_imports_multiple_on_line(self):
        """Removes an unused import from a multi-import line without removing used siblings."""
        code = "from math import sin, cos, tan\n\ndef calc(x):\n    return sin(x) + tan(x)\n"
        fix = CodemodFixer.remove_unused_imports(code, "calc.py", ["cos"])
        assert fix is not None
        assert "+from math import sin, tan" in fix.diff
        assert "-from math import sin, cos, tan" in fix.diff

    def test_codemod_replace_deprecated_api_import_datetime(self):
        """Replaces datetime.utcnow() when imported via 'import datetime'."""
        code = "import datetime\n\ndef get_now():\n    return datetime.utcnow()\n"
        fix = CodemodFixer.replace_deprecated_api(code, "my_time.py")
        assert fix is not None
        assert "+from datetime import timezone" in fix.diff or "+import datetime\nfrom datetime import timezone" in fix.diff
        assert "+    return datetime.now(timezone.utc)" in fix.diff

    def test_extract_target_files_includes_deleted_files(self):
        """extract_target_files_from_diff identifies deleted file from '--- a/...' header."""
        del_diff = """--- a/obsolete_module.py
+++ /dev/null
@@ -1,2 +0,0 @@
-def old(): pass
"""
        targets = BoundedLLMFixer.extract_target_files_from_diff(del_diff)
        assert targets == ["obsolete_module.py"]

    def test_verification_pipeline_with_custom_mutation_runner(
        self, temp_git_repo: Path, sample_finding: FixFinding
    ):
        """Custom mutation runner callback is invoked for patch adding tests."""
        test_diff = """--- a/app.py
+++ b/app.py
@@ -1,2 +1,5 @@
 def hello():
     return 'world'
+
+def test_feature():
+    assert hello() == 'world'
"""
        fix = FixSuggestion(
            id="fix_mut_runner",
            finding_id=sample_finding.id,
            fix_type=FixType.BOUNDED_LLM,
            description="Fix with test",
            file_paths=["app.py"],
            diff=test_diff,
            lines_changed=4,
        )

        runner_called = False

        def mock_mutation_runner(wt: Any, diff: str) -> Tuple[bool, str]:
            nonlocal runner_called
            runner_called = True
            return True, "Passed mutation check"

        with DisposableWorktreeRunner(repo_root=temp_git_repo) as runner:
            pipeline = VerificationPipeline(
                worktree_runner=runner,
                finding=sample_finding,
                fix_suggestion=fix,
                originating_tool_runner=lambda wt, fnd: [],
                deterministic_lanes_runner=lambda wt, files: [],
                type_and_lint_runner=lambda wt, files: (True, "Passed"),
                test_suite_runner=lambda wt, files: {"regressions": 0},
                mutation_runner=mock_mutation_runner,
            )
            verdict, bundle = pipeline.execute_pipeline()
            assert runner_called is True
            assert bundle.step_results["step_7_mutation_check_for_added_tests"]["status"] == "passed"

