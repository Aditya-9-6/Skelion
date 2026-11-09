import React from 'react';
import { LegalPageTemplate } from '../LegalPageTemplate';

export const SecurityPolicyPage: React.FC = () => {
  return (
    <LegalPageTemplate documentKey="security_policy" documentTitle="Security Policy">
      <h3>1. Enterprise Security Standards</h3>
      <p>
        Skelion is built with zero-trust architecture, AES-256 encryption at rest, and TLS 1.3 in transit for all proxy communications.
      </p>

      <h3>2. Vulnerability Disclosure</h3>
      <p>
        If you discover a security vulnerability in Skelion or our web platform, please report it immediately to security@skelion.ai for responsible disclosure and remediation.
      </p>
    </LegalPageTemplate>
  );
};
