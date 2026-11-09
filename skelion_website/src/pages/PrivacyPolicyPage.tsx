import React from 'react';
import { LegalPageTemplate } from '../components/LegalPageTemplate';

export const PrivacyPolicyPage: React.FC = () => (
  <LegalPageTemplate documentKey="privacy_policy" documentTitle="Privacy Policy">
    <h3>1. Data Collection</h3>
    <p>We collect only the data necessary to provide Skelion services, including usage metrics and authentication details.</p>
    <h3>2. Data Usage</h3>
    <p>Collected data is used for service operation, security monitoring, and improvement of AI models.</p>
    <h3>3. User Rights</h3>
    <p>Users may request data deletion, export, or correction via the account settings page.</p>
  </LegalPageTemplate>
);
