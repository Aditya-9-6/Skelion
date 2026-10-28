# Skelion Pilot Outreach & Founder Sales Kit

This kit contains tested, high-converting outreach sequences for the Skelion Pilot Program.
Positioning: **Production Intelligence & Verified Healing** (Runs alongside Cursor / Claude Code).

---

## Template 1: Direct Message (Cold-Warm, LinkedIn / X / Email)
**Subject:** Free 48-hour production health audit for {{company_name}}?

> Hey {{first_name}}, quick one.
>
> I've been building **Skelion**, a developer tool that intercepts silent errors breaking in production and automatically generates minimal fixes verified against real captured traffic in an isolated sandbox.
>
> Unlike generic coding assistants, it doesn't try to replace your IDE chat—it feeds verified production incident intelligence directly into Cursor and Claude Code via MCP. Everything runs on your side (zero secrets or raw customer logs leave your servers).
>
> Could I run a completely free 48-hour health audit for {{company_name}}?
>
> It takes ~2 minutes to run locally (`skelion audit nginx.log`) and produces a clean, self-contained diagnostic report showing:
> 1. Silent 200 failures and unhandled 5xx spikes.
> 2. Rate-limit 429 storms draining upstream API quotas.
> 3. Latency regressions across your top API routes.
>
> Happy to send over the CLI or jump on a quick 10-minute setup call if you're curious!
>
> Best,  
> Aditya | Skelion

---

## Template 2: Follow-Up with Audit Report Evidence
**Subject:** Results from the health audit (3 silent regressions spotted)

> Hey {{first_name}},
>
> Following up on our chat—I generated a sample diagnostic card from our test run.
>
> In the audit, Skelion identified:
> - **1 silent 200 failure** on `/api/checkout` (returning an error payload disguised as 200 OK).
> - **429 rate limit storm** under peak traffic on external LLM calls.
> - **Replay-verified fix** that passed 100% of idempotent tests with zero regressions.
>
> Attached the HTML report for your team to inspect. If you'd like to test the VS Code extension or deploy the local proxy daemon with your team, here is a founding developer coupon:
>
> 🎁 **Coupon Code:** `FOUNDING50` (30% off any tier for 12 months)
>
> Let me know if you'd like me to set up a private team workspace!
>
> Cheers,  
> Aditya

---

## Template 3: Onboarding & Founding Pilot Invitation
**Subject:** Welcome to the Skelion Founding Pilot (Setup in 3 steps)

> Welcome aboard, {{first_name}}!
>
> Here are the 3 quick steps to activate Skelion in your development environment:
>
> ### 1. Install the VS Code Extension
> Open VS Code &rarr; Extensions &rarr; `Install from VSIX...` &rarr; select `skelion-vscode-0.1.0.vsix`.
>
> ### 2. Run Self-Diagnostics
> In your terminal:
> ```bash
> skelion doctor
> ```
> This verifies local database connectivity, offline license validation, and BYO-LLM endpoints.
>
> ### 3. Connect to Cursor / Claude Code (MCP)
> Add this to your `.cursor/mcp.json` or `claude_desktop_config.json`:
> ```json
> {
>   "mcpServers": {
>     "skelion": {
>       "command": "python",
>       "args": ["-m", "skelion_mcp.server"],
>       "env": {
>         "SKELION_API_URL": "http://127.0.0.1:8002"
>       }
>     }
>   }
> }
> ```
>
> Your Master Control Dashboard is live locally at `http://127.0.0.1:8002/admin`.
>
> Reach out anytime if you need assistance!
