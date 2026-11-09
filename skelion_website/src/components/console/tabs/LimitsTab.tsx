import React, { useState, useEffect } from 'react';
import { 
  Gauge, 
  Key, 
  Zap, 
  RotateCw, 
  ShieldCheck, 
  CreditCard, 
  ArrowUpRight,
  TrendingUp,
  AlertTriangle,
  Receipt,
  CheckCircle2,
  Clock
} from 'lucide-react';
import { getUserCreditState, UserCreditState } from '../../../utils/creditLedger';

interface LimitsTabProps {
  onOpenCheckout?: (
    planId?: string, 
    coupon?: string, 
    currency?: 'INR' | 'USD', 
    customData?: { customAmount: number; customCredits: number }
  ) => void;
}

export const LimitsTab: React.FC<LimitsTabProps> = ({ onOpenCheckout }) => {
  const [creditState, setCreditState] = useState<UserCreditState>(getUserCreditState);

  useEffect(() => {
    const handleUpdate = (e: any) => {
      if (e.detail) {
        setCreditState(e.detail);
      } else {
        setCreditState(getUserCreditState());
      }
    };
    window.addEventListener('skelion:credits-updated', handleUpdate);
    return () => window.removeEventListener('skelion:credits-updated', handleUpdate);
  }, []);

  const keyPools = [
    { name: 'Skelion Primary Reasoning Cluster (US-East Edge · Mesh 1)', quota: '120k / 150k tpm', percent: 80, status: 'Healthy', color: 'bg-emerald-500' },
    { name: 'Skelion High-Throughput Node (EU-Central Edge · Mesh 2)', quota: '45k / 100k tpm', percent: 45, status: 'Active', color: 'bg-cyan-500' },
    { name: 'Skelion Low-Latency Standby Mesh (AP-South Edge · Mesh 3)', quota: '12k / 80k tpm', percent: 15, status: 'Standby', color: 'bg-purple-500' },
    { name: 'Skelion Autonomous Fallback Ring (Global Gossip · Mesh 4)', quota: '8k / 200k tpm', percent: 4, status: 'Idle', color: 'bg-blue-500' }
  ];

  const creditPercentage = Math.min(100, Math.round(((creditState.balance || 0) / (creditState.totalPurchased || 2000)) * 100));

  return (
    <div className="space-y-6">
      {/* Header Overview Card */}
      <div className="bg-white/80 backdrop-blur-xl border border-slate-200/80 rounded-2xl p-5 shadow-[0_8px_32px_0_rgba(31,38,135,0.07)] flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-lg font-bold text-slate-900">API Limits, Key Pools &amp; Quotas</h2>
            <span className="px-2 py-0.5 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
              Mesh Resilient (0 Throttles)
            </span>
          </div>
          <p className="text-xs text-slate-500 font-mono mt-0.5">
            Active Tier: <span className="text-cyan-700 font-bold">{creditState.activePlan}</span> · Real-time agent token consumption &amp; persistent credit ledger.
          </p>
        </div>

        {onOpenCheckout && (
          <div className="flex items-center gap-2">
            <button
              onClick={() => onOpenCheckout('custom', undefined, 'INR', { customAmount: 500, customCredits: 500 })}
              className="px-3.5 py-2 rounded-xl bg-white border border-slate-300 text-slate-800 text-xs font-bold hover:bg-slate-50 flex items-center gap-1.5 transition shadow-xs cursor-pointer"
            >
              <Zap className="w-3.5 h-3.5 text-cyan-600" />
              <span>Custom Refill</span>
            </button>
            <button
              onClick={() => onOpenCheckout('pro')}
              className="px-4 py-2 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 text-white text-xs font-bold shadow-md shadow-cyan-500/20 hover:from-cyan-400 hover:to-blue-500 flex items-center gap-1.5 transition cursor-pointer"
            >
              <CreditCard className="w-3.5 h-3.5" />
              <span>Increase Token Quota</span>
              <ArrowUpRight className="w-3.5 h-3.5" />
            </button>
          </div>
        )}
      </div>

      {/* Metrics Row */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Dynamic Live Credits Card */}
        <div className="bg-white/80 backdrop-blur-xl border border-slate-200/80 rounded-2xl p-4 shadow-xs">
          <div className="flex items-center justify-between text-xs text-slate-500">
            <span>Available Credits</span>
            <Zap className="w-4 h-4 text-cyan-600" />
          </div>
          <div className="text-2xl font-black text-slate-900 mt-2 font-mono">
            {creditState.balance.toLocaleString()} Credits
          </div>
          <div className="text-[11px] text-cyan-700 font-mono mt-1 font-semibold">
            = {(creditState.balance * 1000).toLocaleString()} Model Tokens
          </div>
          <div className="w-full bg-slate-100 rounded-full h-1.5 mt-2.5 overflow-hidden">
            <div className="bg-cyan-500 h-full rounded-full transition-all duration-500" style={{ width: `${creditPercentage}%` }} />
          </div>
        </div>

        <div className="bg-white/80 backdrop-blur-xl border border-slate-200/80 rounded-2xl p-4 shadow-xs">
          <div className="flex items-center justify-between text-xs text-slate-500">
            <span>429 Bypasses Executed</span>
            <RotateCw className="w-4 h-4 text-emerald-600" />
          </div>
          <div className="text-2xl font-black text-slate-900 mt-2 font-mono">142 Intercepts</div>
          <div className="text-[11px] text-emerald-600 font-mono mt-1 font-semibold">100% zero downtime maintained</div>
          <div className="w-full bg-slate-100 rounded-full h-1.5 mt-2.5 overflow-hidden">
            <div className="bg-emerald-500 h-full rounded-full" style={{ width: '100%' }} />
          </div>
        </div>

        <div className="bg-white/80 backdrop-blur-xl border border-slate-200/80 rounded-2xl p-4 shadow-xs">
          <div className="flex items-center justify-between text-xs text-slate-500">
            <span>Tokens Preserved</span>
            <TrendingUp className="w-4 h-4 text-purple-600" />
          </div>
          <div className="text-2xl font-black text-slate-900 mt-2 font-mono">489.2k Tokens</div>
          <div className="text-[11px] text-purple-700 font-mono mt-1 font-semibold">Saved via AST deduplication</div>
          <div className="w-full bg-slate-100 rounded-full h-1.5 mt-2.5 overflow-hidden">
            <div className="bg-purple-500 h-full rounded-full" style={{ width: '84%' }} />
          </div>
        </div>

        <div className="bg-white/80 backdrop-blur-xl border border-slate-200/80 rounded-2xl p-4 shadow-xs">
          <div className="flex items-center justify-between text-xs text-slate-500">
            <span>Multi-Region Mesh</span>
            <ShieldCheck className="w-4 h-4 text-emerald-600" />
          </div>
          <div className="text-2xl font-black text-slate-900 mt-2 font-mono">4 / 4 Nodes Active</div>
          <div className="text-[11px] text-slate-500 font-mono mt-1">Automated Failover Ready</div>
          <div className="w-full bg-slate-100 rounded-full h-1.5 mt-2.5 overflow-hidden">
            <div className="bg-emerald-500 h-full rounded-full" style={{ width: '100%' }} />
          </div>
        </div>
      </div>

      {/* Token Economics Formula Transparency Card */}
      <div className="bg-white/80 backdrop-blur-xl border border-slate-200/80 rounded-2xl p-5 shadow-xs space-y-3">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-lg bg-cyan-100 text-cyan-700 flex items-center justify-center font-bold text-xs">
              ₹
            </div>
            <h3 className="text-sm font-bold text-slate-900">
              Predictable Credit Economics Standard
            </h3>
          </div>
          <span className="text-[11px] font-mono px-2 py-0.5 rounded-md bg-emerald-50 text-emerald-700 border border-emerald-200 font-semibold">
            1 Credit = 1,000 Tokens (Exact)
          </span>
        </div>
        <p className="text-xs text-slate-600 leading-relaxed">
          Skelion maintains strict, mathematical token transparency across all models. Billed cleanly via credits with 0ms 429 failover routing, AST verification, and real-time PII redaction included.
        </p>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-2">
          <div className="p-3 rounded-xl bg-slate-50 border border-slate-200/80">
            <div className="text-[11px] text-slate-500 font-mono">1 Credit Equivalent</div>
            <div className="text-base font-black text-slate-900 mt-0.5 font-mono">1,000 Tokens</div>
            <div className="text-[10px] text-slate-400 font-mono mt-0.5">High-speed model inference</div>
          </div>
          <div className="p-3 rounded-xl bg-cyan-50/60 border border-cyan-200/80">
            <div className="text-[11px] text-cyan-800 font-mono font-semibold">Resilience Hotpath</div>
            <div className="text-base font-black text-cyan-900 mt-0.5 font-mono">0ms Downtime</div>
            <div className="text-[10px] text-cyan-600 font-mono mt-0.5">Automated key rotation pool</div>
          </div>
          <div className="p-3 rounded-xl bg-purple-50/60 border border-purple-200/80">
            <div className="text-[11px] text-purple-800 font-mono font-semibold">Credit Rollover</div>
            <div className="text-base font-black text-purple-900 mt-0.5 font-mono">12 Months</div>
            <div className="text-[10px] text-purple-600 font-mono mt-0.5">Credits never expire early</div>
          </div>
        </div>
      </div>

      {/* Real Persistent Credit Ledger & Transaction History */}
      <div className="bg-white/80 backdrop-blur-xl border border-slate-200/80 rounded-2xl p-5 shadow-xs space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Receipt className="w-4 h-4 text-cyan-600" />
            <h3 className="text-sm font-bold text-slate-900">
              Credit Ledger &amp; Refill Transaction History
            </h3>
          </div>
          <span className="text-xs text-slate-500 font-mono">
            {creditState.transactions.length} Verified Ledger Events
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs font-mono">
            <thead>
              <tr className="border-b border-slate-200 text-slate-500 text-[11px]">
                <th className="pb-2 font-semibold">DATE</th>
                <th className="pb-2 font-semibold">DESCRIPTION</th>
                <th className="pb-2 font-semibold">CREDITS</th>
                <th className="pb-2 font-semibold">EXACT TOKENS</th>
                <th className="pb-2 font-semibold">AMOUNT PAID</th>
                <th className="pb-2 font-semibold">INVOICE</th>
                <th className="pb-2 font-semibold text-right">STATUS</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {creditState.transactions.map((tx) => (
                <tr key={tx.id} className="hover:bg-slate-50/80 transition-colors">
                  <td className="py-2.5 text-slate-500 flex items-center gap-1.5">
                    <Clock className="w-3 h-3 text-slate-400" />
                    <span>{tx.date}</span>
                  </td>
                  <td className="py-2.5 text-slate-900 font-semibold">{tx.description}</td>
                  <td className="py-2.5">
                    <span className={`font-bold ${tx.credits >= 0 ? 'text-emerald-700' : 'text-rose-600'}`}>
                      {tx.credits >= 0 ? `+${tx.credits.toLocaleString()}` : tx.credits.toLocaleString()} Cr
                    </span>
                  </td>
                  <td className="py-2.5 text-cyan-700 font-semibold">
                    {tx.tokens >= 0 ? `+${tx.tokens.toLocaleString()}` : tx.tokens.toLocaleString()} Tokens
                  </td>
                  <td className="py-2.5 text-slate-800 font-medium">
                    {tx.amountPaid === 0 ? 'Free ($0)' : `${tx.currency === 'USD' ? '$' : '₹'}${tx.amountPaid.toLocaleString()}`}
                  </td>
                  <td className="py-2.5 text-slate-700 font-mono text-[11px]">
                    <div className="flex items-center gap-1.5">
                      <span>{tx.invoiceNumber}</span>
                      <a
                        href={`/api/receipt?invoiceNumber=${encodeURIComponent(tx.invoiceNumber)}&amount=${tx.amountPaid}&currency=${tx.currency}&credits=${tx.credits}&description=${encodeURIComponent(tx.description)}`}
                        target="_blank"
                        rel="noreferrer"
                        title="Download / Print Official Receipt"
                        className="text-cyan-600 hover:text-cyan-800 p-0.5 rounded hover:bg-slate-100 transition inline-flex items-center"
                      >
                        <Receipt className="w-3.5 h-3.5" />
                      </a>
                    </div>
                  </td>
                  <td className="py-2.5 text-right">
                    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
                      <CheckCircle2 className="w-3 h-3 text-emerald-600" />
                      <span>{tx.status}</span>
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Multi-Provider Key Pools Breakdown */}
      <div className="bg-white/80 backdrop-blur-xl border border-slate-200/80 rounded-2xl p-5 shadow-xs space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
            <Key className="w-4 h-4 text-cyan-600" />
            <span>Active Skelion Mesh Node Clusters</span>
          </h3>
          <span className="text-xs text-slate-500 font-mono">Auto-Failover Priority: 1 → 2 → 3 → 4</span>
        </div>

        <div className="space-y-3.5">
          {keyPools.map((pool, idx) => (
            <div key={idx} className="p-3.5 rounded-xl border border-slate-200/70 bg-white/70 space-y-2">
              <div className="flex items-center justify-between text-xs font-semibold text-slate-800">
                <div className="flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-emerald-500" />
                  <span>{pool.name}</span>
                </div>
                <div className="flex items-center gap-3 font-mono text-[11px]">
                  <span className="text-slate-500">{pool.quota}</span>
                  <span className="px-2 py-0.5 rounded-md bg-slate-100 text-slate-700 font-bold">{pool.status}</span>
                </div>
              </div>

              <div className="w-full bg-slate-100 rounded-full h-2 overflow-hidden">
                <div className={`${pool.color} h-full rounded-full transition-all duration-500`} style={{ width: `${pool.percent}%` }} />
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
