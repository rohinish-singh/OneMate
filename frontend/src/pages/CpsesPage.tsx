import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Trash2, Plus, ArrowRight, Check, X, Loader2, RefreshCw, AlertCircle, CheckCircle2 } from 'lucide-react';
import { api, ApiClientError } from '../api/client';
import type { CPSE } from '../types/api';
import { useCpse } from '../context/CpseContext';
import { LoadingState } from '../components/common/LoadingState';
import { ErrorState } from '../components/common/ErrorState';
import { EmptyState } from '../components/common/EmptyState';
import { Badge } from '../components/common/Badge';
import { CpseDeleteModal } from '../components/cpses/CpseDeleteModal';

export const CpsesPage: React.FC = () => {
  const navigate = useNavigate();
  const { selectedCpse, setSelectedCpse } = useCpse();

  const [cpses, setCpses] = useState<CPSE[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Create Modal State
  const [isModalOpen, setIsModalOpen] = useState<boolean>(false);
  const [createCode, setCreateCode] = useState<string>('');
  const [createName, setCreateName] = useState<string>('');
  const [createLoading, setCreateLoading] = useState<boolean>(false);
  const [createError, setCreateError] = useState<string | null>(null);

  // Delete Modal State
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState<boolean>(false);
  const [deleteModalCpse, setDeleteModalCpse] = useState<CPSE | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const fetchCpses = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.cpses.list();
      setCpses(data);
    } catch (err: unknown) {
      if (err instanceof ApiClientError) {
        setError(err.message);
      } else if (err instanceof Error) {
        setError(err.message);
      } else {
        setError('Unable to load CPSE directory from backend.');
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchCpses();
  }, [fetchCpses]);

  const handleOpenCreateModal = () => {
    setCreateCode('');
    setCreateName('');
    setCreateError(null);
    setIsModalOpen(true);
  };

  const handleCloseCreateModal = () => {
    if (createLoading) return;
    setIsModalOpen(false);
    setCreateError(null);
  };

  const handleCreateCpse = async (e: React.FormEvent) => {
    e.preventDefault();
    const trimmedCode = createCode.trim();
    const trimmedName = createName.trim();

    if (!trimmedCode || !trimmedName) {
      setCreateError('Both enterprise code and enterprise name are required.');
      return;
    }

    setCreateLoading(true);
    setCreateError(null);

    try {
      const newCpse = await api.cpses.create({
        code: trimmedCode,
        name: trimmedName,
      });

      // Update state: close modal, refresh list, select newly created CPSE
      setIsModalOpen(false);
      setCreateCode('');
      setCreateName('');
      setCpses((prev) => {
        const existing = prev.filter((c) => c.id !== newCpse.id);
        return [...existing, newCpse].sort((a, b) => a.name.localeCompare(b.name));
      });
      setSelectedCpse(newCpse);
    } catch (err: unknown) {
      if (err instanceof ApiClientError) {
        setCreateError(err.message);
      } else if (err instanceof Error) {
        setCreateError(err.message);
      } else {
        setCreateError('An unexpected error occurred while creating CPSE.');
      }
    } finally {
      setCreateLoading(false);
    }
  };

  const handleSelectCpse = (cpse: CPSE) => {
    setSelectedCpse(cpse);
  };

  const handleNavigateToMaterials = (cpse: CPSE, e?: React.MouseEvent) => {
    e?.stopPropagation();
    setSelectedCpse(cpse);
    navigate('/materials');
  };

  const formatDate = (isoString: string) => {
    try {
      const date = new Date(isoString);
      return date.toLocaleDateString(undefined, {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
      });
    } catch {
      return isoString;
    }
  };

  const handleDeleteSuccess = (deletedId: string) => {
    const deleted = cpses.find((c) => c.id === deletedId);
    setCpses((prev) => prev.filter((c) => c.id !== deletedId));
    if (selectedCpse?.id === deletedId) {
      setSelectedCpse(null);
    }
    setSuccessMessage(
      deleted
        ? `Enterprise ${deleted.name} (${deleted.code}) deleted successfully.`
        : 'Enterprise workspace deleted successfully.'
    );
  };

  return (
    <div className="p-4 sm:p-6 lg:p-8 max-w-7xl w-full mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-page-title text-charcoal">Central Public Sector Enterprises</h1>
          <p className="text-body text-charcoal-muted mt-1">
            Registered enterprises
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={fetchCpses}
            disabled={loading}
            title="Refresh list"
            className="p-2 rounded-input border border-border bg-surface text-charcoal-muted hover:text-charcoal hover:bg-surface-secondary transition-colors disabled:opacity-50"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
          <button
            type="button"
            onClick={handleOpenCreateModal}
            className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-input bg-brand text-white text-body font-medium hover:bg-brand-hover transition-colors shadow-xs"
          >
            <Plus className="w-4 h-4" />
            <span>Add CPSE</span>
          </button>
        </div>
      </div>

      {/* Success Notification */}
      {successMessage && (
        <div className="rounded-panel border border-semantic-same-border bg-semantic-same-bg p-3.5 flex items-center justify-between gap-2.5 text-body-sm text-semantic-same-text">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 shrink-0" />
            <span>{successMessage}</span>
          </div>
          <button
            type="button"
            onClick={() => setSuccessMessage(null)}
            className="text-xs font-semibold underline hover:opacity-80"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Main Content Area */}
      {loading && cpses.length === 0 ? (
        <LoadingState message="Loading CPSE directory..." className="py-16" />
      ) : error ? (
        <ErrorState
          title="Unable to load CPSE directory"
          message={error}
          onRetry={fetchCpses}
        />
      ) : cpses.length === 0 ? (
        <EmptyState
          icon={<Trash2 className="w-5 h-5" />}
          title="No CPSEs registered"
          description="No enterprises are currently registered. Register your first CPSE to begin."
          action={
            <button
              type="button"
              onClick={handleOpenCreateModal}
              className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-input bg-brand text-white text-body font-medium hover:bg-brand-hover transition-colors shadow-xs"
            >
              <Plus className="w-4 h-4" />
              <span>Add CPSE</span>
            </button>
          }
        />
      ) : (
        <div className="rounded-panel border border-border bg-surface overflow-hidden shadow-xs">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-surface-secondary/70 border-b border-border text-table-header text-charcoal-caption uppercase">
                  <th scope="col" className="py-2.5 px-4 font-medium w-8 text-center">
                    #
                  </th>
                  <th scope="col" className="py-2.5 px-4 font-medium min-w-[240px]">
                    Enterprise Name
                  </th>
                  <th scope="col" className="py-2.5 px-4 font-medium min-w-[140px]">
                    Enterprise Code
                  </th>
                  <th scope="col" className="py-2.5 px-4 font-medium min-w-[130px]">
                    Registered
                  </th>
                  <th scope="col" className="py-2.5 px-4 font-medium text-right min-w-[200px]">
                    Action
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border/60 text-body">
                {cpses.map((cpse, idx) => {
                  const isSelected = selectedCpse?.id === cpse.id;

                  return (
                    <tr
                      key={cpse.id}
                      onClick={() => handleSelectCpse(cpse)}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter' || e.key === ' ') {
                          e.preventDefault();
                          handleSelectCpse(cpse);
                        }
                      }}
                      tabIndex={0}
                      className={`group cursor-pointer transition-colors outline-none focus-visible:bg-surface-secondary ${
                        isSelected
                          ? 'bg-brand-tint/60 ring-1 ring-inset ring-brand/20'
                          : 'hover:bg-surface-hover'
                      }`}
                    >
                      {/* Selection indicator column */}
                      <td className="py-3 px-4 text-center">
                        {isSelected ? (
                          <span
                            className="inline-flex items-center justify-center w-4 h-4 rounded-full bg-brand text-white"
                            title="Currently Selected CPSE"
                          >
                            <Check className="w-2.5 h-2.5 stroke-[3]" />
                          </span>
                        ) : (
                          <span className="text-body-sm text-charcoal-caption group-hover:hidden">
                            {idx + 1}
                          </span>
                        )}
                        {!isSelected && (
                          <span className="hidden group-hover:inline-flex items-center justify-center w-4 h-4 rounded-full border border-border/80 text-transparent">
                            •
                          </span>
                        )}
                      </td>

                      {/* Name */}
                      <td className="py-3 px-4">
                        <div className="flex items-center gap-2 max-w-md">
                          <span className="font-semibold text-charcoal truncate" title={cpse.name}>
                            {cpse.name}
                          </span>
                          {isSelected && (
                            <Badge variant="brand" className="text-[10px] py-0 px-1.5 shrink-0">
                              Selected
                            </Badge>
                          )}
                        </div>
                      </td>

                      {/* Code */}
                      <td className="py-3 px-4 whitespace-nowrap">
                        <span className="font-mono text-body-sm font-medium text-charcoal bg-surface-secondary/80 px-2 py-0.5 rounded-badge border border-border/60">
                          {cpse.code}
                        </span>
                      </td>

                      {/* Created date */}
                      <td className="py-3 px-4 text-charcoal-caption text-body-sm whitespace-nowrap">
                        {formatDate(cpse.created_at)}
                      </td>

                      {/* Action */}
                      <td className="py-3 px-4 text-right whitespace-nowrap">
                        {isSelected ? (
                          <div className="inline-flex items-center gap-2">
                            <button
                              type="button"
                              onClick={(e) => {
                                e.stopPropagation();
                                setDeleteModalCpse(cpse);
                                setIsDeleteModalOpen(true);
                              }}
                              className="inline-flex items-center gap-1 px-2.5 py-1 rounded-input border border-border text-charcoal-muted hover:text-semantic-diff-text hover:border-semantic-diff-border hover:bg-semantic-diff-bg text-body-sm font-medium transition-colors"
                              title="Delete enterprise and source materials"
                            >
                              <Trash2 className="w-3.5 h-3.5" />
                              <span>Delete</span>
                            </button>
                            <button
                              type="button"
                              onClick={(e) => handleNavigateToMaterials(cpse, e)}
                              className="inline-flex items-center gap-1.5 px-3 py-1 rounded-input bg-brand text-white text-body-sm font-medium hover:bg-brand-hover transition-colors shadow-xs"
                            >
                              <span>Open Materials</span>
                              <ArrowRight className="w-3.5 h-3.5" />
                            </button>
                          </div>
                        ) : (
                          <button
                            type="button"
                            onClick={(e) => {
                              e.stopPropagation();
                              handleSelectCpse(cpse);
                            }}
                            className="inline-flex items-center gap-1 px-2.5 py-1 rounded-input border border-border text-charcoal-muted hover:text-charcoal hover:bg-surface-secondary text-body-sm font-medium transition-colors"
                          >
                            <span>Select</span>
                          </button>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          <div className="px-4 py-3 bg-surface-secondary/30 border-t border-border flex items-center justify-between text-body-sm text-charcoal-caption">
            <span>
              Total CPSEs registered: <strong className="font-medium text-charcoal">{cpses.length}</strong>
            </span>
            <span className="text-xs">
              Click any row to select enterprise workspace
            </span>
          </div>
        </div>
      )}

      {/* Add CPSE Modal Dialog */}
      {isModalOpen && (
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="modal-title"
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-charcoal/40 overflow-y-auto"
          onClick={handleCloseCreateModal}
        >
          <div
            className="w-full max-w-md max-h-[90vh] flex flex-col bg-surface rounded-panel border border-border shadow-xl p-5 sm:p-6 space-y-4 sm:space-y-5 overflow-y-auto"
            onClick={(e) => e.stopPropagation()}
          >

            {/* Modal Header */}
            <div className="flex items-start justify-between gap-4">
              <div>
                <h3 id="modal-title" className="text-section-title text-charcoal">
                  Register New CPSE
                </h3>
                <p className="text-body-sm text-charcoal-muted mt-0.5">
                  Add a central public sector enterprise to the catalog harmonization system.
                </p>
              </div>
              <button
                type="button"
                onClick={handleCloseCreateModal}
                disabled={createLoading}
                className="p-1 rounded-input text-charcoal-caption hover:text-charcoal hover:bg-surface-secondary transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Error Display inside modal */}
            {createError && (
              <div className="rounded-panel border border-semantic-diff-border bg-semantic-diff-bg p-3.5 flex items-start gap-2.5 text-body-sm text-semantic-diff-text">
                <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
                <div className="flex-1">{createError}</div>
              </div>
            )}

            {/* Form */}
            <form onSubmit={handleCreateCpse} className="space-y-4">
              <div>
                <label
                  htmlFor="cpse-code"
                  className="block text-body-sm font-medium text-charcoal mb-1"
                >
                  Enterprise Code <span className="text-semantic-diff-text">*</span>
                </label>
                <input
                  id="cpse-code"
                  type="text"
                  required
                  disabled={createLoading}
                  value={createCode}
                  onChange={(e) => setCreateCode(e.target.value)}
                  placeholder="e.g. CPCL-DEMO"
                  className="w-full px-3 py-2 rounded-input border border-border bg-surface text-charcoal font-mono text-body placeholder:text-charcoal-disabled focus:border-border-strong focus:outline-none transition-colors"
                />
                <p className="text-xs text-charcoal-caption mt-1">
                  Unique identifier used for tenant isolation and material code prefixing.
                </p>
              </div>

              <div>
                <label
                  htmlFor="cpse-name"
                  className="block text-body-sm font-medium text-charcoal mb-1"
                >
                  Enterprise Name <span className="text-semantic-diff-text">*</span>
                </label>
                <input
                  id="cpse-name"
                  type="text"
                  required
                  disabled={createLoading}
                  value={createName}
                  onChange={(e) => setCreateName(e.target.value)}
                  placeholder="e.g. Chennai Petroleum Corporation Limited"
                  className="w-full px-3 py-2 rounded-input border border-border bg-surface text-charcoal text-body placeholder:text-charcoal-disabled focus:border-border-strong focus:outline-none transition-colors"
                />
                <p className="text-xs text-charcoal-caption mt-1">
                  Official name of the central public sector enterprise.
                </p>
              </div>

              {/* Modal Footer */}
              <div className="pt-2 flex items-center justify-end gap-3 border-t border-border/80">
                <button
                  type="button"
                  onClick={handleCloseCreateModal}
                  disabled={createLoading}
                  className="px-3.5 py-2 rounded-input border border-border text-charcoal-muted hover:text-charcoal hover:bg-surface-secondary text-body font-medium transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={createLoading}
                  className="inline-flex items-center gap-1.5 px-4 py-2 rounded-input bg-brand text-white text-body font-medium hover:bg-brand-hover transition-colors disabled:opacity-60 shadow-xs"
                >
                  {createLoading && <Loader2 className="w-4 h-4 animate-spin" />}
                  <span>{createLoading ? 'Registering...' : 'Register CPSE'}</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Delete CPSE Confirmation Modal */}
      <CpseDeleteModal
        isOpen={isDeleteModalOpen}
        cpse={deleteModalCpse}
        onClose={() => {
          setIsDeleteModalOpen(false);
          setDeleteModalCpse(null);
        }}
        onSuccess={handleDeleteSuccess}
      />
    </div>
  );
};


