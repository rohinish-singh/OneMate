import React, { useState, useEffect, useCallback } from 'react';
import {
  History,
  RefreshCw,
  Filter,
  X,
  Check,
} from 'lucide-react';
import { api, ApiClientError } from '../api/client';
import type { AuditLogItem } from '../types/api';
import { LoadingState } from '../components/common/LoadingState';
import { ErrorState } from '../components/common/ErrorState';
import { EmptyState } from '../components/common/EmptyState';
import { Badge, type BadgeVariant } from '../components/common/Badge';
import { AuditInspector } from '../components/audit/AuditInspector';

export const AuditPage: React.FC = () => {
  const [logs, setLogs] = useState<AuditLogItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [entityType, setEntityType] = useState<string>('');
  const [entityId, setEntityId] = useState<string>('');
  const [appliedEntityType, setAppliedEntityType] = useState<string>('');
  const [appliedEntityId, setAppliedEntityId] = useState<string>('');

  // Selected Log
  const [selectedLog, setSelectedLog] = useState<AuditLogItem | null>(null);

  const fetchLogs = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.audit.list({
        entity_type: appliedEntityType || undefined,
        entity_id: appliedEntityId || undefined,
        skip: 0,
        limit: 100,
      });
      setLogs(data);
    } catch (err: unknown) {
      if (err instanceof ApiClientError) {
        setError(err.message);
      } else if (err instanceof Error) {
        setError(err.message);
      } else {
        setError('Failed to fetch audit records.');
      }
    } finally {
      setLoading(false);
    }
  }, [appliedEntityType, appliedEntityId]);

  useEffect(() => {
    fetchLogs();
  }, [fetchLogs]);

  const handleApplyFilters = (e: React.FormEvent) => {
    e.preventDefault();
    setAppliedEntityType(entityType.trim());
    setAppliedEntityId(entityId.trim());
    setSelectedLog(null);
  };

  const handleClearFilters = () => {
    setEntityType('');
    setEntityId('');
    setAppliedEntityType('');
    setAppliedEntityId('');
    setSelectedLog(null);
  };

  const hasActiveFilters = Boolean(appliedEntityType || appliedEntityId);

  const getActionBadgeVariant = (action: string): BadgeVariant => {
    switch (action.toUpperCase()) {
      case 'ACCEPT':
      case 'CREATE_NATIONAL_MATERIAL':
        return 'same';
      case 'MARK_DIFFERENT':
      case 'OVERRIDE':
        return 'potential';
      case 'REJECT':
        return 'diff';
      default:
        return 'neutral';
    }
  };

  const formatTimestamp = (iso: string) => {
    try {
      const d = new Date(iso);
      return d.toLocaleString(undefined, {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
      });
    } catch {
      return iso;
    }
  };

  return (
    <div className="p-4 sm:p-6 lg:p-8 max-w-7xl w-full mx-auto space-y-6 flex flex-col min-h-[calc(100vh-4rem)]">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 shrink-0">
        <div>
          <h1 className="text-page-title text-charcoal">Audit Trail</h1>
          <p className="text-body text-charcoal-muted mt-1">
            System and governance history
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={fetchLogs}
            disabled={loading}
            title="Refresh audit ledger"
            className="p-2 rounded-input border border-border bg-surface text-charcoal-muted hover:text-charcoal hover:bg-surface-secondary transition-colors disabled:opacity-50"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* Filter Bar */}
      <form
        onSubmit={handleApplyFilters}
        className="p-3.5 bg-surface rounded-panel border border-border flex flex-col sm:flex-row flex-wrap items-stretch sm:items-center gap-2.5 sm:gap-3 shadow-xs"
      >
        <div className="flex items-center gap-2">
          <Filter className="w-4 h-4 text-charcoal-muted shrink-0" />
          <span className="text-body-sm font-semibold text-charcoal">Filters:</span>
        </div>

        {/* Entity Type Filter */}
        <div className="flex-1 min-w-[180px]">
          <select
            value={entityType}
            onChange={(e) => setEntityType(e.target.value)}
            className="w-full px-3 py-1.5 text-body-sm rounded-input border border-border bg-surface text-charcoal focus:border-border-strong focus:outline-none transition-colors"
          >
            <option value="">All Entity Types</option>
            <option value="MATCH_RECOMMENDATION">MATCH_RECOMMENDATION</option>
            <option value="NATIONAL_MATERIAL">NATIONAL_MATERIAL</option>
            <option value="MATERIAL">MATERIAL</option>
            <option value="MAPPING">MAPPING</option>
          </select>
        </div>

        {/* Entity ID Filter */}
        <div className="flex-1 min-w-[200px]">
          <input
            type="text"
            value={entityId}
            onChange={(e) => setEntityId(e.target.value)}
            placeholder="Filter by Entity UUID..."
            className="w-full px-3 py-1.5 text-body-sm font-mono rounded-input border border-border bg-surface text-charcoal placeholder:text-charcoal-disabled focus:border-border-strong focus:outline-none transition-colors"
          />
        </div>

        {/* Action Buttons */}
        <div className="flex items-center gap-2">
          <button
            type="submit"
            className="px-3.5 py-1.5 rounded-input bg-brand text-white text-body-sm font-medium hover:bg-brand-hover transition-colors shadow-xs"
          >
            Apply
          </button>
          {hasActiveFilters && (
            <button
              type="button"
              onClick={handleClearFilters}
              className="inline-flex items-center gap-1 px-3 py-1.5 rounded-input border border-border text-charcoal-muted hover:text-charcoal hover:bg-surface-secondary text-body-sm font-medium transition-colors"
            >
              <X className="w-3.5 h-3.5" />
              <span>Reset</span>
            </button>
          )}
        </div>
      </form>

      {/* Main Workspace Area */}
      {loading && logs.length === 0 ? (
        <LoadingState message="Loading audit event ledger..." className="py-20" />
      ) : error ? (
        <ErrorState
          title="Unable to load audit ledger"
          message={error}
          onRetry={fetchLogs}
        />
      ) : logs.length === 0 ? (
        <EmptyState
          icon={<History className="w-5 h-5" />}
          title={hasActiveFilters ? 'No matching audit events' : 'No audit events logged'}
          description={
            hasActiveFilters
              ? 'No audit records match the current entity filters.'
              : 'The governance audit log is currently empty.'
          }
          action={
            hasActiveFilters ? (
              <button
                type="button"
                onClick={handleClearFilters}
                className="px-4 py-2 rounded-input border border-border text-charcoal font-medium hover:bg-surface-secondary text-body-sm transition-colors"
              >
                Clear Filters
              </button>
            ) : undefined
          }
        />
      ) : (
        <div className="flex-1 flex flex-col lg:flex-row gap-0 rounded-panel border border-border bg-surface overflow-hidden shadow-xs min-h-[480px]">
          {/* Master Table */}
          <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
            <div className="flex-1 overflow-auto">
              <table className="w-full text-left border-collapse">
                <thead className="sticky top-0 z-10 bg-surface-secondary/80 border-b border-border text-table-header text-charcoal-caption uppercase">
                  <tr>
                    <th scope="col" className="py-2.5 px-4 font-medium w-10 text-center">
                      #
                    </th>
                    <th scope="col" className="py-2.5 px-4 font-medium min-w-[160px]">
                      Timestamp
                    </th>
                    <th scope="col" className="py-2.5 px-4 font-medium min-w-[120px]">
                      Actor
                    </th>
                    <th scope="col" className="py-2.5 px-4 font-medium min-w-[140px]">
                      Action
                    </th>
                    <th scope="col" className="py-2.5 px-4 font-medium min-w-[140px]">
                      Entity Type
                    </th>
                    <th scope="col" className="py-2.5 px-4 font-medium min-w-[200px]">
                      Reason / Notes
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border/60 text-body">
                  {logs.map((log, idx) => {
                    const isSelected = selectedLog?.id === log.id;

                    return (
                      <tr
                        key={log.id}
                        onClick={() => setSelectedLog(log)}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter' || e.key === ' ') {
                            e.preventDefault();
                            setSelectedLog(log);
                          }
                        }}
                        tabIndex={0}
                        className={`group cursor-pointer transition-colors outline-none focus-visible:bg-surface-secondary ${
                          isSelected
                            ? 'bg-brand-tint/60 ring-1 ring-inset ring-brand/20'
                            : 'hover:bg-surface-hover'
                        }`}
                      >
                        {/* Index */}
                        <td className="py-3 px-4 text-center">
                          {isSelected ? (
                            <span className="inline-flex items-center justify-center w-4 h-4 rounded-full bg-brand text-white">
                              <Check className="w-2.5 h-2.5 stroke-[3]" />
                            </span>
                          ) : (
                            <span className="text-body-sm text-charcoal-caption">
                              {idx + 1}
                            </span>
                          )}
                        </td>

                        {/* Timestamp */}
                        <td className="py-3 px-4 text-xs text-charcoal-muted whitespace-nowrap">
                          {formatTimestamp(log.created_at)}
                        </td>

                        {/* Actor */}
                        <td className="py-3 px-4 font-mono text-xs font-semibold text-charcoal whitespace-nowrap">
                          {log.actor}
                        </td>

                        {/* Action Badge */}
                        <td className="py-3 px-4 whitespace-nowrap">
                          <Badge variant={getActionBadgeVariant(log.action)}>
                            {log.action}
                          </Badge>
                        </td>

                        {/* Entity Type */}
                        <td className="py-3 px-4 whitespace-nowrap">
                          <span className="font-mono text-xs text-charcoal-muted bg-surface-secondary px-1.5 py-0.5 rounded-badge border border-border/60">
                            {log.entity_type}
                          </span>
                        </td>

                        {/* Reason / Notes */}
                        <td className="py-3 px-4 text-xs text-charcoal leading-snug truncate max-w-xs" title={log.reason || undefined}>
                          {log.reason || <span className="text-charcoal-disabled italic">—</span>}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>

            {/* Table Footer */}
            <div className="px-4 py-2.5 bg-surface-secondary/30 border-t border-border flex items-center justify-between text-body-sm text-charcoal-caption shrink-0">
              <span>
                Total events in ledger: <strong className="font-medium text-charcoal">{logs.length}</strong>
              </span>
              <span className="text-xs">
                {selectedLog
                  ? 'Viewing event state in inspector'
                  : 'Click any row to inspect before/after state transformation'}
              </span>
            </div>
          </div>

          {/* Audit Inspector Panel */}
          {selectedLog && (
            <AuditInspector
              log={selectedLog}
              onClose={() => setSelectedLog(null)}
            />
          )}
        </div>
      )}
    </div>
  );
};

