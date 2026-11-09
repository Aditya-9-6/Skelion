import React, { useState } from 'react';
import { 
  Check, 
  CreditCard, 
  ChevronRight, 
  Tag, 
  CheckCircle2,
  Sparkles,
  Zap,
  Globe,
  ShieldCheck
} from 'lucide-react';

export interface CustomCreditOrderData {
  customAmount: number;
  customCredits: number;
}

interface PricingCalculatorProps {
  onSelectPlan: (
    planId: string, 
    coupon?: string, 
    currency?: 'INR' | 'USD', 
    customData?: CustomCreditOrderData
  ) => void;
}

export const PricingCalculator: React.FC<PricingCalculatorProps> = ({ onSelectPlan }) => {
  const [billingCycle, setBillingCycle] = useState<'monthly' | 'annual'>('monthly');
  const [currency, setCurrency] = useState<'INR' | 'USD'>('INR');
  const [couponInput, setCouponInput] = useState<string>('FOUNDING50');
  const [appliedCoupon, setAppliedCoupon] = useState<{ code: string; percent: number; desc: string } | null>({
    code: 'FOUNDING50',
    percent: 30,
    desc: 'Founding Developer Special: 30% discount applied!',
  });
  const [couponError, setCouponError] = useState<string | null>(null);

  // Custom credit refill input
  const [customAmountInput, setCustomAmountInput] = useState<number>(500);

  const coupons: Record<string, { percent: number; desc: string }> = {
    FOUNDING50: { percent: 30, desc: 'Founding Developer Special: 30% discount applied!' },
    STUDENT_OSS: { percent: 50, desc: 'Student & Open Source Maintainer 50% discount applied!' },
    EARLYBIRD: { percent: 20, desc: 'Early Adopter 20% discount applied!' },
  };

  const handleApplyCoupon = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    setCouponError(null);
    const cleaned = couponInput.trim().toUpperCase();
    if (coupons[cleaned]) {
      setAppliedCoupon({
        code: cleaned,
        percent: coupons[cleaned].percent,
        desc: coupons[cleaned].desc,
      });
    } else {
      setCouponError('Invalid or expired coupon code. Try FOUNDING50 or STUDENT_OSS.');
    }
  };

  const calculateFinalPrice = (baseMonthlyINR: number, baseMonthlyUSD: number) => {
    const isUSD = currency === 'USD';
    const baseMonthly = isUSD ? baseMonthlyUSD : baseMonthlyINR;
    if (baseMonthly === 0) return 0;

    // Annual discount: 2 months free (~17% off)
    let price = billingCycle === 'annual' ? Math.round((baseMonthly * 10) / 12) : baseMonthly;
    if (appliedCoupon) {
      price = Math.round(price * (1 - appliedCoupon.percent / 100));
    }
    return price;
  };

  const plans = [
    {
      id: 'pilot',
      name: 'Hosted Community',
      subtitle: 'Free & Solo Exploration',
      basePriceMonthlyINR: 0,
      basePriceMonthlyUSD: 0,
      credits: '50 Credits / mo',
      seats: '1 Seat',
      projects: '1 Project',
      models: 'Skelion AI Agent (Mesh Evaluation)',
      popular: false,
      buttonText: 'Get Started Free',
      features: [
        '50 Credits included monthly (50,000 Tokens)',
        'Fail-open edge proxy telemetry',
        'Basic incident fingerprinting',
        'Deterministic synthetic replay generation',
        '7-day trace & log retention',
        'Community Discord support',
      ],
    },
    {
      id: 'hosted_lite',
      name: 'Developer Lite',
      subtitle: 'Solo Devs & Indie Hackers',
      basePriceMonthlyINR: 749,
      basePriceMonthlyUSD: 9,
      originalPriceMonthlyINR: 999,
      originalPriceMonthlyUSD: 12,
      credits: '1,000 Credits / mo',
      seats: '1 Seat',
      projects: '3 Projects',
      models: 'Skelion AI Agent (Autonomous Mesh)',
      popular: false,
      buttonText: 'Upgrade to Lite',
      features: [
        '1,000 Credits included monthly (1,000,000 Tokens)',
        'Autonomous AST self-healing unlocked',
        'Full fail-open proxy with PII redaction',
        'Turnkey pytest/jest test synthesizer',
        '30-day trace & audit retention',
        'Standard email support',
      ],
    },
    {
      id: 'pro',
      name: 'Pro Developer',
      subtitle: 'Full-Featured Autonomous IDE',
      basePriceMonthlyINR: 1349,
      basePriceMonthlyUSD: 16,
      originalPriceMonthlyINR: 1899,
      originalPriceMonthlyUSD: 23,
      credits: '3,500 Credits / mo',
      seats: '1 Seat (Multi-Device)',
      projects: '10 Projects',
      models: 'Skelion Multi-Provider Concurrency Mesh',
      popular: true,
      buttonText: 'Upgrade to Pro',
      badge: 'MOST POPULAR · 20% LOWER THAN CURSOR',
      features: [
        '3,500 Credits included monthly (3,500,000 Tokens)',
        'Full-screen Antigravity-style IDE workspace',
        'Automated GitHub PR diagnostic cards & 1-click merge',
        'Shared multi-provider key-pool with 0ms 429 failover',
        'Monaco Editor with live syntax & AST validation',
        '90-day trace & audit retention',
        'Priority email & Discord response',
      ],
    },
    {
      id: 'hosted_team',
      name: 'Engineering Team',
      subtitle: 'High-Velocity Product Teams',
      basePriceMonthlyINR: 3799,
      basePriceMonthlyUSD: 45,
      originalPriceMonthlyINR: 4999,
      originalPriceMonthlyUSD: 60,
      credits: '12,000 Credits / mo',
      seats: '5 Seats Included',
      projects: '25 Projects',
      models: 'Skelion Team Concurrency Mesh',
      popular: false,
      buttonText: 'Upgrade to Team',
      features: [
        '12,000 Credits included monthly (12,000,000 Tokens)',
        '5 Developer seats included (add more at ₹599 / $7 per seat)',
        'Autonomous PR fix generation with CI verification',
        'Slack & Discord automated incident alerts',
        'Centralized team API keys & usage telemetry',
        '180-day audit ledger retention',
        'Dedicated onboarding session',
      ],
    },
    {
      id: 'hosted_business',
      name: 'Business Scale',
      subtitle: 'High-Volume Enterprise Systems',
      basePriceMonthlyINR: 9999,
      basePriceMonthlyUSD: 119,
      originalPriceMonthlyINR: 13999,
      originalPriceMonthlyUSD: 169,
      credits: '35,000 Credits / mo',
      seats: '20 Seats Included',
      projects: 'Unlimited Projects',
      models: 'Skelion Enterprise Intelligence Mesh',
      popular: false,
      buttonText: 'Upgrade to Business',
      features: [
        '35,000 Credits included monthly (35,000,000 Tokens)',
        '20 Developer seats included',
        'Priority reasoning queues & custom AST rules',
        'Immutable 365-day audit log retention & JSON export',
        'Custom error rate thresholds & webhook triggers',
        'Dedicated webhook & telemetry bridges',
        'High-priority engineering email & Discord assistance',
      ],
    },
    {
      id: 'enterprise',
      name: 'Enterprise Custom',
      subtitle: 'Bespoke Scale & Enterprise Governance',
      basePriceMonthlyINR: 39999,
      basePriceMonthlyUSD: 499,
      credits: '100,000+ Credits',
      seats: 'Unlimited Seats',
      projects: 'Unlimited Projects',
      models: 'Dedicated Multi-Region AI Mesh',
      popular: false,
      buttonText: 'Contact Enterprise Sales',
      features: [
        '100,000+ Credits included monthly (100,000,000+ Tokens)',
        'Custom credit quotas & volume scale pricing',
        'Custom SAML SSO & Team Access Governance',
        'Auto-merge for verified non-breaking patches',
        'Dedicated proxy egress bridges & IP allowlisting',
        'Custom enterprise contract & dedicated support channel',
        'Annual invoicing with GST / Net-30 terms',
      ],
    },
  ];

  const topupPacks = [
    {
      id: 'topup_small',
      name: 'Starter Pack',
      credits: '500 Credits',
      tokens: '500,000 Tokens',
      priceINR: 399,
      priceUSD: 5,
      effectiveRateINR: '₹0.79 / credit',
      effectiveRateUSD: '$0.010 / credit',
      badge: 'QUICK REFILL',
      popular: false,
    },
    {
      id: 'topup_medium',
      name: 'Growth Pack',
      credits: '1,500 Credits',
      tokens: '1,500,000 Tokens',
      priceINR: 999,
      priceUSD: 12,
      effectiveRateINR: '₹0.66 / credit',
      effectiveRateUSD: '$0.008 / credit',
      badge: 'SAVE 15% · POPULAR',
      popular: true,
    },
    {
      id: 'topup_large',
      name: 'Power Pack',
      credits: '5,000 Credits',
      tokens: '5,000,000 Tokens',
      priceINR: 2899,
      priceUSD: 35,
      effectiveRateINR: '₹0.57 / credit',
      effectiveRateUSD: '$0.007 / credit',
      badge: 'BEST VALUE · SAVE 25%',
      popular: false,
    },
  ];

  const currencySymbol = currency === 'USD' ? '$' : '₹';

  // Custom on-demand refill calculation (No discounts, standard base rate)
  // Starter pack is ~₹0.79/cr ($0.010/cr), Growth is ~₹0.66/cr ($0.008/cr), Power is ~₹0.57/cr ($0.007/cr)
  // Custom rate: ₹1.00 / credit in INR, $0.013 / credit in USD
  const customRatePerCredit = currency === 'USD' ? 0.013 : 1.0;
  const minCustomAmount = currency === 'USD' ? 2 : 100;
  const presetCustomAmounts = currency === 'USD' ? [2, 5, 10, 25, 50, 100] : [100, 250, 500, 1000, 2500, 5000];

  const validCustomAmount = Math.max(minCustomAmount, customAmountInput || minCustomAmount);
  const calculatedCustomCredits = Math.floor(validCustomAmount / customRatePerCredit);
  const calculatedCustomTokens = calculatedCustomCredits * 1000;

  return (
    <section id="pricing" className="py-24 relative overflow-hidden">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Section Header */}
        <div className="text-center max-w-3xl mx-auto mb-12">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-mono font-semibold bg-cyan-50 text-cyan-800 border border-cyan-200 mb-4 shadow-xs">
            <CreditCard className="w-3.5 h-3.5 text-cyan-600" />
            <span>TRANSPARENT VALUE · NO HIDDEN PROVIDER MARKUPS</span>
          </div>
          <h2 className="text-3xl sm:text-4xl lg:text-5xl font-extrabold tracking-tight text-slate-950">
            Simple, Predictable Pricing for Developers &amp; Teams
          </h2>
          <p className="mt-4 text-sm sm:text-base text-slate-600 leading-relaxed">
            Every plan includes our autonomous multi-provider failover mesh, AST verification, and real-time PII redaction. Switch currencies or apply discount coupons anytime.
          </p>

          {/* Controls: Billing Cycle Switcher + Currency Switcher */}
          <div className="mt-8 flex flex-wrap items-center justify-center gap-4">
            {/* Monthly / Annual Toggle */}
            <div className="inline-flex items-center p-1 rounded-2xl bg-slate-100 border border-slate-200/90 shadow-inner">
              <button
                onClick={() => setBillingCycle('monthly')}
                className={`px-4 py-1.5 rounded-xl text-xs font-semibold transition ${
                  billingCycle === 'monthly'
                    ? 'bg-white text-slate-900 shadow-sm'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                Monthly Billing
              </button>
              <button
                onClick={() => setBillingCycle('annual')}
                className={`px-4 py-1.5 rounded-xl text-xs font-semibold transition flex items-center gap-1.5 ${
                  billingCycle === 'annual'
                    ? 'bg-white text-slate-900 shadow-sm'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                <span>Annual Billing</span>
                <span className="px-1.5 py-0.2 rounded-md bg-emerald-100 text-emerald-800 text-[10px] font-bold">
                  2 MONTHS FREE
                </span>
              </button>
            </div>

            {/* Currency Switcher */}
            <div className="inline-flex items-center p-1 rounded-2xl bg-slate-100 border border-slate-200/90 shadow-inner">
              <button
                onClick={() => {
                  setCurrency('INR');
                  setCustomAmountInput(500);
                }}
                className={`px-3 py-1.5 rounded-xl text-xs font-semibold transition flex items-center gap-1 ${
                  currency === 'INR'
                    ? 'bg-white text-slate-900 shadow-sm font-bold'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                <span>₹ INR</span>
                <span className="text-[10px] text-slate-500 font-mono">(India)</span>
              </button>
              <button
                onClick={() => {
                  setCurrency('USD');
                  setCustomAmountInput(10);
                }}
                className={`px-3 py-1.5 rounded-xl text-xs font-semibold transition flex items-center gap-1 ${
                  currency === 'USD'
                    ? 'bg-white text-slate-900 shadow-sm font-bold'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                <span>$ USD</span>
                <span className="text-[10px] text-slate-500 font-mono">(Global)</span>
              </button>
            </div>
          </div>

          {/* Coupon Code Input Pill */}
          <div className="mt-4 max-w-md mx-auto">
            <form onSubmit={handleApplyCoupon} className="flex gap-2 items-center">
              <div className="relative flex-1">
                <Tag className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
                <input
                  type="text"
                  value={couponInput}
                  onChange={(e) => setCouponInput(e.target.value)}
                  placeholder="Coupon code (e.g. FOUNDING50)"
                  className="w-full pl-9 pr-3 py-1.5 rounded-xl text-xs bg-white border border-slate-200 text-slate-800 placeholder-slate-400 focus:outline-none focus:border-cyan-500 font-mono uppercase"
                />
              </div>
              <button
                type="submit"
                className="px-3 py-1.5 rounded-xl text-xs font-bold bg-slate-900 hover:bg-slate-800 text-white transition shadow-xs cursor-pointer"
              >
                Apply Coupon
              </button>
            </form>
            {appliedCoupon && (
              <div className="mt-1.5 text-xs text-emerald-700 flex items-center justify-center gap-1 font-medium animate-fade-in">
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 shrink-0" />
                <span>{appliedCoupon.desc}</span>
              </div>
            )}
            {couponError && (
              <div className="mt-1.5 text-xs text-rose-600 font-medium">{couponError}</div>
            )}
          </div>
        </div>

        {/* Pricing Cards Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 lg:gap-8 items-stretch">
          {plans.map((plan) => {
            const finalMonthlyPrice = calculateFinalPrice(
              plan.basePriceMonthlyINR,
              plan.basePriceMonthlyUSD
            );

            return (
              <div
                key={plan.id}
                className={`glass-panel rounded-3xl p-6 sm:p-7 flex flex-col justify-between transition-all duration-300 relative border ${
                  plan.popular
                    ? 'border-cyan-400/80 shadow-[0_16px_40px_rgba(6,182,212,0.12)] ring-1 ring-cyan-300/60 bg-gradient-to-b from-white via-cyan-50/20 to-white'
                    : 'border-slate-200/90 shadow-sm hover:border-slate-300 hover:shadow-md bg-white/90'
                }`}
              >
                {/* Popular / Best Value Badge */}
                {plan.badge && (
                  <div className="absolute -top-3 left-1/2 -translate-x-1/2 px-3 py-0.5 rounded-full text-[10px] font-mono uppercase font-bold tracking-wider bg-gradient-to-r from-cyan-600 to-blue-600 text-white shadow-sm">
                    {plan.badge}
                  </div>
                )}

                <div>
                  {/* Plan Name & Subtitle */}
                  <div className="mb-4">
                    <h3 className="text-xl font-bold text-slate-950">{plan.name}</h3>
                    <p className="text-xs text-slate-500 font-medium mt-0.5">{plan.subtitle}</p>
                  </div>

                  {/* Price Block */}
                  <div className="mb-5 pb-5 border-b border-slate-100">
                    <div className="flex items-baseline gap-1">
                      <span className="text-3xl sm:text-4xl font-black tracking-tight text-slate-950">
                        {finalMonthlyPrice === 0 
                          ? 'Free' 
                          : `${plan.id === 'enterprise' ? '+' : ''}${currencySymbol}${finalMonthlyPrice.toLocaleString('en-IN')}`}
                      </span>
                      {finalMonthlyPrice > 0 && (
                        <span className="text-xs text-slate-500 font-medium">/ month</span>
                      )}
                    </div>

                    {/* Strikethrough comparison if coupon/discount is applied */}
                    {appliedCoupon && finalMonthlyPrice > 0 && (
                      <div className="text-[11px] text-slate-400 font-mono line-through mt-0.5">
                        Base: {plan.id === 'enterprise' ? '+' : ''}{currencySymbol}
                        {(currency === 'USD' ? plan.basePriceMonthlyUSD : plan.basePriceMonthlyINR).toLocaleString('en-IN')}
                        /mo
                      </div>
                    )}

                    <div className="text-[11px] text-slate-500 font-mono mt-1 flex items-center gap-1.5">
                      <Zap className="w-3 h-3 text-cyan-600 shrink-0" />
                      <span>{plan.credits}</span>
                    </div>
                  </div>

                  {/* Quotas & Limits Highlights */}
                  <div className="grid grid-cols-2 gap-2 mb-5 p-2.5 rounded-xl bg-slate-50 border border-slate-200/60 text-xs font-mono">
                    <div>
                      <span className="text-slate-400 block text-[10px]">TEAM ACCESS</span>
                      <span className="font-semibold text-slate-800">{plan.seats}</span>
                    </div>
                    <div>
                      <span className="text-slate-400 block text-[10px]">REPOSITORIES</span>
                      <span className="font-semibold text-slate-800">{plan.projects}</span>
                    </div>
                  </div>

                  {/* Features List */}
                  <ul className="space-y-2.5 text-xs text-slate-700 mb-6">
                    {plan.features.map((feature, fIdx) => (
                      <li key={fIdx} className="flex items-start gap-2">
                        <Check className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
                        <span className="leading-tight">{feature}</span>
                      </li>
                    ))}
                  </ul>
                </div>

                {/* Plan Action Button */}
                <button
                  onClick={() => onSelectPlan(plan.id, appliedCoupon?.code, currency)}
                  className={`w-full py-3 rounded-2xl text-xs font-bold transition flex items-center justify-center gap-1.5 shadow-sm cursor-pointer ${
                    plan.popular
                      ? 'bg-gradient-to-r from-cyan-600 via-blue-600 to-indigo-600 hover:from-cyan-500 hover:to-blue-500 text-white shadow-cyan-600/20'
                      : 'bg-slate-900 hover:bg-slate-800 text-white'
                  }`}
                >
                  <span>{plan.buttonText}</span>
                  <ChevronRight className="w-3.5 h-3.5" />
                </button>
              </div>
            );
          })}
        </div>

        {/* Top-up Packs & Add-ons Grid */}
        <div className="mt-14 glass-panel p-6 sm:p-8 rounded-3xl border border-slate-200/90 shadow-md bg-white/90">
          <div className="max-w-2xl mb-6">
            <span className="text-xs font-mono uppercase text-cyan-700 font-bold block mb-1">
              Top-Up Packs &amp; On-Demand Credits
            </span>
            <h4 className="text-xl sm:text-2xl font-bold text-slate-950 mb-2">
              Need Extra Credits Between Subscription Cycles?
            </h4>
            <p className="text-xs sm:text-sm text-slate-600 leading-relaxed">
              Top-up credits roll over automatically and never expire for 12 months. Perfect for heavy PR patch sprints and large repo index scans.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {topupPacks.map((pack) => {
              const packPrice = currency === 'USD' ? pack.priceUSD : pack.priceINR;

              return (
                <div
                  key={pack.id}
                  className={`p-5 rounded-2xl border transition flex flex-col justify-between ${
                    pack.popular
                      ? 'bg-cyan-50/50 border-cyan-300 shadow-sm ring-1 ring-cyan-200'
                      : 'bg-slate-50/80 border-slate-200 hover:border-slate-300'
                  }`}
                >
                  <div>
                    <div className="flex justify-between items-start mb-2">
                      <span className="text-[10px] font-mono uppercase font-bold text-cyan-800 bg-cyan-100/80 px-2 py-0.5 rounded">
                        {pack.badge}
                      </span>
                    </div>

                    <h5 className="text-base font-bold text-slate-900">{pack.name}</h5>
                    <div className="text-2xl font-extrabold text-slate-950 mt-1">
                      {currencySymbol}{packPrice.toLocaleString('en-IN')}
                    </div>
                    <div className="text-xs text-cyan-700 font-mono font-semibold mt-0.5">
                      {pack.credits} ({pack.tokens})
                    </div>
                    <div className="text-[11px] text-slate-500 font-mono mt-1">
                      Effective: {currency === 'USD' ? pack.effectiveRateUSD : pack.effectiveRateINR}
                    </div>
                  </div>

                  <button
                    onClick={() => onSelectPlan(pack.id, appliedCoupon?.code, currency)}
                    className={`mt-4 w-full py-2.5 rounded-xl text-xs font-bold transition flex items-center justify-center gap-1 shadow-xs cursor-pointer ${
                      pack.popular
                        ? 'bg-cyan-600 hover:bg-cyan-500 text-white'
                        : 'bg-white hover:bg-slate-100 border border-slate-300 text-slate-800'
                    }`}
                  >
                    <span>Buy {pack.credits}</span>
                    <ChevronRight className="w-3.5 h-3.5" />
                  </button>
                </div>
              );
            })}
          </div>

          {/* Custom On-Demand Amount Credit Refill */}
          <div className="mt-8 p-6 sm:p-7 rounded-3xl bg-slate-900 text-white border border-slate-800 shadow-xl relative overflow-hidden">
            <div className="relative z-10">
              <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 mb-5">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-cyan-950 text-cyan-300 border border-cyan-800/80">
                      EXACT ON-DEMAND REFILL
                    </span>
                    <span className="text-[11px] text-slate-400 font-mono">No Subscription Commitment</span>
                  </div>
                  <h4 className="text-lg sm:text-xl font-bold text-slate-100 mt-1">
                    Enter Any Amount to Purchase Custom Credits
                  </h4>
                  <p className="text-xs text-slate-400 max-w-2xl mt-0.5">
                    Need a specific amount of credits? Enter any budget in {currency === 'USD' ? 'USD ($)' : 'INR (₹)'}. Billed at standard base rate ({currency === 'USD' ? '$0.013' : '₹1.00'} per credit with no bulk discount). Credits never expire for 12 months.
                  </p>
                </div>

                <div className="text-right sm:shrink-0 bg-slate-800/80 px-3.5 py-2 rounded-xl border border-slate-700/80">
                  <div className="text-[10px] uppercase font-mono text-slate-400">Standard Base Rate</div>
                  <div className="text-sm font-bold text-cyan-400 font-mono mt-0.5">
                    {currency === 'USD' ? '$0.013 / credit' : '₹1.00 / credit'}
                  </div>
                </div>
              </div>

              <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 items-center bg-slate-950/70 p-4 sm:p-5 rounded-2xl border border-slate-800/90">
                <div className="lg:col-span-6 space-y-3">
                  <label className="text-xs font-semibold text-slate-300 flex items-center justify-between">
                    <span>Enter Amount ({currencySymbol})</span>
                    <span className="text-[11px] text-slate-400 font-mono">
                      Min: {currencySymbol}{minCustomAmount}
                    </span>
                  </label>
                  <div className="relative">
                    <span className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400 font-bold text-lg">
                      {currencySymbol}
                    </span>
                    <input
                      type="number"
                      min={minCustomAmount}
                      step={currency === 'USD' ? '1' : '50'}
                      value={customAmountInput}
                      onChange={(e) => setCustomAmountInput(Math.max(0, Number(e.target.value)))}
                      className="w-full pl-9 pr-4 py-2.5 rounded-xl bg-slate-900 border border-slate-700 text-white font-mono text-base font-bold focus:outline-none focus:border-cyan-500 transition"
                      placeholder={currency === 'USD' ? '10' : '500'}
                    />
                  </div>

                  {/* Quick Presets */}
                  <div className="flex flex-wrap gap-1.5 pt-1">
                    <span className="text-[10px] text-slate-400 font-mono self-center mr-1">Presets:</span>
                    {presetCustomAmounts.map((preset) => (
                      <button
                        key={preset}
                        type="button"
                        onClick={() => setCustomAmountInput(preset)}
                        className={`px-2.5 py-1 rounded-lg text-[11px] font-mono font-semibold transition cursor-pointer ${
                          customAmountInput === preset
                            ? 'bg-cyan-500 text-slate-950 font-bold'
                            : 'bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700'
                        }`}
                      >
                        {currencySymbol}{preset.toLocaleString()}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Exact Equivalencies Card */}
                <div className="lg:col-span-6 flex flex-col sm:flex-row items-center justify-between gap-4 p-4 rounded-xl bg-slate-900 border border-slate-800">
                  <div className="space-y-1 text-center sm:text-left w-full sm:w-auto">
                    <div className="text-[10px] font-mono uppercase text-slate-400">You Will Receive Exactly</div>
                    <div className="text-xl sm:text-2xl font-black text-cyan-300 font-mono">
                      {calculatedCustomCredits.toLocaleString()} Credits
                    </div>
                    <div className="text-xs text-emerald-400 font-mono font-semibold">
                      = {calculatedCustomTokens.toLocaleString()} High-Speed Model Tokens
                    </div>
                  </div>

                  <button
                    type="button"
                    onClick={() =>
                      onSelectPlan('custom', undefined, currency, {
                        customAmount: validCustomAmount,
                        customCredits: calculatedCustomCredits,
                      })
                    }
                    className="w-full sm:w-auto px-5 py-3 rounded-xl text-xs font-bold bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-slate-950 transition flex items-center justify-center gap-2 shadow-lg shadow-cyan-500/20 cursor-pointer shrink-0 font-sans"
                  >
                    <CreditCard className="w-4 h-4 text-slate-950" />
                    <span>Buy {calculatedCustomCredits.toLocaleString()} Credits</span>
                    <ChevronRight className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>

              <div className="mt-3.5 flex flex-wrap items-center justify-between text-[11px] text-slate-400 font-mono gap-2">
                <div>
                  * Exact standard: 1 Credit = 1,000 Tokens. No bulk discount on custom on-demand refills.
                </div>
                <div className="text-cyan-400">
                  Need bulk discount? Growth Pack saves 15%, Power Pack saves 25% above.
                </div>
              </div>
            </div>
          </div>

          <div className="mt-4 pt-4 border-t border-slate-100 flex flex-wrap items-center justify-between text-[11px] text-slate-500 font-mono gap-2">
            <div className="flex items-center gap-1.5">
              <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
              <span>Instant ledger confirmation with Razorpay webhook verification.</span>
            </div>
            <div className="text-slate-400">
              1 Credit = 1,000 High-Speed Model Tokens · Zero-Restart Failover Included
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};
