import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import React from 'react';
import { VerificationBadge, formatVerificationStatus } from './VerificationBadge.ts';

describe('VerificationBadge Component & Helper Tests', () => {
  it('formats verified status with default label and icon', () => {
    const res = formatVerificationStatus('verified');
    assert.ok(res.colorClass.includes('text-emerald-400'));
    assert.equal(res.icon, '✔️');
    assert.equal(res.displayText, '100% Verified');
  });

  it('formats pending status with default label and icon', () => {
    const res = formatVerificationStatus('pending');
    assert.ok(res.colorClass.includes('text-amber-400'));
    assert.equal(res.icon, '⏳');
    assert.equal(res.displayText, 'Verification In Progress');
  });

  it('formats failed status with default label and icon', () => {
    const res = formatVerificationStatus('failed');
    assert.ok(res.colorClass.includes('text-rose-400'));
    assert.equal(res.icon, '❌');
    assert.equal(res.displayText, 'Verification Failed');
  });

  it('supports custom label across all statuses', () => {
    const res = formatVerificationStatus('verified', 'Custom Verified Label');
    assert.equal(res.displayText, 'Custom Verified Label');
  });

  it('handles showIcon=false correctly', () => {
    const res = formatVerificationStatus('verified', undefined, false);
    assert.equal(res.icon, '');
  });

  it('handles unknown status fallback gracefully', () => {
    const res = formatVerificationStatus('unknown' as any, undefined, true);
    assert.ok(res.colorClass.includes('text-slate-400'));
    assert.equal(res.icon, '❓');
    assert.equal(res.displayText, 'Unknown Status');
  });

  it('renders VerificationBadge component as a React element', () => {
    const element = React.createElement(VerificationBadge, {
      status: 'verified',
    });
    assert.ok(element);
    assert.equal(element.type, VerificationBadge);
    assert.equal(element.props.status, 'verified');

    // Render with all optional props
    const elementCustom = React.createElement(VerificationBadge, {
      status: 'failed',
      label: 'Security Check Failed',
      showIcon: false,
    });
    assert.equal(elementCustom.props.label, 'Security Check Failed');
    assert.equal(elementCustom.props.showIcon, false);

    // Call the component function directly to exercise JSX tree construction
    const vnode = VerificationBadge({ status: 'verified' });
    assert.ok(vnode);
    assert.equal(vnode.props['data-testid'], 'verification-badge');

    const vnodeNoIcon = VerificationBadge({ status: 'pending', showIcon: false });
    assert.ok(vnodeNoIcon);
  });
});
