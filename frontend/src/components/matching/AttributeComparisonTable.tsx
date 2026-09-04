import React from 'react';
import type { MaterialDetailResponse } from '../../types/api';

interface AttributeComparisonTableProps {
  sourceDetail: MaterialDetailResponse | null;
  candidateDetail: MaterialDetailResponse | null;
}



export const AttributeComparisonTable: React.FC<AttributeComparisonTableProps> = ({
  sourceDetail,
  candidateDetail,
}) => {
  const renderCell = (value: unknown, isMono = false) => {
    if (value === null || value === undefined || (typeof value === 'string' && value.trim() === '')) {
      return <span className="text-charcoal-disabled italic text-xs">UNKNOWN</span>;
    }
    const str = String(value);
    return (
      <span className={isMono ? 'font-mono text-body-sm font-medium text-charcoal' : 'text-body-sm text-charcoal leading-snug'}>
        {str}
      </span>
    );
  };

  const sAttrs = (sourceDetail?.normalized_attributes as Record<string, unknown>) || {};
  const cAttrs = (candidateDetail?.normalized_attributes as Record<string, unknown>) || {};

  const rawSrcCat = sourceDetail?.category || (sAttrs.category as string) || '';
  const rawCandCat = candidateDetail?.category || (cAttrs.category as string) || '';
  const sourceCategory = rawSrcCat ? rawSrcCat.toUpperCase() : null;
  const candCategory = rawCandCat ? rawCandCat.toUpperCase() : null;
  const primaryCategory = sourceCategory || candCategory;

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

  const resolveVal = (key: string, detail: MaterialDetailResponse | null, attrs: Record<string, unknown>): unknown => {
    if (!detail) return null;
    if (attrs[key] !== undefined && attrs[key] !== null) return attrs[key];
    const detailObj = detail as unknown as Record<string, unknown>;
    if (detailObj[key] !== undefined && detailObj[key] !== null) return detailObj[key];
    if (key === 'category') return detail.category || attrs.category;
    if (key === 'pressure_rating') return detail.pressure_class || attrs.pressure_class;
    if (key === 'pressure_class') return detail.pressure_class || attrs.pressure_rating;
    if (key === 'material_grade') return detail.body_material || attrs.body_material || attrs.casing_material;
    if (key === 'body_material') return detail.body_material || attrs.material_grade;
    if (key === 'facing_connection') return detail.connection_type || attrs.connection_type;
    if (key === 'connection_type') return detail.connection_type || attrs.facing_connection;
    if (key === 'valve_type') return detail.valve_type || attrs.type || attrs.material_type;
    if (key === 'type') return attrs.type || detail.valve_type || attrs.material_type;
    if (key === 'trim') return detail.trim || attrs.trim_material;
    if (key === 'seat_material') return attrs.seat_material || attrs.liner_material;
    if (key === 'normalized_uom') return detail.normalized_uom || attrs.normalized_uom;
    return null;
  };

  interface RowData {
    label: string;
    sourceVal: unknown;
    candVal: unknown;
    isMono?: boolean;
  }

  const rows: RowData[] = [];
  const renderedKeys = new Set<string>();

  const schema = primaryCategory && CATEGORY_SCHEMAS[primaryCategory] ? CATEGORY_SCHEMAS[primaryCategory] : (
    (!primaryCategory && (sourceDetail?.valve_type || candidateDetail?.valve_type || sourceDetail?.trim || candidateDetail?.trim))
      ? CATEGORY_SCHEMAS.VALVE
      : null
  );

  if (schema) {
    for (const item of schema) {
      const sourceVal = resolveVal(item.key, sourceDetail, sAttrs);
      const candVal = resolveVal(item.key, candidateDetail, cAttrs);
      if (item.key === 'seat_material' && !sourceVal && !candVal) {
        continue;
      }
      renderedKeys.add(item.key);
      rows.push({
        label: item.label,
        sourceVal,
        candVal,
        isMono: true,
      });
    }
  } else {
    // Fallback for unknown category
    rows.push({
      label: 'Category',
      sourceVal: sourceCategory,
      candVal: candCategory,
      isMono: true,
    });
    renderedKeys.add('category');
  }

  // Collect any extra domain attributes
  const ignoreKeys = new Set([
    'schema_version', 'category', 'additional_attributes', 'extraction_confidence', 'provenance_tokens',
    'normalized_uom', 'normalized_description', 'liner_material'
  ]);

  const allExtraKeys = new Set<string>();
  for (const k of Object.keys(sAttrs)) {
    if (!renderedKeys.has(k) && !ignoreKeys.has(k) && typeof sAttrs[k] !== 'object') allExtraKeys.add(k);
  }
  for (const k of Object.keys(cAttrs)) {
    if (!renderedKeys.has(k) && !ignoreKeys.has(k) && typeof cAttrs[k] !== 'object') allExtraKeys.add(k);
  }

  for (const key of Array.from(allExtraKeys).sort()) {
    const label = key.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
    rows.push({
      label,
      sourceVal: sAttrs[key],
      candVal: cAttrs[key],
      isMono: true,
    });
  }

  // Always include Normalized Description and Source Description
  rows.push(
    { label: 'Normalized Description', sourceVal: sourceDetail?.normalized_description, candVal: candidateDetail?.normalized_description },
    { label: 'Source Description', sourceVal: sourceDetail?.source_description, candVal: candidateDetail?.source_description },
  );

  return (
    <div className="rounded-panel border border-border bg-surface overflow-hidden shadow-xs">
      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="bg-surface-secondary/80 border-b border-border text-table-header text-charcoal-caption uppercase">
              <th scope="col" className="py-2.5 px-4 font-medium w-1/4 min-w-[110px]">
                Attribute
              </th>
              <th scope="col" className="py-2.5 px-4 font-medium w-[37.5%] min-w-[140px]">
                Source Material
              </th>
              <th scope="col" className="py-2.5 px-4 font-medium w-[37.5%] min-w-[140px]">
                Candidate Material
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border/60 text-body">
            {rows.map((row) => {
              const sourceVal = row.sourceVal;
              const candVal = row.candVal;

              const isSourceEmpty = sourceVal === null || sourceVal === undefined || sourceVal === '';
              const isCandEmpty = candVal === null || candVal === undefined || candVal === '';
              const isDifferent = !isSourceEmpty && !isCandEmpty && String(sourceVal).trim().toLowerCase() !== String(candVal).trim().toLowerCase();

              return (
                <tr
                  key={row.label}
                  className={`transition-colors hover:bg-surface-hover ${
                    isDifferent ? 'bg-semantic-potential-bg/30' : ''
                  }`}
                >
                  {/* Attribute Label */}
                  <td className="py-2.5 px-4 text-xs font-semibold text-charcoal-muted uppercase tracking-wider bg-surface-secondary/20">
                    {row.label}
                  </td>

                  {/* Source Value */}
                  <td className="py-2.5 px-4">
                    {renderCell(sourceVal, row.isMono)}
                  </td>

                  {/* Candidate Value */}
                  <td className="py-2.5 px-4">
                    {renderCell(candVal, row.isMono)}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
};
