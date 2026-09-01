import React from 'react';
import type { MaterialDetailResponse } from '../../types/api';

interface AttributeComparisonTableProps {
  sourceDetail: MaterialDetailResponse | null;
  candidateDetail: MaterialDetailResponse | null;
}

interface AttributeRow {
  label: string;
  sourceKey: keyof MaterialDetailResponse;
  candidateKey: keyof MaterialDetailResponse;
  isMono?: boolean;
}

const ATTRIBUTE_ROWS: AttributeRow[] = [
  { label: 'Category', sourceKey: 'category', candidateKey: 'category', isMono: true },
  { label: 'Valve Type', sourceKey: 'valve_type', candidateKey: 'valve_type', isMono: true },
  { label: 'Size', sourceKey: 'size', candidateKey: 'size', isMono: true },
  { label: 'Body Material', sourceKey: 'body_material', candidateKey: 'body_material', isMono: true },
  { label: 'Pressure Class', sourceKey: 'pressure_class', candidateKey: 'pressure_class', isMono: true },
  { label: 'Connection Type', sourceKey: 'connection_type', candidateKey: 'connection_type', isMono: true },
  { label: 'Trim Material', sourceKey: 'trim', candidateKey: 'trim', isMono: true },
  { label: 'Normalized UOM', sourceKey: 'normalized_uom', candidateKey: 'normalized_uom', isMono: true },
  { label: 'Normalized Description', sourceKey: 'normalized_description', candidateKey: 'normalized_description' },
  { label: 'Source Description', sourceKey: 'source_description', candidateKey: 'source_description' },
];

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
            {ATTRIBUTE_ROWS.map((attr) => {
              const sourceVal = sourceDetail ? sourceDetail[attr.sourceKey] : null;
              const candVal = candidateDetail ? candidateDetail[attr.candidateKey] : null;

              const isSourceEmpty = sourceVal === null || sourceVal === undefined || sourceVal === '';
              const isCandEmpty = candVal === null || candVal === undefined || candVal === '';
              const isDifferent = !isSourceEmpty && !isCandEmpty && String(sourceVal).trim().toLowerCase() !== String(candVal).trim().toLowerCase();

              return (
                <tr
                  key={attr.label}
                  className={`transition-colors hover:bg-surface-hover ${
                    isDifferent ? 'bg-semantic-potential-bg/30' : ''
                  }`}
                >
                  {/* Attribute Label */}
                  <td className="py-2.5 px-4 text-xs font-semibold text-charcoal-muted uppercase tracking-wider bg-surface-secondary/20">
                    {attr.label}
                  </td>

                  {/* Source Value */}
                  <td className="py-2.5 px-4">
                    {renderCell(sourceVal, attr.isMono)}
                  </td>

                  {/* Candidate Value */}
                  <td className="py-2.5 px-4">
                    {renderCell(candVal, attr.isMono)}
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
