import React, { useEffect, useState } from 'react';
import { api } from '../../api/client';

export type ConnectionStatus = 'connected' | 'connecting' | 'unavailable';

export const ConnectionIndicator: React.FC = () => {
  const [status, setStatus] = useState<ConnectionStatus>('connecting');
  const [lastChecked, setLastChecked] = useState<Date | null>(null);

  const checkHealth = async () => {
    try {
      const res = await api.health.check();
      if (res.status === 'ok') {
        setStatus('connected');
      } else {
        setStatus('unavailable');
      }
    } catch {
      setStatus('unavailable');
    } finally {
      setLastChecked(new Date());
    }
  };

  useEffect(() => {
    checkHealth();
    // Re-check every 30 seconds
    const interval = setInterval(checkHealth, 30000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="flex items-center gap-2 px-2.5 py-1.5 rounded-input bg-surface-secondary/70 border border-border/80 text-body-sm">
      <span className="relative flex h-2 w-2">
        {status === 'connected' && (
          <>
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
          </>
        )}
        {status === 'connecting' && (
          <span className="relative inline-flex rounded-full h-2 w-2 bg-amber-400 animate-pulse"></span>
        )}
        {status === 'unavailable' && (
          <span className="relative inline-flex rounded-full h-2 w-2 bg-rose-500"></span>
        )}
      </span>

      <div className="flex flex-col">
        <span className="text-[11px] font-medium leading-tight text-charcoal">
          {status === 'connected' && 'API Connected'}
          {status === 'connecting' && 'Connecting...'}
          {status === 'unavailable' && 'API Unavailable'}
        </span>
        {lastChecked && (
          <span className="text-[10px] text-charcoal-caption leading-tight">
            {lastChecked.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
          </span>
        )}
      </div>

      {status === 'unavailable' && (
        <button
          onClick={checkHealth}
          title="Retry health check"
          className="ml-auto text-[11px] font-medium text-brand hover:underline"
        >
          Retry
        </button>
      )}
    </div>
  );
};
