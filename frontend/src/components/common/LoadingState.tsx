import React from 'react';
import { Loader2 } from 'lucide-react';

interface LoadingStateProps {
  message?: string;
  className?: string;
}

export const LoadingState: React.FC<LoadingStateProps> = ({
  message = 'Loading operational data...',
  className = '',
}) => {
  return (
    <div className={`flex flex-col items-center justify-center p-8 text-center ${className}`}>
      <Loader2 className="w-5 h-5 text-charcoal-muted animate-spin mb-2" />
      <span className="text-body-sm text-charcoal-muted">{message}</span>
    </div>
  );
};
