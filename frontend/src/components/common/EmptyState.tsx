import React from 'react';
import { PackageOpen } from 'lucide-react';

interface EmptyStateProps {
  title?: string;
  description?: string;
  action?: React.ReactNode;
  icon?: React.ReactNode;
  className?: string;
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  title = 'No records found',
  description = 'No operational records exist for this section.',
  action,
  icon,
  className = '',
}) => {
  return (
    <div
      className={`flex flex-col items-center justify-center p-12 text-center rounded-panel border border-dashed border-border bg-surface ${className}`}
    >
      <div className="w-10 h-10 rounded-input bg-surface-secondary flex items-center justify-center text-charcoal-muted mb-3">
        {icon || <PackageOpen className="w-5 h-5" />}
      </div>
      <h3 className="text-card-title text-charcoal">{title}</h3>
      <p className="text-body-sm text-charcoal-muted max-w-sm mt-1 mb-4">{description}</p>
      {action && <div>{action}</div>}
    </div>
  );
};
