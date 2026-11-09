import React, { useState } from 'react';
import { 
  ShieldCheck, 
  Check, 
  X, 
  Zap, 
  GitPullRequest, 
  Server, 
  Lock, 
  Terminal, 
  Cpu, 
  Sparkles,
  ArrowRight
} from 'lucide-react';

export const WhyChooseUs: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'matrix' | 'loop' | 'proxy'>('matrix');

  const comparisonFeatures = [
    {
      feature: '24/7 Autonomous Plan-to-Issue-to-PR Loop',
      skelion: 'Full 24/7 Continuous Loop (Scans repo plans, awaits "accept", writes PRs)',
      cursorCopilot: 'None (Only runs when developer is actively typing in IDE)',
      sentryDatadog: 'None (Passive telemetry only; cannot write code or PRs)',
      gateways: 'None (Traffic routing only)',
    },
    {
      feature: 'Reverse Proxy Threat & Prompt-Injection Detector',
      skelion: 'Active Edge Loop (Sub-5ms, prompt injection shield, token burn guard)',
      cursorCopilot: 'None (No network reverse proxy)',
      sentryDatadog: 'None (Detects crashes after the fact, no active proxy defense)',
      gateways: 'Basic rate limiting only (No deep payload threat detection)',
    },
    {
      feature: 'Zero-Downtime Fail-Open Resilience Contract',
      skelion: 'Guaranteed (Engine failure never drops production user traffic)',
      cursorCopilot: 'N/A (Client-only tool)',
      sentryDatadog: 'N/A (Async monitoring agent only)',
      gateways: 'Varies (Proxy outages cause service downtime)',
    },
    {
      feature: 'Deterministic Crash Sandbox & Replay Verification',
      skelion: 'Isolated micro-container reproduces crash, generates test & verifies fix',
      cursorCopilot: 'None (Manual developer prompting required)',
      sentryDatadog: 'Stack trace snapshot only (No sandbox execution or PR generation)',
      gateways: 'None',
    },
    {
      feature: 'PII Redaction & Credential Sanitization',
      skelion: 'Zero-trust edge redaction before LLMs or third-party vendors see traces',
      cursorCopilot: 'Code context sent to provider servers',
      sentryDatadog: 'Client scrubbing filters (often leaks sensitive header tokens)',
      gateways: 'Optional or basic regex',
    },
    {
      feature: 'Token-Metered Append-Only Credit Ledger',
      skelion: 'Granular per-action accounting with Cost + 30% margin guarantee',
      cursorCopilot: 'Opaque flat monthly subscription with rate limits',
      sentryDatadog: 'Event volume billing with expensive overages',
      gateways: 'Pass-through token markup or seat licenses',
    },
  ];

  return (
    <section id="why-us" className="py-24 relative overflow-hidden bg-gradient-to-b from-white via-cyan-50/20 to-white border-y border-slate-200/80 scroll-mt-20">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Section Header */}
        <div className="text-center max-w-3xl mx-auto mb-16">
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-cyan-50 border border-cyan-200 text-cyan-800 mb-3 shadow-xs">
            <Sparkles className="w-3.5 h-3.5 text-cyan-600" />
            <span>UNMATCHED COMPETITIVE ADVANTAGE</span>
          </div>
          <h2 className="text-3xl sm:text-5xl font-extrabold text-slate-950 tracking-tight leading-tight">
            Why Engineering Teams Choose Skelion Over Competitors
          </h2>
          <p className="mt-4 text-base sm:text-lg text-slate-600 leading-relaxed">
            Unlike IDE extensions that only assist when you type, or monitoring tools that wake you up with raw errors,
            Skelion is an <strong>autonomous resilience ecosystem</strong> that protects your edge, hunts regressions,
            and writes verified PR fixes 24/7.
          </p>

          {/* Toggle Pills */}
          <div className="mt-8 inline-flex items-center p-1 rounded-2xl bg-slate-100 border border-slate-200 shadow-inner">
            <button
              onClick={() => setActiveTab('matrix')}
              className={`px-4 py-1.5 rounded-xl text-xs font-semibold transition ${
                activeTab === 'matrix' ? 'bg-white text-slate-900 shadow-sm font-bold' : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              Full Comparison Matrix
            </button>
            <button
              onClick={() => setActiveTab('loop')}
              className={`px-4 py-1.5 rounded-xl text-xs font-semibold transition ${
                activeTab === 'loop' ? 'bg-white text-slate-900 shadow-sm font-bold' : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              Autonomous Dev Loop
            </button>
            <button
              onClick={() => setActiveTab('proxy')}
              className={`px-4 py-1.5 rounded-xl text-xs font-semibold transition ${
                activeTab === 'proxy' ? 'bg-white text-slate-900 shadow-sm font-bold' : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              Reverse Proxy Threat Defense
            </button>
          </div>
        </div>

        {/* Tab 1: Comparison Matrix */}
        {activeTab === 'matrix' && (
          <div className="glass-panel rounded-3xl border border-slate-200 shadow-xl overflow-hidden animate-fade-in">
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse text-xs sm:text-sm">
                <thead>
                  <tr className="bg-slate-50 border-b border-slate-200 text-slate-700 font-mono">
                    <th className="py-4 px-6 font-bold w-1/4">Capability</th>
                    <th className="py-4 px-6 font-extrabold text-cyan-800 bg-cyan-100/60 border-x border-cyan-200 w-1/3">
                      <div className="flex items-center gap-1.5">
                        <ShieldCheck className="w-4 h-4 text-cyan-600" />
                        <span>Skelion Platform</span>
                      </div>
                    </th>
                    <th className="py-4 px-6 font-medium text-slate-600 w-1/6">Cursor / Copilot</th>
                    <th className="py-4 px-6 font-medium text-slate-600 w-1/6">Sentry / Datadog</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {comparisonFeatures.map((row, idx) => (
                    <tr key={idx} className="hover:bg-slate-50/50 transition">
                      <td className="py-4 px-6 font-semibold text-slate-900">
                        {row.feature}
                      </td>
                      <td className="py-4 px-6 font-bold text-cyan-950 bg-cyan-50/40 border-x border-cyan-100/80">
                        <div className="flex items-start gap-2">
                          <Check className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
                          <span>{row.skelion}</span>
                        </div>
                      </td>
                      <td className="py-4 px-6 text-slate-500">
                        <div className="flex items-start gap-1.5">
                          <X className="w-4 h-4 text-rose-500 shrink-0 mt-0.5" />
                          <span>{row.cursorCopilot}</span>
                        </div>
                      </td>
                      <td className="py-4 px-6 text-slate-500">
                        <div className="flex items-start gap-1.5">
                          <X className="w-4 h-4 text-rose-500 shrink-0 mt-0.5" />
                          <span>{row.sentryDatadog}</span>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Tab 2: Autonomous Dev Loop Spotlight */}
        {activeTab === 'loop' && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 items-center animate-fade-in">
            <div className="space-y-4">
              <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-indigo-50 border border-indigo-200 text-indigo-700">
                <GitPullRequest className="w-3.5 h-3.5" />
                <span>24/7 PLAN-TO-ISSUE-TO-PR AUTONOMY</span>
              </div>
              <h3 className="text-2xl sm:text-3xl font-extrabold text-slate-950">
                A Senior AI Engineer Working On Your Roadmap While You Sleep
              </h3>
              <p className="text-sm text-slate-600 leading-relaxed">
                Traditional AI tools require a developer to sit and prompt line by line. Skelion's Autonomous Dev Loop
                reads your repository markdown plans, converts pending roadmap items into structured GitHub issues,
                and waits for a single maintainer review word (<code className="font-mono bg-indigo-50 px-1 py-0.5 rounded text-indigo-800">accept</code>).
              </p>
              <ul className="space-y-2.5 text-xs text-slate-700">
                <li className="flex items-center gap-2">
                  <Check className="w-4 h-4 text-emerald-600" />
                  <span>Scans repository markdown plans and roadmaps 24/7 in the cloud</span>
                </li>
                <li className="flex items-center gap-2">
                  <Check className="w-4 h-4 text-emerald-600" />
                  <span>Creates detailed GitHub issues with target file paths &amp; acceptance criteria</span>
                </li>
                <li className="flex items-center gap-2">
                  <Check className="w-4 h-4 text-emerald-600" />
                  <span>One-word maintainer comment triggers AST patch synthesis in sandbox</span>
                </li>
                <li className="flex items-center gap-2">
                  <Check className="w-4 h-4 text-emerald-600" />
                  <span>Runs full pytest/jest test suites before opening verified pull requests</span>
                </li>
              </ul>
            </div>
            <div className="rounded-2xl border border-slate-800 bg-slate-950 p-5 shadow-2xl text-xs font-mono text-cyan-300 space-y-2">
              <div className="text-slate-400 pb-2 border-b border-slate-800 flex items-center justify-between">
                <span>autonomous_loop_daemon.log</span>
                <span className="text-emerald-400">● 24/7 Active</span>
              </div>
              <p className="text-slate-300">[02:14:02] Scanning docs/plans/ROADMAP.md: 3 tasks pending</p>
              <p className="text-indigo-400">[02:14:03] Generated GitHub Issue #194: "feat(auth): Add SAML session token cache"</p>
              <p className="text-amber-400">[02:15:22] Maintainer @lead-dev commented: "looks great, accept"</p>
              <p className="text-cyan-400">[02:15:23] Spin-up isolated sandbox micro-container (SHA: 8f9b2c)</p>
              <p className="text-emerald-400">[02:16:10] AST Synthesizer: 4 files modified, 36/36 tests passed (0 regressions)</p>
              <p className="text-white font-bold">[02:16:12] PR #195 submitted with diagnostic review card &amp; diff summary</p>
            </div>
          </div>
        )}

        {/* Tab 3: Reverse Proxy Threat Defense Spotlight */}
        {activeTab === 'proxy' && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 items-center animate-fade-in">
            <div className="space-y-4">
              <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-cyan-50 border border-cyan-200 text-cyan-800">
                <ShieldCheck className="w-3.5 h-3.5 text-cyan-600" />
                <span>ZERO-DOWNTIME THREAT DEFENSE</span>
              </div>
              <h3 className="text-2xl sm:text-3xl font-extrabold text-slate-950">
                Reverse Proxy Threat Detector with Fail-Open Guarantee
              </h3>
              <p className="text-sm text-slate-600 leading-relaxed">
                Positioned in front of your microservices and LLM applications, Skelion acts as an intelligent
                shield. It intercepts prompt-injection payloads, prevents recursive token burn rates, and adheres
                strictly to a fail-open contract: if our engine ever encounters an unexpected exception, it immediately
                bypasses without dropping customer traffic.
              </p>
              <ul className="space-y-2.5 text-xs text-slate-700">
                <li className="flex items-center gap-2">
                  <Check className="w-4 h-4 text-emerald-600" />
                  <span>Sub-5ms hot-path reverse proxy written for extreme concurrency</span>
                </li>
                <li className="flex items-center gap-2">
                  <Check className="w-4 h-4 text-emerald-600" />
                  <span>Live prompt-injection scanning and toxic payload quarantine</span>
                </li>
                <li className="flex items-center gap-2">
                  <Check className="w-4 h-4 text-emerald-600" />
                  <span>Zero-downtime fail-open: telemetry errors never cause 502/504 outages</span>
                </li>
                <li className="flex items-center gap-2">
                  <Check className="w-4 h-4 text-emerald-600" />
                  <span>Available on Pro Developer Tier and higher for continuous peace of mind</span>
                </li>
              </ul>
            </div>
            <div className="rounded-2xl border border-slate-800 bg-slate-950 p-5 shadow-2xl text-xs font-mono text-cyan-300 space-y-2">
              <div className="text-slate-400 pb-2 border-b border-slate-800 flex items-center justify-between">
                <span>edge_threat_proxy.log</span>
                <span className="text-cyan-400">&lt; 2.1ms Hot-path</span>
              </div>
              <p className="text-slate-300">[14:31:01.002] INGRESS POST /v1/agent/chat: 1,480 bytes</p>
              <p className="text-amber-400">[14:31:01.003] Threat Detector: Pattern matched: recursive jailbreak prompt</p>
              <p className="text-rose-400">[14:31:01.004] Quarantined toxic prompt payload (Threat ID: INJ-9821)</p>
              <p className="text-cyan-400">[14:31:01.005] Substituted sanitized policy response; 0 tokens debited</p>
              <p className="text-emerald-400">[14:31:01.006] Upstream LLM shielded from runaway token consumption</p>
            </div>
          </div>
        )}
      </div>
    </section>
  );
};
