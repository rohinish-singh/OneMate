import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Trash2,
  Plus,
  ArrowRight,
  Check,
  X,
  Loader2,
  RefreshCw,
  AlertCircle,
  CheckCircle2,
  Globe,
  StopCircle,
  AlertTriangle,
} from 'lucide-react';
import { api, ApiClientError } from '../api/client';
import type { CPSE, MaterialListItem } from '../types/api';
import { useCpse } from '../context/CpseContext';
import { LoadingState } from '../components/common/LoadingState';
import { ErrorState } from '../components/common/ErrorState';
import { EmptyState } from '../components/common/EmptyState';
import { Badge } from '../components/common/Badge';
import { CpseDeleteModal } from '../components/cpses/CpseDeleteModal';

export type GlobalMatchStatus =
  | 'IDLE'
  | 'STARTING'
  | 'RUNNING'
  | 'COMPLETED'
  | 'CANCELLED'
  | 'FAILED';

interface GlobalMatchProgress {
  totalEligible: number;
  evaluated: number;
  successful: number;
  failed: number;
  matchFailed: number;
  harmonizeFailed: number;
  activeWorkers: number;
  skipped: number;
}

interface GlobalMatchResult {
  totalEligible: number;
  evaluated: number;
  successful: number;
  failed: number;
  matchFailed: number;
  harmonizeFailed: number;
  skipped: number;
  cancelled: boolean;
  remaining: number;
}

const CONCURRENCY_LIMIT = 2;

