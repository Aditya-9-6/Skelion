import React from 'react';

export interface VerificationBadgeProps {
  status: 'verified' | 'pending' | 'failed';
  label?: string;
  showIcon?: boolean;
}

export function formatVerificationStatus(
  status: VerificationBadgeProps['status'],
  customLabel?: string,
  showIcon: boolean = true
): {
  colorClass: string;
  icon: string;
  displayText: string;
} {
  let colorClass = '';
  switch (status) {
    case 'verified':
      colorClass = 'text-emerald-400 bg-emerald-950/60 border-emerald-500/40';
      break;
    case 'pending':
      colorClass = 'text-amber-400 bg-amber-950/60 border-amber-500/40';
      break;
    case 'failed':
      colorClass = 'text-rose-400 bg-rose-950/60 border-rose-500/40';
      break;
    default:
      colorClass = 'text-slate-400 bg-slate-950/60 border-slate-500/40';
      break;
  }

  let icon = '';
  if (showIcon) {
    if (status === 'verified') {
      icon = '✔️';
    } else if (status === 'pending') {
      icon = '⏳';
    } else if (status === 'failed') {
      icon = '❌';
    } else {
      icon = '❓';
    }
  }

  let displayText = '';
  if (customLabel) {
    displayText = customLabel;
  } else if (status === 'verified') {
    displayText = '100% Verified';
  } else if (status === 'pending') {
    displayText = 'Verification In Progress';
  } else if (status === 'failed') {
    displayText = 'Verification Failed';
  } else {
    displayText = 'Unknown Status';
  }

  return { colorClass, icon, displayText };
}

export const VerificationBadge: React.FC<VerificationBadgeProps> = ({
  status,
  label,
  showIcon = true,
}) => {
  const { colorClass, icon, displayText } = formatVerificationStatus(status, label, showIcon);

  return React.createElement(
    'div',
    {
      'data-testid': 'verification-badge',
      className: `inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-mono font-medium rounded-md border ${colorClass}`,
    },
    icon ? React.createElement('span', { 'data-testid': 'badge-icon' }, icon) : null,
    React.createElement('span', { 'data-testid': 'badge-label' }, displayText)
  );
};

export default VerificationBadge;
