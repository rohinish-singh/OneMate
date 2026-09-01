import React from 'react';

export type BadgeVariant =
  | 'same'
  | 'potential'
  | 'diff'
  | 'neutral'
  | 'brand';

interface BadgeProps {
  children: React.ReactNode;
  variant?: BadgeVariant;
  className?: string;
}

const variantStyles: Record<BadgeVariant, string> = {
  same: 'bg-semantic-same-bg text-semantic-same-text border-semantic-same-border',
  potential: 'bg-semantic-potential-bg text-semantic-potential-text border-semantic-potential-border',
  diff: 'bg-semantic-diff-bg text-semantic-diff-text border-semantic-diff-border',
  neutral: 'bg-semantic-neutral-bg text-semantic-neutral-text border-semantic-neutral-border',
  brand: 'bg-brand-tint text-brand border-border',
};

export const Badge: React.FC<BadgeProps> = ({
  children,
  variant = 'neutral',
  className = '',
}) => {
  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded-badge text-[11px] font-medium border uppercase tracking-wider ${variantStyles[variant]} ${className}`}
    >
      {children}
    </span>
  );
};
