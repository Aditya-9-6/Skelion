# Project Audit & Baseline Assessment (AUDIT.md)

## 1. Current State Assessment

### What Exists and Works
1. **Control Plane Core (`skelion_agent/control_plane.py`)**:
   - FastAPI application with routers for admin, metrics, PR comments, and billing.
   - SQLModel database initialization and telemetry ingestion.
   - Redis async client connection management.
2. **Data Models (`skelion_agent/models.py`)**:
   - `Organization`: Supports `plan`, `credits_total`, `credits_used`, `token`, `monthly_quota`, and payment customer IDs (`razorpay_customer_id`, `stripe_customer_id`).
   - `Incident`, `ProxyNode`, `AgentRun`, `PRReview`.
3. **Billing Foundation (`skelion_agent/plan_config.py` & `billing_routes.py`)**:
   - Plan definitions: `pilot` (₹0, 100 credits), `pro` (₹3,999, 5,000 credits), `enterprise` (₹9,999, 25,000 credits).
   - Razorpay order creation (`create_order`) and basic webhook handler.
4. **Resilience & Key-Pool (`gossipmesh_agent/key_pool.py`)**:
   - Multi-key rotation and exponential backoff on HTTP 429 errors from upstream LLM providers.
5. **Fail-Open Edge Proxy (`skelion_edge/proxy.py`)**:
   - Proxy middleware ensuring client traffic never breaks if internal services fail.

### Gaps Identified & Work Required for Production Launch
1. **GitHub Auth Endpoint**:
   - Missing `POST /v1/auth/github` endpoint to verify GitHub access tokens, auto-create users, and issue JWT + refresh token.
2. **Chat Gateway & Agent Loop (`/v1/chat`)**:
   - Need SSE streaming endpoint that orchestrates LLM responses, evaluates tool calls, and handles client tool results.
3. **Usage & Quotas (`/v1/me/usage`)**:
   - Needs atomic deduction and real-time status reporting for remaining credits.
4. **VS Code Extension UI & Packaging**:
   - Need polished multi-screen webview (Sign-in, Chat with diff card review, Model picker, Usage meter, and Subscription management).
   - Clean VSIX packaging build script that eliminates entrypoint mismatch errors.
