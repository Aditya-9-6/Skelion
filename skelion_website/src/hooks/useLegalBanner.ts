import { useState, useEffect } from 'react';
import legalVersions from '../../config/legal_versions.json';
import { getStoredUser } from '../utils/auth';

export interface LegalBannerState {
  needsReacceptance: boolean;
  documentKey: string | null;
  currentVersion: string | null;
  storedVersion: string | null;
}

export const useLegalBanner = (): LegalBannerState => {
  const [state, setState] = useState<LegalBannerState>({
    needsReacceptance: false,
    documentKey: null,
    currentVersion: null,
    storedVersion: null,
  });

  useEffect(() => {
    const user = getStoredUser();
    if (!user) return;

    const acceptancesKey = `skelion_legal_acceptances_${user.id}`;
    try {
      const stored = localStorage.getItem(acceptancesKey);
      const userAcceptances = stored ? JSON.parse(stored) : {};

      for (const [docKey, currentVer] of Object.entries(legalVersions)) {
        const acceptedVer = userAcceptances[docKey];
        if (!acceptedVer || acceptedVer !== currentVer) {
          setState({
            needsReacceptance: true,
            documentKey: docKey,
            currentVersion: currentVer as string,
            storedVersion: acceptedVer || null,
          });
          break;
        }
      }
    } catch (e) {
      // ignore
    }
  }, []);

  return state;
};
