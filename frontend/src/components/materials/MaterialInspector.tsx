import React, { useEffect, useState, useCallback } from 'react';
import {
  X,
  ChevronDown,
  ChevronRight,
  FileCode,
  Layers,
  Database,
  Building2,
  Trash2,
} from 'lucide-react';
import { api, ApiClientError } from '../../api/client';
import type { MaterialDetailResponse } from '../../types/api';
import { LoadingState } from '../common/LoadingState';
import { ErrorState } from '../common/ErrorState';
import { Badge, type BadgeVariant } from '../common/Badge';

interface MaterialInspectorProps {
  materialId: string | null;
  selectedCpseName?: string;
  selectedCpseCode?: string;
  onClose: () => void;
  onDeleteRequest?: (detail: MaterialDetailResponse) => void;
}

export const MaterialInspector: React.FC<MaterialInspectorProps> = ({
  materialId,
  selectedCpseName,
  selectedCpseCode,
  onClose,
  onDeleteRequest,
}) => {
  const [detail, setDetail] = useState<MaterialDetailResponse | null>(null);
  const [status, setStatus] = useState<string>('NOT PROCESSED');
  const [nationalCode, setNationalCode] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Collapsible sections
  const [showRawSource, setShowRawSource] = useState<boolean>(false);
  const [showNormalizedAttributes, setShowNormalizedAttributes] = useState<boolean>(false);

  const getStatusVariant = (st?: string | null): BadgeVariant => {
    switch (st?.toUpperCase()) {
      case 'MAPPED':
        return 'same';
      case 'NEEDS REVIEW':
      case 'POTENTIALLY_EQUIVALENT':
        return 'potential';
      case 'DIFFERENT':
        return 'diff';
      case 'UNMATCHED':
      case 'NOT PROCESSED':
      default:
        return 'neutral';
    }
  };

  const fetchDetail = useCallback(async (id: string) => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.materials.get(id);
      setDetail(data);
      setStatus(data.mapping_status || 'NOT PROCESSED');
      setNationalCode(data.national_material_code || null);
    } catch (err: unknown) {
      if (err instanceof ApiClientError) {
        setError(err.message);
      } else if (err instanceof Error) {
        setError(err.message);
      } else {
        setError('Failed to fetch material details.');
      }
    } finally {
      setLoading(false);
    }
  }, []);


  useEffect(() => {
    if (materialId) {
      fetchDetail(materialId);
    } else {
      setDetail(null);
      setStatus('NOT PROCESSED');
      setNationalCode(null);
      setError(null);
    }
  }, [materialId, fetchDetail]);

  if (!materialId) {
    return null;
  }

  const renderValue = (val: string | null | undefined, isMono = false) => {
    if (val === null || val === undefined || val.trim() === '') {
      return <span className="text-charcoal-disabled italic text-xs">UNKNOWN</span>;
    }
    return (
      <span className={isMono ? 'font-mono text-body-sm text-charcoal' : 'text-body-sm text-charcoal'}>
        {val}
      </span>
    );
  };

  return (
    <>
      {/* Mobile backdrop */}
      <div
        className="fixed inset-0 z-40 bg-black/40 lg:hidden animate-in fade-in duration-150"
        onClick={onClose}
      />
      <aside className="fixed inset-y-0 right-0 z-50 w-full sm:max-w-md lg:static lg:w-[460px] lg:z-auto shrink-0 bg-surface border-l border-border flex flex-col h-full overflow-hidden select-text shadow-xl lg:shadow-sm animate-in slide-in-from-right-full lg:animate-none duration-200">
      {/* Inspector Header */}
      <div className="h-14 px-5 flex items-center justify-between border-b border-border bg-surface-secondary/40 shrink-0">
        <div className="flex items-center gap-2 min-w-0">
          <Database className="w-4 h-4 text-charcoal-muted shrink-0" />
          <div className="flex flex-col min-w-0">
            <span className="text-card-title text-charcoal truncate">
              {detail ? detail.source_material_code : 'Material Inspector'}
            </span>
            <span className="text-[11px] text-charcoal-caption truncate">
              Technical Attribute Inspection
            </span>
          </div>
        </div>

        <div className="flex items-center gap-1">
          {detail && onDeleteRequest && (
            <button
              type="button"
              onClick={() => onDeleteRequest(detail)}
              title="Delete material"
              className="p-1.5 rounded-input text-charcoal-caption hover:text-semantic-diff-text hover:bg-semantic-diff-bg transition-colors"
            >
              <Trash2 className="w-4 h-4" />
            </button>
          )}
          <button
            type="button"
            onClick={onClose}
            title="Close inspector"
            className="p-1.5 rounded-input text-charcoal-caption hover:text-charcoal hover:bg-surface-secondary transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Inspector Content */}
      <div className="flex-1 overflow-y-auto p-5 space-y-6">
        {loading ? (
          <LoadingState message="Loading material details..." className="py-16" />
        ) : error ? (
          <ErrorState
            title="Failed to load details"
            message={error}
            onRetry={() => materialId && fetchDetail(materialId)}
          />
        ) : detail ? (
          <>
            {/* 0. HARMONIZATION STATUS */}
            <div className="space-y-3">
              <div className="flex items-center justify-between border-b border-border pb-1.5">
                <h4 className="text-table-header uppercase text-charcoal-caption font-semibold tracking-wider">
                  Harmonization
                </h4>
                <Badge variant={getStatusVariant(status)} className="text-[10px] font-semibold tracking-wider">
                  {status}
                </Badge>
              </div>

              <div className="space-y-2 text-body-sm">
                <div>
                  <span className="text-xs font-medium text-charcoal-muted block">Status</span>
                  <span className="text-charcoal font-medium">{status}</span>
                </div>
                {status === 'MAPPED' && nationalCode ? (
                  <div>
                    <span className="text-xs font-medium text-charcoal-muted block">National Material</span>
                    <span className="font-mono font-semibold text-brand">{nationalCode}</span>
                  </div>
                ) : null}
                {status === 'NOT PROCESSED' && (
                  <div>
                    <span className="text-xs font-medium text-charcoal-muted block">Processing</span>
                    <span className="text-charcoal-muted">Awaiting normalization and matching workflow.</span>
                  </div>
                )}
                {status === 'NEEDS REVIEW' && (
                  <div>
                    <span className="text-xs font-medium text-charcoal-muted block">Review</span>
                    <span className="text-semantic-potential-text">Unresolved candidate match pending human review.</span>
                  </div>
                )}
                {status === 'DIFFERENT' && (
                  <div>
                    <span className="text-xs font-medium text-charcoal-muted block">Outcome</span>
                    <span className="text-semantic-diff-text">Classified as distinct engineering material.</span>
                  </div>
                )}
                {status === 'UNMATCHED' && (
                  <div>
                    <span className="text-xs font-medium text-charcoal-muted block">Outcome</span>
                    <span className="text-charcoal-muted">Processed with no equivalent candidates found.</span>
                  </div>
                )}
              </div>
            </div>


            {/* 1. SOURCE SECTION */}
            <div className="space-y-3">
              <div className="flex items-center justify-between border-b border-border pb-1.5">
                <h4 className="text-table-header uppercase text-charcoal-caption font-semibold tracking-wider">
                  Source Data (Immutable)
                </h4>
                {selectedCpseCode && (
                  <span className="inline-flex items-center gap-1 text-[11px] font-mono text-charcoal-muted bg-surface-secondary px-1.5 py-0.5 rounded-badge border border-border/80">
                    <Building2 className="w-3 h-3" />
                    {selectedCpseCode}
                  </span>
                )}
              </div>

              <div className="space-y-2 text-body-sm">
                <div>
                  <span className="text-xs font-medium text-charcoal-muted block">Source Material Code</span>
                  <span className="font-mono font-semibold text-charcoal">{detail.source_material_code}</span>
                </div>

                <div>
                  <span className="text-xs font-medium text-charcoal-muted block">Source Description</span>
                  <span className="text-charcoal leading-snug">{detail.source_description}</span>
                </div>

                <div className="grid grid-cols-2 gap-3 pt-1 border-t border-border/40">
                  <div>
                    <span className="text-xs font-medium text-charcoal-muted block">Source UOM</span>
                    {renderValue(detail.source_uom, true)}
                  </div>
                  <div>
                    <span className="text-xs font-medium text-charcoal-muted block">Specifications</span>
                    {renderValue(detail.source_specifications)}
                  </div>
                </div>

                {selectedCpseName && (
                  <div className="pt-1 border-t border-border/40">
                    <span className="text-xs font-medium text-charcoal-muted block">Enterprise Tenant</span>
                    <span className="text-charcoal text-xs">{selectedCpseName}</span>
                  </div>
                )}
              </div>
            </div>

            {/* 2. NORMALIZED IDENTITY */}
            <div className="space-y-3">
              <div className="flex items-center justify-between border-b border-border pb-1.5">
                <h4 className="text-table-header uppercase text-charcoal-caption font-semibold tracking-wider">
                  Normalized Identity
                </h4>
                <span className="text-[11px] text-charcoal-caption">Deterministic Standard</span>
              </div>

              <div className="space-y-2">
                <div>
                  <span className="text-xs font-medium text-charcoal-muted block mb-0.5">
                    Canonical Normalized Description
                  </span>
                  <div className="p-2.5 bg-surface-secondary/40 rounded-panel border border-border text-body-sm font-medium text-charcoal">
                    {renderValue(detail.normalized_description)}
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-2 text-body-sm pt-1">
                  <div className="p-2.5 bg-surface rounded-input border border-border/80">
                    <span className="text-[11px] font-medium text-charcoal-muted block">Category</span>
                    {renderValue(detail.category, true)}
                  </div>

                  <div className="p-2.5 bg-surface rounded-input border border-border/80">
                    <span className="text-[11px] font-medium text-charcoal-muted block">Valve Type</span>
                    {renderValue(detail.valve_type, true)}
                  </div>

                  <div className="p-2.5 bg-surface rounded-input border border-border/80">
                    <span className="text-[11px] font-medium text-charcoal-muted block">Size</span>
                    {renderValue(detail.size, true)}
                  </div>

                  <div className="p-2.5 bg-surface rounded-input border border-border/80">
                    <span className="text-[11px] font-medium text-charcoal-muted block">Pressure Class</span>
                    {renderValue(detail.pressure_class, true)}
                  </div>

                  <div className="p-2.5 bg-surface rounded-input border border-border/80">
                    <span className="text-[11px] font-medium text-charcoal-muted block">Body Material</span>
                    {renderValue(detail.body_material, true)}
                  </div>

                  <div className="p-2.5 bg-surface rounded-input border border-border/80">
                    <span className="text-[11px] font-medium text-charcoal-muted block">Connection Type</span>
                    {renderValue(detail.connection_type, true)}
                  </div>

                  <div className="p-2.5 bg-surface rounded-input border border-border/80">
                    <span className="text-[11px] font-medium text-charcoal-muted block">Trim Material</span>
                    {renderValue(detail.trim, true)}
                  </div>

                  <div className="p-2.5 bg-surface rounded-input border border-border/80">
                    <span className="text-[11px] font-medium text-charcoal-muted block">Normalized UOM</span>
                    {renderValue(detail.normalized_uom, true)}
                  </div>
                </div>
              </div>
            </div>

            {/* 3. ORIGINAL RAW PAYLOAD */}
            <div className="space-y-2 border border-border rounded-panel overflow-hidden bg-surface">
              <button
                type="button"
                onClick={() => setShowRawSource(!showRawSource)}
                className="w-full px-3.5 py-2.5 flex items-center justify-between bg-surface-secondary/50 hover:bg-surface-secondary/80 text-left transition-colors"
              >
                <div className="flex items-center gap-2">
                  <FileCode className="w-4 h-4 text-charcoal-muted" />
                  <span className="text-body-sm font-semibold text-charcoal">Original Raw Payload</span>
                  {detail.raw_source_data && (
                    <span className="text-[11px] font-mono text-charcoal-caption bg-surface px-1.5 py-0.2 rounded-badge border border-border">
                      {Object.keys(detail.raw_source_data).length} keys
                    </span>
                  )}
                </div>
                {showRawSource ? (
                  <ChevronDown className="w-4 h-4 text-charcoal-muted" />
                ) : (
                  <ChevronRight className="w-4 h-4 text-charcoal-muted" />
                )}
              </button>

              {showRawSource && (
                <div className="p-3 bg-canvas border-t border-border space-y-2">
                  <p className="text-[11px] text-charcoal-caption">
                    Immutable raw record preserved exactly as imported from CPSE spreadsheet.
                  </p>
                  <pre className="p-2.5 bg-surface rounded-input border border-border font-mono text-[11px] text-charcoal overflow-x-auto leading-relaxed">
                    {detail.raw_source_data
                      ? JSON.stringify(detail.raw_source_data, null, 2)
                      : 'null'}
                  </pre>
                </div>
              )}
            </div>

            {/* 4. EXTRACTED NORMALIZED ATTRIBUTES JSON */}
            {detail.normalized_attributes && (
              <div className="space-y-2 border border-border rounded-panel overflow-hidden bg-surface">
                <button
                  type="button"
                  onClick={() => setShowNormalizedAttributes(!showNormalizedAttributes)}
                  className="w-full px-3.5 py-2.5 flex items-center justify-between bg-surface-secondary/50 hover:bg-surface-secondary/80 text-left transition-colors"
                >
                  <div className="flex items-center gap-2">
                    <Layers className="w-4 h-4 text-charcoal-muted" />
                    <span className="text-body-sm font-semibold text-charcoal">
                      Normalized Attributes Payload
                    </span>
                  </div>
                  {showNormalizedAttributes ? (
                    <ChevronDown className="w-4 h-4 text-charcoal-muted" />
                  ) : (
                    <ChevronRight className="w-4 h-4 text-charcoal-muted" />
                  )}
                </button>

                {showNormalizedAttributes && (
                  <div className="p-3 bg-canvas border-t border-border space-y-2">
                    <pre className="p-2.5 bg-surface rounded-input border border-border font-mono text-[11px] text-charcoal overflow-x-auto leading-relaxed">
                      {JSON.stringify(detail.normalized_attributes, null, 2)}
                    </pre>
                  </div>
                )}
              </div>
            )}
          </>
        ) : null}
      </div>
    </aside>
    </>
  );
};

