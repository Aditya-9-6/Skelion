import React, { useState } from 'react';
import { 
  AlertTriangle, 
  ShieldAlert, 
  CheckCircle2, 
  Clock, 
  ArrowUpRight, 
  Terminal, 
  Filter, 
  Search, 
  Wrench,
  ExternalLink,
  ChevronDown,
  ChevronUp,
  Cpu,
  Bot,
  Sparkles,
  ArrowRight
} from 'lucide-react';

export interface IncidentDeepDivePayload {
  incidentId: string;
  service: string;
  title: string;
  severity: 'CRITICAL' | 'WARNING' | 'INFO';
  affectedEndpoint: string;
  affectedFile: string;
  rootCause: string;
  stackTrace: string;
  initialCode: string;
  suggestedPatch?: string;
}

export interface IncidentsTabProps {
  onSynthesizePatch?: (incidentId: string) => void;
  onDeepDive?: (payload: IncidentDeepDivePayload) => void;
}

export interface IncidentRecord {
  id: string;
  service: string;
  title: string;
  severity: 'CRITICAL' | 'WARNING' | 'INFO';
  status: 'ACTIVE' | 'RESOLVED' | 'INTERCEPTED' | 'ROTATED';
  timestamp: string;
  latencyBypass: string;
  tokensPreserved: string;
  rootCause: string;
  stackTrace: string;
  affectedEndpoint: string;
  affectedFile: string;
  initialCode: string;
  suggestedPatch?: string;
}

