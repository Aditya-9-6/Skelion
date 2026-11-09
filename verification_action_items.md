# Verification Action Items

This file tracks all pending verification tasks for the Helios web project. It is updated as tasks are completed.

| ID | Description | Owner | Tooling | Status |
|----|-------------|-------|---------|--------|
| 1 | Set up front‑end test framework (Jest, c8, Node test runner) | Front-end Engineer | npm, jest, c8 | DONE |
| 2 | Write baseline front‑end unit tests for each UI component (VerificationBadge) | Front-end Engineer | node test runner, c8 | DONE |
| 3 | Add Razorpay mock server (WireMock + standalone server) | DevOps / Backend | WireMock, Docker, Python | DONE |
| 4 | Implement integration test suite (FastAPI TestClient + mock Razorpay) | Backend Engineer | pytest, httpx, TestClient | DONE |
| 5 | Scaffold Playwright end‑to‑end tests (checkout flow, webhook handling) | QA Lead | Playwright, npm | DONE |
| 6 | Add performance load testing (k6 script @ 500 RPS) | Performance Engineer | k6 | DONE |
| 7 | Run accessibility & SEO audit (Lighthouse CI, axe‑core) | UX Designer | lighthouse, axe-core | DONE |
| 8 | Instrument observability (OpenTelemetry, Prometheus, Grafana) | SRE | opentelemetry, grafana | DONE |
| 9 | Create CI/CD pipeline (GitHub Actions) with jobs for each verification phase | DevOps | GitHub Actions (.github/workflows/verification.yml) | DONE |
| 10 | Enforce coverage thresholds (Python ‑‑cov‑fail‑under=100, JS c8 ‑‑check‑coverage) | Quality Engineer | pytest‑cov, c8 (.c8rc.json) | DONE |
| 11 | Assemble final signed verification report (SHA‑256 manifest, badge) | Security / Release | python, sha256 | DONE |
| 12 | Schedule nightly verification run to maintain 100 % coverage | DevOps | GitHub Actions cron schedule | DONE |

*Status keys*: `TODO` – not started, `IN‑PROGRESS` – work underway, `DONE` – completed.
