import React from 'react';
import { LegalPageTemplate } from '../LegalPageTemplate';

export const PrivacyPolicyPage: React.FC = () => {
  return (
    <LegalPageTemplate documentKey="privacy_policy" documentTitle="Privacy Policy">
      <h3>1. Information We Collect</h3>
      <p>
        Skelion collects minimal telemetry, GitHub profile metadata upon OAuth login, and API usage metrics required to power our key-pool proxy and cloud agent web platform features.
      </p>

      <h3>2. Zero Code Training Guarantee</h3>
      <p>
        Your proprietary source code, prompts, and completions processed through Skelion are never used to train foundational AI models. All proxy traffic is encrypted in transit and transiently handled.
      </p>

      <h3>3. Data Deletion</h3>
      <p>
        You may request complete purging of your account and legal acceptance logs at any time by contacting privacy@skelion.ai.
      </p>
    </LegalPageTemplate>
  );
};
