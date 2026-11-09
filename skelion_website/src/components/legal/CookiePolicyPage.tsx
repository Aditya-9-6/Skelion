import React from 'react';
import { LegalPageTemplate } from '../LegalPageTemplate';

export const CookiePolicyPage: React.FC = () => {
  return (
    <LegalPageTemplate documentKey="cookie_policy" documentTitle="Cookie Policy">
      <h3>1. Use of Cookies</h3>
      <p>
        Skelion uses secure local storage and essential cookies to maintain your user session, GitHub authentication state, and legal consent tracking records.
      </p>

      <h3>2. Third-Party Analytics</h3>
      <p>
        We do not employ invasive third-party ad trackers. Telemetry is limited to operational performance metrics and error diagnostics via Vercel edge infrastructure.
      </p>
    </LegalPageTemplate>
  );
};
