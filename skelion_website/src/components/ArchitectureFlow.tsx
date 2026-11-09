import React, { useState } from 'react';
import { 
  ArrowRight, 
  ShieldCheck, 
  Cpu, 
  GitPullRequest, 
  CheckCircle, 
  Server, 
  Layers, 
  Lock
} from 'lucide-react';

export const ArchitectureFlow: React.FC = () => {
  const [activeStep, setActiveStep] = useState(0);

  const workflowSteps = [
    {
      step: '01',
      title: 'Edge Ingress & Fail-Open Proxy',
      icon: Server,
      color: 'text-cyan-600',
      tag: '< 5ms Overhead',
      desc: 'All HTTP and microservice RPC traffic passes through the Skelion Edge Proxy. If any proxy error occurs, it fails open instantly without disrupting requests.',
      specs: ['Transparent reverse proxy', 'PII redaction at ingress', 'Prometheus latency metrics'],
    },
    {
      step: '02',
      title: 'Incident Interception & Trace Isolation',
      icon: ShieldCheck,
      color: 'text-amber-600',
      tag: 'Real-time Capture',
      desc: 'When an unhandled 5xx exception or latency spike occurs, Skelion captures the full stack trace, headers, and request context in memory.',
      specs: ['Zero data leakage', 'Full stack snapshot', 'Correlation ID propagation'],
    },
    {
      step: '03',
      title: 'Deterministic Sandbox Reproduction',
      icon: Layers,
      color: 'text-purple-600',
      tag: 'Ephemeral Containers',
      desc: 'An isolated micro-container environment boots up with the exact commit SHA and environment variables, deterministically reproducing the bug.',
      specs: ['Air-gapped execution', 'Automatic pytest test generation', 'Zero host contamination'],
    },
    {
      step: '04',
      title: 'Autonomous AST Patch Synthesis',
      icon: Cpu,
      color: 'text-pink-600',
      tag: 'Zero 429 Rate Limits',
      desc: 'The resilient key-pool routes context to the Skelion AI Agent, synthesizing an abstract syntax tree (AST) compliant source code patch.',
      specs: ['Cost + 30% margin accounting', 'Zero-downtime mesh failover', 'Semantic AST validation'],
    },
    {
      step: '05',
      title: 'Regression Verification & GitHub PR',
      icon: GitPullRequest,
      color: 'text-emerald-600',
      tag: 'Self-Healing CI',
      desc: 'The test suite verifies the fix passes with 100% green tests and zero regressions. A self-documenting GitHub PR with diagnostic cards is automatically opened.',
      specs: ['Turnkey diagnostic cards', 'Automated test proofs', 'Auto-merge on Enterprise'],
    },
  ];

  return (
    <section id="architecture" className="py-24 relative overflow-hidden">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center max-w-3xl mx-auto mb-16">
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-purple-50 border border-purple-200 text-purple-700 mb-3 shadow-sm">
            <Layers className="w-3.5 h-3.5" />
            <span>AUTONOMOUS PIPELINE ARCHITECTURE</span>
          </div>
          <h2 className="text-3xl sm:text-5xl font-extrabold text-slate-950 tracking-tight">
            How Skelion Self-Heals Production
          </h2>
          <p className="mt-4 text-base sm:text-lg text-slate-600">
            A battle-tested architecture that isolates, reproduces, and repairs regressions
            without waking up on-call engineers.
          </p>
        </div>

        {/* Step-by-Step Flow Cards */}
        <div className="grid grid-cols-1 md:grid-cols-5 gap-4 relative">
          {workflowSteps.map((ws, i) => {
            const Icon = ws.icon;
            const isCurrent = activeStep === i;
            return (
              <div
                key={i}
                onClick={() => setActiveStep(i)}
                className={`p-5 rounded-2xl border cursor-pointer transition-all duration-300 relative ${
                  isCurrent
                    ? 'bg-white border-2 border-cyan-500 shadow-xl shadow-cyan-500/10 scale-105 ring-2 ring-cyan-500/15'
                    : 'bg-white/75 backdrop-blur-xl border-slate-200/90 hover:bg-white hover:border-slate-300 shadow-sm'
                }`}
              >
                <div className="flex items-center justify-between mb-4">
                  <span className="text-xs font-mono font-bold text-slate-400">
                    PHASE {ws.step}
                  </span>
                  <span className={`text-[10px] font-mono font-semibold px-2 py-0.5 rounded border border-slate-200 bg-slate-50 ${ws.color}`}>
                    {ws.tag}
                  </span>
                </div>

                <div className="mb-3">
                  <Icon className={`w-8 h-8 ${ws.color} mb-2`} />
                  <h3 className="text-base font-bold text-slate-900 leading-snug">{ws.title}</h3>
                </div>

                <p className="text-xs text-slate-600 leading-relaxed mb-4">
                  {ws.desc}
                </p>

                <div className="pt-3 border-t border-slate-100 space-y-1">
                  {ws.specs.map((sp, idx) => (
                    <div key={idx} className="text-[11px] text-slate-600 flex items-center gap-1.5">
                      <div className="w-1.5 h-1.5 rounded-full bg-cyan-500" />
                      <span>{sp}</span>
                    </div>
                  ))}
                </div>
              </div>
            );
          })}
        </div>

        {/* Visual Pipeline Summary Box */}
        <div className="mt-12 glass-panel p-6 rounded-2xl border border-slate-200/90 text-center flex flex-wrap items-center justify-around gap-4 text-xs font-mono text-slate-700 shadow-md">
          <div className="flex items-center gap-2 text-cyan-800 font-semibold">
            <Server className="w-4 h-4 text-cyan-600" />
            <span>Ingress Traffic</span>
          </div>
          <ArrowRight className="w-4 h-4 text-slate-400 hidden sm:block" />
          <div className="flex items-center gap-2 text-amber-800 font-semibold">
            <Lock className="w-4 h-4 text-amber-600" />
            <span>PII Scrubbed</span>
          </div>
          <ArrowRight className="w-4 h-4 text-slate-400 hidden sm:block" />
          <div className="flex items-center gap-2 text-purple-800 font-semibold">
            <Layers className="w-4 h-4 text-purple-600" />
            <span>Sandbox Replay</span>
          </div>
          <ArrowRight className="w-4 h-4 text-slate-400 hidden sm:block" />
          <div className="flex items-center gap-2 text-pink-800 font-semibold">
            <Cpu className="w-4 h-4 text-pink-600" />
            <span>AST AI Patch</span>
          </div>
          <ArrowRight className="w-4 h-4 text-slate-400 hidden sm:block" />
          <div className="flex items-center gap-2 text-emerald-800 font-semibold">
            <CheckCircle className="w-4 h-4 text-emerald-600" />
            <span>Verified PR Auto-Merge</span>
          </div>
        </div>
      </div>
    </section>
  );
};
