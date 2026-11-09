import React, { useState, useEffect } from 'react';
import { 
  Terminal, 
  ShieldCheck, 
  Zap, 
  GitPullRequest, 
  CheckCircle2, 
  AlertTriangle, 
  Play, 
  RotateCcw, 
  Copy, 
  Check, 
  ExternalLink,
  ChevronRight,
  Server,
  Cpu,
  Lock
} from 'lucide-react';

interface HeroProps {
  onOpenCheckout: (planId?: string) => void;
}

interface IncidentStep {
  time: string;
  badge: string;
  badgeColor: string;
  title: string;
  detail: string;
}

export const Hero: React.FC<HeroProps> = ({ onOpenCheckout }) => {
  const [copiedCmd, setCopiedCmd] = useState<string | null>(null);
  const [activeScenario, setActiveScenario] = useState<'500' | '429' | 'leak'>('500');
  const [stepIndex, setStepIndex] = useState<number>(4);
  const [isPlaying, setIsPlaying] = useState<boolean>(true);

  const scenarios: Record<'500' | '429' | 'leak', { name: string; icon: any; steps: IncidentStep[] }> = {
    '500': {
      name: '500 Server Crash (Null Pointer)',
      icon: AlertTriangle,
      steps: [
        {
          time: '00:00.012',
          badge: 'EDGE PROXY',
          badgeColor: 'text-amber-300 bg-amber-400/10 border-amber-400/30',
          title: 'HTTP 500 Intercepted on POST /v1/checkout/pay',
          detail: 'Fail-open proxy engaged in 1.8ms. PII scrubbed: Authorization token and Bearer secret redacted.',
        },
        {
          time: '00:00.045',
          badge: 'ISOLATION',
          badgeColor: 'text-cyan-300 bg-cyan-400/10 border-cyan-400/30',
          title: 'Sandboxing Anomaly in Micro-Container',
          detail: 'Trace captured: TypeError: NoneType object has no attribute "discount_percent" in billing_rules.py:178',
        },
        {
          time: '00:00.120',
          badge: 'AI SYNTHESIS',
          badgeColor: 'text-purple-300 bg-purple-400/10 border-purple-400/30',
          title: 'Synthesizing AST-Verified Fix & Replay Test',
          detail: 'Generated safe fallback coupon handler and deterministic pytest test_coupon_none_safety()',
        },
        {
          time: '00:00.310',
          badge: 'VERIFICATION',
          badgeColor: 'text-emerald-300 bg-emerald-400/10 border-emerald-400/30',
          title: 'Sandbox Test Suite Passed (100% Green)',
          detail: 'Synthetic execution completed in 180ms without regressions. Zero side-effects detected.',
        },
        {
          time: '00:00.420',
          badge: 'SELF-HEALING PR',
          badgeColor: 'text-cyan-300 bg-cyan-400/10 border-cyan-400/30',
          title: 'GitHub PR #249 Created & Diagnostic Card Posted',
          detail: 'Auto-PR generated with diff preview, full trace explanation, and one-click auto-merge approval.',
        },
      ],
    },
    '429': {
      name: 'LLM Upstream 429 (Rate Limit Exhaustion)',
      icon: Zap,
      steps: [
        {
          time: '00:00.008',
          badge: 'KEY POOL',
          badgeColor: 'text-amber-300 bg-amber-400/10 border-amber-400/30',
          title: 'Upstream HTTP 429 received from OpenAI GPT-4o',
          detail: 'Key sk-live-99 reached Tier 5 TPM limit. Key Pool intercepted without dropping customer prompt.',
        },
        {
          time: '00:00.015',
          badge: 'AUTO ROTATION',
          badgeColor: 'text-cyan-300 bg-cyan-400/10 border-cyan-400/30',
          title: 'Jittered Exponential Backoff Applied',
          detail: 'Rotated to healthy pool node sk-live-102. Promoted Prometheus metric rate_limits_saved_total +1.',
        },
        {
          time: '00:00.038',
          badge: 'TRANSPARENT RETRY',
          badgeColor: 'text-emerald-300 bg-emerald-400/10 border-emerald-400/30',
          title: 'Customer Request Resolved with 0 Dropped Tokens',
          detail: 'Response tokens streamed seamlessly to client. Marginal debit recorded in ledger with Cost + 30% margin accounting.',
        },
      ],
    },
    'leak': {
      name: 'Database Connection Pool Exhaustion',
      icon: AlertTriangle,
      steps: [
        {
          time: '00:00.019',
          badge: 'EBPF SENTINEL',
          badgeColor: 'text-pink-300 bg-pink-400/10 border-pink-400/30',
          title: 'Postgres Connection Pool Utilization at 99.4%',
          detail: 'Sudden traffic spike threatened cascade crash. Edge circuit-breaker throttled non-critical telemetry.',
        },
        {
          time: '00:00.062',
          badge: 'DRAIN & BACKOFF',
          badgeColor: 'text-purple-300 bg-purple-400/10 border-purple-400/30',
          title: 'Synthetic Traffic Shedding & Stale Socket Recycle',
          detail: 'Skelion shed unessential non-blocking telemetry jobs and recycled stale idle sockets.',
        },
        {
          time: '00:00.110',
          badge: 'RECOVERY',
          badgeColor: 'text-emerald-300 bg-emerald-400/10 border-emerald-400/30',
          title: 'Pool Stabilized at 12 Active Connections',
          detail: 'Average latency restored to 3.2ms. Slack & PagerDuty notification dispatches cleared.',
        },
      ],
    },
  };

  const currentSteps = scenarios[activeScenario].steps;

  // Step through simulation
  useEffect(() => {
    if (!isPlaying) return;
    const timer = setInterval(() => {
      setStepIndex((prev) => (prev < currentSteps.length - 1 ? prev + 1 : 0));
    }, 2800);
    return () => clearInterval(timer);
  }, [isPlaying, currentSteps.length]);

  const copyToClipboard = (text: string, label: string) => {
    navigator.clipboard.writeText(text);
    setCopiedCmd(label);
    setTimeout(() => setCopiedCmd(null), 2000);
  };

  return (
    <section className="relative pt-12 pb-20 md:pt-20 md:pb-32 overflow-hidden">
      {/* Background Cyber Glow & Radial Grid */}
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[1000px] h-[550px] bg-gradient-radial from-cyan-300/25 via-purple-300/15 to-transparent blur-3xl pointer-events-none -z-10" />
      <div className="absolute top-1/3 right-10 w-96 h-96 bg-purple-300/20 rounded-full blur-3xl pointer-events-none -z-10" />

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Badges Bar */}
        <div className="flex flex-wrap items-center justify-center gap-2.5 mb-6">
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-cyan-50 border border-cyan-200 text-cyan-800 shadow-sm">
            <ShieldCheck className="w-3.5 h-3.5 text-cyan-600" />
            <span>Autonomous Incident Intelligence</span>
          </div>

          <a
            href="#console"
            className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium bg-white/90 border border-slate-200 text-slate-700 hover:text-slate-900 hover:border-slate-300 transition shadow-sm"
          >
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-ping" />
            <span>Cloud Platform Live</span>
          </a>

          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-mono bg-purple-50 border border-purple-200 text-purple-700">
            <span>pip install skelion</span>
          </div>
        </div>

        {/* Hero Logo Emblem */}
        <div className="flex justify-center mb-6">
          <div className="relative group">
            <div className="absolute -inset-3 bg-gradient-to-r from-cyan-400/40 via-purple-400/30 to-blue-500/40 rounded-3xl blur-xl opacity-70 group-hover:opacity-100 transition duration-500 animate-pulse"></div>
            <div className="relative w-16 h-16 sm:w-20 sm:h-20 rounded-2xl bg-white/90 backdrop-blur-xl p-2.5 border border-white/80 shadow-xl flex items-center justify-center">
              <img
                src="/icon.svg"
                alt="Skelion Emblem"
                className="w-full h-full object-contain filter drop-shadow-sm"
                onError={(e) => {
                  (e.target as HTMLImageElement).src = '/icon.png';
                }}
              />
            </div>
          </div>
        </div>

        {/* Hero Main Heading & Copy */}
        <div className="text-center max-w-4xl mx-auto mb-12">
          <h1 className="text-4xl sm:text-6xl lg:text-7xl font-extrabold tracking-tight text-slate-950 mb-6">
            Zero-Downtime Resilience.{' '}
            <span className="gradient-text-purple block sm:inline">Autonomous Self-Healing.</span>
          </h1>

          <p className="text-lg sm:text-xl text-slate-600 max-w-3xl mx-auto leading-relaxed">
            Skelion intercepts latency spikes, redacts PII at the edge, and automatically synthesizes
            verified PR fixes in isolated micro-sandboxes — before your users even notice.
          </p>

          {/* Call to Actions */}
          <div className="mt-8 flex flex-wrap items-center justify-center gap-4">
            <a
              href="#console"
              className="px-6 py-3.5 rounded-xl text-sm font-bold text-white bg-gradient-to-r from-cyan-500 via-cyan-400 to-blue-600 hover:from-cyan-400 hover:to-blue-500 shadow-xl shadow-cyan-500/20 hover:shadow-cyan-500/35 transition-all flex items-center gap-2 group"
            >
              <Terminal className="w-4 h-4 text-white" />
              <span>Launch Web Console</span>
              <ChevronRight className="w-4 h-4 group-hover:translate-x-0.5 transition-transform" />
            </a>

            <button
              onClick={() => onOpenCheckout('pilot')}
              className="px-6 py-3.5 rounded-xl text-sm font-semibold text-slate-800 bg-white hover:bg-slate-50 border border-slate-300 hover:border-cyan-500/50 transition-all shadow-sm hover:shadow-md flex items-center gap-2"
            >
              <Zap className="w-4 h-4 text-cyan-600" />
              <span>Start Free Pilot (50 Credits)</span>
            </button>

            <a
              href="https://github.com/Aditya-9-6/Skelion"
              target="_blank"
              rel="noopener noreferrer"
              className="px-5 py-3.5 rounded-xl text-sm font-medium text-slate-700 hover:text-slate-900 bg-slate-100 hover:bg-slate-200 border border-slate-200 transition flex items-center gap-2"
            >
              <ExternalLink className="w-4 h-4" />
              <span>Explore GitHub Repo</span>
            </a>
          </div>

          {/* Command Copy Quick Bar */}
          <div className="mt-6 inline-flex flex-wrap items-center justify-center gap-3 text-xs text-slate-500 font-mono">
            <span className="text-slate-400 font-sans">Quick Install:</span>
            <button
              onClick={() => copyToClipboard('pip install skelion', 'pip')}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white border border-slate-200 hover:border-cyan-400 text-slate-700 hover:text-slate-900 transition shadow-sm"
            >
              <span>pip install skelion</span>
              {copiedCmd === 'pip' ? <Check className="w-3.5 h-3.5 text-emerald-600" /> : <Copy className="w-3.5 h-3.5 text-slate-400" />}
            </button>
            <button
              onClick={() => copyToClipboard('npm install skelion-node', 'npm')}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white border border-slate-200 hover:border-cyan-400 text-slate-700 hover:text-slate-900 transition shadow-sm"
            >
              <span>npm install skelion-node</span>
              {copiedCmd === 'npm' ? <Check className="w-3.5 h-3.5 text-emerald-600" /> : <Copy className="w-3.5 h-3.5 text-slate-400" />}
            </button>
          </div>
        </div>

        {/* Interactive Live Incident Simulator */}
        <div id="simulator" className="max-w-5xl mx-auto">
          <div className="glass-panel rounded-2xl border border-slate-200 shadow-2xl overflow-hidden">
            {/* Terminal Top Window Chrome */}
            <div className="bg-slate-50 px-4 py-3 border-b border-slate-200 flex flex-wrap items-center justify-between gap-3">
              <div className="flex items-center gap-2">
                <div className="flex items-center gap-1.5">
                  <div className="w-3 h-3 rounded-full bg-red-400/90" />
                  <div className="w-3 h-3 rounded-full bg-amber-400/90" />
                  <div className="w-3 h-3 rounded-full bg-emerald-400/90" />
                </div>
                <span className="text-xs font-mono text-slate-600 ml-2 flex items-center gap-1">
                  <Terminal className="w-3.5 h-3.5 text-cyan-600" />
                  skelion-incident-runtime.log — live pipeline
                </span>
              </div>

              {/* Scenario Toggles */}
              <div className="flex items-center gap-1.5 bg-white p-1 rounded-lg border border-slate-200 text-xs font-mono shadow-sm">
                {(['500', '429', 'leak'] as const).map((sc) => {
                  const SIcon = scenarios[sc].icon;
                  return (
                    <button
                      key={sc}
                      onClick={() => {
                        setActiveScenario(sc);
                        setStepIndex(scenarios[sc].steps.length - 1);
                      }}
                      className={`px-2.5 py-1 rounded flex items-center gap-1 transition ${
                        activeScenario === sc
                          ? 'bg-cyan-50 text-cyan-800 border border-cyan-200 font-semibold'
                          : 'text-slate-600 hover:text-slate-900'
                      }`}
                    >
                      <SIcon className="w-3 h-3" />
                      <span>{sc === '500' ? '500 Bug' : sc === '429' ? '429 Rate Limit' : 'Memory Leak'}</span>
                    </button>
                  );
                })}
              </div>

              {/* Player Controls */}
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setIsPlaying(!isPlaying)}
                  className="p-1.5 rounded-md text-slate-600 hover:text-slate-900 hover:bg-slate-200 transition"
                  title={isPlaying ? 'Pause auto-play' : 'Resume auto-play'}
                >
                  <Play className={`w-3.5 h-3.5 ${isPlaying ? 'text-cyan-600' : 'text-slate-400'}`} />
                </button>
                <button
                  onClick={() => setStepIndex(0)}
                  className="p-1.5 rounded-md text-slate-600 hover:text-slate-900 hover:bg-slate-200 transition"
                  title="Reset simulation"
                >
                  <RotateCcw className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>

            {/* Pipeline Stage Content - Frosted Dark Terminal Card */}
            <div className="p-6 bg-slate-950 font-mono space-y-4 min-h-[380px]">
              <div className="text-xs text-slate-400 pb-2 border-b border-slate-800 flex items-center justify-between">
                <span>SIMULATION TARGET: {scenarios[activeScenario].name}</span>
                <span className="text-cyan-400 animate-pulse">● ENGINE REALTIME ACTIVE</span>
              </div>

              <div className="space-y-3">
                {currentSteps.map((step, idx) => {
                  const isVisible = idx <= stepIndex;
                  const isCurrent = idx === stepIndex;

                  if (!isVisible) return null;

                  return (
                    <div
                      key={idx}
                      className={`p-3.5 rounded-xl border transition-all duration-300 ${
                        isCurrent
                          ? 'bg-slate-900/95 border-cyan-500/50 shadow-lg shadow-cyan-500/10 translate-x-1'
                          : 'bg-slate-900/50 border-slate-800/80 opacity-80'
                      }`}
                    >
                      <div className="flex flex-wrap items-center justify-between gap-2 mb-1.5">
                        <div className="flex items-center gap-2">
                          <span className={`text-[10px] uppercase font-bold px-2 py-0.5 rounded border ${step.badgeColor}`}>
                            {step.badge}
                          </span>
                          <span className="text-sm font-semibold text-slate-100">{step.title}</span>
                        </div>
                        <span className="text-[11px] text-slate-400">+{step.time}s</span>
                      </div>
                      <p className="text-xs text-slate-300 pl-0 sm:pl-1 leading-relaxed">
                        {step.detail}
                      </p>
                    </div>
                  );
                })}
              </div>

              {/* Final PR Card Preview if last step is visible */}
              {stepIndex === currentSteps.length - 1 && activeScenario === '500' && (
                <div className="mt-4 p-4 rounded-xl bg-gradient-to-r from-cyan-950/60 to-purple-950/60 border border-cyan-500/40 flex flex-wrap items-center justify-between gap-3">
                  <div className="flex items-center gap-3">
                    <div className="w-9 h-9 rounded-lg bg-cyan-500/20 border border-cyan-500/40 flex items-center justify-center">
                      <GitPullRequest className="w-5 h-5 text-cyan-400" />
                    </div>
                    <div>
                      <div className="text-xs font-semibold text-cyan-200">
                        PR #249: fix(billing): safe coupon discount calculation & null check
                      </div>
                      <div className="text-[11px] text-slate-400">
                        Synthesized by Skelion Agent • 1 commit • +6 -1 lines • 2 new tests passing
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="inline-flex items-center gap-1 text-[11px] text-emerald-400 bg-emerald-950/60 border border-emerald-500/30 px-2 py-1 rounded">
                      <CheckCircle2 className="w-3 h-3" /> CI Passed
                    </span>
                    <button
                      onClick={() => onOpenCheckout('pro')}
                      className="text-xs px-3 py-1 rounded bg-cyan-400 text-slate-950 font-bold hover:bg-cyan-300 transition"
                    >
                      Auto-Merge in Pro
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};
