import React from 'react';
import {
  ConsentGate as ConsentGateBase,
  ConsentGateProps,
  REQUIRED_LEGAL_DOCS,
  checkConsentAccepted,
  RequiredLegalDoc,
} from './ConsentGate';
import { LegalFooterConsent } from './LegalFooterConsent';

export const ConsentGate: React.FC<{children: React.ReactNode}> = ({ children }) => {
  return (
    <ConsentGateBase ConsentItemComponent={LegalFooterConsent}>
      {children}
    </ConsentGateBase>
  );
};

export { REQUIRED_LEGAL_DOCS, checkConsentAccepted };
export type { RequiredLegalDoc, ConsentGateProps };
export default ConsentGate;
