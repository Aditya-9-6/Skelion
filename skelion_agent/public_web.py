# skelion_agent/public_web.py — Public Marketing Landing Page & Legal Compliance Pages

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter(tags=["Public Web & Legal"])


@router.get("/", response_class=HTMLResponse)
@router.get("/landing", response_class=HTMLResponse)
async def serve_landing_page():
    """Serve the public commercial landing page for Skelion SaaS."""
    html_content = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Skelion — Autonomous Production Intelligence & Self-Healing Platform</title>
  <meta name="description" content="AI coding assistants are blind to production. Skelion intercepts production crashes fail-open, scrubs PII, tests AST patches in isolated replay sandboxes, and opens 0-regression PRs." />
  <style>
    :root {
      --bg: #090d16;
      --card-bg: #111827;
      --card-border: #1f2937;
      --primary: #38bdf8;
      --accent: #10b981;
      --text: #f3f4f6;
      --muted: #9ca3af;
      --code-bg: #030712;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      background: var(--bg);
      color: var(--text);
      line-height: 1.6;
      overflow-x: hidden;
    }
    a { color: var(--primary); text-decoration: none; }
    a:hover { text-decoration: underline; }
    .container { max-width: 1200px; margin: 0 auto; padding: 0 24px; }
    
    /* NAV */
    nav {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 24px 0;
      border-bottom: 1px solid rgba(255,255,255,0.06);
    }
    .logo {
      font-size: 22px;
      font-weight: 800;
      letter-spacing: -0.5px;
      display: flex;
      align-items: center;
      gap: 10px;
    }
    .logo-badge {
      background: linear-gradient(135deg, #38bdf8, #818cf8);
      color: #000;
      font-size: 11px;
      padding: 2px 8px;
      border-radius: 12px;
      font-weight: 700;
    }
    .nav-links { display: flex; gap: 28px; align-items: center; }
    .nav-links a { color: var(--muted); font-size: 14px; font-weight: 500; transition: color 0.2s; }
    .nav-links a:hover { color: #fff; text-decoration: none; }
    .btn {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 10px 20px;
      border-radius: 8px;
      font-size: 14px;
      font-weight: 600;
      cursor: pointer;
      transition: all 0.2s;
      text-decoration: none !important;
    }
    .btn-primary {
      background: linear-gradient(135deg, #38bdf8 0%, #2563eb 100%);
      color: #fff;
      border: none;
      box-shadow: 0 4px 14px rgba(56, 189, 248, 0.3);
    }
    .btn-primary:hover {
      box-shadow: 0 6px 20px rgba(56, 189, 248, 0.5);
      transform: translateY(-1px);
    }
    .btn-outline {
      background: rgba(255,255,255,0.05);
      color: #fff;
      border: 1px solid var(--card-border);
    }
    .btn-outline:hover { background: rgba(255,255,255,0.1); }

    /* HERO */
    .hero {
      text-align: center;
      padding: 90px 0 60px;
      position: relative;
    }
    .hero-pill {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      background: rgba(56, 189, 248, 0.1);
      border: 1px solid rgba(56, 189, 248, 0.3);
      padding: 6px 14px;
      border-radius: 20px;
      font-size: 13px;
      color: var(--primary);
      margin-bottom: 24px;
    }
    .hero h1 {
      font-size: 56px;
      font-weight: 900;
      letter-spacing: -1.5px;
      line-height: 1.15;
      margin-bottom: 24px;
      background: linear-gradient(180deg, #ffffff 0%, #cbd5e1 100%);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
    }
    .hero p {
      font-size: 20px;
      color: var(--muted);
      max-width: 780px;
      margin: 0 auto 36px;
    }
    .hero-actions {
      display: flex;
      justify-content: center;
      gap: 16px;
      margin-bottom: 60px;
    }

    /* CODE DEMO WINDOW */
    .demo-window {
      background: var(--code-bg);
      border: 1px solid var(--card-border);
      border-radius: 12px;
      overflow: hidden;
      box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.7);
      text-align: left;
      margin: 0 auto 100px;
      max-width: 900px;
    }
    .window-header {
      background: #111827;
      padding: 12px 16px;
      display: flex;
      align-items: center;
      gap: 8px;
      border-bottom: 1px solid var(--card-border);
    }
    .dot { width: 12px; height: 12px; border-radius: 50%; }
    .dot-red { background: #ef4444; }
    .dot-yellow { background: #f59e0b; }
    .dot-green { background: #10b981; }
    .window-title { font-size: 12px; color: var(--muted); margin-left: 12px; font-family: monospace; }
    .code-body { padding: 24px; font-family: monospace; font-size: 13px; overflow-x: auto; line-height: 1.8; }
    .line-comment { color: #6b7280; }
    .line-error { color: #f87171; background: rgba(239, 68, 68, 0.1); padding: 2px 4px; border-radius: 4px; }
    .line-success { color: #34d399; font-weight: 600; }
    .line-step { color: #38bdf8; }

    /* GRID FEATURES */
    .features-grid {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 24px;
      margin-bottom: 120px;
    }
    .feature-card {
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      padding: 32px;
      border-radius: 12px;
      transition: border-color 0.2s;
    }
    .feature-card:hover { border-color: rgba(56, 189, 248, 0.4); }
    .feature-icon {
      font-size: 28px;
      margin-bottom: 16px;
      display: inline-block;
    }
    .feature-card h3 { font-size: 18px; margin-bottom: 10px; color: #fff; }
    .feature-card p { font-size: 14px; color: var(--muted); }

    /* PRICING */
    .pricing-section {
      text-align: center;
      padding-bottom: 120px;
    }
    .pricing-grid {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 28px;
      margin-top: 50px;
    }
    .price-card {
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      padding: 40px 32px;
      border-radius: 16px;
      position: relative;
      text-align: left;
    }
    .price-card.popular {
      border: 2px solid var(--primary);
      box-shadow: 0 0 40px rgba(56, 189, 248, 0.15);
    }
    .badge-pop {
      position: absolute;
      top: -12px;
      left: 50%;
      transform: translateX(-50%);
      background: var(--primary);
      color: #000;
      font-size: 11px;
      font-weight: 800;
      padding: 3px 12px;
      border-radius: 20px;
      text-transform: uppercase;
    }
    .price-card h3 { font-size: 20px; color: #fff; margin-bottom: 8px; }
    .price-val { font-size: 40px; font-weight: 800; color: #fff; margin: 18px 0; }
    .price-val span { font-size: 16px; color: var(--muted); font-weight: 400; }
    .feature-list { list-style: none; margin: 24px 0 32px; }
    .feature-list li {
      font-size: 13px;
      color: var(--muted);
      margin-bottom: 12px;
      display: flex;
      align-items: center;
      gap: 10px;
    }
    .feature-list li::before { content: "✓"; color: var(--accent); font-weight: 800; }

    /* FOOTER */
    footer {
      border-top: 1px solid rgba(255,255,255,0.08);
      padding: 40px 0;
      font-size: 13px;
      color: var(--muted);
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
    .footer-links { display: flex; gap: 24px; }

    @media (max-width: 850px) {
      .hero h1 { font-size: 38px; }
      .features-grid, .pricing-grid { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
  <div class="container">
    <nav>
      <div class="logo">
        ⚡ Skelion <span class="logo-badge">SaaS v2.0</span>
      </div>
      <div class="nav-links">
        <a href="#features">Features</a>
        <a href="#pricing">Pricing</a>
        <a href="/portal">Customer Portal</a>
        <a href="/docs">API Docs</a>
        <a href="/portal" class="btn btn-primary">Open Console →</a>
      </div>
    </nav>

    <section class="hero">
      <div class="hero-pill">
        🛡️ Fail-Open Edge Resilience + Zero-PII Production Intelligence
      </div>
      <h1>Modern AI Coding is Blind to Production.<br><span style="color:#38bdf8;">Skelion Heals It In Realtime.</span></h1>
      <p>
        AI assistants write code in your IDE, but they never see runtime crashes. 
        Skelion intercepts edge 500s fail-open, scrubs sensitive PII, proves AST patches in isolated replay sandboxes, and opens 0-regression Pull Requests.
      </p>
      <div class="hero-actions">
        <a href="/portal" class="btn btn-primary" style="padding:14px 28px; font-size:16px;">Start Free with 2 Lines of Code →</a>
        <a href="/docs" class="btn btn-outline" style="padding:14px 28px; font-size:16px;">View Documentation</a>
      </div>

      <!-- INTERACTIVE ANIMATED FLOW WINDOW -->
      <div class="demo-window">
        <div class="window-header">
          <div class="dot dot-red"></div>
          <div class="dot dot-yellow"></div>
          <div class="dot dot-green"></div>
          <span class="window-title">skelion-edge-pipeline // live-telemetry-feed</span>
        </div>
        <div class="code-body">
          <div class="line-comment">// 1. Drop-in Middleware Intercepts Production Crash Fail-Open (0 Downtime):</div>
          <div><span class="line-error">💥 [CRASH] POST /api/v1/orders/checkout — 500 TypeError: Cannot read properties of undefined (reading 'billing_address')</span></div>
          <div class="line-step">🛡️ [Skelion SDK] Fail-Open Boundary Engaged: Request buffered cleanly. End-user receives synthetic fallback.</div>
          <br>
          <div class="line-comment">// 2. Zero-PII Sanitization & Deterministic Fingerprinting:</div>
          <div>🔒 Authorization Bearer: [REDACTED] | Card Number: [REDACTED] | User PII: Cleansed</div>
          <div>🧬 Generated Incident Fingerprint: <code>fp_4e1a179c0f</code> (Deduplicated occurrence: #14)</div>
          <br>
          <div class="line-comment">// 3. Isolated Sandbox Replay & Mathematical Proof:</div>
          <div>🧪 Executing Replay Sandbox: Reproducing crash from sanitized state trace... [PASS]</div>
          <div>🧠 Groq 120B / Qwen 27B AST Synthesizer: Generated AST patch for <code>src/controllers/checkout.js</code></div>
          <div>📊 Regression Proof: 16/16 Unit Tests Passed, 0 Regressions. Proof Score: 1.000</div>
          <br>
          <div class="line-comment">// 4. Automated Autonomous GitHub Pull Request:</div>
          <div class="line-success">🚀 Opened Pull Request #260 on github.com/company/api [skelion/fix-fp_4e1a1] with verified replay verification!</div>
        </div>
      </div>
    </section>

    <!-- FEATURES -->
    <section id="features" style="padding-bottom: 80px;">
      <div style="text-align: center; margin-bottom: 50px;">
        <h2 style="font-size: 34px; margin-bottom: 12px;">Engineered for Production Reliability</h2>
        <p style="color: var(--muted);">Everything engineering teams need to close the loop between runtime crashes and IDE fixes.</p>
      </div>

      <div class="features-grid">
        <div class="feature-card">
          <div class="feature-icon">🛡️</div>
          <h3>Guaranteed Fail-Open</h3>
          <p>Skelion never crashes your app or blocks production traffic. If telemetry ingress is ever unreachable, client apps continue seamlessly without latency overhead.</p>
        </div>
        <div class="feature-card">
          <div class="feature-icon">🔒</div>
          <h3>Zero-PII Client Masking</h3>
          <p>Credit cards, authorization tokens, cookies, and passwords are sanitized before leaving your infrastructure. Full compliance with SOC2, GDPR, and HIPAA.</p>
        </div>
        <div class="feature-card">
          <div class="feature-icon">🧪</div>
          <h3>Mathematical Replay Sandbox</h3>
          <p>Patches are never suggested blindly. Every fix is simulated in an isolated container sandbox against the exact captured failure trace to guarantee zero regressions.</p>
        </div>
        <div class="feature-card">
          <div class="feature-icon">🤖</div>
          <h3>Autonomous GitHub PR Bot</h3>
          <p>Self-healing fixes are delivered directly to your engineering team as ready-to-merge Pull Requests with complete verification proof and test coverage.</p>
        </div>
        <div class="feature-card">
          <div class="feature-icon">🧩</div>
          <h3>Drop-in SDKs (Node & Python)</h3>
          <p>Integrate in under 60 seconds with <code>@skelion/node</code> for Express or <code>skelion</code> for FastAPI and ASGI applications.</p>
        </div>
        <div class="feature-card">
          <div class="feature-icon">⚡</div>
          <h3>Pocket-Friendly Token Pacing</h3>
          <p>Dual-window token quotas prevent runaway spending. High 5-hour burst limits let you survive incident spikes without paying astronomical cloud overage fees.</p>
        </div>
      </div>
    </section>

    <!-- PRICING -->
    <section id="pricing" class="pricing-section">
      <h2 style="font-size: 34px; margin-bottom: 12px;">Pocket-Friendly, Predictable Pricing</h2>
      <p style="color: var(--muted);">No unexpected overages. Upgrade or refill credits on demand via Razorpay (UPI/INR) or Stripe (USD).</p>

      <div class="pricing-grid">
        <div class="price-card">
          <h3>Starter</h3>
          <p style="color:var(--muted); font-size:13px;">For solo developers and side projects</p>
          <div class="price-val">₹0 <span>/ forever</span></div>
          <a href="/portal" class="btn btn-outline" style="width:100%; justify-content:center;">Get Started Free</a>
          <ul class="feature-list">
            <li>500 Tokens / 5-hour burst</li>
            <li>1,500 Tokens / weekly window</li>
            <li>50,000 Autofix tokens included</li>
            <li>Community Replay Sandbox</li>
            <li>Fail-Open Drop-in SDKs</li>
          </ul>
        </div>

        <div class="price-card popular">
          <div class="badge-pop">Most Popular</div>
          <h3>Pro Developer</h3>
          <p style="color:var(--muted); font-size:13px;">For fast-moving startups & scaling APIs</p>
          <div class="price-val">₹2,499 <span>/ month ($29)</span></div>
          <a href="/portal" class="btn btn-primary" style="width:100%; justify-content:center;">Upgrade to Pro</a>
          <ul class="feature-list">
            <li>3,000 Tokens / 5-hour burst</li>
            <li>12,000 Tokens / weekly window</li>
            <li>200,000 Autofix tokens included</li>
            <li>Autonomous GitHub PR Bot</li>
            <li>Priority Sandbox Execution (Groq 120B)</li>
            <li>Webhook Alert Integrations (Slack/Discord)</li>
          </ul>
        </div>

        <div class="price-card">
          <h3>Team & Business</h3>
          <p style="color:var(--muted); font-size:13px;">For engineering orgs and critical workloads</p>
          <div class="price-val">₹7,999 <span>/ month ($99)</span></div>
          <a href="/portal" class="btn btn-outline" style="width:100%; justify-content:center;">Launch Team Plan</a>
          <ul class="feature-list">
            <li>10,000 Tokens / 5-hour burst</li>
            <li>40,000 Tokens / weekly window</li>
            <li>1,000,000 Autofix tokens included</li>
            <li>Unlimited Team Members & RBAC</li>
            <li>Dedicated Spryzen Edge WAF Proxy</li>
            <li>99.9% Production Uptime SLA</li>
          </ul>
        </div>
      </div>
    </section>

    <!-- FOOTER -->
    <footer>
      <div>
        © 2026 Skelion Technologies Inc. All rights reserved.
      </div>
      <div class="footer-links">
        <a href="/terms">Terms of Service</a>
        <a href="/privacy">Privacy Policy</a>
        <a href="/refund">Refund Policy</a>
        <a href="/portal">Portal</a>
        <a href="/docs">Docs</a>
      </div>
    </footer>
  </div>
</body>
</html>
"""
    return HTMLResponse(content=html_content)


@router.get("/terms", response_class=HTMLResponse)
async def serve_terms_of_service():
    """Serve Terms of Service legal compliance document."""
    html_content = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Terms of Service — Skelion</title>
  <style>
    body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #090d16; color: #e2e8f0; line-height: 1.7; padding: 40px 20px; }
    .container { max-width: 800px; margin: 0 auto; background: #111827; border: 1px solid #1f2937; padding: 40px; border-radius: 12px; }
    h1 { font-size: 28px; margin-bottom: 20px; color: #38bdf8; }
    h2 { font-size: 18px; margin: 24px 0 10px; color: #fff; }
    p, li { font-size: 14px; color: #9ca3af; margin-bottom: 12px; }
    a { color: #38bdf8; text-decoration: none; }
  </style>
</head>
<body>
  <div class="container">
    <h1>Terms of Service</h1>
    <p>Last Updated: October 30, 2026</p>
    
    <h2>1. Acceptance of Terms</h2>
    <p>By accessing or using the Skelion SaaS platform, client SDKs (@skelion/node, skelion-python), or edge proxy (Spryzen WAF), you agree to be bound by these Terms of Service.</p>

    <h2>2. Service Description & Fail-Open Resilience</h2>
    <p>Skelion provides automated runtime telemetry ingestion, zero-PII sanitization, AST patch synthesis, and replay verification. All Skelion client SDKs are engineered to operate strictly fail-open: in the event of upstream network interruption, customer application traffic is preserved without disruption.</p>

    <h2>3. Scoped API Key Governance</h2>
    <p>Users are responsible for safeguarding API keys (skl_live_... / skl_test_...). You agree to notify Skelion immediately upon suspecting any unauthorized compromise of your organization credentials.</p>

    <h2>4. Token Quotas & Billing</h2>
    <p>Token usage is metered according to our dual-window pacing model (5-hour burst window and 7-day weekly window). Subscriptions renew automatically every 30 days unless canceled prior to the renewal date.</p>

    <h2>5. Limitation of Liability</h2>
    <p>Skelion is provided "as is". While our replay sandbox verifies patches with 0-regression proofs, software teams remain responsible for reviewing and merging GitHub Pull Requests into their production repositories.</p>

    <p style="margin-top: 30px;"><a href="/">← Return to Homepage</a> | <a href="/portal">Customer Portal</a></p>
  </div>
</body>
</html>
"""
    return HTMLResponse(content=html_content)


@router.get("/privacy", response_class=HTMLResponse)
async def serve_privacy_policy():
    """Serve Privacy Policy legal compliance document."""
    html_content = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Privacy Policy — Skelion</title>
  <style>
    body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #090d16; color: #e2e8f0; line-height: 1.7; padding: 40px 20px; }
    .container { max-width: 800px; margin: 0 auto; background: #111827; border: 1px solid #1f2937; padding: 40px; border-radius: 12px; }
    h1 { font-size: 28px; margin-bottom: 20px; color: #38bdf8; }
    h2 { font-size: 18px; margin: 24px 0 10px; color: #fff; }
    p, li { font-size: 14px; color: #9ca3af; margin-bottom: 12px; }
    a { color: #38bdf8; text-decoration: none; }
  </style>
</head>
<body>
  <div class="container">
    <h1>Privacy Policy</h1>
    <p>Last Updated: October 30, 2026</p>

    <h2>1. Zero-PII Ingestion Commitment</h2>
    <p>Skelion is built from the ground up on a Zero-PII (Personally Identifiable Information) architectural boundary. All headers, query parameters, cookies, session identifiers, and body fields are sanitized through client-side masking before transmission.</p>

    <h2>2. Data Collected</h2>
    <ul>
      <li>Account Information: Organization name, email, GitHub identifier.</li>
      <li>Crash Telemetry: HTTP route path, method, response status code, sanitized stack traces.</li>
      <li>Billing Records: Payment transaction IDs from Razorpay and Stripe (we do not store raw credit card numbers).</li>
    </ul>

    <h2>3. How Telemetry is Used</h2>
    <p>Sanitized crash traces are processed exclusively to group error fingerprints, simulate isolated replay sandboxes, and synthesize verified code patches. Your source code and telemetry are never used to train public foundation models.</p>

    <h2>4. GDPR & CCPA Compliance</h2>
    <p>You have the right to request access, rectification, or complete deletion of your organization records at any time through the Customer Portal or by emailing privacy@skelion.dev.</p>

    <p style="margin-top: 30px;"><a href="/">← Return to Homepage</a> | <a href="/portal">Customer Portal</a></p>
  </div>
</body>
</html>
"""
    return HTMLResponse(content=html_content)


@router.get("/refund", response_class=HTMLResponse)
async def serve_refund_policy():
    """Serve Refund & Cancellation Policy legal compliance document."""
    html_content = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Refund & Cancellation Policy — Skelion</title>
  <style>
    body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #090d16; color: #e2e8f0; line-height: 1.7; padding: 40px 20px; }
    .container { max-width: 800px; margin: 0 auto; background: #111827; border: 1px solid #1f2937; padding: 40px; border-radius: 12px; }
    h1 { font-size: 28px; margin-bottom: 20px; color: #38bdf8; }
    h2 { font-size: 18px; margin: 24px 0 10px; color: #fff; }
    p, li { font-size: 14px; color: #9ca3af; margin-bottom: 12px; }
    a { color: #38bdf8; text-decoration: none; }
  </style>
</head>
<body>
  <div class="container">
    <h1>Refund & Cancellation Policy</h1>
    <p>Last Updated: October 30, 2026</p>

    <h2>1. 14-Day Money-Back Guarantee</h2>
    <p>If you are not completely satisfied with Skelion Pro or Team subscriptions, you may request a 100% full refund within 14 days of your initial purchase date, no questions asked.</p>

    <h2>2. Subscription Cancellations</h2>
    <p>You can cancel your recurring subscription at any time with one click from the <a href="/portal">Customer Portal</a>. Upon cancellation, you retain full access to your paid quota until the conclusion of your current billing period.</p>

    <h2>3. Prepaid Refill Passes</h2>
    <p>Unused prepaid token refill passes do not expire and rollover across monthly billing cycles until consumed.</p>

    <h2>4. How to Request a Refund</h2>
    <p>To request a refund, contact billing@skelion.dev with your Organization Name and Payment ID. Refunds are processed back to the original payment method (UPI / Credit Card / Netbanking) within 5–7 business days.</p>

    <p style="margin-top: 30px;"><a href="/">← Return to Homepage</a> | <a href="/portal">Customer Portal</a></p>
  </div>
</body>
</html>
"""
    return HTMLResponse(content=html_content)
