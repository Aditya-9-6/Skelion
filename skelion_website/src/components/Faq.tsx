import React, { useState } from 'react';
import { ChevronDown, HelpCircle } from 'lucide-react';

export const Faq: React.FC = () => {
  const [openIdx, setOpenIdx] = useState<number | null>(0);

  const faqs = [
    {
      q: 'Does Skelion slow down my production traffic or add latency?',
      a: 'No. The Skelion edge proxy is written in high-throughput asynchronous Python/Caddy/eBPF hotpaths adding less than 5ms of latency overhead. Telemetry analysis and incident sandboxing occur entirely out-of-band in isolated worker queues.',
    },
    {
      q: 'What is the Fail-Open guarantee?',
      a: 'If any internal error, unhandled exception, or timeout occurs inside the Skelion engine, the proxy fail-opens immediately. This guarantees that an issue with the telemetry layer will never break or drop your production customer traffic.',
    },
    {
      q: 'How does Razorpay billing and credit accounting work?',
      a: 'Skelion supports both INR (₹) via Razorpay (UPI, Cards, NetBanking) and USD ($) for international developers. All subscriptions and top-up credits provide transparent access to our autonomous incident detection, AST invariant verification, and zero-downtime key failover.',
    },
    {
      q: 'Can I bring my own LLM keys (BYOK)?',
      a: 'Yes. The Local Community and Local Solo tiers let you provide your own cluster API keys or local mesh endpoints with zero marginal credit debits.',
    },
    {
      q: 'Is my proprietary code protected from LLM training?',
      a: 'Absolutely. We enforce a zero-retention, zero-training agreement across all upstream model providers. Furthermore, the PII Redaction Engine masks authorization tokens, secrets, cookies, and database connection strings before traces are evaluated.',
    },
    {
      q: 'How does Skelion handle trace and log retention?',
      a: 'Skelion enforces tiered, privacy-first retention policies with automated epoch-based garbage collection: 7 days on Developer Tier, 30 days on Pro Developer Tier, 90 days on Engineering Team Tier, and 365 days of immutable append-only audit logs on Custom Tier. All traces undergo strict zero-trust PII redaction at the edge before storage, masking Authorization tokens, API keys, cookies, and personal identifiers. Logs and traces can be exported as structured JSON or purged immediately via self-service privacy controls.',
    },
    {
      q: 'How does the Web Platform synchronize incident state with the cloud?',
      a: 'The Skelion Cloud Console communicates with the control plane and edge proxy via authenticated WebSockets and real-time streams. Quota refills, model gate unlocks, and incident diagnostic reviews reflect live instantly without needing to refresh.',
    },
  ];

  return (
    <section id="faq" className="py-24 relative overflow-hidden scroll-mt-20">
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center mb-16">
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-cyan-50 border border-cyan-200 text-cyan-800 mb-3 shadow-sm">
            <HelpCircle className="w-3.5 h-3.5 text-cyan-600" />
            <span>FREQUENTLY ASKED QUESTIONS</span>
          </div>
          <h2 className="text-3xl sm:text-4xl font-extrabold text-slate-950 tracking-tight">
            Got Questions? We Have Answers.
          </h2>
        </div>

        <div className="space-y-4">
          {faqs.map((faq, idx) => {
            const isOpen = openIdx === idx;
            return (
              <div
                key={idx}
                className="rounded-2xl border border-slate-200/90 bg-white/80 backdrop-blur-xl shadow-sm overflow-hidden transition-all duration-200 hover:border-slate-300"
              >
                <button
                  onClick={() => setOpenIdx(isOpen ? null : idx)}
                  className="w-full p-5 text-left flex items-center justify-between gap-4 font-semibold text-sm sm:text-base text-slate-900 hover:text-cyan-700 transition"
                >
                  <span>{faq.q}</span>
                  <ChevronDown
                    className={`w-5 h-5 text-slate-400 shrink-0 transition-transform duration-200 ${
                      isOpen ? 'rotate-180 text-cyan-600' : ''
                    }`}
                  />
                </button>
                {isOpen && (
                  <div className="px-5 pb-5 text-xs sm:text-sm text-slate-600 leading-relaxed border-t border-slate-100 pt-3">
                    {faq.a}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
};
