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
                  {(() => {
                    const normAttrs = (detail.normalized_attributes as Record<string, unknown>) || {};
                    const rawCat = detail.category || (normAttrs.category as string) || null;
                    const category = rawCat ? rawCat.toUpperCase() : null;

                    const CATEGORY_SCHEMAS: Record<string, { label: string; key: string }[]> = {
                      VALVE: [
                        { label: 'Category', key: 'category' },
                        { label: 'Valve Type', key: 'valve_type' },
                        { label: 'Size', key: 'size' },
                        { label: 'Pressure Class', key: 'pressure_class' },
                        { label: 'Body Material', key: 'body_material' },
                        { label: 'Connection Type', key: 'connection_type' },
                        { label: 'Trim Material', key: 'trim' },
                        { label: 'Seat Material', key: 'seat_material' },
                        { label: 'Normalized UOM', key: 'normalized_uom' },
                      ],
                      STRAINER: [
                        { label: 'Category', key: 'category' },
                        { label: 'Strainer Type', key: 'type' },
                        { label: 'Size', key: 'size' },
                        { label: 'Pressure Rating', key: 'pressure_rating' },
                        { label: 'Material Grade', key: 'material_grade' },
                        { label: 'Mesh', key: 'mesh' },
                        { label: 'Normalized UOM', key: 'normalized_uom' },
                      ],
                      PIPE: [
                        { label: 'Category', key: 'category' },
                        { label: 'Construction', key: 'construction' },
                        { label: 'Size', key: 'size' },
                        { label: 'Schedule', key: 'schedule' },
                        { label: 'Material Grade', key: 'material_grade' },
                        { label: 'Standard Grade', key: 'standard_grade' },
                        { label: 'Normalized UOM', key: 'normalized_uom' },
                      ],
                      FLANGE: [
                        { label: 'Category', key: 'category' },
                        { label: 'Flange Type', key: 'flange_type' },
                        { label: 'Size', key: 'size' },
                        { label: 'Pressure Rating', key: 'pressure_rating' },
                        { label: 'Material Grade', key: 'material_grade' },
                        { label: 'Facing Connection', key: 'facing_connection' },
                        { label: 'Normalized UOM', key: 'normalized_uom' },
                      ],
                      GASKET: [
                        { label: 'Category', key: 'category' },
                        { label: 'Gasket Type', key: 'gasket_type' },
                        { label: 'Size', key: 'size' },
                        { label: 'Pressure Rating', key: 'pressure_rating' },
                        { label: 'Filler Material', key: 'materials_filler' },
                        { label: 'Normalized UOM', key: 'normalized_uom' },
                      ],
                      PUMP: [
                        { label: 'Category', key: 'category' },
                        { label: 'Pump Type', key: 'pump_type' },
                        { label: 'Flow Rate', key: 'flow_rate' },
                        { label: 'Head', key: 'head' },
                        { label: 'Casing Material', key: 'casing_material' },
                        { label: 'Normalized UOM', key: 'normalized_uom' },
                      ],
                      TRANSMITTER: [
                        { label: 'Category', key: 'category' },
                        { label: 'Instrument Type', key: 'instrument_type' },
                        { label: 'Measurement Range', key: 'measurement_range' },
                        { label: 'Signal', key: 'signal' },
                        { label: 'Protocol', key: 'protocol' },
                        { label: 'Normalized UOM', key: 'normalized_uom' },
                      ],
                      'O-RING': [
                        { label: 'Category', key: 'category' },
                        { label: 'Elastomer Material', key: 'material_elastomer' },
                        { label: 'Inner Diameter', key: 'inner_diameter' },
                        { label: 'Cross Section', key: 'cross_section' },
                        { label: 'Normalized UOM', key: 'normalized_uom' },
                      ],
                      FASTENER: [
                        { label: 'Category', key: 'category' },
                        { label: 'Fastener Type', key: 'type' },
                        { label: 'Size', key: 'size' },
                        { label: 'Length', key: 'length' },
                        { label: 'Grade', key: 'grade' },
                        { label: 'Nut Specification', key: 'nut_specification' },
                        { label: 'Normalized UOM', key: 'normalized_uom' },
                      ],
                      FITTING: [
                        { label: 'Category', key: 'category' },
                        { label: 'Fitting Type', key: 'fitting_type' },
                        { label: 'Size', key: 'size' },
                        { label: 'Schedule', key: 'schedule' },
                        { label: 'Material Grade', key: 'material_grade' },
                        { label: 'Normalized UOM', key: 'normalized_uom' },
                      ],
                      MOTOR: [
                        { label: 'Category', key: 'category' },
                        { label: 'Motor Type', key: 'motor_type' },
                        { label: 'Phase', key: 'phase' },
                        { label: 'Power', key: 'power' },
                        { label: 'Voltage', key: 'voltage' },
                        { label: 'Speed', key: 'speed' },
                        { label: 'Efficiency', key: 'efficiency' },
                        { label: 'Normalized UOM', key: 'normalized_uom' },
                      ],
                      BEARING: [
                        { label: 'Category', key: 'category' },
                        { label: 'Bearing Type', key: 'bearing_type' },
                        { label: 'Bearing Number', key: 'bearing_number' },
                        { label: 'Seal / Shield', key: 'seal_shield' },
                        { label: 'Normalized UOM', key: 'normalized_uom' },
                      ],
                      BELT: [
                        { label: 'Category', key: 'category' },
                        { label: 'Belt Type', key: 'belt_type' },
                        { label: 'Profile', key: 'profile' },
                        { label: 'Length', key: 'length' },
                        { label: 'Normalized UOM', key: 'normalized_uom' },
                      ],
                    };

                    const resolveAttr = (key: string): string | null | undefined => {
                      if (normAttrs[key] !== undefined && normAttrs[key] !== null) {
                        return String(normAttrs[key]);
                      }
                      const detailObj = detail as unknown as Record<string, unknown>;
                      if (detailObj[key] !== undefined && detailObj[key] !== null) {
                        return String(detailObj[key]);
                      }
                      if (key === 'category') return category;
                      if (key === 'pressure_rating') return detail.pressure_class || (normAttrs.pressure_class as string);
                      if (key === 'pressure_class') return detail.pressure_class || (normAttrs.pressure_rating as string);
                      if (key === 'material_grade') return detail.body_material || (normAttrs.body_material as string) || (normAttrs.casing_material as string);
                      if (key === 'body_material') return detail.body_material || (normAttrs.material_grade as string);
                      if (key === 'facing_connection') return detail.connection_type || (normAttrs.connection_type as string);
                      if (key === 'connection_type') return detail.connection_type || (normAttrs.facing_connection as string);
                      if (key === 'valve_type') return detail.valve_type || (normAttrs.type as string) || (normAttrs.material_type as string);
                      if (key === 'type') return (normAttrs.type as string) || detail.valve_type || (normAttrs.material_type as string);
                      if (key === 'trim') return detail.trim || (normAttrs.trim_material as string);
                      if (key === 'seat_material') return (normAttrs.seat_material as string) || (normAttrs.liner_material as string);
                      if (key === 'normalized_uom') return detail.normalized_uom || (normAttrs.normalized_uom as string);
                      return null;
                    };

                    const schema = category && CATEGORY_SCHEMAS[category] ? CATEGORY_SCHEMAS[category] : (
                      (!category && (detail.valve_type || detail.trim)) ? CATEGORY_SCHEMAS.VALVE : null
                    );

                    const fields: { label: string; value: string | null | undefined }[] = [];
                    const renderedKeys = new Set<string>();

                    if (schema) {
                      for (const item of schema) {
                        const val = resolveAttr(item.key);
                        if (item.key === 'seat_material' && !val) {
                          continue;
                        }
                        renderedKeys.add(item.key);
                        fields.push({
                          label: item.label,
                          value: val,
                        });
                      }
                    } else {
                      fields.push({ label: 'Category', value: category || 'UNKNOWN' });
                      for (const [k, v] of Object.entries(normAttrs)) {
                        if (!['schema_version', 'category'].includes(k) && v !== null && v !== undefined && typeof v !== 'object') {
                          const label = k.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
                          fields.push({ label, value: String(v) });
                          renderedKeys.add(k);
                        }
                      }
                      fields.push({ label: 'Normalized UOM', value: detail.normalized_uom || (normAttrs.normalized_uom as string) });
                    }

                    // Render any additional attributes not in schema
                    const ignoreKeys = new Set([
                      'schema_version', 'category', 'additional_attributes', 'extraction_confidence', 'provenance_tokens',
                      'normalized_uom', 'normalized_description', 'liner_material'
                    ]);

                    for (const [k, v] of Object.entries(normAttrs)) {
                      if (!renderedKeys.has(k) && !ignoreKeys.has(k) && v !== null && v !== undefined && typeof v !== 'object') {
                        const label = k.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
                        fields.push({ label, value: String(v) });
                      }
                    }

                    return fields.map((f) => (
                      <div key={f.label} className="p-2.5 bg-surface rounded-input border border-border/80">
                        <span className="text-[11px] font-medium text-charcoal-muted block">{f.label}</span>
                        {renderValue(f.value, true)}
                      </div>
                    ));
                  })()}
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

