# Owner Control Dashboard

The repository includes a private operator dashboard for the platform owner.
It is separate from the customer application and provides:

- live organization, revenue, payment, incident, and active-run KPIs;
- plan, billing, incident, run, payment, refund, and transaction analysis;
- customer search and the existing audited administrative actions;
- audit-log inspection, token/limit controls, license management, and step-up
  authentication for mutating operations.

## Production setup

Run the admin API separately from the customer control plane:

```bash
export ENVIRONMENT=production
export DATABASE_URL=postgresql://...
export ADMIN_DATABASE_URL="$DATABASE_URL"
export ADMIN_GITHUB_CLIENT_ID=...
export ADMIN_GITHUB_SECRET=...
export ADMIN_GITHUB_REDIRECT_URI=https://admin.example.com/auth/github/callback
export ADMIN_GITHUB_IDS=123456789
export ADMIN_OWNER_EMAILS=owner@example.com
export ADMIN_COOKIE_SECRET="$(openssl rand -hex 32)"
export ADMIN_DATABASE_URL="$DATABASE_URL"

cd admin_web
npm ci
npm run build
```

Deploy `admin_api.main:app` behind a private hostname such as
`admin.example.com`, Cloudflare Access, or an equivalent identity-aware proxy.
The GitHub callback URL must exactly match `ADMIN_GITHUB_REDIRECT_URI`.
Cloudflare Access must send `CF-Access-Authenticated-User-Email`; production
requests are accepted only when that email is listed in
`ADMIN_OWNER_EMAILS`.

Start the API and frontend during local development:

```bash
# terminal 1, from the repository root
ADMIN_OWNER_EMAILS=owner@example.com \
ADMIN_COOKIE_SECRET=local-only-secret \
ADMIN_GITHUB_REDIRECT_URI=http://localhost:5173/auth/github/callback \
uvicorn admin_api.main:app --host 127.0.0.1 --port 8003

# terminal 2
cd admin_web
npm run dev
```

Open the Vite URL, select **Login with GitHub**, and complete the OAuth flow.
The browser session is an HttpOnly cookie; do not put admin credentials or
provider secrets in the React app or local storage.

## Main application protection

The legacy `/admin`, `/dashboard`, and `/v1/admin/*` routes in the main
control-plane app are also owner-gated. Configure one or both of:

```bash
PLATFORM_OWNER_EMAILS=owner@example.com
PLATFORM_OWNER_USER_IDS=usr_...
```

These values are allowlists, not customer organization roles. Keep them
limited to the platform owner/operator identities and rotate access through
the normal deployment secret-management process.

## Operational guidance

Use the dashboard for observation and controlled support operations, not as a
replacement for migrations, backups, reconciliation jobs, or incident
response. Keep Cloudflare Access, GitHub OAuth, the admin cookie secret, and
the database on separate production-managed controls. Test owner denial with
an unauthorized GitHub identity before exposing the hostname.
