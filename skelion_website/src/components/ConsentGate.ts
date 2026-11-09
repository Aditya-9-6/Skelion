import React, { useState, useEffect } from 'react';
import { ShieldCheck, FileText, Lock, Cookie, ExternalLink } from 'lucide-react';

export interface RequiredLegalDoc {
  key: string;
  title: string;
  route: string;
}

export const REQUIRED_LEGAL_DOCS: RequiredLegalDoc[] = [
  { key: 'terms_of_service', title: 'Terms of Service', route: '#terms' },
  { key: 'privacy_policy', title: 'Privacy Policy', route: '#privacy' },
];

const getStoredUserLocal = (): { id: string | number } | null => {
  if (typeof window === 'undefined') return null;
  try {
    const stored = localStorage.getItem('skelion_user');
    return stored ? JSON.parse(stored) : null;
  } catch {
    return null;
  }
};

export const checkConsentAccepted = (
  user: { id: string | number } | null,
  getStoredAcceptances: (userId: string | number) => Record<string, any> | null,
  docs: RequiredLegalDoc[] = REQUIRED_LEGAL_DOCS,
  allowGuest: boolean = false
): boolean => {
  if (!user && !allowGuest) return false;
  const effectiveId = user ? user.id : 'guest';
  try {
    const stored = getStoredAcceptances(effectiveId);
    if (!stored) return false;
    return docs.every(doc => !!stored[doc.key]);
  } catch {
    return false;
  }
};

export interface ConsentGateProps {
  children: React.ReactNode;
  ConsentItemComponent?: React.ComponentType<{ documentKey: string; documentTitle: string }>;
}

/**
 * Checks whether the current user has accepted required legal documents.
 * If not, displays a full‑screen overlay with consent checkboxes and policy links.
 * Once all required documents are accepted, the overlay disappears.
 */
