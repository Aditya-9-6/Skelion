import React from 'react';
import { LegalPageTemplate } from '../LegalPageTemplate';

export const TermsOfServicePage: React.FC = () => {
  return (
    <LegalPageTemplate documentKey="terms_of_service" documentTitle="Terms of Service">
      <h3>1. Acceptance of Terms</h3>
      <p>
        By accessing or using the Skelion web platform, cloud agent console, and API proxy services, you agree to be bound by these Terms of Service.
      </p>

      <h3>2. Fail-Open Resilience & Key-Pool Proxy</h3>
      <p>
        Skelion provides automated fallback, key rotation, and incident intelligence. You acknowledge that while Skelion maximizes uptime, upstream LLM provider outages are outside our direct liability.
      </p>

      <h3>3. Acceptable Use</h3>
      <p>
        You agree not to use Skelion for malicious crawling, unauthorized penetration testing of unowned infrastructure, or violation of applicable data residency regulations.
      </p>
    </LegalPageTemplate>
  );
};
