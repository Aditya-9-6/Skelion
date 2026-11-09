import React from 'react';
import { Gauge, ShieldAlert, Cpu, Lock } from 'lucide-react';

export const StatsBar: React.FC = () => {
  const stats = [
    {
      label: 'Edge Proxy Overhead',
      value: '< 5ms',
      desc: 'Transparent reverse proxy telemetry with sub-millisecond hotpath',
      icon: Gauge,
      color: 'text-cyan-600',
      badgeBg: 'bg-cyan-50 border-cyan-200 text-cyan-800',
    },
    {
      label: 'Fail-Open Reliability',
      value: '100%',
      desc: 'Zero-drop guarantee: edge never breaks customer traffic on engine panic',
      icon: ShieldAlert,
      color: 'text-emerald-600',
      badgeBg: 'bg-emerald-50 border-emerald-200 text-emerald-800',
    },
    {
      label: '429 Rate Limits Saved',
      value: '0 Dropped',
      desc: 'Multi-provider LLM key pool rotates with exponential backoff',
      icon: Cpu,
      color: 'text-purple-600',
      badgeBg: 'bg-purple-50 border-purple-200 text-purple-800',
    },
    {
      label: 'Zero-Trust PII Redaction',
      value: '100% Scrubbed',
      desc: 'Authorization tokens, bearer secrets, cookies & credentials masked',
      icon: Lock,
      color: 'text-pink-600',
      badgeBg: 'bg-pink-50 border-pink-200 text-pink-800',
    },
  ];

  return (
    <section className="border-y border-slate-200/80 bg-white/70 backdrop-blur-xl py-10 shadow-sm">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
          {stats.map((stat, i) => {
            const Icon = stat.icon;
            return (
              <div
                key={i}
                className="p-5 rounded-2xl bg-white/80 backdrop-blur-md border border-slate-200/90 shadow-sm hover:shadow-lg hover:border-cyan-400/50 transition-all duration-300"
              >
                <div className="flex items-center justify-between mb-3">
                  <span className="text-xs uppercase tracking-wider font-semibold text-slate-500 font-mono">
                    {stat.label}
                  </span>
                  <div className={`p-1.5 rounded-lg border ${stat.badgeBg}`}>
                    <Icon className={`w-4 h-4 ${stat.color}`} />
                  </div>
                </div>
                <div className="text-3xl font-extrabold tracking-tight mb-1 text-slate-900">
                  {stat.value}
                </div>
                <p className="text-xs text-slate-600 leading-relaxed">
                  {stat.desc}
                </p>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
};
