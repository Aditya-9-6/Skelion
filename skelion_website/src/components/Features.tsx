import React, { useState } from 'react';
import { 
  ShieldAlert, 
  Cpu, 
  GitPullRequest, 
  Lock, 
  Terminal, 
  Activity, 
  Zap, 
  CheckCircle2, 
  Code2
} from 'lucide-react';

export const Features: React.FC = () => {
  const [selectedFeature, setSelectedFeature] = useState(0);

  const features = [
    {
      id: 'proxy',
      title: 'Fail-Open Resilience Proxy',
      category: 'EDGE INFRASTRUCTURE',
      icon: ShieldAlert,
      color: 'text-cyan-600',
      bgColor: 'bg-cyan-50',
      borderColor: 'border-cyan-200',
      tagline: 'Never drop production requests on internal telemetry hiccups.',
      description:
        'Skelion sits transparently between your ingress gateway and upstream services. With its strict fail-open contract, any unexpected proxy exception, network timeout, or downstream stall immediately bypasses the engine, delivering the original payload unharmed.',
      bullets: [
        'Sub-5ms hot-path request proxying with zero memory buffering bloat',
        'Automatic circuit breaking with jittered backoff on saturated backends',
        'Configurable error-rate threshold triggers with auto-drain mechanisms',
        'Transparent reverse proxy support for FastAPI, Node.js, Go, and Ruby',
      ],
      codeSnippet: `# skelion_edge/proxy.py: Fail-open guarantee
try:
    response = await skelion_inspect_and_forward(request)
except Exception as exc:
    # Fail-open: log metric, bypass telemetry, return authentic request
    prometheus.rate_limits_saved_total.inc()
    return await raw_upstream_forward(request)`,
    },
    {
      id: 'incident',
      title: 'Autonomous Sandboxed Remediation',
      category: 'AI INCIDENT RESPONSE',
      icon: GitPullRequest,
      color: 'text-purple-600',
      bgColor: 'bg-purple-50',
      borderColor: 'border-purple-200',
      tagline: 'From 500 error to verified GitHub PR in seconds.',
      description:
        'When an uncaught exception strikes, Skelion captures the trace, spins up an isolated sandbox micro-container, reproduces the failure deterministically, writes a reproduction test, and synthesizes an AST-verified patch that passes all regression tests.',
      bullets: [
        'Deterministic synthetic replay generation from live crash telemetry',
        'Sandbox test-runner validates fix against entire repository test suite',
        'Opens GitHub PR with full diagnostic cards and root-cause explanations',
        'Auto-merge support for verified non-breaking patches in Enterprise',
      ],
      codeSnippet: `// Diagnostic PR Output
[Skelion Agent] Bug identified: Missing null check in coupon validator
[Verification] Ran 42 tests in sandbox: 42 passed (0 regressions)
[GitHub] PR #142 submitted with automated review card`,
    },
    {
      id: 'keypool',
      title: 'Shared Multi-Provider LLM Key Pool',
      category: 'AI TOKEN ORCHESTRATION',
      icon: Cpu,
      color: 'text-emerald-600',
      bgColor: 'bg-emerald-50',
      borderColor: 'border-emerald-200',
      tagline: 'Eliminate HTTP 429 rate limits across distributed agent nodes.',
      description:
        'Stop waking up to exhausted TPM/RPM limits. Skelion pools API infrastructure across high-throughput resilient edge nodes, applying exponential backoff and transparent key rotation without dropping a single user prompt.',
      bullets: [
        'Zero 429 dropped requests across high-volume burst traffic',
        'Dynamic failover from tier-limited keys to warm standby keys',
        'Strict Cost + 30% margin ledger accounting ensuring predictable gross margins',
        'Supports both Hosted shared pools and Bring-Your-Own-Key (BYOK) local modes',
      ],
      codeSnippet: `# Dynamic resilient node rotation
node = await key_pool.acquire(tier="resilient_mesh")
try:
    return await agent_generate(prompt, node=node)
except RateLimitError:
    key_pool.penalize(node, cooldown_secs=30)
    return await key_pool.retry_transparent(prompt)`,
    },
    {
      id: 'redact',
      title: 'Zero-Trust PII Redaction Engine',
      category: 'DATA SECURITY & COMPLIANCE',
      icon: Lock,
      color: 'text-pink-600',
      bgColor: 'bg-pink-50',
      borderColor: 'border-pink-200',
      tagline: 'Your secrets never touch LLMs or third-party monitoring vendors.',
      description:
        'Skelion scrubs sensitive credentials, session tokens, JWTs, credit card numbers, and PII right at the proxy boundary before telemetry data or crash traces are ever recorded or passed to AI models.',
      bullets: [
        'Automatic masking of Authorization, Cookie, X-Api-Key, and Bearer tokens',
        'Regex and entropy-based API key scrubbers for AWS, Stripe, and GitHub tokens',
        'Zero-retention PII sanitization & regex scrubbing on incoming/outgoing payloads',
        'Zero training policy on customer payloads and repository code',
      ],
      codeSnippet: `// Sample redacted payload before LLM inspection
{
  "headers": {
    "authorization": "[REDACTED_BEARER_TOKEN]",
    "cookie": "session=[REDACTED_SESSION_ID]"
  },
  "user": { "email": "[REDACTED_EMAIL]" }
}`,
    },
    {
      id: 'web-console',
      title: 'Cloud Agent Console & Hallmark Provider',
      category: 'DEVELOPER EXPERIENCE',
      icon: Terminal,
      color: 'text-amber-600',
      bgColor: 'bg-amber-50',
      borderColor: 'border-amber-200',
      tagline: 'Real-time telemetry and Impeccable Validator in your browser.',
      description:
        'Access the Skelion Web Platform to inspect live edge incidents, visualize architecture with REA Graphs, generate diagrams with Scrapling Canvas, and manage autonomous incident repairs directly from the cloud console.',
      bullets: [
        'Hallmark Provider & Impeccable Validator syntax verification',
        'Live credit status, token top-up, and plan switching without restart',
        'REA Graph dependency and distributed service visualization',
        'Direct Cloud Agent integration for autonomous file editing and tool use',
      ],
      codeSnippet: `# Launch the interactive web console
https://skelion.dev/#console

# Full autonomous cloud agent with GitHub integration`,
    },
    {
      id: 'telemetry',
      title: 'Prometheus & Real-time Webhooks',
      category: 'OBSERVABILITY & ALERTS',
      icon: Activity,
      color: 'text-blue-600',
      bgColor: 'bg-blue-50',
      borderColor: 'border-blue-200',
      tagline: 'Plug-and-play metrics with Grafana templates and Slack alerts.',
      description:
        'Skelion exposes production-grade Prometheus metrics on /metrics. Track rate limits saved, proxy latencies, sandbox execution times, and automated PR success rates with turnkey Grafana dashboards and instant Slack notifications.',
      bullets: [
        'Standard Prometheus metrics: rate_limits_saved_total, proxy_latency_ms',
        'Instant Slack, Discord, and PagerDuty alert dispatches on anomaly spikes',
        'Audit log with append-only ledger entries for all remediation actions',
        'Structured JSON logging with request tracing IDs across microservices',
      ],
      codeSnippet: `# curl http://localhost:8002/metrics
# HELP rate_limits_saved_total Requests preserved via key-pool backoff
# TYPE rate_limits_saved_total counter
rate_limits_saved_total 1842
skelion_incident_resolved_total 89`,
    },
  ];

  return (
    <section id="features" className="py-24 relative overflow-hidden">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center max-w-3xl mx-auto mb-16">
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-cyan-50 border border-cyan-200 text-cyan-800 mb-3 shadow-sm">
            <Zap className="w-3.5 h-3.5 text-cyan-600" />
            <span>ENTERPRISE-GRADE CAPABILITIES</span>
          </div>
          <h2 className="text-3xl sm:text-5xl font-extrabold text-slate-950 tracking-tight">
            Built for Zero-Downtime Resilience
          </h2>
          <p className="mt-4 text-base sm:text-lg text-slate-600">
            Engineered to safeguard high-throughput microservices, eliminate developer firefighting,
            and autonomously repair production regressions before they affect your users.
          </p>
        </div>

        {/* Interactive Feature Tabs & Spotlight Display */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
          {/* Feature List (Left Column) */}
          <div className="lg:col-span-5 space-y-3">
            {features.map((feat, index) => {
              const Icon = feat.icon;
              const isSelected = selectedFeature === index;
              return (
                <button
                  key={feat.id}
                  onClick={() => setSelectedFeature(index)}
                  className={`w-full text-left p-4 rounded-xl border transition-all duration-200 flex items-start gap-4 ${
                    isSelected
                      ? 'bg-white border-2 border-cyan-500 shadow-lg shadow-cyan-500/10 ring-2 ring-cyan-500/15'
                      : 'bg-white/70 backdrop-blur-md border-slate-200/90 hover:bg-white hover:border-slate-300 shadow-sm'
                  }`}
                >
                  <div className={`p-2.5 rounded-lg border ${feat.bgColor} ${feat.borderColor} shrink-0 shadow-sm`}>
                    <Icon className={`w-5 h-5 ${feat.color}`} />
                  </div>
                  <div>
                    <span className="text-[10px] uppercase font-mono tracking-wider text-slate-400">
                      {feat.category}
                    </span>
                    <h3 className="text-base font-bold text-slate-900 mt-0.5">{feat.title}</h3>
                    <p className="text-xs text-slate-600 mt-1 line-clamp-2">{feat.tagline}</p>
                  </div>
                </button>
              );
            })}
          </div>

          {/* Feature Spotlight Details & Code Sandbox (Right Column) */}
          <div className="lg:col-span-7">
            {(() => {
              const feat = features[selectedFeature];
              const Icon = feat.icon;
              return (
                <div className="glass-panel p-6 sm:p-8 rounded-2xl border border-slate-200/90 shadow-2xl relative">
                  <div className="flex items-center gap-3 mb-4">
                    <div className={`p-3 rounded-xl border ${feat.bgColor} ${feat.borderColor} shadow-sm`}>
                      <Icon className={`w-6 h-6 ${feat.color}`} />
                    </div>
                    <div>
                      <span className="text-xs font-mono uppercase text-cyan-700 font-semibold">
                        {feat.category}
                      </span>
                      <h3 className="text-2xl font-bold text-slate-950">{feat.title}</h3>
                    </div>
                  </div>

                  <p className="text-sm text-slate-600 leading-relaxed mb-6">
                    {feat.description}
                  </p>

                  <div className="mb-6">
                    <h4 className="text-xs font-mono uppercase text-slate-500 font-bold mb-3 tracking-wider">
                      Key Highlights
                    </h4>
                    <ul className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                      {feat.bullets.map((bullet, idx) => (
                        <li key={idx} className="flex items-start gap-2 text-xs text-slate-700">
                          <CheckCircle2 className="w-4 h-4 text-cyan-600 shrink-0 mt-0.5" />
                          <span>{bullet}</span>
                        </li>
                      ))}
                    </ul>
                  </div>

                  {/* Code Sandbox View */}
                  <div className="rounded-xl overflow-hidden border border-slate-800 bg-slate-950 shadow-xl">
                    <div className="bg-slate-900 px-4 py-2 border-b border-slate-800 flex items-center justify-between">
                      <span className="text-xs font-mono text-slate-300 flex items-center gap-1.5">
                        <Code2 className="w-3.5 h-3.5 text-cyan-400" />
                        Implementation Snippet
                      </span>
                      <span className="text-[10px] font-mono text-slate-400">Production Verified</span>
                    </div>
                    <pre className="p-4 text-xs font-mono text-cyan-300 overflow-x-auto leading-relaxed">
                      <code>{feat.codeSnippet}</code>
                    </pre>
                  </div>
                </div>
              );
            })()}
          </div>
        </div>
      </div>
    </section>
  );
};
