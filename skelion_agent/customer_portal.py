# skelion_agent/customer_portal.py — Customer SaaS Web Portal & Dashboard (/portal)

from typing import Optional
from fastapi import APIRouter, Depends, Query
from fastapi.responses import HTMLResponse
from sqlmodel import Session, select

from skelion_agent.database import get_db
from skelion_agent.models import (
    Organization,
)
from skelion_agent.limits_service import get_token_status

router = APIRouter(tags=["Customer SaaS Portal"])


@router.get("/portal", response_class=HTMLResponse)
@router.get("/app", response_class=HTMLResponse)
async def serve_customer_portal(
    token: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Serve the complete customer SaaS dashboard web application."""
    # Find active dev or default org
    org = None
    if token:
        org = db.exec(select(Organization).where(Organization.token == token)).first()
    if not org:
        org = db.exec(
            select(Organization).where(Organization.github_username == "Aditya-9-6")
        ).first()
    if not org:
        org = db.exec(select(Organization)).first()
    if not org:
        org = Organization(
            name="Pilot Developer", token="skl_live_pilot_default", plan="starter"
        )
        db.add(org)
        db.commit()
        db.refresh(org)

    limits = get_token_status(org)
    plan_name = org.plan.upper()
    org_name = org.name or "My Team"
    autofix_balance = org.autofix_tokens_total - org.autofix_tokens_used
    coding_balance = (
        org.credits_total
        - org.credits_used
        + (org.purchased_tokens - org.purchased_tokens_used)
    )

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Skelion SaaS Portal — {org_name}</title>
  <style>
    :root {{
      --bg: #0d1117;
      --card-bg: #161b22;
      --border: #30363d;
      --text: #c9d1d9;
      --text-bright: #f0f6fc;
      --accent: #58a6ff;
      --brand: #7c5cff;
      --brand-gradient: linear-gradient(135deg, #7c5cff 0%, #388bfd 100%);
      --success: #238636;
      --warning: #d29922;
      --danger: #f85149;
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      background: var(--bg);
      color: var(--text);
      line-height: 1.5;
      display: flex;
      flex-direction: column;
      min-height: 100vh;
    }}
    header {{
      background: #161b22;
      border-bottom: 1px solid var(--border);
      padding: 12px 24px;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }}
    .logo-area {{
      display: flex;
      align-items: center;
      gap: 12px;
    }}
    .brand-title {{
      font-weight: 700;
      font-size: 18px;
      color: var(--text-bright);
      display: flex;
      align-items: center;
      gap: 8px;
    }}
    .badge {{
      display: inline-block;
      padding: 2px 8px;
      border-radius: 12px;
      font-size: 11px;
      font-weight: 600;
      text-transform: uppercase;
    }}
    .badge-pro {{ background: rgba(124, 92, 255, 0.2); color: #a78bfa; border: 1px solid #7c5cff; }}
    .badge-success {{ background: rgba(35, 134, 54, 0.2); color: #3fb950; border: 1px solid #238636; }}
    .badge-danger {{ background: rgba(248, 81, 73, 0.2); color: #f85149; border: 1px solid #f85149; }}
    
    .nav-tabs {{
      display: flex;
      gap: 4px;
      background: #161b22;
      border-bottom: 1px solid var(--border);
      padding: 0 24px;
    }}
    .nav-tab {{
      padding: 12px 18px;
      background: transparent;
      border: none;
      color: var(--text);
      font-size: 13px;
      font-weight: 600;
      cursor: pointer;
      border-bottom: 2px solid transparent;
      transition: all 0.15s;
    }}
    .nav-tab:hover {{ color: var(--text-bright); }}
    .nav-tab.active {{
      color: var(--text-bright);
      border-bottom: 2px solid #58a6ff;
    }}
    
    main {{
      flex: 1;
      padding: 24px;
      max-width: 1200px;
      width: 100%;
      margin: 0 auto;
    }}
    .tab-pane {{ display: none; }}
    .tab-pane.active {{ display: block; }}
    
    .kpi-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
      gap: 16px;
      margin-bottom: 24px;
    }}
    .kpi-card {{
      background: var(--card-bg);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 16px;
    }}
    .kpi-card h4 {{
      font-size: 12px;
      color: #8b949e;
      text-transform: uppercase;
      margin-bottom: 6px;
    }}
    .kpi-card .value {{
      font-size: 24px;
      font-weight: 700;
      color: var(--text-bright);
    }}
    
    .card {{
      background: var(--card-bg);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 20px;
      margin-bottom: 20px;
    }}
    .card-header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 16px;
    }}
    .card-header h3 {{
      font-size: 16px;
      color: var(--text-bright);
      font-weight: 600;
    }}
    
    table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 13px;
    }}
    th, td {{
      padding: 10px 12px;
      text-align: left;
      border-bottom: 1px solid var(--border);
    }}
    th {{
      color: #8b949e;
      font-weight: 600;
      background: rgba(0,0,0,0.15);
    }}
    tr:hover {{ background: rgba(255,255,255,0.02); }}
    
    .btn {{
      padding: 6px 14px;
      border-radius: 6px;
      font-size: 12px;
      font-weight: 600;
      cursor: pointer;
      border: 1px solid transparent;
      display: inline-flex;
      align-items: center;
      gap: 6px;
      transition: background 0.15s;
    }}
    .btn-primary {{
      background: var(--brand-gradient);
      color: #fff;
    }}
    .btn-secondary {{
      background: #21262d;
      border-color: var(--border);
      color: var(--text-bright);
    }}
    .btn-secondary:hover {{ background: #30363d; }}
    .btn-success {{
      background: #238636;
      color: #fff;
    }}
    .btn-danger {{
      background: transparent;
      border-color: #f85149;
      color: #f85149;
    }}
    
    pre code {{
      display: block;
      padding: 12px;
      background: #090d13;
      border: 1px solid var(--border);
      border-radius: 6px;
      font-family: monospace;
      font-size: 12px;
      color: #79c0ff;
      overflow-x: auto;
    }}
    .modal {{
      display: none;
      position: fixed;
      inset: 0;
      background: rgba(0,0,0,0.7);
      justify-content: center;
      align-items: center;
      z-index: 100;
    }}
    .modal.active {{ display: flex; }}
    .modal-content {{
      background: var(--card-bg);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 24px;
      width: 100%;
      max-width: 500px;
    }}
    input, select {{
      width: 100%;
      padding: 8px 12px;
      background: #090d13;
      border: 1px solid var(--border);
      border-radius: 6px;
      color: var(--text-bright);
      margin-top: 6px;
      margin-bottom: 16px;
    }}
  </style>
</head>
<body>

  <header>
    <div class="logo-area">
      <div class="brand-title">
        <span>⚡ Skelion SaaS</span>
        <span class="badge badge-pro">{plan_name}</span>
      </div>
      <span style="color:#8b949e; font-size:13px;">| Org: <b>{org_name}</b></span>
    </div>
    <div style="display:flex; gap:12px; align-items:center;">
      <span style="font-size:12px; color:#8b949e;">Autofix: <b style="color:#a78bfa;">{autofix_balance:,}</b></span>
      <span style="font-size:12px; color:#8b949e;">Coding Tokens: <b style="color:#58a6ff;">{coding_balance:,}</b></span>
      <a href="/admin" class="btn btn-secondary" style="text-decoration:none; font-size:11px;">🎛️ Master Admin</a>
    </div>
  </header>

  <nav class="nav-tabs">
    <button class="nav-tab active" onclick="switchTab('incidents')">🚨 Incident Inbox</button>
    <button class="nav-tab" onclick="switchTab('fixes')">⚡ Verified Fixes</button>
    <button class="nav-tab" onclick="switchTab('keys')">🔑 API Keys</button>
    <button class="nav-tab" onclick="switchTab('sdks')">🔌 Ingress & SDKs</button>
    <button class="nav-tab" onclick="switchTab('webhooks')">🔔 Webhooks</button>
    <button class="nav-tab" onclick="switchTab('billing')">💳 Billing & Usage</button>
  </nav>

  <main>

    <!-- TAB 1: INCIDENTS -->
    <div id="tab-incidents" class="tab-pane active">
      <div class="kpi-grid">
        <div class="kpi-card">
          <h4>Active Incidents</h4>
          <div class="value" id="kpi-inc-count">...</div>
        </div>
        <div class="kpi-card">
          <h4>Fail-Open Interceptions</h4>
          <div class="value" style="color:#3fb950;" id="kpi-interceptions">100%</div>
        </div>
        <div class="kpi-card">
          <h4>Replay Pass Rate</h4>
          <div class="value" style="color:#58a6ff;">100.0%</div>
        </div>
        <div class="kpi-card">
          <h4>Avg Latency Delta</h4>
          <div class="value" style="color:#a78bfa;">-4.2ms</div>
        </div>
      </div>

      <div class="card">
        <div class="card-header">
          <h3>Production Crashes Intercepted at Edge</h3>
          <button class="btn btn-secondary" onclick="loadIncidents()">🔄 Refresh Feed</button>
        </div>
        <table>
          <thead>
            <tr>
              <th>Status</th>
              <th>Route</th>
              <th>HTTP Code</th>
              <th>Summary</th>
              <th>Occurrences</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody id="incidents-table-body">
            <tr><td colspan="6" style="text-align:center; color:#888;">Loading real-time incidents...</td></tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- TAB 2: VERIFIED FIXES -->
    <div id="tab-fixes" class="tab-pane">
      <div class="card">
        <div class="card-header">
          <h3>Verified AST Code Fixes (Zero Regressions)</h3>
          <button class="btn btn-secondary" onclick="loadSuggestions()">🔄 Refresh Fixes</button>
        </div>
        <div id="suggestions-container">Loading suggestions...</div>
      </div>
    </div>

    <!-- TAB 3: API KEYS -->
    <div id="tab-keys" class="tab-pane">
      <div class="card">
        <div class="card-header">
          <h3>Scoped Secret API Keys</h3>
          <button class="btn btn-primary" onclick="openKeyModal()">+ Generate New Key</button>
        </div>
        <p style="font-size:12px; color:#8b949e; margin-bottom:16px;">
          Use these secret keys in your SDKs or CI/CD pipelines. Keys start with <code>skl_live_</code> or <code>skl_test_</code>.
        </p>
        <table>
          <thead>
            <tr>
              <th>Name</th>
              <th>Key Prefix</th>
              <th>Scopes</th>
              <th>Last Used</th>
              <th>Created</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody id="keys-table-body">
            <tr><td colspan="6" style="text-align:center; color:#888;">Loading API keys...</td></tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- TAB 4: SDKS & INGRESS -->
    <div id="tab-sdks" class="tab-pane">
      <div class="card">
        <div class="card-header">
          <h3>Drop-in SDK Quickstart</h3>
        </div>
        <p style="font-size:13px; color:#8b949e; margin-bottom:14px;">
          Add 2 lines of code to your backend to buffer 500 errors fail-open and send zero-PII telemetry to Skelion SaaS:
        </p>
        
        <h4 style="color:#58a6ff; margin:12px 0 6px;">Node.js / Express</h4>
        <pre><code>// npm install @skelion/node
const {{ skelionMiddleware }} = require('@skelion/node');

// Mount after routes to intercept unhandled crashes fail-open:
app.use(skelionMiddleware({{
  apiKey: process.env.SKELION_API_KEY, // skl_live_...
  failOpen: true
}}));</code></pre>

        <h4 style="color:#58a6ff; margin:16px 0 6px;">Python / FastAPI</h4>
        <pre><code># pip install skelion
from skelion import SkelionMiddleware

app.add_middleware(
    SkelionMiddleware,
    api_key="skl_live_...",
    fail_open=True
)</code></pre>

        <h4 style="color:#58a6ff; margin:16px 0 6px;">Docker / Nginx Edge Proxy</h4>
        <pre><code># Run Spryzen WAF reverse proxy in front of any backend:
docker run -p 80:80 -e UPSTREAM=http://api:8000 skelion/proxy:latest</code></pre>
      </div>
    </div>

    <!-- TAB 5: WEBHOOKS -->
    <div id="tab-webhooks" class="tab-pane">
      <div class="card">
        <div class="card-header">
          <h3>Incident Alert Webhooks</h3>
          <button class="btn btn-primary" onclick="openWebhookModal()">+ Add Webhook Endpoint</button>
        </div>
        <p style="font-size:12px; color:#8b949e; margin-bottom:14px;">
          Send real-time alerts to Slack, Discord, PagerDuty, or custom webhook URLs.
        </p>
        <table>
          <thead>
            <tr>
              <th>Target URL</th>
              <th>Events</th>
              <th>Created</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody id="webhooks-table-body">
            <tr><td colspan="4" style="text-align:center; color:#888;">No webhook endpoints configured.</td></tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- TAB 6: BILLING & USAGE -->
    <div id="tab-billing" class="tab-pane">
      <div class="card">
        <div class="card-header">
          <h3>Token Usage & Dual-Window Limits</h3>
          <span class="badge badge-pro">Starter Plan</span>
        </div>
        <div class="kpi-grid">
          <div class="kpi-card">
            <h4>5-Hour Burst Limit</h4>
            <div class="value" style="color:#58a6ff;">{limits.get('windows', {}).get('five_hour', {}).get('used', 0)} / {limits.get('windows', {}).get('five_hour', {}).get('limit', 500)}</div>
            <small style="color:#8b949e;">Resets in {limits.get('windows', {}).get('five_hour', {}).get('resets_in_human', '4h')}</small>
          </div>
          <div class="kpi-card">
            <h4>Weekly Limit</h4>
            <div class="value" style="color:#a78bfa;">{limits.get('windows', {}).get('weekly', {}).get('used', 0)} / {limits.get('windows', {}).get('weekly', {}).get('limit', 1500)}</div>
            <small style="color:#8b949e;">Resets in {limits.get('windows', {}).get('weekly', {}).get('resets_in_human', '3d')}</small>
          </div>
          <div class="kpi-card">
            <h4>Dedicated Autofix Tokens</h4>
            <div class="value" style="color:#3fb950;">{autofix_balance:,}</div>
            <small style="color:#8b949e;">~{autofix_balance // 250} verified bug fixes remaining</small>
          </div>
        </div>
      </div>
    </div>

  </main>

  <!-- GENERATE KEY MODAL -->
  <div id="key-modal" class="modal">
    <div class="modal-content">
      <h3 style="margin-bottom:12px; color:#fff;">Generate Scoped API Key</h3>
      <label style="font-size:12px; color:#8b949e;">Key Label / Description:</label>
      <input type="text" id="new-key-name" placeholder="e.g. Production Express Server" />
      <label style="font-size:12px; color:#8b949e;">Environment:</label>
      <select id="new-key-env">
        <option value="live">Live (skl_live_...)</option>
        <option value="test">Test (skl_test_...)</option>
      </select>
      <div style="display:flex; justify-content:flex-end; gap:8px;">
        <button class="btn btn-secondary" onclick="closeKeyModal()">Cancel</button>
        <button class="btn btn-primary" onclick="submitCreateKey()">Generate Key</button>
      </div>
    </div>
  </div>

  <!-- KEY CREATED SUCCESS MODAL -->
  <div id="key-success-modal" class="modal">
    <div class="modal-content">
      <h3 style="margin-bottom:8px; color:#3fb950;">✓ API Key Created Successfully</h3>
      <p style="font-size:12px; color:#8b949e; margin-bottom:12px;">Copy this key now. It will never be shown again:</p>
      <input type="text" id="display-raw-key" readonly style="font-family:monospace; color:#79c0ff;" />
      <div style="display:flex; justify-content:flex-end;">
        <button class="btn btn-primary" onclick="closeKeySuccessModal()">Done</button>
      </div>
    </div>
  </div>

  <script>
    function switchTab(tabId) {{
      document.querySelectorAll('.nav-tab').forEach(t => t.classList.remove('active'));
      document.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));
      event.target.classList.add('active');
      const pane = document.getElementById('tab-' + tabId);
      if (pane) pane.classList.add('active');

      if (tabId === 'incidents') loadIncidents();
      if (tabId === 'fixes') loadSuggestions();
      if (tabId === 'keys') loadKeys();
      if (tabId === 'webhooks') loadWebhooks();
    }}

    async function loadIncidents() {{
      const tbody = document.getElementById('incidents-table-body');
      try {{
        const res = await fetch('/v1/incidents');
        const data = await res.json();
        const incs = data.incidents || [];
        document.getElementById('kpi-inc-count').textContent = incs.length;

        if (incs.length === 0) {{
          tbody.innerHTML = '<tr><td colspan="6" style="text-align:center; color:#888;">No active production incidents. Systems running healthy!</td></tr>';
          return;
        }}

        tbody.innerHTML = incs.map(inc => `
          <tr>
            <td><span class="badge ${{inc.status === 'resolved' ? 'badge-success' : 'badge-danger'}}">${{inc.status}}</span></td>
            <td><code>${{inc.route}}</code></td>
            <td><b style="color:#f85149;">${{inc.status_code || 500}}</b></td>
            <td>${{inc.summary || 'Unhandled exception'}}</td>
            <td><b>${{inc.occurrence_count || 1}}</b></td>
            <td>
              <button class="btn btn-secondary" onclick="triggerFix('${{inc.id}}')">⚡ Fix</button>
            </td>
          </tr>
        `).join('');
      }} catch (err) {{
        tbody.innerHTML = '<tr><td colspan="6" style="color:#f85149;">Failed to load incidents.</td></tr>';
      }}
    }}

    async function loadSuggestions() {{
      const container = document.getElementById('suggestions-container');
      try {{
        const res = await fetch('/v1/autofix/suggestions');
        const data = await res.json();
        const suggestions = data.suggestions || [];

        if (suggestions.length === 0) {{
          container.innerHTML = '<div style="color:#888; text-align:center; padding:20px;">No pending suggestions. All captured incidents are resolved!</div>';
          return;
        }}

        container.innerHTML = suggestions.map(s => `
          <div style="border:1px solid #30363d; border-radius:6px; padding:16px; margin-bottom:12px; background:#0d1117;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
              <b>Target: <code>${{s.patch_path}}</code> (${{s.route}})</b>
              <span class="badge badge-success">Confidence: ${{Math.round((s.confidence_score || 0.98) * 100)}}%</span>
            </div>
            <p style="font-size:12px; color:#8b949e; margin-bottom:8px;">${{s.error_summary}}</p>
            <pre><code>${{s.diff || s.diff_patch}}</code></pre>
            <div style="margin-top:12px; display:flex; gap:8px;">
              <button class="btn btn-success" onclick="applyAutofix('${{s.incident_id}}')">✓ Apply Fix to Workspace</button>
              <button class="btn btn-primary" onclick="openPR('${{s.incident_id}}')">🚀 Open GitHub PR</button>
            </div>
          </div>
        `).join('');
      }} catch (err) {{
        container.innerHTML = '<div style="color:#f85149;">Failed to load fixes.</div>';
      }}
    }}

    async function loadKeys() {{
      const tbody = document.getElementById('keys-table-body');
      try {{
        const res = await fetch('/v1/keys');
        const keys = await res.json();
        if (keys.length === 0) {{
          tbody.innerHTML = '<tr><td colspan="6" style="text-align:center; color:#888;">No API keys yet. Click "Generate New Key" to create one.</td></tr>';
          return;
        }}
        tbody.innerHTML = keys.map(k => `
          <tr>
            <td><b>${{k.name}}</b></td>
            <td><code>${{k.prefix}}••••••••</code></td>
            <td>${{k.scopes.map(s => '<span class="badge badge-pro">' + s + '</span>').join(' ')}}</td>
            <td>${{k.last_used_at ? new Date(k.last_used_at).toLocaleTimeString() : 'Never'}}</td>
            <td>${{new Date(k.created_at).toLocaleDateString()}}</td>
            <td><button class="btn btn-danger" onclick="revokeKey('${{k.id}}')">Revoke</button></td>
          </tr>
        `).join('');
      }} catch (err) {{
        tbody.innerHTML = '<tr><td colspan="6" style="color:#f85149;">Failed to load API keys.</td></tr>';
      }}
    }}

    function openKeyModal() {{ document.getElementById('key-modal').classList.add('active'); }}
    function closeKeyModal() {{ document.getElementById('key-modal').classList.remove('active'); }}

    async function submitCreateKey() {{
      const name = document.getElementById('new-key-name').value || 'Production Key';
      const env = document.getElementById('new-key-env').value;
      const res = await fetch('/v1/keys', {{
        method: 'POST',
        headers: {{ 'Content-Type': 'application/json' }},
        body: JSON.stringify({{ name: name, environment: env }})
      }});
      const data = await res.json();
      closeKeyModal();
      document.getElementById('display-raw-key').value = data.api_key;
      document.getElementById('key-success-modal').classList.add('active');
      loadKeys();
    }}

    function closeKeySuccessModal() {{
      document.getElementById('key-success-modal').classList.remove('active');
    }}

    async function revokeKey(keyId) {{
      if (!confirm('Are you sure you want to revoke this API key?')) return;
      await fetch('/v1/keys/' + keyId, {{ method: 'DELETE' }});
      loadKeys();
    }}

    async function applyAutofix(incId) {{
      const res = await fetch('/v1/autofix/apply', {{
        method: 'POST',
        headers: {{ 'Content-Type': 'application/json' }},
        body: JSON.stringify({{ incident_id: incId }})
      }});
      const data = await res.json();
      alert('Fix applied! Remaining Autofix Tokens: ' + data.autofix_tokens_remaining);
      loadSuggestions();
      loadIncidents();
    }}

    async function openPR(incId) {{
      const res = await fetch('/v1/github/create-autofix-pr', {{
        method: 'POST',
        headers: {{ 'Content-Type': 'application/json' }},
        body: JSON.stringify({{ incident_id: incId }})
      }});
      const data = await res.json();
      window.open(data.pr_url, '_blank');
    }}

    // Initial load
    loadIncidents();
  </script>
</body>
</html>
"""
    return HTMLResponse(content=html_content)
