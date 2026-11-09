import React, { useState, useEffect } from 'react';
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
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [incidents, setIncidents] = useState<IncidentRecord[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  const fetchIncidents = async () => {
    setIsLoading(true);
    try {
      const apiBase = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8002';
      const res = await fetch(`${apiBase}/v1/incidents`).catch(() => fetch('/api/incidents'));
      if (res && res.ok) {
        const data = await res.json();
        const rawList = data.incidents || (Array.isArray(data) ? data : []);
        if (Array.isArray(rawList)) {
          const mapped: IncidentRecord[] = rawList.map((inc: any) => ({
            id: inc.id || 'INC-LIVE',
            service: inc.service || inc.route || inc.route_path || 'Production Route',
            title: inc.title || inc.summary || inc.error_summary || 'Edge Incident',
            severity: (inc.severity || (inc.status_code >= 500 ? 'CRITICAL' : 'WARNING')) as any,
            status: (inc.status ? inc.status.toUpperCase() : 'ACTIVE') as any,
            timestamp: inc.last_seen_at || inc.created_at ? new Date(inc.last_seen_at || inc.created_at).toLocaleTimeString() : 'Just now',
            latencyBypass: inc.latency_ms ? `${inc.latency_ms}ms latency` : '0ms edge bypass',
            tokensPreserved: inc.tokens_saved || '0 tokens',
            affectedEndpoint: inc.route || inc.route_path || 'N/A',
            affectedFile: inc.affected_file || inc.file || 'server',
            rootCause: inc.summary || inc.error_summary || 'No root cause recorded',
            stackTrace: inc.stackTrace || inc.captured_body || 'No stack trace captured',
            initialCode: inc.initialCode || '',
            suggestedPatch: inc.generated_diff || inc.suggestedPatch || undefined,
          }));
          setIncidents(mapped);
          if (mapped.length > 0) setExpandedId(mapped[0].id);
          setIsLoading(false);
          return;
        }
      }
    } catch (e) {
      console.warn('Failed to fetch real incidents:', e);
    }
    setIncidents([]);
    setIsLoading(false);
  };

  useEffect(() => {
    fetchIncidents();
  }, []);

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
        {filteredIncidents.length === 0 && (
          <div className="bg-white/80 backdrop-blur-xl border border-slate-200/80 rounded-2xl p-10 text-center space-y-3 shadow-[0_8px_32px_0_rgba(31,38,135,0.07)]">
            <div className="w-12 h-12 rounded-full bg-emerald-50 text-emerald-600 flex items-center justify-center mx-auto border border-emerald-200">
              <CheckCircle2 className="w-6 h-6" />
            </div>
            <h3 className="text-base font-bold text-slate-900">Zero Active Incidents</h3>
            <p className="text-xs text-slate-500 max-w-md mx-auto">
              All production routes and LLM gateways are operating normally. The Skelion Edge proxy is actively intercepting and monitoring traffic with zero unhandled exceptions.
            </p>
            <button
              onClick={fetchIncidents}
              className="mt-2 inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold bg-slate-100 hover:bg-slate-200 text-slate-700 transition"
            >
              <span>Refresh Feed</span>
            </button>
          </div>
        )}

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
