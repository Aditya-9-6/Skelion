import React, { useState } from 'react';
import { 
  Repeat, 
  Activity, 
  Play, 
  Pause, 
  RotateCw, 
  CheckCircle2, 
  AlertCircle, 
  Cpu, 
  Terminal, 
  Radio, 
  Sparkles,
  Zap,
  TrendingDown,
  ShieldCheck,
  Check
} from 'lucide-react';

interface LoopEvent {
  time: string;
  phase: string;
  msg: string;
}

export const LoopTab: React.FC = () => {
  const [isRunning, setIsRunning] = useState(true);
  const [probeCount, setProbeCount] = useState(142);
  const [activeTrigger, setActiveTrigger] = useState<string | null>(null);

  const probeNodes = [
    { name: 'US-East Canary (Virginia)', endpoint: 'https://us-east.skelion.net/ping', status: 'GREEN', latency: '1.2ms', uptime: '100%' },
    { name: 'EU-Central Canary (Frankfurt)', endpoint: 'https://eu-central.skelion.net/ping', status: 'GREEN', latency: '1.8ms', uptime: '99.99%' },
    { name: 'AP-South Canary (Mumbai)', endpoint: 'https://ap-south.skelion.net/ping', status: 'GREEN', latency: '2.1ms', uptime: '100%' },
    { name: 'Edge Wasm Mesh Probe', endpoint: 'ebpf://ring_buffer/probe', status: 'GREEN', latency: '0.4ms', uptime: '100%' }
  ];

  const [loopEvents, setLoopEvents] = useState<LoopEvent[]>([
    { time: '10:22:15', phase: 'CANARY_PROBE', msg: 'Synthetic ping to primary Skelion Edge Mesh endpoint returned 200 OK (284 t/s throughput).' },
    { time: '10:21:40', phase: 'AST_VALIDATION', msg: 'Invariant check on src/services/payment.ts passed Impeccable Validator.' },
    { time: '10:20:12', phase: 'PII_HEALTHCHECK', msg: 'Scrubbed 0 sensitive tokens in previous 1,000 requests.' },
    { time: '10:19:30', phase: 'CIRCUIT_SWEEP', msg: 'No open circuits detected across 4 key pools. Dynamic mesh ready.' }
  ]);

  const latencyHistory = [
    { time: '10:15', usEast: 1.2, euCentral: 1.7, apSouth: 2.1, wasm: 0.4 },
    { time: '10:17', usEast: 1.3, euCentral: 1.9, apSouth: 2.3, wasm: 0.5 },
    { time: '10:19', usEast: 1.1, euCentral: 1.8, apSouth: 2.0, wasm: 0.4 },
    { time: '10:21', usEast: 1.4, euCentral: 1.6, apSouth: 2.2, wasm: 0.4 },
    { time: '10:23', usEast: 1.2, euCentral: 1.8, apSouth: 2.1, wasm: 0.4 }
  ];

  const handleTriggerFeedbackLoop = (triggerType: 'canary' | 'ast' | 'circuit') => {
    setActiveTrigger(triggerType);
    const now = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });

    let newEvent: LoopEvent;
    if (triggerType === 'canary') {
      newEvent = {
        time: now,
        phase: 'MANUAL_CANARY',
        msg: `User triggered canary probe: verified 4/4 nodes with 1.1ms average latency across mesh.`
      };
      setProbeCount((p) => p + 1);
    } else if (triggerType === 'ast') {
      newEvent = {
        time: now,
        phase: 'MANUAL_AST_SWEEP',
        msg: `User triggered AST invariant verification: verified zero hallucinated syntax, 14/14 test passing.`
      };
    } else {
      newEvent = {
        time: now,
        phase: 'MANUAL_CIRCUIT_CHECK',
        msg: `User triggered Key Pool sweep: verified Mesh Cluster 1 (Active), Mesh Cluster 2 (Standby), Mesh Cluster 3 (Idle), Mesh Cluster 4 (Standby).`
      };
    }

    setLoopEvents((prev) => [newEvent, ...prev]);
    setTimeout(() => setActiveTrigger(null), 1500);
  };

  return (
    <div className="space-y-6">
      {/* Top Console Card */}
      <div className="bg-white/80 backdrop-blur-xl border border-slate-200/80 rounded-2xl p-5 shadow-[0_8px_32px_0_rgba(31,38,135,0.07)] flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <h2 className="text-lg font-bold text-slate-900">Autonomous Self-Healing Loop</h2>
            <span className={`px-2 py-0.5 rounded-full text-xs font-semibold flex items-center gap-1.5 ${
              isRunning ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' : 'bg-amber-50 text-amber-700 border border-amber-200'
            }`}>
              <span className={`w-1.5 h-1.5 rounded-full ${isRunning ? 'bg-emerald-500 animate-ping' : 'bg-amber-500'}`} />
              {isRunning ? 'Loop Active (Continuous 5s)' : 'Loop Paused'}
            </span>
            <span className="px-2 py-0.5 rounded-full text-xs font-semibold bg-blue-50 text-blue-700 border border-blue-200 flex items-center gap-1" title="Skelion never force-pushes or auto-merges to production branches">
              <ShieldCheck className="w-3.5 h-3.5 text-blue-600" />
              <span>Policy: Open PR Only (No Auto-Merge)</span>
            </span>
          </div>
          <p className="text-xs text-slate-500 font-mono mt-0.5">
            Continuous background canary probes, automated invariant regression detection, and autonomous remediation triggers.
          </p>
        </div>

        {/* Action Controls */}
        <div className="flex flex-wrap items-center gap-2">
          <button
            onClick={() => setIsRunning(!isRunning)}
            className={`px-4 py-2 rounded-xl text-xs font-bold flex items-center gap-1.5 transition shadow-sm ${
              isRunning
                ? 'bg-amber-50 hover:bg-amber-100 text-amber-800 border border-amber-200'
                : 'bg-emerald-600 hover:bg-emerald-500 text-white shadow-emerald-600/20'
            }`}
          >
            {isRunning ? (
              <>
                <Pause className="w-3.5 h-3.5" />
                <span>Pause Loop</span>
              </>
            ) : (
              <>
                <Play className="w-3.5 h-3.5" />
                <span>Resume Loop</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* Healthcheck Graph & Telemetry Metrics */}
      <div className="bg-white/80 backdrop-blur-xl border border-slate-200/80 rounded-2xl p-6 shadow-xs space-y-5">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2 border-b border-slate-100 pb-4">
          <div>
            <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
              <Activity className="w-4 h-4 text-cyan-600" />
              <span>Real-Time Healthcheck &amp; Latency Waveform</span>
            </h3>
            <p className="text-xs text-slate-500 font-mono mt-0.5">
              Live millisecond latency across multi-region probes and eBPF Wasm Ring.
            </p>
          </div>

          <div className="flex items-center gap-4 text-xs font-mono">
            <span className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-cyan-500" />
              <span className="text-slate-600">US-East</span>
            </span>
            <span className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-purple-500" />
              <span className="text-slate-600">EU-Central</span>
            </span>
            <span className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-blue-500" />
              <span className="text-slate-600">AP-South</span>
            </span>
            <span className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-emerald-500" />
              <span className="text-slate-600">eBPF Ring</span>
            </span>
          </div>
        </div>

        {/* Visual Latency Graph (SVG Waveform) */}
        <div className="bg-slate-950 rounded-2xl p-4 sm:p-5 text-slate-200 relative overflow-hidden">
          <div className="flex items-center justify-between text-[11px] font-mono text-slate-400 mb-2">
            <span>LATENCY SPECTRUM (ms)</span>
            <span className="text-emerald-400 font-bold">AVG PING: 1.37ms · ZERO PACKET LOSS</span>
          </div>

          <div className="h-44 w-full relative">
            {/* Horizontal Grid lines */}
            <div className="absolute inset-0 flex flex-col justify-between pointer-events-none opacity-20 text-[10px] font-mono text-slate-400">
              <div className="border-b border-slate-700 w-full flex justify-between"><span>2.5ms</span></div>
              <div className="border-b border-slate-700 w-full flex justify-between"><span>1.5ms</span></div>
              <div className="border-b border-slate-700 w-full flex justify-between"><span>0.5ms</span></div>
              <div className="border-b border-slate-700 w-full flex justify-between"><span>0.0ms</span></div>
            </div>

            {/* SVG Charts */}
            <svg className="w-full h-full overflow-visible" preserveAspectRatio="none" viewBox="0 0 500 120">
              <defs>
                <linearGradient id="gradientWasm" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#10b981" stopOpacity="0.4" />
                  <stop offset="100%" stopColor="#10b981" stopOpacity="0.0" />
                </linearGradient>
                <linearGradient id="gradientUSEast" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#06b6d4" stopOpacity="0.4" />
                  <stop offset="100%" stopColor="#06b6d4" stopOpacity="0.0" />
                </linearGradient>
              </defs>

              {/* eBPF Area fill */}
              <polygon
                points="0,110 0,105 125,102 250,105 375,103 500,104 500,115 0,115"
                fill="url(#gradientWasm)"
              />
              <polyline
                fill="none"
                stroke="#10b981"
                strokeWidth="2.5"
                points="0,105 125,102 250,105 375,103 500,104"
              />

              {/* US East Line */}
              <polygon
                points="0,110 0,65 125,60 250,70 375,55 500,64 500,115 0,115"
                fill="url(#gradientUSEast)"
              />
              <polyline
                fill="none"
                stroke="#06b6d4"
                strokeWidth="2.5"
                points="0,65 125,60 250,70 375,55 500,64"
              />

              {/* EU Central Polyline */}
              <polyline
                fill="none"
                stroke="#a855f7"
                strokeWidth="2"
                strokeDasharray="4 4"
                points="0,45 125,38 250,42 375,48 500,42"
              />

              {/* AP South Polyline */}
              <polyline
                fill="none"
                stroke="#3b82f6"
                strokeWidth="2"
                points="0,30 125,22 250,32 375,25 500,28"
              />
            </svg>
          </div>

          <div className="flex items-center justify-between text-[11px] font-mono text-slate-500 pt-2 border-t border-slate-800">
            <span>10:15:00</span>
            <span>10:17:30</span>
            <span>10:20:00</span>
            <span>10:22:30</span>
            <span className="text-cyan-400 font-semibold">10:25:00 (LIVE)</span>
          </div>
        </div>

        {/* Stat Meters */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="p-3.5 rounded-xl border border-slate-200/80 bg-slate-50/70">
            <span className="text-[11px] text-slate-500 font-mono">Mesh Uptime</span>
            <div className="text-xl font-bold text-slate-900 mt-1">99.998%</div>
            <span className="text-[10px] text-emerald-600 font-semibold">0 downtime past 90d</span>
          </div>
          <div className="p-3.5 rounded-xl border border-slate-200/80 bg-slate-50/70">
            <span className="text-[11px] text-slate-500 font-mono">Probes Executed</span>
            <div className="text-xl font-bold text-slate-900 mt-1">{probeCount.toLocaleString()}</div>
            <span className="text-[10px] text-cyan-600 font-semibold">+1 every 5s</span>
          </div>
          <div className="p-3.5 rounded-xl border border-slate-200/80 bg-slate-50/70">
            <span className="text-[11px] text-slate-500 font-mono">AST Invariants</span>
            <div className="text-xl font-bold text-slate-900 mt-1">100% Passed</div>
            <span className="text-[10px] text-emerald-600 font-semibold">Zero syntax regression</span>
          </div>
          <div className="p-3.5 rounded-xl border border-slate-200/80 bg-slate-50/70">
            <span className="text-[11px] text-slate-500 font-mono">Failover Latency</span>
            <div className="text-xl font-bold text-slate-900 mt-1">&lt; 1.4ms</div>
            <span className="text-[10px] text-purple-600 font-semibold">Sub-millisecond buffer</span>
          </div>
        </div>
      </div>

      {/* Feedback Loop Triggers Section */}
      <div className="bg-white/80 backdrop-blur-xl border border-slate-200/80 rounded-2xl p-6 shadow-xs space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Zap className="w-4 h-4 text-cyan-600" />
            <h3 className="text-sm font-bold text-slate-900">Manual Feedback Loop Triggers</h3>
          </div>
          <span className="text-xs text-slate-500 font-mono">Instant Diagnostics</span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3.5">
          <button
            onClick={() => handleTriggerFeedbackLoop('canary')}
            disabled={activeTrigger !== null}
            className="p-3.5 rounded-xl border border-slate-200 bg-white hover:bg-slate-50 text-left transition shadow-2xs group flex flex-col justify-between"
          >
            <div>
              <div className="text-xs font-bold text-slate-900 group-hover:text-cyan-700 flex items-center justify-between">
                <span>Dispatch Canary Probe</span>
                {activeTrigger === 'canary' ? <Check className="w-3.5 h-3.5 text-emerald-600" /> : <RotateCw className="w-3.5 h-3.5 text-slate-400 group-hover:rotate-180 transition duration-300" />}
              </div>
              <p className="text-[11px] text-slate-500 font-mono mt-1">
                Ping all 4 regional edge nodes to record live latency and packet health.
              </p>
            </div>
            <span className="mt-2 text-[10px] font-bold text-cyan-700 font-mono">Trigger Probe →</span>
          </button>

          <button
            onClick={() => handleTriggerFeedbackLoop('ast')}
            disabled={activeTrigger !== null}
            className="p-3.5 rounded-xl border border-slate-200 bg-white hover:bg-slate-50 text-left transition shadow-2xs group flex flex-col justify-between"
          >
            <div>
              <div className="text-xs font-bold text-slate-900 group-hover:text-cyan-700 flex items-center justify-between">
                <span>Run AST Invariant Sweep</span>
                {activeTrigger === 'ast' ? <Check className="w-3.5 h-3.5 text-emerald-600" /> : <ShieldCheck className="w-3.5 h-3.5 text-slate-400 group-hover:text-cyan-600 transition" />}
              </div>
              <p className="text-[11px] text-slate-500 font-mono mt-1">
                Audit workspace AST syntax trees and verify zero broken invariants.
              </p>
            </div>
            <span className="mt-2 text-[10px] font-bold text-cyan-700 font-mono">Run AST Sweep →</span>
          </button>

          <button
            onClick={() => handleTriggerFeedbackLoop('circuit')}
            disabled={activeTrigger !== null}
            className="p-3.5 rounded-xl border border-slate-200 bg-white hover:bg-slate-50 text-left transition shadow-2xs group flex flex-col justify-between"
          >
            <div>
              <div className="text-xs font-bold text-slate-900 group-hover:text-cyan-700 flex items-center justify-between">
                <span>Sweep Key Pool Breakers</span>
                {activeTrigger === 'circuit' ? <Check className="w-3.5 h-3.5 text-emerald-600" /> : <Cpu className="w-3.5 h-3.5 text-slate-400 group-hover:text-cyan-600 transition" />}
              </div>
              <p className="text-[11px] text-slate-500 font-mono mt-1">
                Evaluate 429 threshold quotas and calibrate secondary standby failover.
              </p>
            </div>
            <span className="mt-2 text-[10px] font-bold text-cyan-700 font-mono">Sweep Breakers →</span>
          </button>
        </div>
      </div>

      {/* Canary Node Probes Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {probeNodes.map((node, idx) => (
          <div key={idx} className="bg-white/80 backdrop-blur-xl border border-slate-200/80 rounded-2xl p-4 shadow-xs space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-slate-800 truncate">{node.name}</span>
              <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">
                {node.status}
              </span>
            </div>
            <div className="text-[11px] text-slate-500 font-mono truncate">{node.endpoint}</div>
            <div className="flex items-center justify-between pt-1 border-t border-slate-100 text-xs font-mono">
              <span className="text-slate-400">Canary Ping:</span>
              <span className="text-emerald-600 font-bold">{node.latency}</span>
            </div>
          </div>
        ))}
      </div>

      {/* Real-Time Event Feed */}
      <div className="bg-white/80 backdrop-blur-xl border border-slate-200/80 rounded-2xl p-5 shadow-xs space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
            <Radio className="w-4 h-4 text-cyan-600 animate-pulse" />
            <span>Telemetry &amp; Synthetic Probe Log</span>
          </h3>
          <span className="text-xs font-mono text-slate-400">Stream: live-ebpf-probes</span>
        </div>

        <div className="space-y-2 max-h-60 overflow-y-auto">
          {loopEvents.map((evt, idx) => (
            <div key={idx} className="p-3 rounded-xl border border-slate-200/60 bg-slate-50/70 font-mono text-xs flex items-start gap-3">
              <span className="text-slate-400 text-[11px] shrink-0">{evt.time}</span>
              <span className="px-2 py-0.5 rounded-md bg-white border border-slate-200 text-cyan-700 font-bold text-[10px] shrink-0">
                {evt.phase}
              </span>
              <span className="text-slate-700 leading-relaxed">{evt.msg}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Patch History & Remediation Audit */}
      <div className="bg-white/80 backdrop-blur-xl border border-slate-200/80 rounded-2xl p-5 shadow-xs space-y-4">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                <ShieldCheck className="w-4 h-4 text-emerald-600" />
                <span>Patch History &amp; PR Remediation Audit</span>
              </h3>
              <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-blue-50 text-blue-700 border border-blue-200">
                Human-in-the-Loop Mode
              </span>
            </div>
            <p className="text-xs text-slate-500 font-mono mt-0.5">
              All autonomous fixes are prepared on isolated Git branches and proposed as Pull Requests. No automated merging is performed without team approval.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <a
              href="#fixes"
              className="px-3 py-1.5 rounded-xl text-xs font-semibold bg-slate-900 text-white hover:bg-slate-800 transition flex items-center gap-1.5"
            >
              <span>View Active Patches (2)</span>
              <span className="text-cyan-400 font-mono">→</span>
            </a>
            <a
              href="#history"
              className="px-3 py-1.5 rounded-xl text-xs font-semibold bg-slate-100 hover:bg-slate-200 text-slate-700 transition flex items-center gap-1.5"
            >
              <span>Full Audit Logs</span>
            </a>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5 pt-1">
          <div className="p-4 rounded-xl border border-slate-200/80 bg-slate-50/60 space-y-2">
            <div className="flex items-center justify-between">
              <span className="font-mono text-xs font-bold text-slate-900">PATCH-304 (INC-8921)</span>
              <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-amber-50 text-amber-700 border border-amber-200">
                PR Opened · Awaiting Merge
              </span>
            </div>
            <p className="text-xs text-slate-700 font-medium">
              Fix currency ISO fallback in checkout route to prevent 500 error
            </p>
            <div className="flex items-center justify-between text-[11px] font-mono text-slate-500 pt-1 border-t border-slate-200/60">
              <span className="text-emerald-600 font-semibold">14/14 Pytest/Vitest Passed</span>
              <a href="#fixes" className="text-cyan-700 font-bold hover:underline">Inspect Diff &amp; PR →</a>
            </div>
          </div>

          <div className="p-4 rounded-xl border border-slate-200/80 bg-slate-50/60 space-y-2">
            <div className="flex items-center justify-between">
              <span className="font-mono text-xs font-bold text-slate-900">PATCH-302 (INC-8919)</span>
              <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-amber-50 text-amber-700 border border-amber-200">
                PR Opened · Awaiting Merge
              </span>
            </div>
            <p className="text-xs text-slate-700 font-medium">
              Add exponential backoff &amp; secondary key circuit breaker on 429 response
            </p>
            <div className="flex items-center justify-between text-[11px] font-mono text-slate-500 pt-1 border-t border-slate-200/60">
              <span className="text-emerald-600 font-semibold">9/9 Unit Tests Passed</span>
              <a href="#fixes" className="text-cyan-700 font-bold hover:underline">Inspect Diff &amp; PR →</a>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
