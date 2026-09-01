import React, { useEffect, useState, useCallback } from 'react';
import {
  X,
  ShieldCheck,
  Key,
  Building2,
  ChevronRight,
  Layers,
} from 'lucide-react';
import { api, ApiClientError } from '../../api/client';
import type { NationalMaterialDetailResponse } from '../../types/api';
import { LoadingState } from '../common/LoadingState';
import { ErrorState } from '../common/ErrorState';
import { Badge } from '../common/Badge';

interface NationalMaterialInspectorProps {
  nationalMaterialId: string | null;
  onClose: () => void;
  onSelectMaterial?: (materialId: string, cpseId: string, cpseName: string, cpseCode: string) => void;
}

export const NationalMaterialInspector: React.FC<NationalMaterialInspectorProps> = ({
  nationalMaterialId,
  onClose,
  onSelectMaterial,
}) => {
  const [detail, setDetail] = useState<NationalMaterialDetailResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const fetchDetail = useCallback(async (id: string) => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.nationalMaterials.get(id);
      setDetail(data);
    } catch (err: unknown) {
      if (err instanceof ApiClientError) {
        setError(err.message);
      } else if (err instanceof Error) {
        setError(err.message);
      } else {
        setError('Failed to load National Material specification.');
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (nationalMaterialId) {
      fetchDetail(nationalMaterialId);
    } else {
      setDetail(null);
      setError(null);
    }
  }, [nationalMaterialId, fetchDetail]);

  if (!nationalMaterialId) return null;

  const renderValue = (val: string | null | undefined, isMono = false) => {
    if (val === null || val === undefined || val.trim() === '') {
      return <span className="text-charcoal-disabled italic text-xs">UNKNOWN</span>;
    }
    return (
      <span className={isMono ? 'font-mono text-body-sm font-medium text-charcoal' : 'text-body-sm text-charcoal'}>
        {val}
      </span>
    );
  };

  const mappedCount = detail?.mapped_materials?.length || 0;

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
            <ShieldCheck className="w-4 h-4 text-brand shrink-0" />
            <div className="flex flex-col min-w-0">
              <span className="text-card-title text-charcoal truncate font-mono">
                {detail ? detail.national_code : 'National Specification'}
              </span>
              <span className="text-[11px] text-charcoal-caption truncate">
                Standardized Catalog Entity
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
          {loading ? (
            <LoadingState message="Loading specification details..." className="py-16" />
          ) : error ? (
            <ErrorState
              title="Failed to load specification"
              message={error}
              onRetry={() => nationalMaterialId && fetchDetail(nationalMaterialId)}
            />
          ) : detail ? (
            <>
              {/* 1. CANONICAL IDENTITY */}
              <div className="space-y-3">
                <div className="flex items-center justify-between border-b border-border pb-1.5">
                  <h4 className="text-table-header uppercase text-charcoal-caption font-semibold tracking-wider">
                    Canonical Description
                  </h4>
                  {detail.status && (
                    <Badge variant={detail.status === 'ACTIVE' ? 'same' : 'neutral'}>
                      {detail.status}
                    </Badge>
                  )}
                </div>

                <div className="p-3 bg-surface-secondary/40 rounded-panel border border-border text-body font-medium text-charcoal leading-snug">
                  {detail.canonical_description}
                </div>
              </div>

              {/* 2. MAPPED SOURCE MATERIALS */}
              <div className="space-y-3">
                <div className="flex items-center justify-between border-b border-border pb-1.5">
                  <h4 className="text-table-header uppercase text-charcoal-caption font-semibold tracking-wider flex items-center gap-2">
                    <Layers className="w-3.5 h-3.5 text-charcoal-muted" />
                    <span>Mapped Source Materials</span>
                    <span className="font-mono text-xs text-charcoal bg-surface-secondary px-1.5 py-0.5 rounded-badge border border-border">
                      {mappedCount}
                    </span>
                  </h4>
                  <span className="text-[11px] text-charcoal-caption">Authoritative Traceability</span>
                </div>

                {!detail.mapped_materials || detail.mapped_materials.length === 0 ? (
                  <div className="p-4 bg-surface-secondary/30 rounded-panel border border-border text-center text-xs text-charcoal-muted">
                    No source materials currently mapped to this National Material.
                  </div>
                ) : (
                  <div className="space-y-2.5">
                    {detail.mapped_materials.map((m) => (
                      <div
                        key={m.mapping_id}
                        onClick={() => onSelectMaterial?.(m.material_id, m.cpse_id, m.cpse_name, m.cpse_code)}
                        className={`p-3.5 bg-surface rounded-panel border border-border/80 space-y-2 text-body-sm transition-colors ${
                          onSelectMaterial
                            ? 'cursor-pointer hover:border-brand/40 hover:bg-surface-secondary/40'
                            : ''
                        }`}
                      >
                        <div className="flex items-center justify-between gap-2 flex-wrap">
                          <div className="flex items-center gap-1.5 min-w-0">
                            <Building2 className="w-3.5 h-3.5 text-charcoal-muted shrink-0" />
                            <span className="font-semibold text-charcoal text-xs truncate max-w-[160px]" title={m.cpse_name}>
                              {m.cpse_name}
                            </span>
                            <span className="font-mono text-[10px] text-charcoal-muted bg-surface-secondary px-1 py-0.2 rounded-badge border border-border shrink-0">
                              {m.cpse_code}
                            </span>
                          </div>
                          <div className="flex items-center gap-1.5 shrink-0">
                            <Badge variant={m.mapping_status === 'ACTIVE' ? 'same' : 'neutral'} className="text-[10px] py-0 px-1.5">
                              {m.mapping_status}
                            </Badge>
                            {m.mapping_basis && (
                              <span className="font-mono text-[10px] text-charcoal-caption bg-surface-secondary px-1.5 py-0.2 rounded-badge border border-border">
                                {m.mapping_basis}
                              </span>
                            )}
                          </div>
                        </div>

                        <div className="flex items-start justify-between gap-2 pt-1 border-t border-border/40">
                          <div className="space-y-1 min-w-0 flex-1">
                            <div className="flex items-center gap-1.5">
                              <span className="text-[11px] font-medium text-charcoal-muted">Source Code:</span>
                              <span className="font-mono text-xs font-semibold text-charcoal bg-surface-secondary px-1.5 py-0.2 rounded-badge border border-border/60">
                                {m.source_material_code}
                              </span>
                            </div>
                            <p className="text-xs text-charcoal-muted leading-snug line-clamp-2" title={m.source_description}>
                              {m.source_description}
                            </p>
                          </div>
                          {onSelectMaterial && (
                            <ChevronRight className="w-4 h-4 text-charcoal-caption shrink-0 self-center" />
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* 3. TECHNICAL ATTRIBUTE MATRIX */}
              <div className="space-y-3">
                <div className="flex items-center justify-between border-b border-border pb-1.5">
                  <h4 className="text-table-header uppercase text-charcoal-caption font-semibold tracking-wider">
                    Standardized Attributes
                  </h4>
                  <span className="text-[11px] text-charcoal-caption">Deterministic Standard</span>
                </div>

                <div className="grid grid-cols-2 gap-2 text-body-sm">
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

              {/* 4. SYSTEM IDENTIFIERS */}
              <div className="space-y-3">
                <div className="flex items-center justify-between border-b border-border pb-1.5">
                  <h4 className="text-table-header uppercase text-charcoal-caption font-semibold tracking-wider">
                    Registry Identifiers
                  </h4>
                </div>

                <div className="p-3.5 bg-surface rounded-panel border border-border space-y-2.5 text-body-sm">
                  <div>
                    <span className="text-xs font-medium text-charcoal-muted flex items-center gap-1.5 mb-1">
                      <Key className="w-3.5 h-3.5" />
                      Identity Key (Composite Hash)
                    </span>
                    <div className="p-2 bg-surface-secondary/80 rounded-input border border-border font-mono text-xs text-charcoal break-all leading-relaxed">
                      {detail.identity_key}
                    </div>
                  </div>

                  <div className="pt-2 border-t border-border/60 flex items-center justify-between text-xs">
                    <span className="text-charcoal-muted">System UUID</span>
                    <span className="font-mono text-charcoal">{detail.id}</span>
                  </div>
                </div>
              </div>
            </>
          ) : null}
        </div>
      </aside>
    </>
  );
};


