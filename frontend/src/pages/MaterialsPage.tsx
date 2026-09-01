import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Package,
  Building2,
  Upload,
  RefreshCw,
  ArrowRight,
  Check,
  CheckCircle2,
  ClipboardList,
  Sparkles,
  AlertTriangle,
} from 'lucide-react';
import { api, ApiClientError } from '../api/client';
import type { MaterialListItem, MaterialDetailResponse } from '../types/api';
import { useCpse } from '../context/CpseContext';
import { LoadingState } from '../components/common/LoadingState';
import { ErrorState } from '../components/common/ErrorState';
import { EmptyState } from '../components/common/EmptyState';
import { Badge } from '../components/common/Badge';
import { MaterialInspector } from '../components/materials/MaterialInspector';
import { MaterialImportModal } from '../components/materials/MaterialImportModal';
import { MaterialDeleteModal } from '../components/materials/MaterialDeleteModal';

export const MaterialsPage: React.FC = () => {
  const navigate = useNavigate();
  const { selectedCpse } = useCpse();

  const [materials, setMaterials] = useState<MaterialListItem[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Inspector and Import state
  const [selectedMaterialId, setSelectedMaterialId] = useState<string | null>(null);
  const [isImportOpen, setIsImportOpen] = useState<boolean>(false);

  // Material Deletion state
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState<boolean>(false);
  const [materialToDelete, setMaterialToDelete] = useState<MaterialListItem | MaterialDetailResponse | null>(null);
  const [deleteSuccessMessage, setDeleteSuccessMessage] = useState<string | null>(null);

  // Normalization state
  const [isNormalizing, setIsNormalizing] = useState<boolean>(false);
  const [normalizationProgress, setNormalizationProgress] = useState<{ current: number; total: number } | null>(null);
  const [normalizationStatusMessage, setNormalizationStatusMessage] = useState<{ type: 'success' | 'warning' | 'error'; message: string } | null>(null);

  const isCancelledRef = useRef<boolean>(false);

  const fetchMaterials = useCallback(async () => {
    if (!selectedCpse) return;
    setLoading(true);
    setError(null);

    try {
      const data = await api.materials.listByCpse(selectedCpse.id);
      setMaterials(data);
    } catch (err: unknown) {
      if (err instanceof ApiClientError) {
        setError(err.message);
      } else if (err instanceof Error) {
        setError(err.message);
      } else {
        setError('Unable to load materials for the selected enterprise.');
      }
    } finally {
      setLoading(false);
    }
  }, [selectedCpse]);

  // Load materials when selected CPSE changes
  useEffect(() => {
    setSelectedMaterialId(null);
    setIsNormalizing(false);
    setNormalizationProgress(null);
    setNormalizationStatusMessage(null);
    if (selectedCpse) {
      fetchMaterials();
    } else {
      setMaterials([]);
      setError(null);
    }
  }, [selectedCpse, fetchMaterials]);


  useEffect(() => {
    return () => {
      isCancelledRef.current = true;
    };
  }, []);

  const getStatusVariant = (state?: string | null) => {
    switch (state?.toUpperCase()) {
      case 'MAPPED':
        return 'same';
      case 'NEEDS REVIEW':
      case 'POTENTIALLY_EQUIVALENT':
        return 'potential';
      case 'DIFFERENT':
        return 'diff';
      case 'UNMATCHED':
      default:
        return 'neutral';
    }
  };

  const unprocessedMaterials = materials.filter(
    (m) => m.mapping_status === 'NOT PROCESSED' || (!m.normalized_description && !m.mapping_status)
  );

  const handleNormalizeMaterials = async () => {
    if (!selectedCpse || unprocessedMaterials.length === 0 || isNormalizing) return;

    setIsNormalizing(true);
    setNormalizationStatusMessage(null);
    isCancelledRef.current = false;

    const total = unprocessedMaterials.length;
    let successCount = 0;
    let failCount = 0;

    for (let i = 0; i < total; i++) {
      if (isCancelledRef.current) break;
      const mat = unprocessedMaterials[i];
      setNormalizationProgress({ current: i + 1, total });

      try {
        await api.materials.normalize(mat.id);
        successCount++;
      } catch {
        failCount++;
      }
    }

    if (!isCancelledRef.current) {
      await fetchMaterials();
      setIsNormalizing(false);
      setNormalizationProgress(null);

      if (failCount === 0) {
        setNormalizationStatusMessage({
          type: 'success',
          message: `Normalization complete — ${successCount} material${successCount === 1 ? '' : 's'} processed.`,
        });
      } else {
        setNormalizationStatusMessage({
          type: 'warning',
          message: `Normalization completed with ${failCount} failure${failCount > 1 ? 's' : ''} (${successCount} processed successfully).`,
        });
      }
    }
  };

  const handleDeleteSuccess = (deletedId: string) => {
    const deleted = materials.find((m) => m.id === deletedId);
    setMaterials((prev) => prev.filter((m) => m.id !== deletedId));
    if (selectedMaterialId === deletedId) {
      setSelectedMaterialId(null);
    }
    setDeleteSuccessMessage(
      deleted
        ? `Material ${deleted.source_material_code} deleted successfully.`
        : 'Material deleted successfully.'
    );
  };

  const handleReviewThisCpse = () => {
    if (!selectedCpse) return;
    navigate(`/review?cpseId=${selectedCpse.id}`);
  };

  // 1. NO CPSE SELECTED EMPTY STATE
  if (!selectedCpse) {
    return (
      <div className="p-8 max-w-7xl w-full mx-auto space-y-6">
        <div>
          <h1 className="text-page-title text-charcoal">Materials Explorer</h1>
          <p className="text-body text-charcoal-muted mt-1">
            Inspect and manage CPSE materials
          </p>
        </div>

        <EmptyState
          icon={<Building2 className="w-5 h-5" />}
          title="No CPSE selected"
          description="Choose a CPSE from the directory to inspect materials."
          action={
            <button
              type="button"
              onClick={() => navigate('/cpses')}
              className="inline-flex items-center gap-1.5 px-4 py-2 rounded-input bg-brand text-white text-body font-medium hover:bg-brand-hover transition-colors shadow-xs"
            >
              <span>Choose a CPSE</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          }
        />
      </div>
    );
  }

  return (
    <div className="p-4 sm:p-6 lg:p-8 max-w-7xl w-full mx-auto space-y-6 flex flex-col min-h-[calc(100vh-4rem)]">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 shrink-0">
        <div>
          <h1 className="text-page-title text-charcoal">Materials Explorer</h1>
          <p className="text-body text-charcoal-muted mt-1">
            {selectedCpse.name}{' '}
            <span className="font-mono text-xs text-charcoal-muted bg-surface-secondary px-1.5 py-0.5 rounded-badge border border-border">
              {selectedCpse.code}
            </span>
          </p>
        </div>

        <div className="flex items-center gap-2.5 flex-wrap">
          <button
            type="button"
            onClick={fetchMaterials}
            disabled={loading || isNormalizing}
            title="Refresh material list"
            className="p-2 rounded-input border border-border bg-surface text-charcoal-muted hover:text-charcoal hover:bg-surface-secondary transition-colors disabled:opacity-50"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>

          {/* Workflow Action: Normalize Materials */}
          {unprocessedMaterials.length > 0 && (
            <button
              type="button"
              onClick={handleNormalizeMaterials}
              disabled={isNormalizing || loading}
              className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-input bg-brand text-white text-body-sm font-medium hover:bg-brand-hover transition-colors shadow-xs disabled:opacity-50"
            >
              <Sparkles className={`w-4 h-4 ${isNormalizing ? 'animate-spin' : ''}`} />
              <span>
                {isNormalizing
                  ? `Normalizing (${normalizationProgress?.current || 0}/${normalizationProgress?.total || 0})...`
                  : `Normalize Materials (${unprocessedMaterials.length})`}
              </span>
            </button>
          )}

          <button
            type="button"
            onClick={handleReviewThisCpse}
            className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-input border border-border bg-surface text-charcoal hover:bg-surface-secondary transition-colors shadow-xs text-body-sm font-medium"
          >
            <ClipboardList className="w-4 h-4" />
            <span>Review this CPSE</span>
          </button>

          <button
            type="button"
            onClick={() => setIsImportOpen(true)}
            disabled={isNormalizing}
            className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-input border border-border bg-surface text-charcoal hover:bg-surface-secondary transition-colors shadow-xs text-body-sm font-medium disabled:opacity-50"
          >
            <Upload className="w-4 h-4" />
            <span>Import Materials</span>
          </button>
        </div>
      </div>

      {/* Normalization Progress Notification */}
      {isNormalizing && normalizationProgress && (
        <div className="rounded-panel border border-brand/30 bg-brand-tint/60 p-3.5 flex items-center justify-between gap-3 text-body-sm text-charcoal shadow-xs animate-in fade-in">
          <div className="flex items-center gap-2.5">
            <RefreshCw className="w-4 h-4 text-brand animate-spin shrink-0" />
            <span className="font-semibold">Normalizing materials for {selectedCpse.name}...</span>
            <span className="font-mono text-xs bg-surface px-2 py-0.5 rounded-badge border border-border">
              {normalizationProgress.current} of {normalizationProgress.total} processed
            </span>
          </div>
          <span className="text-xs text-charcoal-muted hidden sm:inline">
            Applying deterministic engineering normalization rules
          </span>
        </div>
      )}

      {/* Normalization Status Notification */}
      {normalizationStatusMessage && (
        <div
          className={`rounded-panel p-3.5 flex items-center justify-between gap-2.5 text-body-sm shadow-xs ${
            normalizationStatusMessage.type === 'success'
              ? 'border border-semantic-same-border bg-semantic-same-bg text-semantic-same-text'
              : 'border border-semantic-potential-border bg-semantic-potential-bg text-semantic-potential-text'
          }`}
        >
          <div className="flex items-center gap-2">
            {normalizationStatusMessage.type === 'success' ? (
              <CheckCircle2 className="w-4 h-4 shrink-0" />
            ) : (
              <AlertTriangle className="w-4 h-4 shrink-0" />
            )}
            <span>{normalizationStatusMessage.message}</span>
          </div>
          <button
            type="button"
            onClick={() => setNormalizationStatusMessage(null)}
            className="text-xs font-semibold underline hover:opacity-80"
          >
            Dismiss
          </button>
        </div>
      )}


      {/* Success Notification */}
      {deleteSuccessMessage && (
        <div className="rounded-panel border border-semantic-same-border bg-semantic-same-bg p-3.5 flex items-center justify-between gap-2.5 text-body-sm text-semantic-same-text">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 shrink-0" />
            <span>{deleteSuccessMessage}</span>
          </div>
          <button
            type="button"
            onClick={() => setDeleteSuccessMessage(null)}
            className="text-xs font-semibold underline hover:opacity-80"
          >
            Dismiss
          </button>
        </div>
      )}



      {/* Main Workspace Area */}
      {loading && materials.length === 0 ? (
        <LoadingState
          message={`Loading material catalog for ${selectedCpse.name}...`}
          className="py-20"
        />
      ) : error ? (
        <ErrorState
          title="Unable to load materials"
          message={error}
          onRetry={fetchMaterials}
        />
      ) : materials.length === 0 ? (
        <EmptyState
          icon={<Package className="w-5 h-5" />}
          title="No materials imported"
          description={`No material records exist for ${selectedCpse.name}.`}
          action={
            <button
              type="button"
              onClick={() => setIsImportOpen(true)}
              className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-input bg-brand text-white text-body font-medium hover:bg-brand-hover transition-colors shadow-xs"
            >
              <Upload className="w-4 h-4" />
              <span>Import Materials</span>
            </button>
          }
        />
      ) : (
        <div className="flex-1 flex flex-col lg:flex-row gap-0 rounded-panel border border-border bg-surface overflow-hidden shadow-xs min-h-[480px]">
          {/* Master Material Table */}
          <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
            <div className="flex-1 overflow-auto">
              <table className="w-full text-left border-collapse">
                <thead className="sticky top-0 z-10 bg-surface-secondary/80 border-b border-border text-table-header text-charcoal-caption uppercase">
                  <tr>
                    <th scope="col" className="py-2.5 px-4 font-medium w-10 text-center">
                      #
                    </th>
                    <th scope="col" className="py-2.5 px-4 font-medium min-w-[150px]">
                      Material Code
                    </th>
                    <th scope="col" className="py-2.5 px-4 font-medium min-w-[280px]">
                      Source Description
                    </th>
                    <th scope="col" className="py-2.5 px-4 font-medium min-w-[100px]">
                      Category
                    </th>
                    <th scope="col" className="py-2.5 px-4 font-medium min-w-[180px]">
                      Harmonization Status
                    </th>
                    <th scope="col" className="py-2.5 px-4 font-medium min-w-[240px]">
                      Normalized Description
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border/60 text-body">
                  {materials.map((material, idx) => {
                    const isSelected = selectedMaterialId === material.id;

                    return (
                      <tr
                        key={material.id}
                        onClick={() => setSelectedMaterialId(material.id)}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter' || e.key === ' ') {
                            e.preventDefault();
                            setSelectedMaterialId(material.id);
                          }
                        }}
                        tabIndex={0}
                        className={`group cursor-pointer transition-colors outline-none focus-visible:bg-surface-secondary ${
                          isSelected
                            ? 'bg-brand-tint/60 ring-1 ring-inset ring-brand/20'
                            : 'hover:bg-surface-hover'
                        }`}
                      >
                        {/* Row Index / Indicator */}
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

                        {/* Material Code */}
                        <td className="py-3 px-4 whitespace-nowrap">
                          <span
                            className="font-mono text-body-sm font-semibold text-charcoal bg-surface-secondary/80 px-2 py-0.5 rounded-badge border border-border/60"
                            title={material.source_material_code}
                          >
                            {material.source_material_code}
                          </span>
                        </td>

                        {/* Source Description */}
                        <td className="py-3 px-4 text-charcoal leading-snug max-w-sm">
                          <span className="line-clamp-2" title={material.source_description}>
                            {material.source_description}
                          </span>
                        </td>

                        {/* Category */}
                        <td className="py-3 px-4 whitespace-nowrap">
                          {material.category ? (
                            <span className="font-mono text-xs font-medium text-charcoal-muted uppercase bg-surface-secondary px-1.5 py-0.5 rounded-badge border border-border/60">
                              {material.category}
                            </span>
                          ) : (
                            <span className="text-charcoal-disabled italic text-xs">UNKNOWN</span>
                          )}
                        </td>

                        {/* Harmonization Status */}
                        <td className="py-3 px-4 align-top">
                          <div className="space-y-1.5">
                            <Badge
                              variant={getStatusVariant(material.mapping_status)}
                              className="text-[10px] font-semibold tracking-wider"
                            >
                              {material.mapping_status || 'UNMATCHED'}
                            </Badge>
                            {material.mapping_status === 'MAPPED' && material.national_material_code ? (
                              <div>
                                <button
                                  type="button"
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    navigate('/national-materials');
                                  }}
                                  title="View in National Materials Registry"
                                  className="font-mono text-[11px] font-medium text-brand hover:underline bg-surface-secondary border border-border/80 rounded-badge px-1.5 py-0.5 inline-flex items-center gap-1 transition-colors"
                                >
                                  <span>{material.national_material_code}</span>
                                </button>
                              </div>
                            ) : null}
                          </div>
                        </td>


                        {/* Normalized Description */}
                        <td className="py-3 px-4 text-body-sm text-charcoal leading-snug max-w-sm">
                          {material.normalized_description ? (
                            <span className="line-clamp-2" title={material.normalized_description}>
                              {material.normalized_description}
                            </span>
                          ) : (
                            <span className="text-charcoal-disabled italic text-xs">UNKNOWN</span>
                          )}
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
                Total materials in workspace: <strong className="font-medium text-charcoal">{materials.length}</strong>
              </span>
              <span className="text-xs">
                {selectedMaterialId
                  ? 'Viewing selected material in inspector'
                  : 'Click any row to inspect technical attributes'}
              </span>
            </div>
          </div>

          {/* Right-Side Detail Inspector */}
          {selectedMaterialId && (
            <MaterialInspector
              materialId={selectedMaterialId}
              selectedCpseName={selectedCpse.name}
              selectedCpseCode={selectedCpse.code}
              onClose={() => setSelectedMaterialId(null)}
              onDeleteRequest={(detail) => {
                setMaterialToDelete(detail);
                setIsDeleteModalOpen(true);
              }}
            />
          )}
        </div>
      )}

      {/* Import Modal Dialog */}
      <MaterialImportModal
        isOpen={isImportOpen}
        cpseId={selectedCpse.id}
        cpseName={selectedCpse.name}
        cpseCode={selectedCpse.code}
        onClose={() => setIsImportOpen(false)}
        onImportSuccess={fetchMaterials}
      />

      {/* Delete Material Confirmation Modal */}
      <MaterialDeleteModal
        isOpen={isDeleteModalOpen}
        material={materialToDelete}
        onClose={() => {
          setIsDeleteModalOpen(false);
          setMaterialToDelete(null);
        }}
        onSuccess={handleDeleteSuccess}
      />
    </div>
  );
};



