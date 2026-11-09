import React from 'react';
import { ExternalLink, ArrowUp } from 'lucide-react';
import { LEGAL_DOCUMENTS } from '../types/legal';

export const Footer: React.FC = () => {
  const scrollToTop = () => {
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  return (
    <footer className="relative z-10 bg-[#04060d]/90 backdrop-blur-2xl border-t border-white/10 pt-16 pb-12 text-slate-400 text-xs">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 space-y-12">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
          {/* Brand Col */}
          <div className="md:col-span-2 space-y-4">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-xl bg-cyan-950/50 p-1.5 border border-cyan-500/30 flex items-center justify-center">
                <img
                  src="/skelion_logo_white.svg"
                  alt="Skelion Logo"
                  className="w-5 h-5 object-contain"
                  onError={(e) => {
                    (e.target as HTMLImageElement).src = '/icon.svg';
                  }}
                />
              </div>
              <span className="text-base font-extrabold text-white tracking-wider font-mono">
                SKELION LEGAL & COMPLIANCE
              </span>
              <span className="text-[10px] px-2 py-0.5 rounded-full bg-cyan-500/10 text-cyan-400 border border-cyan-500/30 font-mono">
                v0.1.4
              </span>
            </div>

            <p className="text-slate-400 text-xs leading-relaxed max-w-md font-sans">
              Autonomous AI developer platform, incident remediation agent, and fail-open telemetry proxy.
              Committed to Zero Code Retention, open source transparency, and user data sovereignty under
              the India Digital Personal Data Protection (DPDP) Act, 2023 and GDPR.
            </p>

            <div className="flex items-center gap-2 text-emerald-400 font-mono text-[11px]">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
              <span>Zero-Code-Retention Verified • DPDP Act 2023 Compliant</span>
            </div>
          </div>

          {/* Legal Navigation */}
          <div className="space-y-3">
            <span className="text-white font-mono font-bold uppercase tracking-wider text-[11px] block">
              Legal Documents
            </span>
            <ul className="space-y-2">
              {LEGAL_DOCUMENTS.map((doc) => (
                <li key={doc.id}>
                  <a
                    href={`#${doc.slug}`}
                    className="hover:text-cyan-400 transition-colors flex items-center gap-1.5"
                  >
                    <span>{doc.shortTitle}</span>
                  </a>
                </li>
              ))}
            </ul>
          </div>

          {/* Ecosystem & Links */}
          <div className="space-y-3">
            <span className="text-white font-mono font-bold uppercase tracking-wider text-[11px] block">
              Ecosystem & Repositories
            </span>
            <ul className="space-y-2">
              <li>
                <a
                  href="#console"
                  className="hover:text-cyan-400 transition-colors flex items-center gap-1"
                >
                  <span>Cloud Agent Console</span>
                </a>
              </li>
              <li>
                <a
                  href="https://github.com/Aditya-9-6/Skelion"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="hover:text-cyan-400 transition-colors flex items-center gap-1"
                >
                  <span>Core GitHub Repository</span>
                  <ExternalLink className="w-3 h-3" />
                </a>
              </li>
              <li>
                <a
                  href="https://github.com/Aditya-9-6/Skelion_website"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="hover:text-cyan-400 transition-colors flex items-center gap-1"
                >
                  <span>Website Source Code</span>
                  <ExternalLink className="w-3 h-3" />
                </a>
              </li>
              <li>
                <a
                  href="https://pypi.org/project/skelion/"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="hover:text-cyan-400 transition-colors flex items-center gap-1"
                >
                  <span>PyPI Python Package</span>
                  <ExternalLink className="w-3 h-3" />
                </a>
              </li>
            </ul>
          </div>
        </div>

        {/* Bottom Bar */}
        <div className="pt-8 border-t border-white/10 flex flex-wrap items-center justify-between gap-4">
          <div className="text-slate-500 text-[11px]">
            © {new Date().getFullYear()} Skelion Platform. Authored by Dahale Aditya Dnyaneshwar. All rights reserved.
          </div>

          <div className="flex items-center gap-4">
            <span className="text-slate-500 font-mono text-[11px]">
              Pune, Maharashtra, India
            </span>

            <button
              onClick={scrollToTop}
              className="flex items-center gap-1 px-3 py-1.5 rounded-full bg-white/5 hover:bg-white/10 text-cyan-400 border border-white/10 text-xs font-mono transition-all"
            >
              <span>Back to Top</span>
              <ArrowUp className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </div>
    </footer>
  );
};