export const IncidentsTab: React.FC<IncidentsTabProps> = ({ onSynthesizePatch, onDeepDive }) => {
  const [filterSeverity, setFilterSeverity] = useState<string>('ALL');
  const [searchQuery, setSearchQuery] = useState('');
  const [expandedId, setExpandedId] = useState<string | null>('INC-8921');

  const incidents: IncidentRecord[] = [
    {
      id: 'INC-8921',
      service: 'Payment Ingress Mesh',
      title: '500 Unhandled Currency Parsing Exception',
      severity: 'CRITICAL',
      status: 'ACTIVE',
      timestamp: '12 mins ago',
      latencyBypass: '1.4ms edge interception',
      tokensPreserved: '14.2k tokens',
      affectedEndpoint: 'POST /v1/checkout/pay',
      affectedFile: 'src/services/payment.ts',
      rootCause: 'Payload omitted currency iso code; upstream SDK raised TypeError: cannot read property toUpperCase of undefined.',
      stackTrace: `TypeError: Cannot read properties of undefined (reading 'toUpperCase')
    at validateCurrency (file:///src/services/payment.ts:42:19)
    at handleCheckoutPay (file:///src/api/routes.ts:118:24)
    at async dispatchRoute (file:///src/core/router.ts:89:12)`,
      initialCode: `// src/services/payment.ts
// Payment Ingress Mesh - Currency validation
export function validateCurrency(payload: { amount: number; currency?: string }) {
  // Bug: currency can be undefined, causing 500 TypeError
  return payload.currency.toUpperCase();
}

export async function processPayment(payload: any) {
  const code = validateCurrency(payload);
  return { status: 'processed', currency: code };
}`,
      suggestedPatch: `// src/services/payment.ts
// Fixed: Autonomous AST Null-safety Guard
export function validateCurrency(payload: { amount: number; currency?: string }) {
  const currencyCode = (payload.currency || 'USD').toUpperCase();
  return currencyCode;
}

export async function processPayment(payload: any) {
  const code = validateCurrency(payload);
  return { status: 'processed', currency: code };
}`
    },
    {
      id: 'INC-8919',
      service: 'LLM Key Pool #2 (Resilient Mesh)',
      title: 'Upstream 429 Rate Limit Burst',
      severity: 'WARNING',
      status: 'ROTATED',
      timestamp: '1 hour ago',
      latencyBypass: '0 downtime · auto-rotated node',
      tokensPreserved: '28.9k tokens',
      affectedEndpoint: 'POST /v1/chat/completions',
      affectedFile: 'src/services/resilienceGateway.ts',
      rootCause: 'Primary key node reached 60 req/min tier threshold. Skelion gossip mesh executed 0ms standby rotation to secondary mesh node.',
      stackTrace: `RateLimitError: 429 Too Many Requests (upstream cluster tier exhausted)
    at ProviderKeyPool.verifyHealth (file:///src/mesh/pool.ts:67:15)
    [Skelion Fail-Open Trigger]: Shifted 100% traffic to Secondary Key Node #4`,
      initialCode: `// src/services/resilienceGateway.ts
import { KeyPoolCircuitBreaker } from '@skelion/edge-core';

export async function resilientLLMDispatch(prompt: string, payload: any) {
  const circuit = KeyPoolCircuitBreaker.getPool('resilient-primary-mesh');
  // Bug: Direct dispatch without 429 threshold check or fail-open standby pool rotation
  return await circuit.dispatch(payload);
}`,
      suggestedPatch: `// src/services/resilienceGateway.ts
import { KeyPoolCircuitBreaker, EdgeMesh } from '@skelion/edge-core';

export async function resilientLLMDispatch(prompt: string, payload: any) {
  const circuit = KeyPoolCircuitBreaker.getPool('resilient-primary-mesh');
  
  if (circuit.isThrottled(429)) {
    console.warn('[Skelion Mesh] 429 threshold detected! Shifting traffic to secondary standby pool with 0ms downtime');
    return await EdgeMesh.rotateKeyPool({
      fallbackPool: 'standby-failover-cluster',
      prompt,
      maxRetries: 3,
      backoff: 'exponential'
    });
  }
  
  return await circuit.dispatch(payload);
}`
    },
    {
      id: 'INC-8904',
      service: 'Ingress Auth Filter',
      title: 'Authorization Bearer Token Inadvertent Leak',
      severity: 'WARNING',
      status: 'INTERCEPTED',
      timestamp: '3 hours ago',
      latencyBypass: '0.8ms edge scrub',
      tokensPreserved: 'JWT Token Redacted',
      affectedEndpoint: 'GET /api/user/profile?token=***',
      affectedFile: 'src/filters/pii.ts',
      rootCause: 'Client application passed Authorization JWT in plain URL query parameters. Skelion PII Filter scrubbed query string before it reached internal logs.',
      stackTrace: `PIIWarning: Sensitive Authorization token found in query parameters
    at PIIRedactionFilter.scrubRequest (file:///src/filters/pii.ts:24:9)
    [Skelion Action]: Token masked with [REDACTED_JWT_TOKEN]`,
      initialCode: `// src/filters/pii.ts
export function scrubRequestUrl(url: string): string {
  // Bug: query param tokens leaked to logs
  return url;
}`,
      suggestedPatch: `// src/filters/pii.ts
export function scrubRequestUrl(url: string): string {
  const parsed = new URL(url, 'http://localhost');
  if (parsed.searchParams.has('token')) {
    parsed.searchParams.set('token', '[REDACTED_JWT_TOKEN]');
  }
  return parsed.toString();
}`
    },
    {
      id: 'INC-8872',
      service: 'Inventory Sync Daemon',
      title: 'AST Syntax Regression in Stock Webhook',
      severity: 'INFO',
      status: 'RESOLVED',
      timestamp: '1 day ago',
      latencyBypass: '100% Pytest Unit Green',
      tokensPreserved: '8.4k tokens',
      affectedEndpoint: 'POST /api/inventory/webhook',
      affectedFile: 'src/db/pool.ts',
      rootCause: 'Async race condition between webhook acknowledgment and Postgres connection pool checkout.',
      stackTrace: `DatabaseTimeout: Connection pool exhausted after 5000ms
    at PgPool.acquireConnection (file:///src/db/pool.ts:81:14)
    [Skelion Autofix]: Synthesized connection pool retry queue with exponential backoff.`,
      initialCode: `// src/db/pool.ts
export async function acquireConnection(pool: any) {
  return await pool.connect();
}`,
      suggestedPatch: `// src/db/pool.ts
export async function acquireConnection(pool: any, retries = 3) {
  for (let i = 0; i < retries; i++) {
    try {
      return await pool.connect();
    } catch (err) {
      if (i === retries - 1) throw err;
      await new Promise(r => setTimeout(r, 100 * Math.pow(2, i)));
    }
  }
}`
    }
  ];

  const filteredIncidents = incidents.filter((inc) => {
    const matchesSeverity = filterSeverity === 'ALL' || inc.severity === filterSeverity;
    const matchesSearch = 
      inc.id.toLowerCase().includes(searchQuery.toLowerCase()) ||
      inc.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      inc.affectedEndpoint.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesSeverity && matchesSearch;
  });

  const handleDeepDiveClick = (inc: IncidentRecord) => {
    if (onDeepDive) {
      onDeepDive({
        incidentId: inc.id,
        service: inc.service,
        title: inc.title,
        severity: inc.severity,
        affectedEndpoint: inc.affectedEndpoint,
        affectedFile: inc.affectedFile,
        rootCause: inc.rootCause,
        stackTrace: inc.stackTrace,
        initialCode: inc.initialCode,
        suggestedPatch: inc.suggestedPatch,
      });
    } else if (onSynthesizePatch) {
      onSynthesizePatch(inc.id);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header & Filter Controls */}
      <div className="bg-white/80 backdrop-blur-xl border border-slate-200/80 rounded-2xl p-5 shadow-[0_8px_32px_0_rgba(31,38,135,0.07)] flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-lg font-bold text-slate-900">Incident Triage &amp; Edge Intercepts</h2>
            <span className="px-2 py-0.5 rounded-full text-xs font-semibold bg-rose-50 text-rose-700 border border-rose-200">
              {incidents.filter(i => i.status === 'ACTIVE').length} Active
            </span>
          </div>
          <p className="text-xs text-slate-500 font-mono mt-0.5">
            Continuous real-time telemetry, 429 interception, and automatic AST patch candidates.
          </p>
        </div>

        {/* Search & Filter Pills */}
        <div className="flex flex-wrap items-center gap-2.5 w-full md:w-auto">
          <div className="relative flex-1 md:w-56">
            <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search incidents or endpoints..."
              className="w-full text-xs bg-white border border-slate-200 rounded-xl pl-9 pr-3 py-2 text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-cyan-500/20"
            />
          </div>

          <div className="flex items-center gap-1 bg-slate-100 p-1 rounded-xl text-xs font-semibold">
            {['ALL', 'CRITICAL', 'WARNING', 'INFO'].map((sev) => (
              <button
                key={sev}
                onClick={() => setFilterSeverity(sev)}
                className={`px-2.5 py-1 rounded-lg transition ${
                  filterSeverity === sev
                    ? 'bg-white text-slate-900 shadow-xs'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                {sev}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Incident Cards List */}
      <div className="space-y-3.5">
        {filteredIncidents.map((inc) => {
          const isExpanded = expandedId === inc.id;

          const severityBadge = {
            CRITICAL: 'bg-rose-50 text-rose-700 border-rose-200',
            WARNING: 'bg-amber-50 text-amber-700 border-amber-200',
            INFO: 'bg-cyan-50 text-cyan-700 border-cyan-200'
          }[inc.severity];

          const statusBadge = {
            ACTIVE: 'bg-rose-100 text-rose-800 border-rose-300',
            RESOLVED: 'bg-emerald-100 text-emerald-800 border-emerald-300',
            INTERCEPTED: 'bg-purple-100 text-purple-800 border-purple-300',
            ROTATED: 'bg-cyan-100 text-cyan-800 border-cyan-300'
          }[inc.status];

          return (
            <div
              key={inc.id}
              className="bg-white/80 backdrop-blur-xl border border-slate-200/80 rounded-2xl shadow-xs overflow-hidden transition-all duration-200 hover:border-slate-300"
            >
              <div 
                onClick={() => setExpandedId(isExpanded ? null : inc.id)}
                className="p-4 sm:p-5 flex flex-col md:flex-row items-start md:items-center justify-between gap-4 cursor-pointer select-none hover:bg-slate-50/50"
              >
                <div className="flex items-start gap-3.5">
                  <div className={`w-9 h-9 rounded-xl flex items-center justify-center shrink-0 border ${
                    inc.severity === 'CRITICAL' ? 'bg-rose-50 border-rose-200 text-rose-600' :
                    inc.severity === 'WARNING' ? 'bg-amber-50 border-amber-200 text-amber-600' :
                    'bg-cyan-50 border-cyan-200 text-cyan-600'
                  }`}>
                    {inc.severity === 'CRITICAL' ? <AlertTriangle className="w-4 h-4" /> :
                     inc.severity === 'WARNING' ? <ShieldAlert className="w-4 h-4" /> :
                     <CheckCircle2 className="w-4 h-4" />}
                  </div>

                  <div>
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="font-mono text-xs font-bold text-slate-800">{inc.id}</span>
                      <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold border ${severityBadge}`}>
                        {inc.severity}
                      </span>
                      <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold border ${statusBadge}`}>
                        {inc.status}
                      </span>
                      <span className="text-[11px] text-slate-400 font-mono flex items-center gap-1">
                        <Clock className="w-3 h-3" />
                        {inc.timestamp}
                      </span>
                    </div>

                    <h3 className="text-sm font-bold text-slate-900 mt-1">
                      {inc.title}
                    </h3>
                    <div className="text-xs text-slate-500 font-mono mt-0.5 flex flex-wrap items-center gap-3">
                      <span>Endpoint: <strong className="text-slate-700">{inc.affectedEndpoint}</strong></span>
                      <span>·</span>
                      <span>File: <strong className="text-cyan-700">{inc.affectedFile}</strong></span>
                      <span>·</span>
                      <span>Service: <strong className="text-slate-700">{inc.service}</strong></span>
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-3 self-end md:self-center shrink-0">
                  <div className="text-right hidden sm:block font-mono text-[11px]">
                    <div className="text-emerald-600 font-semibold">{inc.tokensPreserved}</div>
                    <div className="text-slate-400">{inc.latencyBypass}</div>
                  </div>

                  {/* One-Click Incident -> IDE Deep-Dive Action Button */}
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      handleDeepDiveClick(inc);
                    }}
                    className="px-3.5 py-1.5 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-white text-xs font-bold shadow-sm flex items-center gap-1.5 transition cursor-pointer"
                    title={`Open ${inc.affectedFile} in Ask IDE and investigate with Skelion AI`}
                  >
                    <Bot className="w-3.5 h-3.5" />
                    <span>Investigate with AI</span>
                    <ArrowRight className="w-3 h-3" />
                  </button>

                  <div className="text-slate-400">
                    {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                  </div>
                </div>
              </div>

              {/* Collapsible Root Cause & Stack Trace Details */}
              {isExpanded && (
                <div className="px-5 pb-5 pt-2 border-t border-slate-100 bg-slate-50/50 space-y-3 text-xs">
                  <div>
                    <span className="font-bold text-slate-900">Root Cause Diagnostics:</span>
                    <p className="text-slate-700 mt-1 leading-relaxed">{inc.rootCause}</p>
                  </div>

                  <div>
                    <div className="flex items-center justify-between">
                      <span className="font-bold text-slate-900">Captured Edge Stack Trace:</span>
                      <span className="font-mono text-[10px] text-cyan-700 bg-cyan-50 px-2 py-0.5 rounded border border-cyan-200">
                        Affected: {inc.affectedFile}
                      </span>
                    </div>
                    <div className="mt-1.5 p-3 rounded-xl bg-slate-950 text-slate-200 font-mono text-[11px] overflow-x-auto border border-slate-800 leading-normal">
                      <pre><code>{inc.stackTrace}</code></pre>
                    </div>
                  </div>

                  <div className="flex items-center justify-end pt-1">
                    <button
                      onClick={() => handleDeepDiveClick(inc)}
                      className="text-xs font-bold text-cyan-700 hover:text-cyan-800 flex items-center gap-1 cursor-pointer"
                    >
                      <span>Deep-dive into {inc.affectedFile} in IDE</span>
                      <ArrowRight className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};