export const CpsesPage: React.FC = () => {
  const navigate = useNavigate();
  const { selectedCpse, setSelectedCpse } = useCpse();

  const [cpses, setCpses] = useState<CPSE[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Normalization Readiness State
  const [statsLoading, setStatsLoading] = useState<boolean>(false);
  const [statsError, setStatsError] = useState<string | null>(null);
  const [totalMaterialsCount, setTotalMaterialsCount] = useState<number>(0);
  const [totalNormalizedCount, setTotalNormalizedCount] = useState<number>(0);
  const [totalUnnormalizedCount, setTotalUnnormalizedCount] = useState<number>(0);

  // Global Matching State & Lifecycle
  const [globalMatchStatus, setGlobalMatchStatus] = useState<GlobalMatchStatus>('IDLE');
  const [globalMatchError, setGlobalMatchError] = useState<string | null>(null);
  const [isGlobalMatchingRunning, setIsGlobalMatchingRunning] = useState<boolean>(false);
  const [globalMatchProgress, setGlobalMatchProgress] = useState<GlobalMatchProgress | null>(null);
  const [globalMatchResult, setGlobalMatchResult] = useState<GlobalMatchResult | null>(null);
  const cancelRequestedRef = useRef<boolean>(false);

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

  const fetchMaterialStats = useCallback(async (currentCpses: CPSE[]) => {
    if (currentCpses.length === 0) {
      setTotalMaterialsCount(0);
      setTotalNormalizedCount(0);
      setTotalUnnormalizedCount(0);
      setStatsLoading(false);
      return;
    }
    setStatsLoading(true);
    setStatsError(null);
    try {
      const lists = await Promise.all(
        currentCpses.map((c) => api.materials.listByCpse(c.id).catch(() => []))
      );
      let total = 0;
      let normalized = 0;
      let unnormalized = 0;

      for (const list of lists) {
        for (const m of list) {
          total++;
          if (
            m.mapping_status !== 'NOT PROCESSED' &&
            m.normalized_description &&
            m.normalized_description.trim().length > 0
          ) {
            normalized++;
          } else {
            unnormalized++;
          }
        }
      }

      setTotalMaterialsCount(total);
      setTotalNormalizedCount(normalized);
      setTotalUnnormalizedCount(unnormalized);
    } catch (err: unknown) {
      if (err instanceof ApiClientError) {
        setStatsError(err.message);
      } else if (err instanceof Error) {
        setStatsError(err.message);
      } else {
        setStatsError('Failed to load material readiness stats.');
      }
    } finally {
      setStatsLoading(false);
    }
  }, []);

  const fetchCpses = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.cpses.list();
      setCpses(data);
      await fetchMaterialStats(data);
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
  }, [fetchMaterialStats]);

  useEffect(() => {
    fetchCpses();
  }, [fetchCpses]);

  // Rate-Protected Match Request Executor with bounded exponential backoff
  const executeMatchWithRetry = async (materialId: string, maxRetries = 2): Promise<boolean> => {
    let attempt = 0;
    while (attempt <= maxRetries) {
      if (cancelRequestedRef.current) return false;
      try {
        await api.materials.match(materialId);
        return true;
      } catch (err: unknown) {
        attempt++;
        if (attempt > maxRetries || cancelRequestedRef.current) {
          return false;
        }

        if (err instanceof ApiClientError) {
          if ([429, 502, 503, 504].includes(err.status)) {
            const delay = Math.pow(2, attempt) * 400; // 800ms, 1600ms
            await new Promise((resolve) => setTimeout(resolve, delay));
            continue;
          } else {
            // Non-recoverable client error
            return false;
          }
        } else {
          const delay = Math.pow(2, attempt) * 400;
          await new Promise((resolve) => setTimeout(resolve, delay));
        }
      }
    }
    return false;
  };

  // Rate-Protected Harmonize Request Executor with bounded exponential backoff
  const executeHarmonizeWithRetry = async (materialId: string, maxRetries = 2): Promise<boolean> => {
    let attempt = 0;
    while (attempt <= maxRetries) {
      if (cancelRequestedRef.current) return false;
      try {
        await api.materials.harmonize(materialId);
        return true;
      } catch (err: unknown) {
        attempt++;
        if (attempt > maxRetries || cancelRequestedRef.current) {
          return false;
        }

        if (err instanceof ApiClientError) {
          if ([429, 502, 503, 504].includes(err.status)) {
            const delay = Math.pow(2, attempt) * 400; // 800ms, 1600ms
            await new Promise((resolve) => setTimeout(resolve, delay));
            continue;
          } else {
            // Non-recoverable client error
            return false;
          }
        } else {
          const delay = Math.pow(2, attempt) * 400;
          await new Promise((resolve) => setTimeout(resolve, delay));
        }
      }
    }
    return false;
  };

  // Global Matching & Harmonization Runner across ALL CPSEs
  const handleRunGlobalMatching = async () => {
    if (
      globalMatchStatus === 'STARTING' ||
      globalMatchStatus === 'RUNNING' ||
      isGlobalMatchingRunning ||
      cpses.length === 0
    ) {
      return;
    }

    setGlobalMatchStatus('STARTING');
    setIsGlobalMatchingRunning(true);
    setGlobalMatchError(null);
    setGlobalMatchResult(null);
    cancelRequestedRef.current = false;

    // Initial starting state to provide immediate feedback
    setGlobalMatchProgress({
      totalEligible: totalNormalizedCount,
      evaluated: 0,
      successful: 0,
      failed: 0,
      matchFailed: 0,
      harmonizeFailed: 0,
      activeWorkers: 0,
      skipped: 0,
    });

    try {
      // Step A: Fetch all CPSE materials
      const nestedMaterials = await Promise.all(
        cpses.map((c) => api.materials.listByCpse(c.id))
      );
      const allMaterials = nestedMaterials.flat();

      // Step B: Collect eligible normalized materials
      const eligible: MaterialListItem[] = [];
      let skippedCount = 0;

      for (const m of allMaterials) {
        if (
          m.mapping_status !== 'NOT PROCESSED' &&
          m.normalized_description &&
          m.normalized_description.trim().length > 0
        ) {
          eligible.push(m);
        } else {
          skippedCount++;
        }
      }

      if (eligible.length === 0) {
        setGlobalMatchResult({
          totalEligible: 0,
          evaluated: 0,
          successful: 0,
          failed: 0,
          matchFailed: 0,
          harmonizeFailed: 0,
          skipped: skippedCount,
          cancelled: false,
          remaining: 0,
        });
        setGlobalMatchStatus('COMPLETED');
        setGlobalMatchProgress(null);
        return;
      }

      // Step C: Setup worker queue
      let evaluatedCount = 0;
      let successCount = 0;
      let matchFailCount = 0;
      let harmFailCount = 0;
      let activeWorkers = 0;
      let nextIndex = 0;

      const workerCount = Math.min(CONCURRENCY_LIMIT, eligible.length);

      setGlobalMatchStatus('RUNNING');
      setGlobalMatchProgress({
        totalEligible: eligible.length,
        evaluated: 0,
        successful: 0,
        failed: 0,
        matchFailed: 0,
        harmonizeFailed: 0,
        activeWorkers: workerCount,
        skipped: skippedCount,
      });

      const worker = async () => {
        while (nextIndex < eligible.length && !cancelRequestedRef.current) {
          const currentIndex = nextIndex++;
          const item = eligible[currentIndex];

          activeWorkers++;
          setGlobalMatchProgress((prev) => (prev ? { ...prev, activeWorkers } : null));

          // 1. Match evaluation
          const matchSuccess = await executeMatchWithRetry(item.id, 2);

          if (!matchSuccess) {
            matchFailCount++;
          } else {
            // 2. Auto-Harmonization for eligible SAME results
            const harmSuccess = await executeHarmonizeWithRetry(item.id, 2);
            if (!harmSuccess) {
              harmFailCount++;
            } else {
              successCount++;
            }
          }

          activeWorkers--;
          evaluatedCount++;
          const failCount = matchFailCount + harmFailCount;

          setGlobalMatchProgress((prev) =>
            prev
              ? {
                  ...prev,
                  evaluated: evaluatedCount,
                  successful: successCount,
                  failed: failCount,
                  matchFailed: matchFailCount,
                  harmonizeFailed: harmFailCount,
                  activeWorkers,
                }
              : null
          );
        }
      };

      const workers = Array.from({ length: workerCount }, () => worker());
      await Promise.all(workers);

      const wasCancelled = cancelRequestedRef.current;
      const remainingCount = eligible.length - evaluatedCount;
      const totalFailed = matchFailCount + harmFailCount;

      setGlobalMatchResult({
        totalEligible: eligible.length,
        evaluated: evaluatedCount,
        successful: successCount,
        failed: totalFailed,
        matchFailed: matchFailCount,
        harmonizeFailed: harmFailCount,
        skipped: skippedCount,
        cancelled: wasCancelled,
        remaining: remainingCount,
      });

      if (wasCancelled) {
        setGlobalMatchStatus('CANCELLED');
      } else {
        setGlobalMatchStatus('COMPLETED');
      }

      // Refresh stats and CPSE materials
      fetchMaterialStats(cpses);
    } catch (err: unknown) {
      let message = 'Global matching failed.';
      if (err instanceof ApiClientError) {
        message = err.message;
      } else if (err instanceof Error) {
        message = err.message;
      }
      setGlobalMatchError(message);
      setGlobalMatchStatus('FAILED');
      setGlobalMatchProgress(null);
    } finally {
      setIsGlobalMatchingRunning(false);
    }
  };

  const handleCancelGlobalMatching = () => {
    cancelRequestedRef.current = true;
  };

  const handleDismissGlobalMatchError = () => {
    setGlobalMatchError(null);
    setGlobalMatchStatus('IDLE');
  };

  const handleDismissGlobalMatchResult = () => {
    setGlobalMatchResult(null);
    setGlobalMatchStatus('IDLE');
  };



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
        const updated = [...existing, newCpse].sort((a, b) => a.name.localeCompare(b.name));
        fetchMaterialStats(updated);
        return updated;
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
    setCpses((prev) => {
      const updated = prev.filter((c) => c.id !== deletedId);
      fetchMaterialStats(updated);
      return updated;
    });
    if (selectedCpse?.id === deletedId) {
      setSelectedCpse(null);
    }
    setSuccessMessage(
      deleted
        ? `Enterprise ${deleted.name} (${deleted.code}) deleted successfully.`
        : 'Enterprise workspace deleted successfully.'
    );
  };

  const isAllNormalized = totalMaterialsCount > 0 && totalUnnormalizedCount === 0;
  const isGlobalMatchingDisabled =
    !isAllNormalized ||
    globalMatchStatus === 'STARTING' ||
    globalMatchStatus === 'RUNNING' ||
    cpses.length === 0;

  return (
    <div className="p-4 sm:p-6 lg:p-8 max-w-7xl w-full mx-auto space-y-6">
      {/* Header with Global Matching and Actions */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
        <div>
          <h1 className="text-page-title text-charcoal">Central Public Sector Enterprises</h1>
          <div className="flex items-center gap-3 mt-1 flex-wrap">
            <p className="text-body text-charcoal-muted">
              {cpses.length} {cpses.length === 1 ? 'enterprise' : 'enterprises'} registered
            </p>
            {cpses.length > 0 && (
              <>
                <span className="text-charcoal-disabled">•</span>
                {statsLoading ? (
                  <span className="text-xs text-charcoal-muted flex items-center gap-1">
                    <Loader2 className="w-3 h-3 animate-spin" /> Checking normalization status...
                  </span>
                ) : statsError ? (
                  <span className="text-xs text-semantic-diff-text flex items-center gap-1">
                    <AlertCircle className="w-3.5 h-3.5" /> {statsError}
                  </span>
                ) : totalMaterialsCount === 0 ? (
                  <span className="text-xs text-charcoal-muted">0 source materials</span>
                ) : isAllNormalized ? (
                  <span className="inline-flex items-center gap-1 text-xs font-semibold text-semantic-same-text bg-semantic-same-bg border border-semantic-same-border px-2 py-0.5 rounded-badge">
                    <CheckCircle2 className="w-3.5 h-3.5" /> All {totalMaterialsCount} materials ready
                  </span>
                ) : (
                  <span className="inline-flex items-center gap-1 text-xs font-semibold text-semantic-potential-text bg-semantic-potential-bg border border-semantic-potential-border px-2 py-0.5 rounded-badge">
                    <AlertTriangle className="w-3.5 h-3.5" /> Normalization: {totalNormalizedCount} / {totalMaterialsCount} materials ready
                  </span>
                )}
              </>
            )}
          </div>
        </div>

        <div className="flex items-center gap-3 flex-wrap">
          {/* Primary Global Matching Trigger */}
          <div className="flex flex-col items-end">
            <button
              type="button"
              onClick={handleRunGlobalMatching}
              disabled={isGlobalMatchingDisabled}
              title={
                !isAllNormalized
                  ? 'Normalize all CPSE materials before matching.'
                  : 'Find matches across all registered enterprises'
              }
              className="inline-flex items-center gap-2 px-4 py-2 rounded-input bg-brand text-white text-body font-medium hover:bg-brand-hover transition-colors disabled:opacity-50 shadow-xs"
            >
              <Globe
                className={`w-4 h-4 ${
                  globalMatchStatus === 'STARTING' || globalMatchStatus === 'RUNNING'
                    ? 'animate-spin'
                    : ''
                }`}
              />
              <span>
                {globalMatchStatus === 'STARTING'
                  ? 'Starting Matching...'
                  : globalMatchStatus === 'RUNNING'
                  ? 'Matching in Progress...'
                  : 'Find Matches Across All CPSEs'}
              </span>
            </button>
            {!isAllNormalized && totalMaterialsCount > 0 && !isGlobalMatchingRunning && (
              <span className="text-[11px] text-semantic-diff-text font-medium mt-1">
                Normalize all CPSE materials before matching.
              </span>
            )}
          </div>

          <button
            type="button"
            onClick={fetchCpses}
            disabled={
              loading ||
              statsLoading ||
              globalMatchStatus === 'STARTING' ||
              globalMatchStatus === 'RUNNING'
            }
            title="Refresh list and stats"
            className="p-2 rounded-input border border-border bg-surface text-charcoal-muted hover:text-charcoal hover:bg-surface-secondary transition-colors disabled:opacity-50"
          >
            <RefreshCw className={`w-4 h-4 ${loading || statsLoading ? 'animate-spin' : ''}`} />
          </button>

          <button
            type="button"
            onClick={handleOpenCreateModal}
            className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-input bg-surface border border-border text-charcoal text-body font-medium hover:bg-surface-secondary transition-colors shadow-xs"
          >
            <Plus className="w-4 h-4" />
            <span>Add CPSE</span>
          </button>
        </div>
      </div>

      {/* Global Matching Error Banner */}
      {globalMatchStatus === 'FAILED' && globalMatchError && (
        <div className="rounded-panel border border-semantic-diff-border bg-semantic-diff-bg p-4 flex items-start justify-between gap-3 text-body-sm text-semantic-diff-text animate-in fade-in">
          <div className="flex items-start gap-2.5">
            <AlertCircle className="w-5 h-5 shrink-0 mt-0.5 text-semantic-diff-text" />
            <div>
              <p className="font-semibold text-semantic-diff-text">Global matching failed</p>
              <p className="text-body-xs opacity-90 mt-0.5">{globalMatchError}</p>
            </div>
          </div>
          <button
            type="button"
            onClick={handleDismissGlobalMatchError}
            className="text-xs font-semibold text-semantic-diff-text hover:underline shrink-0"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Global Matching Real-Time Progress Banner */}
      {(globalMatchStatus === 'STARTING' || globalMatchStatus === 'RUNNING') && globalMatchProgress && (
        <div className="rounded-panel border border-brand/30 bg-brand-tint/60 p-4 space-y-3 shadow-xs animate-in fade-in">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              <RefreshCw className="w-4 h-4 text-brand animate-spin" />
              <span className="text-body-sm font-semibold text-charcoal">
                {globalMatchStatus === 'STARTING'
                  ? 'Starting Global Matching Across CPSEs'
                  : 'Evaluating and Auto-Harmonizing Materials'}
              </span>
              <span className="font-mono text-xs bg-surface px-2 py-0.5 rounded-badge border border-border">
                {globalMatchStatus === 'STARTING'
                  ? 'Preparing worker queue...'
                  : `${globalMatchProgress.evaluated} of ${globalMatchProgress.totalEligible} evaluated`}
              </span>
            </div>
            <div className="flex items-center gap-3">
              <span className="text-xs text-charcoal-muted">
                Workers active: <strong>{globalMatchProgress.activeWorkers}</strong> (max {CONCURRENCY_LIMIT})
              </span>
              <button
                type="button"
                onClick={handleCancelGlobalMatching}
                className="inline-flex items-center gap-1 px-2.5 py-1 rounded-input border border-semantic-diff-border bg-surface text-semantic-diff-text text-xs font-semibold hover:bg-semantic-diff-bg transition-colors"
              >
                <StopCircle className="w-3.5 h-3.5" />
                <span>Cancel</span>
              </button>
            </div>
          </div>
          {/* Progress bar */}
          <div className="w-full h-2 bg-surface rounded-full overflow-hidden border border-border/60">
            <div
              className="h-full bg-brand transition-all duration-300 rounded-full"
              style={{
                width: `${
                  globalMatchProgress.totalEligible > 0
                    ? Math.round((globalMatchProgress.evaluated / globalMatchProgress.totalEligible) * 100)
                    : 0
                }%`,
              }}
            />
          </div>
        </div>
      )}

      {/* Global Matching Completion / Result Summary */}
      {globalMatchResult && (globalMatchStatus === 'COMPLETED' || globalMatchStatus === 'CANCELLED') && (
        <div className="rounded-panel border border-border bg-surface p-4 shadow-xs space-y-2">
          <div className="flex items-center justify-between gap-2 border-b border-border/60 pb-2">
            <div className="flex items-center gap-2">
              {globalMatchResult.cancelled ? (
                <AlertTriangle className="w-4 h-4 text-semantic-potential-text shrink-0" />
              ) : (
                <CheckCircle2 className="w-4 h-4 text-semantic-same-text shrink-0" />
              )}
              <span className="text-body-sm font-semibold text-charcoal">
                {globalMatchResult.cancelled ? 'Matching Cancelled' : 'Global Matching & Harmonization Complete'}
              </span>
            </div>
            <button
              type="button"
              onClick={handleDismissGlobalMatchResult}
              className="text-xs font-semibold text-charcoal-muted hover:text-charcoal underline"
            >
              Dismiss
            </button>
          </div>
          <div className="flex flex-wrap items-center gap-3 text-xs text-charcoal-muted pt-1">
            <span>Evaluated: <strong className="text-charcoal">{globalMatchResult.evaluated}</strong></span>
            <span>•</span>
            <span>Successful: <strong className="text-semantic-same-text">{globalMatchResult.successful}</strong></span>
            {globalMatchResult.failed > 0 && (
              <>
                <span>•</span>
                <span>
                  Failed: <strong className="text-semantic-diff-text">{globalMatchResult.failed}</strong>
                  {globalMatchResult.matchFailed > 0 && ` (${globalMatchResult.matchFailed} match)`}
                  {globalMatchResult.harmonizeFailed > 0 && ` (${globalMatchResult.harmonizeFailed} harmonize)`}
                </span>
              </>
            )}
            {globalMatchResult.skipped > 0 && (
              <>
                <span>•</span>
                <span>Skipped: <strong className="text-charcoal">{globalMatchResult.skipped} not normalized</strong></span>
              </>
            )}
            {globalMatchResult.cancelled && (
              <>
                <span>•</span>
                <span>Remaining: <strong className="text-charcoal">{globalMatchResult.remaining}</strong></span>
              </>
            )}
          </div>
        </div>
      )}


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


