import React, { useState } from 'react';
import { ShieldAlert } from 'lucide-react';
import { useLegalBanner } from '../hooks/useLegalBanner';

export const LegalUpdateBanner: React.FC = () => {
  const { needsReacceptance, documentKey, currentVersion } = useLegalBanner();
  const [dismissed, setDismissed] = useState(false);

  if (!needsReacceptance || !documentKey || !currentVersion || dismissed) return null;

  const docTitleMap: Record<string, string> = {
    terms: 'Terms of Service',
    privacy: 'Privacy Policy',
    cookies: 'Cookie Policy',
    security: 'Security Policy',
    terms_of_service: 'Terms of Service',
    privacy_policy: 'Privacy Policy',
    cookie_policy: 'Cookie Policy',
    security_policy: 'Security Policy',
  };

  const title = docTitleMap[documentKey] || documentKey;

  const handleScrollToFooter = () => {
    const footerElement = document.querySelector('footer');
    if (footerElement) {
      footerElement.scrollIntoView({ behavior: 'smooth' });
    }
    setDismissed(true);
  };

  return (
    <div className="bg-gradient-to-r from-amber-50 via-white to-cyan-50 border-b border-amber-300 py-2.5 px-4 text-center text-xs sm:text-sm text-amber-950 flex items-center justify-center gap-3 shadow-sm z-50 sticky top-0 backdrop-blur-md">
      <ShieldAlert className="w-4 h-4 text-amber-600 animate-bounce flex-shrink-0" />
      <span>
        <strong>Legal Update Required:</strong> A new version (v{currentVersion}) of the <strong>{title}</strong> has been released. Please re-accept in the footer below.
      </span>
      <button
        onClick={handleScrollToFooter}
        className="underline font-semibold hover:text-amber-800 transition-colors ml-2 bg-amber-100 px-2 py-1 rounded border border-amber-300 flex items-center gap-1 shadow-sm"
      >
        <span>Review Footer</span>
      </button>
      <button
        onClick={() => setDismissed(true)}
        className="text-slate-400 hover:text-slate-700 text-xs ml-2"
        title="Dismiss"
      >
        ✕
      </button>
    </div>
  );
};
