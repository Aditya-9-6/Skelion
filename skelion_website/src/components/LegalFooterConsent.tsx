import React, { useState, useEffect } from 'react';
import { Shield, AlertCircle } from 'lucide-react';
import { getStoredUser, UserProfile } from '../utils/auth';
import legalVersions from '../../config/legal_versions.json';

interface LegalFooterConsentProps {
  documentKey: string; // e.g. 'terms_of_service', 'privacy_policy'
  documentTitle: string;
}

export const LegalFooterConsent: React.FC<LegalFooterConsentProps> = ({ documentKey, documentTitle }) => {
  const [user, setUser] = useState<UserProfile | null>(null);
  const [accepted, setAccepted] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  const currentVersion = (legalVersions as Record<string, string>)[documentKey] || '1.0';

  useEffect(() => {
    const currentUser = getStoredUser();
    setUser(currentUser);

    if (currentUser) {
      // Check localStorage for existing acceptance of this version
      const acceptancesKey = `skelion_legal_acceptances_${currentUser.id}`;
      try {
        const stored = localStorage.getItem(acceptancesKey);
        if (stored) {
          const parsed = JSON.parse(stored);
          if (parsed[documentKey] === currentVersion) {
            setAccepted(true);
          }
        }
      } catch (e) {
        // ignore
      }
    }
  }, [documentKey, currentVersion]);

  const handleCheckboxChange = async () => {
    if (!user) {
      setError('Please log in with GitHub to record your legal consent tracking.');
      return;
    }

    const nextAccepted = !accepted;
    setAccepted(nextAccepted);
    setError(null);
    setSuccessMsg(null);

    if (nextAccepted) {
      setLoading(true);
      const acceptanceRecord = {
        userId: user.id.toString(),
        username: user.username,
        document: documentKey,
        version: currentVersion,
        acceptedAt: new Date().toISOString(),
      };

      try {
        // Record acceptance via API endpoint or local storage sync
        await fetch('/api/legal/accept', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(acceptanceRecord),
        });

        // Also store in localStorage for offline/static deployment resilience
        const acceptancesKey = `skelion_legal_acceptances_${user.id}`;
        let existingMap: Record<string, string> = {};
        try {
          const stored = localStorage.getItem(acceptancesKey);
          if (stored) existingMap = JSON.parse(stored);
        } catch (e) {}
        existingMap[documentKey] = currentVersion;
        localStorage.setItem(acceptancesKey, JSON.stringify(existingMap));

        setSuccessMsg(`Consent recorded for ${documentTitle} (v${currentVersion}).`);
      } catch (err) {
        // Fallback local storage success if serverless endpoint is not active in static static export
        const acceptancesKey = `skelion_legal_acceptances_${user.id}`;
        let existingMap: Record<string, string> = {};
        try {
          const stored = localStorage.getItem(acceptancesKey);
          if (stored) existingMap = JSON.parse(stored);
        } catch (e) {}
        existingMap[documentKey] = currentVersion;
        localStorage.setItem(acceptancesKey, JSON.stringify(existingMap));
        setSuccessMsg(`Consent recorded locally for ${documentTitle} (v${currentVersion}).`);
      } finally {
        setLoading(false);
      }
    }
  };

  return (
    <div className="my-8 p-5 rounded-2xl bg-white/85 backdrop-blur-xl border border-slate-200/90 shadow-md text-slate-700">
      <div className="flex items-start gap-3">
        <div className="p-2 rounded-lg bg-cyan-50 border border-cyan-200 text-cyan-600 mt-0.5 shadow-sm">
          <Shield className="w-5 h-5" />
        </div>
        <div className="flex-1 space-y-2">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <span className="text-sm font-bold text-slate-900 tracking-tight">
              Legal Consent Tracking & Compliance Footer
            </span>
            <span className="text-xs px-2 py-0.5 rounded-full bg-cyan-50 text-cyan-700 border border-cyan-200 font-mono">
              Version {currentVersion}
            </span>
          </div>
          <p className="text-xs text-slate-600 leading-relaxed">
            In compliance with Skelion security and data governance policies, reviewing and accepting{' '}
            <strong className="text-slate-900">{documentTitle}</strong> (v{currentVersion}) is required for all active platform users.
          </p>

          <div className="pt-2 flex items-center gap-3">
            <label className="cursor-pointer flex items-center gap-2.5 select-none group">
              <input
                type="checkbox"
                checked={accepted}
                onChange={handleCheckboxChange}
                disabled={loading}
                className="w-4 h-4 rounded border-slate-300 bg-white text-cyan-600 focus:ring-cyan-500/40 cursor-pointer shadow-sm"
              />
              <span className="text-xs font-medium text-slate-800 group-hover:text-cyan-700 transition-colors">
                I have read and accept {documentTitle} (v{currentVersion})
              </span>
            </label>
          </div>

          {!user && (
            <div className="flex items-center gap-1.5 text-xs text-amber-700 font-mono mt-1">
              <AlertCircle className="w-3.5 h-3.5" />
              <span>Please sign in with GitHub in the navbar to persist your consent record.</span>
            </div>
          )}

          {error && (
            <div className="text-xs text-red-600 font-mono mt-1 flex items-center gap-1">
              <AlertCircle className="w-3.5 h-3.5" />
              <span>{error}</span>
            </div>
          )}

          {successMsg && (
            <div className="text-xs text-emerald-700 font-mono mt-1 flex items-center gap-1">
              <span>✓ {successMsg}</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
