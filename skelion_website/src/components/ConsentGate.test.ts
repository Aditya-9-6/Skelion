import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import React from 'react';
import {
  ConsentGate,
  checkConsentAccepted,
  REQUIRED_LEGAL_DOCS,
} from './ConsentGate.ts';

describe('ConsentGate Component & Logic Tests', () => {
  const dummyUser = { id: 12345, username: 'test-user' };

  it('verifies REQUIRED_LEGAL_DOCS includes terms and privacy', () => {
    assert.equal(REQUIRED_LEGAL_DOCS.length, 2);
    const keys = REQUIRED_LEGAL_DOCS.map(d => d.key);
    assert.ok(keys.includes('terms_of_service'));
    assert.ok(keys.includes('privacy_policy'));
  });

  it('returns false when no user is logged in', () => {
    const isAccepted = checkConsentAccepted(null, () => ({
      terms_of_service: '1.0.0',
      privacy_policy: '1.0.0',
    }));
    assert.equal(isAccepted, false);
  });

  it('returns false when no acceptances are stored', () => {
    const isAccepted = checkConsentAccepted(dummyUser, () => null);
    assert.equal(isAccepted, false);
  });

  it('returns false when only terms of service is accepted', () => {
    const isAccepted = checkConsentAccepted(dummyUser, () => ({
      terms_of_service: '1.0.0',
    }));
    assert.equal(isAccepted, false);
  });

  it('returns false when only privacy policy is accepted', () => {
    const isAccepted = checkConsentAccepted(dummyUser, () => ({
      privacy_policy: '1.0.0',
    }));
    assert.equal(isAccepted, false);
  });

  it('returns true when all required legal documents are accepted', () => {
    const isAccepted = checkConsentAccepted(dummyUser, () => ({
      terms_of_service: '1.0.0',
      privacy_policy: '1.0.0',
    }));
    assert.equal(isAccepted, true);
  });

  it('gracefully handles exceptions in getStoredAcceptances', () => {
    const isAccepted = checkConsentAccepted(dummyUser, () => {
      throw new Error('Corrupt storage');
    });
    assert.equal(isAccepted, false);
  });

  it('supports guest user consent acceptance when allowGuest is enabled', () => {
    const isAccepted = checkConsentAccepted(
      null,
      (userId) => {
        assert.equal(userId, 'guest');
        return {
          terms_of_service: '1.0.0',
          privacy_policy: '1.0.0',
        };
      },
      REQUIRED_LEGAL_DOCS,
      true
    );
    assert.equal(isAccepted, true);
  });

  it('instantiates ConsentGate React element with children', () => {
    const child = React.createElement('div', { id: 'protected-app' }, 'Protected Content');
    const gateElement = React.createElement(ConsentGate, null, child);
    assert.ok(gateElement);
    assert.equal(gateElement.type, ConsentGate);
    assert.equal(gateElement.props.children, child);
  });
});