export const ConsentGate: React.FC<ConsentGateProps> = ({
  children,
  ConsentItemComponent,
}) => {
  const [accepted, setAccepted] = useState(false);
  const [ready, setReady] = useState(false);

  const isLegalRoute = () => {
    if (typeof window === 'undefined') return false;
    const hash = window.location.hash || '';
    return ['#terms', '#privacy', '#cookie', '#security', '#refund'].includes(hash);
  };

  const checkAcceptances = () => {
    return checkConsentAccepted(
      getStoredUserLocal(),
      (userId) => {
        const acceptancesKey = `skelion_legal_acceptances_${userId}`;
        const stored = typeof localStorage !== 'undefined' ? localStorage.getItem(acceptancesKey) : null;
        return stored ? JSON.parse(stored) : null;
      },
      REQUIRED_LEGAL_DOCS,
      true
    );
  };

  useEffect(() => {
    setReady(true);
    setAccepted(checkAcceptances());

    const handleHashChange = () => {
      setAccepted(checkAcceptances());
    };
    if (typeof window !== 'undefined') {
      window.addEventListener('hashchange', handleHashChange);
      return () => window.removeEventListener('hashchange', handleHashChange);
    }
  }, []);

  const handleAccept = () => {
    const user = getStoredUserLocal();
    const effectiveId = user ? user.id : 'guest';
    const acceptancesKey = `skelion_legal_acceptances_${effectiveId}`;
    let existingMap: Record<string, string> = {};
    try {
      const stored = typeof localStorage !== 'undefined' ? localStorage.getItem(acceptancesKey) : null;
      if (stored) existingMap = JSON.parse(stored);
    } catch {}
    REQUIRED_LEGAL_DOCS.forEach(doc => {
      existingMap[doc.key] = '1.0';
    });
    if (typeof localStorage !== 'undefined') {
      localStorage.setItem(acceptancesKey, JSON.stringify(existingMap));
    }
    setAccepted(true);
  };

  if (!ready) return null;

  if (accepted || isLegalRoute()) {
    return React.createElement(React.Fragment, null, children);
  }

  // Overlay prompting acceptance
  return React.createElement(
    'div',
    {
      'data-testid': 'consent-overlay',
      className: 'fixed inset-0 bg-slate-900/80 backdrop-blur-md flex flex-col items-center justify-center p-6 z-50 overflow-y-auto',
    },
    React.createElement(
      'div',
      {
        className: 'bg-white rounded-2xl shadow-2xl max-w-lg w-full p-8 border border-slate-200',
      },
      React.createElement(
        'div',
        { className: 'flex items-center gap-3 mb-4' },
        React.createElement(
          'div',
          { className: 'p-2.5 rounded-xl bg-cyan-50 border border-cyan-200 text-cyan-600' },
          React.createElement(ShieldCheck, { className: 'w-6 h-6' })
        ),
        React.createElement(
          'div',
          null,
          React.createElement('h2', { className: 'text-xl font-bold text-slate-900' }, 'Platform Legal Compliance'),
          React.createElement('p', { className: 'text-xs text-slate-500' }, 'Please review and accept our required policies to continue.')
        )
      ),
      React.createElement(
        'div',
        { className: 'space-y-4 my-6' },
        REQUIRED_LEGAL_DOCS.map(doc =>
          ConsentItemComponent
            ? React.createElement(ConsentItemComponent, {
                key: doc.key,
                documentKey: doc.key,
                documentTitle: doc.title,
              })
            : React.createElement(
                'div',
                {
                  key: doc.key,
                  'data-testid': `consent-doc-${doc.key}`,
                  className: 'p-4 rounded-xl border border-slate-200 bg-slate-50 flex items-center justify-between',
                },
                React.createElement('span', { className: 'text-sm font-medium text-slate-800' }, doc.title),
                React.createElement(
                  'a',
                  {
                    href: doc.route,
                    className: 'text-xs text-cyan-600 font-semibold hover:underline',
                  },
                  'Read Policy'
                )
              )
        )
      ),
      React.createElement(
        'div',
        { className: 'mt-4 pt-4 border-t border-slate-100' },
        React.createElement('p', { className: 'text-xs font-medium text-slate-500 mb-2' }, 'Review platform policies & security standards:'),
        React.createElement(
          'div',
          { className: 'grid grid-cols-2 gap-2 text-xs' },
          React.createElement(
            'a',
            {
              href: '#cookie',
              target: '_blank',
              rel: 'noopener noreferrer',
              'data-testid': 'link-cookie-policy',
              className: 'flex items-center gap-1.5 p-2 rounded-lg bg-slate-50 text-slate-700 hover:bg-cyan-50 hover:text-cyan-700 transition font-medium',
            },
            React.createElement(Cookie, { className: 'w-3.5 h-3.5 text-cyan-600' }),
            React.createElement('span', null, 'Cookie Policy'),
            React.createElement(ExternalLink, { className: 'w-3 h-3 ml-auto opacity-50' })
          ),
          React.createElement(
            'a',
            {
              href: '#security',
              target: '_blank',
              rel: 'noopener noreferrer',
              'data-testid': 'link-security-policy',
              className: 'flex items-center gap-1.5 p-2 rounded-lg bg-slate-50 text-slate-700 hover:bg-cyan-50 hover:text-cyan-700 transition font-medium',
            },
            React.createElement(Lock, { className: 'w-3.5 h-3.5 text-cyan-600' }),
            React.createElement('span', null, 'Security Policy'),
            React.createElement(ExternalLink, { className: 'w-3 h-3 ml-auto opacity-50' })
          ),
          React.createElement(
            'a',
            {
              href: '#terms',
              target: '_blank',
              rel: 'noopener noreferrer',
              'data-testid': 'link-terms-of-service',
              className: 'flex items-center gap-1.5 p-2 rounded-lg bg-slate-50 text-slate-700 hover:bg-cyan-50 hover:text-cyan-700 transition font-medium',
            },
            React.createElement(FileText, { className: 'w-3.5 h-3.5 text-cyan-600' }),
            React.createElement('span', null, 'Terms of Service'),
            React.createElement(ExternalLink, { className: 'w-3 h-3 ml-auto opacity-50' })
          ),
          React.createElement(
            'a',
            {
              href: '#privacy',
              target: '_blank',
              rel: 'noopener noreferrer',
              'data-testid': 'link-privacy-policy',
              className: 'flex items-center gap-1.5 p-2 rounded-lg bg-slate-50 text-slate-700 hover:bg-cyan-50 hover:text-cyan-700 transition font-medium',
            },
            React.createElement(ShieldCheck, { className: 'w-3.5 h-3.5 text-cyan-600' }),
            React.createElement('span', null, 'Privacy Policy'),
            React.createElement(ExternalLink, { className: 'w-3 h-3 ml-auto opacity-50' })
          )
        )
      ),
      React.createElement(
        'div',
        { className: 'mt-6 flex justify-end' },
        React.createElement(
          'button',
          {
            onClick: handleAccept,
            'data-testid': 'btn-accept-consent',
            className: 'w-full py-2.5 px-4 bg-cyan-600 text-white font-medium text-sm rounded-xl hover:bg-cyan-700 shadow-md shadow-cyan-500/20 transition cursor-pointer',
          },
          'I have accepted & continue'
        )
      )
    )
  );
};

export default ConsentGate;
