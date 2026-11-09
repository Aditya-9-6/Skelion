import React from 'react';
import { LegalFooterConsent } from './LegalFooterConsent';
import { Shield } from 'lucide-react';

export const LegalPageTemplate: React.FC<{
  documentKey: string;
  documentTitle: string;
  children: React.ReactNode;
}> = ({ documentKey, documentTitle, children }) => {
  return (
    <div className="min-h-screen bg-[#FAFCFF] text-slate-900 flex flex-col font-sans relative">
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-16 flex-1 space-y-8 relative z-10">
        <div className="space-y-3 border-b border-slate-200 pb-6">
          <div className="flex items-center gap-2 text-cyan-700 font-mono text-xs">
            <Shield className="w-4 h-4 text-cyan-600" />
            <span>Skelion Governance & Compliance</span>
          </div>
          <h1 className="text-3xl sm:text-4xl font-extrabold text-slate-950 tracking-tight">
            {documentTitle}
          </h1>
          <p className="text-sm text-slate-500">
            Last updated: November 2026 • Skelion Autonomous Incident Intelligence & Fail-Open Gateway
          </p>
        </div>

        <div className="prose max-w-none text-slate-700 text-sm leading-relaxed space-y-6">
          {children}
        </div>

        {/* Required Footer Checkbox Consent Tracker */}
        <LegalFooterConsent documentKey={documentKey} documentTitle={documentTitle} />
      </div>

      <footer className="bg-white/80 backdrop-blur-md border-t border-slate-200 py-8 text-slate-500 text-xs text-center relative z-10">
        <div className="max-w-7xl mx-auto px-4">
          © {new Date().getFullYear()} Skelion Platform. All legal policies governed by zero-code training and enterprise compliance standards.
        </div>
      </footer>
    </div>
  );
};
