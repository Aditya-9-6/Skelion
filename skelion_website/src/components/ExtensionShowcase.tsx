import React, { useState } from 'react';
import { 
  Terminal, 
  ExternalLink, 
  Copy, 
  Check, 
  Star, 
  ShieldCheck, 
  Palette, 
  Network, 
  Zap,
  ChevronRight
} from 'lucide-react';

export const ExtensionShowcase: React.FC = () => {
  const [copied, setCopied] = useState(false);
  const [activeTab, setActiveTab] = useState<'hallmark' | 'graph' | 'telemetry' | 'theme'>('hallmark');

  const webPlatformUrl = 'https://skelion.dev/#console';

  const copyUrl = () => {
    navigator.clipboard.writeText(webPlatformUrl);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <section id="console-preview" className="py-24 relative overflow-hidden">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 items-center">
          {/* Left Text Column */}
          <div className="lg:col-span-5 space-y-6">
            <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-cyan-50 border border-cyan-200 text-cyan-800 shadow-sm">
              <Terminal className="w-3.5 h-3.5 text-cyan-600" />
              <span>CLOUD AGENT WEB PLATFORM</span>
            </div>

            <h2 className="text-3xl sm:text-5xl font-extrabold text-slate-950 tracking-tight leading-tight">
              Continuous Cloud Intelligence &amp; Resilience
            </h2>

            <p className="text-base text-slate-600 leading-relaxed">
              Supercharge your engineering workflow with the Skelion Web Platform.
              Inspect live edge telemetry, run the Impeccable Validator, monitor autonomous roadmap PR execution,
              and manage reverse proxy threat detection directly from your cloud console.
            </p>

            {/* URL / Launch Box */}
            <div className="p-3.5 rounded-xl bg-white/90 border border-slate-200 shadow-sm flex items-center justify-between gap-3">
              <div className="font-mono text-xs text-cyan-800 truncate">
                {webPlatformUrl}
              </div>
              <button
                onClick={copyUrl}
                className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-cyan-50 text-cyan-700 hover:bg-cyan-100 border border-cyan-200 transition shrink-0 flex items-center gap-1.5 shadow-sm cursor-pointer"
              >
                {copied ? <Check className="w-3.5 h-3.5 text-emerald-600" /> : <Copy className="w-3.5 h-3.5" />}
                <span>{copied ? 'Copied!' : 'Copy URL'}</span>
              </button>
            </div>

            {/* Console Link & Rating */}
            <div className="flex flex-wrap items-center gap-4 pt-2">
              <a
                href="#console"
                className="px-5 py-2.5 rounded-xl text-xs font-bold text-white bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 transition shadow-lg shadow-cyan-500/20 flex items-center gap-2"
              >
                <Terminal className="w-4 h-4 text-white" />
                <span>Launch Web Console</span>
                <ChevronRight className="w-3.5 h-3.5" />
              </a>

              <div className="flex items-center gap-1 text-xs text-amber-500">
                <div className="flex">
                  {[...Array(5)].map((_, i) => (
                    <Star key={i} className="w-3.5 h-3.5 fill-amber-400 text-amber-500" />
                  ))}
                </div>
                <span className="text-slate-500 ml-1 font-mono">Platform Verified</span>
              </div>
            </div>
          </div>

          {/* Right Interactive Mockup Column */}
          <div className="lg:col-span-7">
            <div className="glass-panel rounded-2xl border border-slate-200 shadow-2xl overflow-hidden">
              {/* Web Platform Window Titlebar */}
              <div className="bg-slate-50 px-4 py-2.5 border-b border-slate-200 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className="flex items-center gap-1.5">
                    <div className="w-3 h-3 rounded-full bg-red-400/90" />
                    <div className="w-3 h-3 rounded-full bg-amber-400/90" />
                    <div className="w-3 h-3 rounded-full bg-emerald-400/90" />
                  </div>
                  <div className="flex items-center gap-1.5 ml-2">
                    <img
                      src="/icon.svg"
                      alt="Skelion"
                      className="w-4 h-4 rounded bg-white p-0.5 border border-slate-200 object-contain shadow-xs"
                      onError={(e) => {
                        (e.target as HTMLImageElement).src = '/icon.png';
                      }}
                    />
                    <span className="text-xs font-mono text-slate-700 font-semibold">
                      Skelion Web Platform — Cloud Agent Console
                    </span>
                  </div>
                </div>

                {/* Sub-view Toggles */}
                <div className="flex items-center gap-1 font-mono text-[11px]">
                  <button
                    onClick={() => setActiveTab('hallmark')}
                    className={`px-2.5 py-1 rounded transition cursor-pointer ${
                      activeTab === 'hallmark' ? 'bg-cyan-50 text-cyan-800 font-bold border border-cyan-200 shadow-sm' : 'text-slate-600 hover:text-slate-900'
                    }`}
                  >
                    Impeccable Validator
                  </button>
                  <button
                    onClick={() => setActiveTab('graph')}
                    className={`px-2.5 py-1 rounded transition cursor-pointer ${
                      activeTab === 'graph' ? 'bg-cyan-50 text-cyan-800 font-bold border border-cyan-200 shadow-sm' : 'text-slate-600 hover:text-slate-900'
                    }`}
                  >
                    REA Graph
                  </button>
                  <button
                    onClick={() => setActiveTab('telemetry')}
                    className={`px-2.5 py-1 rounded transition cursor-pointer ${
                      activeTab === 'telemetry' ? 'bg-cyan-50 text-cyan-800 font-bold border border-cyan-200 shadow-sm' : 'text-slate-600 hover:text-slate-900'
                    }`}
                  >
                    Live Billing
                  </button>
                  <button
                    onClick={() => setActiveTab('theme')}
                    className={`px-2.5 py-1 rounded transition cursor-pointer ${
                      activeTab === 'theme' ? 'bg-cyan-50 text-cyan-800 font-bold border border-cyan-200 shadow-sm' : 'text-slate-600 hover:text-slate-900'
                    }`}
                  >
                    AST Syntax
                  </button>
                </div>
              </div>

              {/* Web Platform Body */}
              <div className="p-6 bg-slate-950 font-mono min-h-[340px] text-xs">
                {activeTab === 'hallmark' && (
                  <div className="space-y-4">
                    <div className="flex items-center justify-between pb-3 border-b border-slate-800">
                      <div className="flex items-center gap-2 text-cyan-400 font-bold">
                        <ShieldCheck className="w-4 h-4" />
                        <span>Impeccable Validator & Hallmark Provider</span>
                      </div>
                      <span className="text-[10px] text-emerald-400 bg-emerald-950/60 border border-emerald-500/30 px-2 py-0.5 rounded">
                        All Hallmarks Intact
                      </span>
                    </div>

                    <div className="p-3 rounded-lg bg-slate-900 border border-slate-800 space-y-2">
                      <div className="text-slate-400">
                        [Scanner] Validating AST integrity for cloud workspace...
                      </div>
                      <div className="text-emerald-400">
                        ✓ Hallmark Check: 0 syntax anomalies detected
                      </div>
                      <div className="text-cyan-300">
                        ✓ PII Boundary Check: No hardcoded secrets found in staging
                      </div>
                      <div className="text-purple-300">
                        ✓ Agent Gate: Skelion AI Agent active & ready for refactor
                      </div>
                    </div>

                    <div className="p-3 rounded-lg bg-slate-900/60 border border-cyan-500/20 text-slate-300 text-[11px] leading-relaxed">
                      💡 <strong>Pro Tip:</strong> Click <a href="#console" className="text-cyan-300 underline font-semibold">Console</a> in the navigation bar to inspect real-time incident cards and run autonomous multi-turn sandboxes.
                    </div>
                  </div>
                )}

                {activeTab === 'graph' && (
                  <div className="space-y-4">
                    <div className="flex items-center justify-between pb-3 border-b border-slate-800">
                      <div className="flex items-center gap-2 text-purple-400 font-bold">
                        <Network className="w-4 h-4" />
                        <span>REA Dependency Graph & Scrapling Canvas</span>
                      </div>
                      <span className="text-[10px] text-purple-300 bg-purple-950/60 border border-purple-500/30 px-2 py-0.5 rounded">
                        Interactive Topology
                      </span>
                    </div>

                    <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 text-center space-y-3">
                      <div className="flex justify-center items-center gap-4 text-xs font-mono">
                        <div className="p-2 rounded bg-cyan-950/60 border border-cyan-500/40 text-cyan-300">
                          [Edge Proxy :8080]
                        </div>
                        <div className="text-slate-500">─────►</div>
                        <div className="p-2 rounded bg-purple-950/60 border border-purple-500/40 text-purple-300">
                          [Control Plane :8002]
                        </div>
                        <div className="text-slate-500">─────►</div>
                        <div className="p-2 rounded bg-emerald-950/60 border border-emerald-500/40 text-emerald-300">
                          [Redis Key Pool]
                        </div>
                      </div>
                      <p className="text-[11px] text-slate-400 pt-2">
                        Visualizes node latencies, downstream error propagation, and microservice mesh states in real time.
                      </p>
                    </div>
                  </div>
                )}

                {activeTab === 'telemetry' && (
                  <div className="space-y-4">
                    <div className="flex items-center justify-between pb-3 border-b border-slate-800">
                      <div className="flex items-center gap-2 text-emerald-400 font-bold">
                        <Zap className="w-4 h-4" />
                        <span>Zero-Restart Live Billing Status</span>
                      </div>
                      <span className="text-[10px] text-emerald-300 bg-emerald-950/60 border border-emerald-500/30 px-2 py-0.5 rounded">
                        Synced via WebSockets
                      </span>
                    </div>

                    <div className="grid grid-cols-2 gap-3">
                      <div className="p-3 rounded-lg bg-slate-900 border border-slate-800">
                        <span className="text-slate-400 text-[10px] block">ACTIVE PLAN</span>
                        <span className="text-lg font-bold text-white">Hosted Pro</span>
                        <span className="text-[10px] text-cyan-400 block mt-0.5">₹3,999 / mo</span>
                      </div>
                      <div className="p-3 rounded-lg bg-slate-900 border border-slate-800">
                        <span className="text-slate-400 text-[10px] block">REMAINING CREDITS</span>
                        <span className="text-lg font-bold text-emerald-400">4,499</span>
                        <span className="text-[10px] text-slate-400 block mt-0.5">of 4,500 monthly quota</span>
                      </div>
                    </div>
                    <p className="text-[11px] text-slate-400">
                      Upgrades and credit refills processed via Razorpay reflect instantaneously in the console without refreshing.
                    </p>
                  </div>
                )}

                {activeTab === 'theme' && (
                  <div className="space-y-4">
                    <div className="flex items-center justify-between pb-3 border-b border-slate-800">
                      <div className="flex items-center gap-2 text-pink-400 font-bold">
                        <Palette className="w-4 h-4" />
                        <span>AST Syntax & Calibrated Theme</span>
                      </div>
                      <span className="text-[10px] text-pink-300 bg-pink-950/60 border border-pink-500/30 px-2 py-0.5 rounded">
                        Web Console UI
                      </span>
                    </div>

                    <div className="p-3 rounded-lg bg-slate-900 border border-pink-500/20 font-mono text-xs space-y-1.5">
                      <div><span className="text-purple-400">const</span> <span className="text-cyan-300">skelion</span> = <span className="text-amber-400">new</span> <span className="text-emerald-400">SkelionClient</span>();</div>
                      <div><span className="text-purple-400">await</span> skelion.<span className="text-cyan-300">intercept</span>({'{'} <span className="text-pink-300">failOpen</span>: <span className="text-cyan-400">true</span> {'}'});</div>
                      <div className="text-slate-500">// High-contrast syntax visualization in web console</div>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};
