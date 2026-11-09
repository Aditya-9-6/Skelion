import React from 'react';
import {
  ShieldCheck,
  Lock,
  RefreshCcw,
  Scale,
  ArrowDown,
  Sparkles,
} from 'lucide-react';

interface TrustHubOverviewProps {
  onScrollToSection: (id: string) => void;
}

export const TrustHubOverview: React.FC<TrustHubOverviewProps> = ({ onScrollToSection }) => {
  const trustPillars = [
    {
      id: 'terms',
      icon: Scale,
      title: '100% Code Ownership',
      badge: 'Zero Vendor Lock',
      color: 'from-cyan-500/20 to-blue-500/10',
      borderColor: 'border-cyan-500/30',
      iconColor: 'text-cyan-400',
      description:
        'You exclusively retain full copyright and intellectual property rights over all repositories, AST nodes, and agent-remediated diffs.',
      actionText: 'View Terms of Service →',
    },
    {
      id: 'privacy',
      icon: ShieldCheck,
      title: 'Zero Code Retention',
      badge: 'DPDP 2023 & GDPR',
      color: 'from-emerald-500/20 to-teal-500/10',
      borderColor: 'border-emerald-500/30',
      iconColor: 'text-emerald-400',
      description:
        'Code inspected for incident remediation is processed exclusively in-memory and instantly purged. Zero files are persisted or mined for AI training.',
      actionText: 'Read Privacy Charter →',
    },
    {
      id: 'refund',
      icon: RefreshCcw,
      title: '7-Day Money-Back Guarantee',
      badge: 'Commercial Fairness',
      color: 'from-amber-500/20 to-orange-500/10',
      borderColor: 'border-amber-500/30',
      iconColor: 'text-amber-400',
      description:
        'Full 100% refund on Pro subscriptions within 7 calendar days if less than 10% monthly credits have been consumed. 1-click self-serve cancellation.',
      actionText: 'Inspect Refund Rules →',
    },
    {
      id: 'security',
      icon: Lock,
      title: 'Fail-Open & Egress Guard',
      badge: 'Zero Exfiltration',
      color: 'from-blue-500/20 to-indigo-500/10',
      borderColor: 'border-blue-500/30',
      iconColor: 'text-blue-400',
      description:
        'Outbound proxy guarantees zero unauthorized telemetry. If cloud services ever degrade, your web environment stays responsive and never blocks.',
      actionText: 'Audit Security Architecture →',
    },
  ];

  return (
    <section
      id="overview"
      className="relative min-h-screen flex flex-col justify-center items-center pt-28 pb-16 px-4 sm:px-6 lg:px-8 z-10"
    >
      <div className="max-w-6xl w-full mx-auto space-y-12">
        {/* Hero Tag & Title */}
        <div className="text-center space-y-5 max-w-3xl mx-auto">
          <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-cyan-950/60 border border-cyan-500/30 text-cyan-300 text-xs font-mono tracking-wider uppercase backdrop-blur-md shadow-[0_0_15px_rgba(0,242,254,0.15)]">
            <Sparkles className="w-3.5 h-3.5 text-cyan-400 animate-pulse" />
            <span>Skelion Legal, Trust & Security Hub</span>
          </div>

          <h1 className="text-4xl sm:text-5xl lg:text-6xl font-black tracking-tight text-white leading-tight">
            Autonomous AI Reliability.{' '}
            <span className="text-gradient-cyan block sm:inline">
              Zero Compromise on Trust.
            </span>
          </h1>

          <p className="text-base sm:text-lg text-slate-300 leading-relaxed max-w-2xl mx-auto font-normal">
            Skelion empowers developer teams with real-time incident remediation and fail-open proxies.
            Our legal contracts are built for modern enterprise scrutiny: transparent, sovereign, and
            guaranteeing complete privacy.
          </p>

          <div className="flex flex-wrap items-center justify-center gap-3 pt-2">
            <button
              onClick={() => onScrollToSection('terms')}
              className="px-6 py-3 rounded-full bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-slate-950 font-bold font-mono text-xs tracking-wider uppercase shadow-[0_0_25px_rgba(0,242,254,0.35)] transition-all hover:scale-105"
            >
              Explore Full Legal Sections
            </button>
            <button
              onClick={() => onScrollToSection('privacy')}
              className="px-6 py-3 rounded-full bg-white/5 hover:bg-white/10 border border-white/15 text-slate-200 font-mono text-xs tracking-wider uppercase backdrop-blur-md transition-all hover:border-cyan-500/40"
            >
              Zero-Code-Retention Charter
            </button>
          </div>
        </div>

        {/* 4 Interactive Glassmorphic Trust Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {trustPillars.map((pillar) => {
            const Icon = pillar.icon;
            return (
              <div
                key={pillar.id}
                onClick={() => onScrollToSection(pillar.id)}
                className={`glass-panel-interactive p-6 sm:p-8 rounded-2xl relative overflow-hidden group cursor-pointer border ${pillar.borderColor} bg-gradient-to-br ${pillar.color}`}
              >
                {/* Background Specular Flare */}
                <div className="absolute top-0 right-0 w-44 h-44 bg-cyan-500/5 rounded-full blur-3xl pointer-events-none group-hover:bg-cyan-500/10 transition-all" />

                <div className="relative z-10 flex flex-col justify-between h-full space-y-4">
                  <div className="flex items-center justify-between">
                    <div className="p-3 rounded-xl bg-white/5 border border-white/10 group-hover:scale-110 transition-transform">
                      <Icon className={`w-6 h-6 ${pillar.iconColor}`} />
                    </div>
                    <span className="text-[10px] font-mono font-bold tracking-widest px-2.5 py-1 rounded-full bg-white/5 text-slate-300 border border-white/10 uppercase">
                      {pillar.badge}
                    </span>
                  </div>

                  <div>
                    <h2 className="text-xl font-bold text-white tracking-tight group-hover:text-cyan-300 transition-colors">
                      {pillar.title}
                    </h2>
                    <p className="mt-2 text-xs sm:text-sm text-slate-300 leading-relaxed">
                      {pillar.description}
                    </p>
                  </div>

                  <div className="pt-2 text-xs font-mono font-semibold text-cyan-400 group-hover:translate-x-1 transition-transform flex items-center gap-1">
                    <span>{pillar.actionText}</span>
                  </div>
                </div>
              </div>
            );
          })}
        </div>

        {/* Trust Badges & Vital Stats Grid */}
        <div className="glass-panel p-6 rounded-2xl border border-white/10">
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-6 text-center divide-y lg:divide-y-0 lg:divide-x divide-white/10">
            <div className="pt-3 lg:pt-0">
              <div className="text-2xl sm:text-3xl font-black text-cyan-400 font-mono">100%</div>
              <div className="text-[11px] font-mono text-slate-400 uppercase tracking-wider mt-1">
                User IP Ownership
              </div>
            </div>

            <div className="pt-3 lg:pt-0">
              <div className="text-2xl sm:text-3xl font-black text-emerald-400 font-mono">0 Bytes</div>
              <div className="text-[11px] font-mono text-slate-400 uppercase tracking-wider mt-1">
                Persistent Code on Disk
              </div>
            </div>

            <div className="pt-3 lg:pt-0">
              <div className="text-2xl sm:text-3xl font-black text-amber-400 font-mono">7 Days</div>
              <div className="text-[11px] font-mono text-slate-400 uppercase tracking-wider mt-1">
                Full Money-Back Guarantee
              </div>
            </div>

            <div className="pt-3 lg:pt-0">
              <div className="text-2xl sm:text-3xl font-black text-purple-400 font-mono">&lt; 24h</div>
              <div className="text-[11px] font-mono text-slate-400 uppercase tracking-wider mt-1">
                Grievance Resolution SLA
              </div>
            </div>
          </div>
        </div>

        {/* Scroll down prompt */}
        <div className="flex flex-col items-center justify-center pt-4 text-center">
          <span className="text-[11px] font-mono text-slate-400 tracking-wider uppercase mb-2">
            Scroll to inspect interactive 3D legal sections
          </span>
          <button
            onClick={() => onScrollToSection('terms')}
            className="p-2 rounded-full bg-white/5 border border-white/10 text-cyan-400 hover:bg-cyan-500/10 hover:border-cyan-500/30 transition-all animate-bounce"
            aria-label="Scroll to Terms"
          >
            <ArrowDown className="w-4 h-4" />
          </button>
        </div>
      </div>
    </section>
  );
};
