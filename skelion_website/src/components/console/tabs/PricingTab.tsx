import React from 'react';
import { PricingCalculator, CustomCreditOrderData } from '../../PricingCalculator';
import { CreditCard, Sparkles, CheckCircle2 } from 'lucide-react';

interface PricingTabProps {
  onSelectPlan: (
    planId: string, 
    coupon?: string, 
    currency?: 'INR' | 'USD', 
    customData?: CustomCreditOrderData
  ) => void;
}

export const PricingTab: React.FC<PricingTabProps> = ({ onSelectPlan }) => {
  return (
    <div className="space-y-6">
      {/* Top Banner */}
      <div className="bg-white/80 backdrop-blur-xl border border-slate-200/80 rounded-2xl p-5 shadow-[0_8px_32px_0_rgba(31,38,135,0.07)] flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-lg font-bold text-slate-900">Subscription &amp; Token Top-up</h2>
            <span className="px-2 py-0.5 rounded-full text-xs font-semibold bg-cyan-50 text-cyan-700 border border-cyan-200">
              Live Razorpay Gateway
            </span>
          </div>
          <p className="text-xs text-slate-500 font-mono mt-0.5">
            Upgrade your team tier, purchase on-demand credit refills, and increase rate limits.
          </p>
        </div>

        <div className="flex items-center gap-2 text-xs font-mono text-emerald-600 bg-emerald-50 px-3 py-1.5 rounded-xl border border-emerald-200">
          <CheckCircle2 className="w-4 h-4" />
          <span>Active Plan: PRO DEVELOPER (Monthly)</span>
        </div>
      </div>

      {/* Pricing Calculator component embedded */}
      <div className="bg-white/70 backdrop-blur-xl border border-slate-200/80 rounded-2xl p-6 shadow-xs">
        <PricingCalculator onSelectPlan={onSelectPlan} />
      </div>
    </div>
  );
};
