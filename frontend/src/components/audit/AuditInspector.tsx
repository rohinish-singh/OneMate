import React from 'react';
import {
  X,
  History,
  User,
  Activity,
  FileCode,
  Calendar,
} from 'lucide-react';
import type { AuditLogItem } from '../../types/api';
import { Badge, type BadgeVariant } from '../common/Badge';

interface AuditInspectorProps {
  log: AuditLogItem | null;
  onClose: () => void;
}

export const AuditInspector: React.FC<AuditInspectorProps> = ({
  log,
  onClose,
}) => {
  if (!log) return null;

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
    <>
      {/* Mobile backdrop */}
      <div
        className="fixed inset-0 z-40 bg-black/40 lg:hidden animate-in fade-in duration-150"
        onClick={onClose}
      />
      <aside className="fixed inset-y-0 right-0 z-50 w-full sm:max-w-md lg:static lg:w-[460px] lg:z-auto shrink-0 bg-surface border-l border-border flex flex-col h-full overflow-hidden select-text shadow-xl lg:shadow-sm animate-in slide-in-from-right-full lg:animate-none duration-200">
      {/* Header */}
      <div className="h-14 px-5 flex items-center justify-between border-b border-border bg-surface-secondary/40 shrink-0">
        <div className="flex items-center gap-2 min-w-0">
          <History className="w-4 h-4 text-charcoal-muted shrink-0" />
          <div className="flex flex-col min-w-0">
            <span className="text-card-title text-charcoal truncate">
              Audit Event Details
            </span>
            <span className="text-[11px] text-charcoal-caption truncate font-mono">
              {log.id.slice(0, 18)}...
            </span>
          </div>
        </div>

        <button
          type="button"
          onClick={onClose}
          title="Close inspector"
          className="p-1.5 rounded-input text-charcoal-caption hover:text-charcoal hover:bg-surface-secondary transition-colors"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-5 space-y-6">
        {/* 1. EVENT OVERVIEW */}
        <div className="space-y-3">
          <div className="flex items-center justify-between border-b border-border pb-1.5">
            <h4 className="text-table-header uppercase text-charcoal-caption font-semibold tracking-wider">
              Governance Action
            </h4>
            <Badge variant={getActionBadgeVariant(log.action)}>
              {log.action}
            </Badge>
          </div>

          <div className="p-3.5 bg-surface-secondary/30 rounded-panel border border-border/70 space-y-3 text-body-sm">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-charcoal-muted flex items-center gap-1.5">
                <User className="w-3.5 h-3.5" />
                Actor
              </span>
              <span className="font-mono font-semibold text-charcoal">{log.actor}</span>
            </div>

            <div className="flex items-center justify-between pt-2 border-t border-border/40">
              <span className="text-xs font-medium text-charcoal-muted flex items-center gap-1.5">
                <Calendar className="w-3.5 h-3.5" />
                Timestamp
              </span>
              <span className="text-xs text-charcoal">{formatTimestamp(log.created_at)}</span>
            </div>

            <div className="pt-2 border-t border-border/40">
              <span className="text-xs font-medium text-charcoal-muted flex items-center gap-1.5 mb-1">
                <Activity className="w-3.5 h-3.5" />
                Target Entity ({log.entity_type})
              </span>
              <div className="font-mono text-xs text-charcoal bg-surface p-2 rounded-input border border-border break-all">
                {log.entity_id}
              </div>
            </div>

            {log.reason && (
              <div className="pt-2 border-t border-border/40">
                <span className="text-xs font-medium text-charcoal-muted block mb-0.5">
                  Recorded Audit Reason
                </span>
                <p className="text-xs text-charcoal leading-relaxed bg-surface p-2.5 rounded-input border border-border">
                  &ldquo;{log.reason}&rdquo;
                </p>
              </div>
            )}
          </div>
        </div>

        {/* 2. STATE TRANSFORMATION */}
        <div className="space-y-4">
          <div className="flex items-center justify-between border-b border-border pb-1.5">
            <h4 className="text-table-header uppercase text-charcoal-caption font-semibold tracking-wider">
              State Transformation
            </h4>
            <span className="text-[11px] text-charcoal-caption">Immutable Event Snapshot</span>
          </div>

          {/* Before State */}
          <div className="space-y-1.5">
            <div className="flex items-center gap-1.5 text-xs font-semibold text-charcoal-muted">
              <FileCode className="w-3.5 h-3.5" />
              <span>Before State</span>
            </div>
            <pre className="p-3 bg-surface rounded-input border border-border font-mono text-[11px] text-charcoal overflow-x-auto leading-relaxed max-h-48">
              {log.before_state && Object.keys(log.before_state).length > 0
                ? JSON.stringify(log.before_state, null, 2)
                : 'null (Initial / Unset)'}
            </pre>
          </div>

          {/* After State */}
          <div className="space-y-1.5">
            <div className="flex items-center gap-1.5 text-xs font-semibold text-charcoal-muted">
              <FileCode className="w-3.5 h-3.5" />
              <span>After State</span>
            </div>
            <pre className="p-3 bg-surface rounded-input border border-border font-mono text-[11px] text-charcoal overflow-x-auto leading-relaxed max-h-48">
              {log.after_state && Object.keys(log.after_state).length > 0
                ? JSON.stringify(log.after_state, null, 2)
                : 'null'}
            </pre>
          </div>
        </div>
      </div>
    </aside>
    </>
  );
};

