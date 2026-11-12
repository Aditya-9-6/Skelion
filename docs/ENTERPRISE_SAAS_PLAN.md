# Skelion Enterprise SaaS Plan

This is the implementation roadmap for turning Skelion from a launch-ready
single-product SaaS into an enterprise platform. The plan is intentionally
incremental: every phase must preserve tenant isolation, billing correctness,
operational visibility, and backwards compatibility for existing SDK clients.

## Target architecture

```text
Browser / SDK / VS Code
        |
   API gateway
   (TLS, WAF, request ID, rate limits)
        |
  Control-plane API  ----  Auth/SSO (OIDC/SAML, SCIM)
        |                     |
   Tenant context        Users/Memberships/RBAC
        |
  Domain services
  billing | incidents | agent runs | repositories | webhooks
        |
  PostgreSQL (RLS) | Redis | object storage | queue/workers
        |
  Observability: metrics, traces, audit stream, alerting, SLOs
```

## Delivery phases

### Phase 0 — Foundation and migration safety

- Keep `/v1` stable and publish OpenAPI contracts.
- Require request IDs, structured JSON logs, health/readiness probes, and
  production secret validation.
- Move production persistence to managed PostgreSQL and Redis; use Alembic for
  every schema change.
- Add migration/rollback checks to CI and backup/restore drills.
- Enforce tenant scope in every query and add negative cross-tenant tests.

### Phase 1 — Enterprise identity and tenancy

- Complete the existing `User`, `Membership`, `ApiKey`, and `AuditLog` model
  path; stop using `Organization` as both user and tenant.
- Add OIDC first, then SAML 2.0, SCIM provisioning, domain verification, and
  optional just-in-time provisioning.
- Implement RBAC roles (`owner`, `admin`, `developer`, `viewer`, `billing`) and
  explicit resource permissions.
- Add API-key scopes, rotation, expiry, revocation, last-used tracking, and
  secret-once display.
- Add organization switching only through an authorized membership, never a
  caller-controlled organization header.

### Phase 2 — Billing and commercial controls

- Keep Razorpay as the initial provider behind a provider interface; add Stripe
  for international cards and tax workflows.
- Make payment, entitlement, refund, invoice, and credit-ledger effects
  idempotent and transactionally auditable.
- Add seat counts, usage metering, budgets, hard/soft limits, overage policy,
  proration, cancellation, refunds, and invoice exports.
- Reconcile provider events against internal ledgers daily and alert on drift.

### Phase 3 — Product reliability

- Separate synchronous API requests from queued incident analysis and agent runs.
- Add per-tenant concurrency limits, fair scheduling, dead-letter queues,
  retries with jitter, and idempotency keys for all write commands.
- Add repository/provider circuit breakers and bounded LLM spend controls.
- Define SLOs: API availability, p95 latency, webhook processing time, and
  fix-generation success rate.

### Phase 4 — Enterprise security and compliance

- Encrypt sensitive fields at rest and use a managed secret/KMS provider.
- Add immutable audit export, retention policies, legal hold, and admin
  step-up authentication.
- Complete threat modeling, dependency/SAST/DAST scanning, penetration testing,
  incident response, and disaster recovery exercises.
- Prepare SOC 2 evidence collection, GDPR/DPDP data workflows, subprocessors,
  DPA, security questionnaire, and customer trust-center content.

### Phase 5 — Enterprise operations

- Multi-region read strategy and documented recovery objectives.
- Blue/green or canary deployments with automated rollback.
- Tenant-aware support tooling with audited impersonation and break-glass
  controls.
- Usage dashboards, audit export, SSO/SCIM admin UI, billing portal, and
  customer-facing status/incident communication.

## Non-negotiable acceptance gates

1. A request cannot read or mutate another tenant's data, even if it supplies
   another organization ID.
2. No browser/local-storage value can authorize credits, plan access, or agent
   execution.
3. Every payment/refund/webhook effect is safe to retry and trace to an
   immutable event and ledger entry.
4. Production starts only with validated secrets and explicitly configured
   origins, database, Redis, and provider credentials.
5. Every privileged action has an actor, tenant, request ID, timestamp, and
   audit record.
6. Backup restoration and provider reconciliation are tested before enterprise
   contracts are sold.

## Current implementation slice

The current branch activates the first identity boundary safely: production
authentication now fails closed, machine keys resolve through hashed
`ProxyNode` records, demo authentication is explicit and non-production only,
and new registrations/GitHub logins establish owner memberships. Scoped
`ApiKey` records now support bounded lifetimes, strict scope validation,
production-safe legacy behavior, and audit entries on creation/revocation.
JWT sessions now carry an actor user ID, organization members can be listed,
added, role-updated, and removed through owner/admin-protected endpoints, and
ingest rejects API keys without the `ingest` scope.
Autonomous runs now charge the append-only ledger and never fabricate a PR
URL; outbound webhooks use HMAC signatures, delivery IDs, bounded retries, and
independent database sessions.
Enterprise control-plane foundations now include owner-managed OIDC/SAML
connection metadata, one-time hashed SCIM token issuance, SCIM user
listing/provisioning, compliance evidence status, and deployment-region
metadata. A Redis Streams queue primitive provides consumer groups, explicit
acknowledgement, bounded retries, and a dead-letter stream for horizontally
scaled workers. Provider integrations fail closed when production credentials
or required configuration are absent.
The remaining enterprise-critical work is actual OIDC callback/JWKS and SAML
assertion verification, complete SCIM PATCH/deprovisioning semantics, applying
RBAC to every protected route, wiring workers to the durable queue, billing
reconciliation/proration, immutable compliance exports, and regional failover
operations.
