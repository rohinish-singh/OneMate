import React from 'react';
import { AlertCircle, RefreshCw } from 'lucide-react';

interface ErrorStateProps {
  title?: string;
  message: string;
  onRetry?: () => void;
  className?: string;
}

export const ErrorState: React.FC<ErrorStateProps> = ({
  title = 'Failed to load data',
  message,
  onRetry,
  className = '',
}) => {
  return (
    <div
      className={`rounded-panel border border-semantic-diff-border bg-semantic-diff-bg p-4 ${className}`}
    >
      <div className="flex items-start gap-3">
        <AlertCircle className="w-5 h-5 text-semantic-diff-text shrink-0 mt-0.5" />
        <div className="flex-1">
          <h4 className="text-body font-semibold text-semantic-diff-text">{title}</h4>
          <p className="text-body-sm text-semantic-diff-text/90 mt-0.5">{message}</p>
          {onRetry && (
            <button
              onClick={onRetry}
              className="mt-3 inline-flex items-center gap-1.5 text-body-sm font-medium text-semantic-diff-text hover:underline"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              Try again
            </button>
          )}
        </div>
      </div>
    </div>
  );
};
