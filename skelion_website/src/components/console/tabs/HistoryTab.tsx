import React, { useState } from 'react';
import { 
  History, 
  Search, 
  Filter, 
  Clock, 
  CheckCircle2, 
  XCircle, 
  ArrowUpRight, 
  GitCommit, 
  ExternalLink,
  MessageSquare,
  Bot
} from 'lucide-react';

interface AuditItem {
  id: string;
  type: 'CHAT' | 'INCIDENT_PATCH' | 'KEY_ROTATION' | 'PII_SCRUB';
  title: string;
  timestamp: string;
  status: 'SUCCESS' | 'MITIGATED' | 'BLOCKED';
  author: string;
  model: string;
  details: string;
}

export const HistoryTab: React.FC = () => {
  const [filterType, setFilterType] = useState<string>('ALL');
  const [searchQuery, setSearchQuery] = useState<string>('');

  const auditLogs: AuditItem[] = [
    {
      id: 'AUD-901',
      type: 'INCIDENT_PATCH',
      title: 'Synthesized checkout currency fallback patch',
      timestamp: 'Today, 10:18 AM',
      status: 'SUCCESS',
      author: 'Skelion Agent (Autonomous)',
      model: 'Skelion AI Agent (Primary Mesh)',
      details: 'Patched validateCurrency() in src/services/payment.ts, unit tests passed 14/14.'
    },
    {
      id: 'AUD-899',
      type: 'KEY_ROTATION',
      title: 'Auto-rotated 429 throttled key pool node #2',
      timestamp: 'Today, 09:24 AM',
      status: 'MITIGATED',
      author: 'Gossip Mesh Controller',
      model: 'Skelion Gossip Mesh Controller',
      details: 'Detected upstream 429 burst. Traffic seamlessly shifted with 1.4ms zero-downtime bypass.'
    },
    {
      id: 'AUD-892',
      type: 'PII_SCRUB',
      title: 'Redacted JWT Bearer Token from query string',
      timestamp: 'Yesterday, 07:45 PM',
      status: 'MITIGATED',
      author: 'Edge Redaction Filter',
      model: 'eBPF Filter v2',
      details: 'Scrubbed query param token=*** from ingress access logging stream.'
    },
    {
      id: 'AUD-880',
      type: 'CHAT',
      title: 'Session: Chaos test generation for payment microservice',
      timestamp: 'Nov 6, 2026, 04:12 PM',
      status: 'SUCCESS',
      author: 'Aditya-9-6',
      model: 'Skelion AI Agent (Interactive)',
      details: 'Generated Vitest mock chaos suite with 500 error injections.'
    },
    {
      id: 'AUD-874',
      type: 'INCIDENT_PATCH',
      title: 'Postgres connection pool leak resolution',
      timestamp: 'Nov 5, 2026, 02:30 PM',
      status: 'SUCCESS',
      author: 'Skelion Agent (Autonomous)',
      model: 'Skelion Autonomous Resilience Agent',
      details: 'Applied release() in finally block across database query handlers.'
    }
  ];

  const filteredLogs = auditLogs.filter((log) => {
    const matchesType = filterType === 'ALL' || log.type === filterType;
    const matchesSearch = 
      log.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      log.details.toLowerCase().includes(searchQuery.toLowerCase()) ||
      log.author.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesType && matchesSearch;
  });

  return (
    <div className="space-y-6">
      {/* Top Controls Bar */}
      <div className="bg-white/80 backdrop-blur-xl border border-slate-200/80 rounded-2xl p-5 shadow-[0_8px_32px_0_rgba(31,38,135,0.07)] flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-lg font-bold text-slate-900">Audit History &amp; Session Logs</h2>
            <span className="px-2 py-0.5 rounded-full text-xs font-semibold bg-slate-100 text-slate-700 border border-slate-200">
              {auditLogs.length} Events Logged
            </span>
          </div>
          <p className="text-xs text-slate-500 font-mono mt-0.5">
            Immutable trace of all autonomous actions, chat sessions, PR generations, and key rotations.
          </p>
        </div>

        {/* Search & Filter */}
        <div className="flex flex-wrap items-center gap-2.5 w-full md:w-auto">
          <div className="relative flex-1 md:w-56">
            <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search audit records..."
              className="w-full text-xs bg-white border border-slate-200 rounded-xl pl-9 pr-3 py-2 text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-cyan-500/20"
            />
          </div>

          <div className="flex items-center gap-1 bg-slate-100 p-1 rounded-xl text-xs font-semibold">
            {['ALL', 'INCIDENT_PATCH', 'KEY_ROTATION', 'PII_SCRUB', 'CHAT'].map((type) => (
              <button
                key={type}
                onClick={() => setFilterType(type)}
                className={`px-2.5 py-1 rounded-lg transition ${
                  filterType === type
                    ? 'bg-white text-slate-900 shadow-xs'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                {type.replace('_', ' ')}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Audit Timeline Records */}
      <div className="space-y-3">
        {filteredLogs.map((item) => {
          const statusBadge = {
            SUCCESS: 'bg-emerald-50 text-emerald-700 border-emerald-200',
            MITIGATED: 'bg-cyan-50 text-cyan-700 border-cyan-200',
            BLOCKED: 'bg-rose-50 text-rose-700 border-rose-200'
          }[item.status];

          return (
            <div
              key={item.id}
              className="bg-white/80 backdrop-blur-xl border border-slate-200/80 rounded-2xl p-4 sm:p-5 shadow-xs hover:border-slate-300 transition"
            >
              <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
                <div className="flex items-start gap-3">
                  <div className="w-8 h-8 rounded-xl bg-slate-100 border border-slate-200 flex items-center justify-center text-slate-700 shrink-0 mt-0.5">
                    {item.type === 'CHAT' ? <MessageSquare className="w-4 h-4 text-cyan-600" /> :
                     item.type === 'KEY_ROTATION' ? <GitCommit className="w-4 h-4 text-purple-600" /> :
                     <CheckCircle2 className="w-4 h-4 text-emerald-600" />}
                  </div>

                  <div>
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="font-mono text-xs font-bold text-slate-900">{item.id}</span>
                      <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold border ${statusBadge}`}>
                        {item.status}
                      </span>
                      <span className="text-[10px] font-mono font-semibold px-2 py-0.5 rounded-md bg-slate-100 text-slate-600 border border-slate-200">
                        {item.type}
                      </span>
                      <span className="text-[11px] text-slate-400 font-mono flex items-center gap-1">
                        <Clock className="w-3 h-3" />
                        {item.timestamp}
                      </span>
                    </div>

                    <h3 className="text-sm font-bold text-slate-900 mt-1">
                      {item.title}
                    </h3>

                    <p className="text-xs text-slate-600 mt-1 leading-relaxed">
                      {item.details}
                    </p>
                  </div>
                </div>

                <div className="self-end sm:self-center font-mono text-[11px] text-right text-slate-500 shrink-0">
                  <div className="font-semibold text-slate-700">{item.author}</div>
                  <div className="text-[10px] text-cyan-700">{item.model}</div>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
