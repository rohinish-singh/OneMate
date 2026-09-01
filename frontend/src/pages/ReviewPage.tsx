import React, { useState, useEffect, useCallback } from 'react';
import { useLocation } from 'react-router-dom';
import {
  CheckSquare,
  KeyRound,
  RefreshCw,
  Search,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Layers,
  ChevronDown,
  ChevronRight,
  FileCode,
  Lock,
  Unlock,
  AlertCircle,
  Building2,
  ArrowLeft,
} from 'lucide-react';

import { api, ApiClientError } from '../api/client';
import type {
  ReviewQueueItem,
  MaterialDetailResponse,
  ReviewActionType,
  ReviewActionResponse,
  CPSE,
} from '../types/api';
import { useCpse } from '../context/CpseContext';
import { LoadingState } from '../components/common/LoadingState';
import { ErrorState } from '../components/common/ErrorState';
import { EmptyState } from '../components/common/EmptyState';
import { Badge, type BadgeVariant } from '../components/common/Badge';
import { AttributeComparisonTable } from '../components/matching/AttributeComparisonTable';
import { ReviewActionModal } from '../components/review/ReviewActionModal';

export const ReviewPage: React.FC = () => {
  const location = useLocation();
  const cpseScopeId = new URLSearchParams(location.search).get('cpseId');
  const { selectedCpse } = useCpse();
  const [scopedCpse, setScopedCpse] = useState<CPSE | null>(null);

  // Reviewer Authentication State
  const [reviewerToken, setReviewerToken] = useState<string>('');
  const [tokenInput, setTokenInput] = useState<string>('');
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(false);
  const [authLoading, setAuthLoading] = useState<boolean>(false);
  const [authError, setAuthError] = useState<string | null>(null);

  // Queue state
  const [queue, setQueue] = useState<ReviewQueueItem[]>([]);
  const [cpseScopeMaterialIds, setCpseScopeMaterialIds] = useState<string[]>([]);
  const [queueLoading, setQueueLoading] = useState<boolean>(false);
  const [queueError, setQueueError] = useState<string | null>(null);
  const [queueSearch, setQueueSearch] = useState<string>('');
  type QueueCategoryFilter = 'ALL' | 'POTENTIAL' | 'DIFFERENT' | 'MAPPED';
  const [classificationFilter, setClassificationFilter] = useState<QueueCategoryFilter>('ALL');

  // Selected recommendation & details
  const [selectedItem, setSelectedItem] = useState<ReviewQueueItem | null>(null);
  const [sourceDetail, setSourceDetail] = useState<MaterialDetailResponse | null>(null);
  const [candidateDetail, setCandidateDetail] = useState<MaterialDetailResponse | null>(null);
  const [detailsLoading, setDetailsLoading] = useState<boolean>(false);
  const [detailsError, setDetailsError] = useState<string | null>(null);

  // Action Modal State
  const [modalAction, setModalAction] = useState<ReviewActionType | null>(null);
  const [actionSuccessMessage, setActionSuccessMessage] = useState<string | null>(null);

  // Collapsible Raw Payloads
  const [showRawComparison, setShowRawComparison] = useState<boolean>(false);

  // Identify scoped CPSE name and code
  useEffect(() => {
    if (!cpseScopeId) {
      setScopedCpse(null);
      return;
    }

    if (selectedCpse && selectedCpse.id === cpseScopeId) {
      setScopedCpse(selectedCpse);
      return;
    }

    let isCancelled = false;
    api.cpses
      .list()
      .then((cpses) => {
        if (!isCancelled) {
          const found = cpses.find((c) => c.id === cpseScopeId);
          setScopedCpse(found || null);
        }
      })
      .catch(() => {
        if (!isCancelled) setScopedCpse(null);
      });

    return () => {
      isCancelled = true;
    };
  }, [cpseScopeId, selectedCpse]);

  // 1. Fetch Review Queue
  const fetchQueue = useCallback(async (token: string) => {
    if (!token.trim()) return;
    setQueueLoading(true);
    setQueueError(null);

    try {
      const data = await api.reviews.getQueue(token.trim());
      setQueue(data.queue);
      setIsAuthenticated(true);
      setReviewerToken(token.trim());
      setAuthError(null);
    } catch (err: unknown) {
      if (err instanceof ApiClientError) {
        if (err.status === 401) {
          setIsAuthenticated(false);
          setAuthError(err.message || 'Unauthorized: Invalid reviewer access token.');
        } else {
          setQueueError(err.message);
        }
      } else if (err instanceof Error) {
        setQueueError(err.message);
      } else {
        setQueueError('Failed to fetch review queue.');
      }
    } finally {
      setQueueLoading(false);
      setAuthLoading(false);
    }
  }, []);

  // Handle Token Submission
  const handleAuthenticate = (e: React.FormEvent) => {
    e.preventDefault();
    if (!tokenInput.trim()) {
      setAuthError('Please enter a reviewer token.');
      return;
    }
    setAuthLoading(true);
    setAuthError(null);
    fetchQueue(tokenInput.trim());
  };

  const handleLogout = () => {
    setIsAuthenticated(false);
    setReviewerToken('');
    setTokenInput('');
    setQueue([]);
    setSelectedItem(null);
    setSourceDetail(null);
    setCandidateDetail(null);
    sessionStorage.removeItem('onemate_reviewer_token');
  };

  useEffect(() => {
    if (!cpseScopeId) {
      setCpseScopeMaterialIds([]);
      return;
    }

    let isCancelled = false;
    api.materials
      .listByCpse(cpseScopeId)
      .then((materials) => {
        if (!isCancelled) {
          setCpseScopeMaterialIds(materials.map((item) => item.id));
        }
      })
      .catch(() => {
        if (!isCancelled) {
          setCpseScopeMaterialIds([]);
        }
      });

    return () => {
      isCancelled = true;
    };
  }, [cpseScopeId]);

  useEffect(() => {
    if (reviewerToken) {
      sessionStorage.setItem('onemate_reviewer_token', reviewerToken);
    }
  }, [reviewerToken]);

  // 2. Fetch details when selectedItem changes
  useEffect(() => {
    if (!selectedItem) {
      setSourceDetail(null);
      setCandidateDetail(null);
      setDetailsError(null);
      return;
    }

    let isCancelled = false;
    setDetailsLoading(true);
    setDetailsError(null);

    Promise.all([
      api.materials.get(selectedItem.source_material_id),
      api.materials.get(selectedItem.candidate_material_id),
    ])
      .then(([src, cand]) => {
        if (!isCancelled) {
          setSourceDetail(src);
          setCandidateDetail(cand);
        }
      })
      .catch((err: unknown) => {
        if (!isCancelled) {
          if (err instanceof ApiClientError) {
            setDetailsError(err.message);
          } else if (err instanceof Error) {
            setDetailsError(err.message);
          } else {
            setDetailsError('Unable to load specifications for comparison.');
          }
        }
      })
      .finally(() => {
        if (!isCancelled) setDetailsLoading(false);
      });

    return () => {
      isCancelled = true;
    };
  }, [selectedItem]);

  // Handle successful action execution
  const handleActionSuccess = (res: ReviewActionResponse) => {
    setActionSuccessMessage(`Action "${res.action}" successfully recorded by backend.`);
    setIsAuthenticated(true);
    // Refresh queue
    fetchQueue(reviewerToken);
    // Clear selection
    setSelectedItem(null);
    setSourceDetail(null);
    setCandidateDetail(null);
  };

  const getClassificationBadgeVariant = (classification: string): BadgeVariant => {
    switch (classification.toUpperCase()) {
      case 'SAME':
      case 'MAPPED':
        return 'same';
      case 'POTENTIALLY_EQUIVALENT':
      case 'POTENTIAL':
      case 'NEEDS REVIEW':
        return 'potential';
      case 'DIFFERENT':
        return 'diff';
      default:
        return 'neutral';
    }
  };

  // Filter Queue Items
  const filteredQueue = queue.filter((item) => {
    const inCpseScope =
      cpseScopeMaterialIds.length === 0 ||
      cpseScopeMaterialIds.includes(item.source_material_id) ||
      cpseScopeMaterialIds.includes(item.candidate_material_id);

    let matchesFilter = true;
    if (classificationFilter === 'POTENTIAL') {
      matchesFilter = item.classification === 'POTENTIALLY_EQUIVALENT' && item.mapping_status !== 'MAPPED';
    } else if (classificationFilter === 'DIFFERENT') {
      matchesFilter = item.classification === 'DIFFERENT' && item.mapping_status !== 'MAPPED';
    } else if (classificationFilter === 'MAPPED') {
      matchesFilter = item.mapping_status === 'MAPPED';
    } else if (classificationFilter === 'ALL') {
      matchesFilter = true;
    }

    const q = queueSearch.toLowerCase().trim();
    if (!q) return inCpseScope && matchesFilter;

    return (
      inCpseScope &&
      matchesFilter &&
      (item.recommendation_id.toLowerCase().includes(q) ||
        item.source_material_id.toLowerCase().includes(q) ||
        item.candidate_material_id.toLowerCase().includes(q) ||
        (item.national_material_code && item.national_material_code.toLowerCase().includes(q)) ||
        (item.mapping_basis && item.mapping_basis.toLowerCase().includes(q)) ||
        (item.explanation && item.explanation.toLowerCase().includes(q)))
    );
  });

  return (
    <div className="px-4 py-5 sm:px-6 sm:py-6 lg:px-8 lg:py-6 w-full space-y-6 flex flex-col min-h-[calc(100vh-4rem)]">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 shrink-0">
        <div>
          <h1 className="text-page-title text-charcoal">Review Queue</h1>
          {scopedCpse ? (
            <div className="mt-1 space-y-0.5">
              <div className="flex items-center gap-1.5 flex-wrap">
                <span className="text-body font-semibold text-charcoal">
                  {scopedCpse.name}
                </span>
                <span className="text-charcoal-muted font-medium">·</span>
                <span className="font-mono text-xs font-semibold text-charcoal bg-surface-secondary px-1.5 py-0.5 rounded-badge border border-border">
                  {scopedCpse.code}
                </span>
              </div>
              <p className="text-xs text-charcoal-caption">
                Review queue scoped to this CPSE
              </p>
            </div>
          ) : (
            <div className="mt-1 space-y-0.5">
              <div className="text-body font-semibold text-charcoal">
                All CPSEs
              </div>
              <p className="text-xs text-charcoal-caption">
                Review queue across all enterprises
              </p>
            </div>
          )}
        </div>


        {/* Reviewer Authentication Strip */}
        <div className="flex items-center gap-2.5">
          {isAuthenticated ? (
            <div className="flex items-center gap-2 bg-surface px-3 py-1.5 rounded-input border border-border shadow-xs text-body-sm">
              <span className="w-2 h-2 rounded-full bg-semantic-same-text shrink-0" />
              <span className="text-charcoal font-medium">Reviewer Active</span>
              <button
                type="button"
                onClick={handleLogout}
                className="text-xs text-charcoal-muted hover:text-charcoal underline ml-1 transition-colors"
              >
                Change
              </button>
            </div>
          ) : (
            <form onSubmit={handleAuthenticate} className="flex items-center gap-2">
              <div className="relative">
                <KeyRound className="w-3.5 h-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-charcoal-caption" />
                <input
                  type="password"
                  value={tokenInput}
                  onChange={(e) => setTokenInput(e.target.value)}
                  placeholder="Reviewer Token..."
                  disabled={authLoading}
                  className="pl-8 pr-3 py-1.5 text-body-sm font-mono rounded-input border border-border bg-surface text-charcoal placeholder:text-charcoal-disabled focus:border-border-strong focus:outline-none transition-colors w-44"
                />
              </div>
              <button
                type="submit"
                disabled={authLoading || !tokenInput.trim()}
                className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-input bg-brand text-white text-body-sm font-medium hover:bg-brand-hover transition-colors disabled:opacity-50 shadow-xs"
              >
                <Unlock className="w-3.5 h-3.5" />
                <span>{authLoading ? 'Verifying...' : 'Unlock'}</span>
              </button>
            </form>
          )}

          {isAuthenticated && (
            <button
              type="button"
              onClick={() => fetchQueue(reviewerToken)}
              disabled={queueLoading}
              title="Refresh review queue"
              className="p-2 rounded-input border border-border bg-surface text-charcoal-muted hover:text-charcoal hover:bg-surface-secondary transition-colors disabled:opacity-50"
            >
              <RefreshCw className={`w-4 h-4 ${queueLoading ? 'animate-spin' : ''}`} />
            </button>
          )}
        </div>
      </div>

      {/* Auth Error Banner if authentication fails */}
      {authError && (
        <div className="rounded-panel border border-semantic-diff-border bg-semantic-diff-bg p-3.5 flex items-start gap-2.5 text-body-sm text-semantic-diff-text">
          <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
          <div className="flex-1 leading-snug">{authError}</div>
        </div>
      )}

      {/* Action Success Notification */}
      {actionSuccessMessage && (
        <div className="rounded-panel border border-semantic-same-border bg-semantic-same-bg p-3.5 flex items-center justify-between gap-2.5 text-body-sm text-semantic-same-text">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 shrink-0" />
            <span>{actionSuccessMessage}</span>
          </div>
          <button
            type="button"
            onClick={() => setActionSuccessMessage(null)}
            className="text-xs font-semibold underline hover:opacity-80"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* 1. NOT AUTHENTICATED STATE */}
      {!isAuthenticated ? (
        <EmptyState
          icon={<Lock className="w-5 h-5" />}
          title="Reviewer authentication required"
          description="Enter your reviewer access token above to unlock the queue."
        />
      ) : queueLoading && queue.length === 0 ? (
        /* 2. LOADING QUEUE STATE */
        <LoadingState message="Loading review queue..." className="py-20" />
      ) : queueError ? (
        /* 3. ERROR STATE */
        <ErrorState
          title="Failed to load review queue"
          message={queueError}
          onRetry={() => fetchQueue(reviewerToken)}
        />
      ) : queue.length === 0 ? (
        /* 4. EMPTY QUEUE STATE */
        <EmptyState
          icon={<CheckSquare className="w-5 h-5" />}
          title="No reviews pending"
          description="The human review queue is currently empty."
        />
      ) : (
        /* 5. MASTER-DETAIL SPLIT WORKSPACE */
        <div className="flex-1 flex flex-col lg:flex-row items-start gap-6 w-full min-w-0">
          {/* LEFT PANE: Review Queue List (~320-340px) */}
          <div className={`w-full lg:w-[320px] xl:w-[340px] shrink-0 rounded-panel border border-border bg-surface overflow-hidden shadow-xs flex flex-col lg:sticky lg:top-6 max-h-[calc(100vh-9rem)] ${
            selectedItem ? 'hidden lg:flex' : 'flex'
          }`}>
            {/* Queue Header & Filters */}
            <div className="p-3.5 border-b border-border bg-surface-secondary/40 space-y-2.5 shrink-0">
              <div className="flex items-center justify-between">
                <span className="text-body-sm font-semibold text-charcoal">
                  {scopedCpse ? 'Scoped Queue' : 'Review Queue'}
                </span>
                <span className="font-mono text-xs font-semibold text-charcoal bg-surface px-2 py-0.5 rounded-badge border border-border shadow-2xs">
                  {filteredQueue.length} items
                </span>
              </div>


              {/* Classification / Category Filter Tabs */}
              <div className="flex items-center gap-1 p-0.5 bg-surface-secondary rounded-input border border-border text-[11px] font-medium">
                {(['ALL', 'POTENTIAL', 'DIFFERENT', 'MAPPED'] as const).map((tab) => (
                  <button
                    key={tab}
                    type="button"
                    onClick={() => setClassificationFilter(tab)}
                    className={`flex-1 py-1 px-1 rounded-badge text-center transition-colors truncate ${
                      classificationFilter === tab
                        ? 'bg-surface text-charcoal shadow-xs font-semibold'
                        : 'text-charcoal-muted hover:text-charcoal'
                    }`}
                  >
                    {tab}
                  </button>
                ))}
              </div>

              {/* Search input */}
              <div className="relative">
                <Search className="w-3.5 h-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-charcoal-caption" />
                <input
                  type="text"
                  value={queueSearch}
                  onChange={(e) => setQueueSearch(e.target.value)}
                  placeholder="Filter queue by ID or text..."
                  className="w-full pl-8 pr-3 py-1 text-body-sm rounded-input border border-border bg-surface text-charcoal placeholder:text-charcoal-disabled focus:border-border-strong focus:outline-none transition-colors"
                />
              </div>
            </div>

            {/* Queue Items List */}
            <div className="flex-1 overflow-y-auto divide-y divide-border/60">
              {filteredQueue.length === 0 ? (
                <div className="p-6 text-center text-xs text-charcoal-muted">
                  No queue items match filter criteria.
                </div>
              ) : (
                filteredQueue.map((item) => {
                  const isSelected = selectedItem?.recommendation_id === item.recommendation_id;
                  const isMapped = item.mapping_status === 'MAPPED';

                  return (
                    <button
                      key={item.recommendation_id}
                      type="button"
                      onClick={() => setSelectedItem(item)}
                      className={`w-full text-left p-3.5 flex flex-col gap-2 transition-colors ${
                        isSelected
                          ? 'bg-brand-tint/60 ring-1 ring-inset ring-brand/20'
                          : 'hover:bg-surface-hover'
                      }`}
                    >
                      <div className="flex items-center justify-between gap-2">
                        {isMapped ? (
                          <div className="flex items-center gap-1.5 flex-wrap">
                            <Badge variant="same" className="text-[10px] font-semibold">
                              MAPPED
                            </Badge>
                            {item.national_material_code && (
                              <span className="font-mono text-[11px] font-semibold text-charcoal bg-surface-secondary px-1.5 py-0.5 rounded-badge border border-border">
                                {item.national_material_code}
                              </span>
                            )}
                          </div>
                        ) : (
                          <Badge variant={getClassificationBadgeVariant(item.classification)}>
                            {item.classification === 'POTENTIALLY_EQUIVALENT' ? 'POTENTIAL' : item.classification}
                          </Badge>
                        )}
                        {item.confidence !== null && (
                          <span className="font-mono text-xs font-semibold text-charcoal">
                            {Math.round(item.confidence * 100)}% Match
                          </span>
                        )}
                      </div>

                      {isMapped && item.mapping_basis ? (
                        <div className="text-[11px] font-mono text-charcoal-muted">
                          Basis: <span className="font-semibold text-charcoal">{item.mapping_basis}</span>
                        </div>
                      ) : item.explanation ? (
                        <p className="text-xs text-charcoal-muted leading-relaxed line-clamp-2">
                          {item.explanation}
                        </p>
                      ) : null}

                      <div className="flex items-center justify-between text-[11px] font-mono text-charcoal-caption pt-1 border-t border-border/40">
                        <span className="truncate max-w-[120px]">
                          Src: {item.source_material_id.slice(0, 8)}...
                        </span>
                        <span className="truncate max-w-[120px]">
                          Cand: {item.candidate_material_id.slice(0, 8)}...
                        </span>
                      </div>
                    </button>
                  );
                })
              )}
            </div>

          </div>

          {/* RIGHT PANE: Decision Workbench (Consumes all remaining width) */}
          <div className={`flex-1 min-w-0 w-full space-y-5 ${!selectedItem ? 'hidden lg:block' : 'block'}`}>
            {!selectedItem ? (
              <div className="rounded-panel border border-border bg-surface p-16 text-center space-y-3 shadow-xs">
                <CheckSquare className="w-8 h-8 text-charcoal-muted mx-auto stroke-[1.5]" />
                <h3 className="text-section-title text-charcoal">Select a Recommendation</h3>
                <p className="text-body-sm text-charcoal-muted max-w-md mx-auto">
                  Choose an item from the review queue on the left to inspect engineering specifications, evaluate backend evidence, and execute governance actions.
                </p>
              </div>
            ) : detailsLoading ? (
              <div className="rounded-panel border border-border bg-surface p-16 shadow-xs">
                <LoadingState message="Loading material pair specifications from backend..." />
              </div>
            ) : detailsError ? (
              <ErrorState
                title="Failed to load material pair"
                message={detailsError}
                onRetry={() => {
                  if (selectedItem) {
                    Promise.all([
                      api.materials.get(selectedItem.source_material_id),
                      api.materials.get(selectedItem.candidate_material_id),
                    ]).then(([src, cand]) => {
                      setSourceDetail(src);
                      setCandidateDetail(cand);
                    });
                  }
                }}
              />
            ) : (
              <div className="space-y-6">
                {/* Mobile Back to Queue Button */}
                <div className="lg:hidden pb-1">
                  <button
                    type="button"
                    onClick={() => setSelectedItem(null)}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-input border border-border bg-surface text-charcoal text-body-sm font-medium hover:bg-surface-secondary transition-colors"
                  >
                    <ArrowLeft className="w-4 h-4" />
                    <span>Back to Review Queue</span>
                  </button>
                </div>

                {/* Mapped State Highlight Banner */}
                {selectedItem.mapping_status === 'MAPPED' && (
                  <div className="rounded-panel border border-semantic-same-border bg-semantic-same-bg p-4 flex flex-wrap items-center justify-between gap-3 text-body-sm text-semantic-same-text shadow-xs">
                    <div className="flex items-center gap-2.5 flex-wrap">
                      <CheckCircle2 className="w-5 h-5 shrink-0 text-semantic-same-text" />
                      <span className="font-bold text-sm tracking-wide">MAPPED RECORD</span>
                      {selectedItem.national_material_code && (
                        <span className="font-mono text-xs bg-surface px-2 py-0.5 rounded-badge border border-semantic-same-border text-charcoal font-semibold">
                          {selectedItem.national_material_code}
                        </span>
                      )}
                      {selectedItem.mapping_basis && (
                        <span className="text-xs text-charcoal font-mono bg-surface/80 px-2 py-0.5 rounded-badge border border-border">
                          Basis: <strong className="text-charcoal">{selectedItem.mapping_basis}</strong>
                        </span>
                      )}
                    </div>
                    <span className="text-xs text-charcoal-muted">
                      Active National Material mapping established
                    </span>
                  </div>
                )}

                {/* 1. MATCH DECISION & BACKEND EXPLANATION CARD */}
                <div className="p-4 rounded-panel border border-border bg-surface shadow-xs space-y-3">


                  <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border/80 pb-3">
                    <div className="flex items-center gap-2.5">
                      <span className="text-xs font-semibold uppercase tracking-wider text-charcoal-caption">
                        Queue Recommendation:
                      </span>
                      <Badge
                        variant={getClassificationBadgeVariant(selectedItem.classification)}
                        className="text-xs px-2.5 py-0.5"
                      >
                        {selectedItem.classification}
                      </Badge>
                    </div>

                    {selectedItem.confidence !== null && (
                      <div className="flex items-center gap-2">
                        <span className="text-xs text-charcoal-caption font-medium">Confidence Score:</span>
                        <span className="font-mono text-body font-bold text-charcoal">
                          {Math.round(selectedItem.confidence * 100)}%
                        </span>
                      </div>
                    )}
                  </div>

                  {selectedItem.explanation && (
                    <div className="p-3 bg-surface-secondary/40 rounded-input border border-border/80 text-body-sm text-charcoal leading-relaxed">
                      <span className="text-xs font-semibold text-charcoal-muted block mb-0.5">
                        Deterministic Decision Explanation
                      </span>
                      &ldquo;{selectedItem.explanation}&rdquo;
                    </div>
                  )}

                  {/* Backend Evidence block if present */}
                  {selectedItem.evidence && Object.keys(selectedItem.evidence).length > 0 && (
                    <div className="p-3 bg-canvas rounded-input border border-border text-xs space-y-1">
                      <span className="font-semibold text-charcoal-muted block uppercase tracking-wider text-[10px]">
                        Backend Evidence Payload
                      </span>
                      <pre className="font-mono text-[11px] text-charcoal overflow-x-auto">
                        {JSON.stringify(selectedItem.evidence, null, 2)}
                      </pre>
                    </div>
                  )}
                </div>

                {/* 2. SIDE-BY-SIDE ENTITY SUMMARY HEADERS */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {/* Left: Source Entity */}
                  <div className="p-4 rounded-panel border border-border bg-surface shadow-xs space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-[11px] font-semibold text-charcoal-caption uppercase tracking-wider">
                        Source Material
                      </span>
                      <span className="font-mono text-xs font-semibold text-charcoal bg-surface-secondary px-1.5 py-0.5 rounded-badge border border-border">
                        {sourceDetail?.source_material_code || selectedItem.source_material_id.slice(0, 8)}
                      </span>
                    </div>
                    <p className="text-body-sm font-medium text-charcoal leading-snug">
                      {sourceDetail?.source_description || 'Loading source description...'}
                    </p>
                    <div className="flex items-center gap-2 text-xs text-charcoal-caption pt-1 border-t border-border/60">
                      <Building2 className="w-3.5 h-3.5" />
                      <span>ID: {selectedItem.source_material_id}</span>
                    </div>
                  </div>

                  {/* Right: Candidate Entity */}
                  <div className="p-4 rounded-panel border border-border bg-surface shadow-xs space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-[11px] font-semibold text-charcoal-caption uppercase tracking-wider">
                        Candidate Material
                      </span>
                      <span className="font-mono text-xs font-semibold text-charcoal bg-surface-secondary px-1.5 py-0.5 rounded-badge border border-border">
                        {candidateDetail?.source_material_code || selectedItem.candidate_material_id.slice(0, 8)}
                      </span>
                    </div>
                    <p className="text-body-sm font-medium text-charcoal leading-snug">
                      {candidateDetail?.source_description || 'Loading candidate description...'}
                    </p>
                    <div className="flex items-center gap-2 text-xs text-charcoal-caption pt-1 border-t border-border/60">
                      <Building2 className="w-3.5 h-3.5" />
                      <span>ID: {selectedItem.candidate_material_id}</span>
                    </div>
                  </div>
                </div>

                {/* 3. TECHNICAL ATTRIBUTE COMPARISON TABLE */}
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <h3 className="text-section-title text-charcoal">
                      Technical Identity Comparison
                    </h3>
                    <span className="text-xs text-charcoal-caption">
                      Aligned engineering specifications
                    </span>
                  </div>

                  <AttributeComparisonTable
                    sourceDetail={sourceDetail}
                    candidateDetail={candidateDetail}
                  />
                </div>

                {/* 4. COLLAPSIBLE IMMUTABLE RAW DATA COMPARISON */}
                <div className="border border-border rounded-panel overflow-hidden bg-surface shadow-xs">
                  <button
                    type="button"
                    onClick={() => setShowRawComparison(!showRawComparison)}
                    className="w-full px-4 py-3 flex items-center justify-between bg-surface-secondary/50 hover:bg-surface-secondary/80 text-left transition-colors"
                  >
                    <div className="flex items-center gap-2">
                      <FileCode className="w-4 h-4 text-charcoal-muted" />
                      <span className="text-body-sm font-semibold text-charcoal">
                        Compare Original Raw Payloads
                      </span>
                      <span className="text-[11px] text-charcoal-caption">
                        (Immutable source records)
                      </span>
                    </div>
                    {showRawComparison ? (
                      <ChevronDown className="w-4 h-4 text-charcoal-muted" />
                    ) : (
                      <ChevronRight className="w-4 h-4 text-charcoal-muted" />
                    )}
                  </button>

                  {showRawComparison && (
                    <div className="p-4 bg-canvas border-t border-border grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div>
                        <span className="text-xs font-semibold text-charcoal-muted block mb-1">
                          Source Raw Payload
                        </span>
                        <pre className="p-3 bg-surface rounded-input border border-border font-mono text-[11px] text-charcoal overflow-x-auto leading-relaxed max-h-56">
                          {sourceDetail?.raw_source_data
                            ? JSON.stringify(sourceDetail.raw_source_data, null, 2)
                            : 'null'}
                        </pre>
                      </div>

                      <div>
                        <span className="text-xs font-semibold text-charcoal-muted block mb-1">
                          Candidate Raw Payload
                        </span>
                        <pre className="p-3 bg-surface rounded-input border border-border font-mono text-[11px] text-charcoal overflow-x-auto leading-relaxed max-h-56">
                          {candidateDetail?.raw_source_data
                            ? JSON.stringify(candidateDetail.raw_source_data, null, 2)
                            : 'null'}
                        </pre>
                      </div>
                    </div>
                  )}
                </div>

                {/* 5. GOVERNANCE ACTION BAR */}
                <div className="p-4 rounded-panel border border-border bg-surface shadow-md flex flex-col sm:flex-row items-center justify-between gap-4 sticky bottom-6">
                  <div>
                    <span className="text-body-sm font-semibold text-charcoal block">
                      Governance Decision
                    </span>
                    <span className="text-xs text-charcoal-muted">
                      Select human action for recommendation {selectedItem.recommendation_id.slice(0, 8)}...
                    </span>
                  </div>

                  <div className="flex flex-wrap items-center gap-2.5 w-full sm:w-auto">
                    {/* ACCEPT */}
                    <button
                      type="button"
                      onClick={() => setModalAction('ACCEPT')}
                      className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-input bg-emerald-700 hover:bg-emerald-800 text-white text-body-sm font-medium transition-colors shadow-xs"
                    >
                      <CheckCircle2 className="w-4 h-4" />
                      <span>ACCEPT</span>
                    </button>

                    {/* REJECT */}
                    <button
                      type="button"
                      onClick={() => setModalAction('REJECT')}
                      className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-input bg-rose-700 hover:bg-rose-800 text-white text-body-sm font-medium transition-colors shadow-xs"
                    >
                      <XCircle className="w-4 h-4" />
                      <span>REJECT</span>
                    </button>

                    {/* MARK DIFFERENT */}
                    <button
                      type="button"
                      onClick={() => setModalAction('MARK_DIFFERENT')}
                      className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-input bg-amber-700 hover:bg-amber-800 text-white text-body-sm font-medium transition-colors shadow-xs"
                    >
                      <AlertTriangle className="w-4 h-4" />
                      <span>MARK DIFFERENT</span>
                    </button>

                    {/* OVERRIDE */}
                    <button
                      type="button"
                      onClick={() => setModalAction('OVERRIDE')}
                      className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-input bg-brand hover:bg-brand-hover text-white text-body-sm font-medium transition-colors shadow-xs"
                    >
                      <Layers className="w-4 h-4" />
                      <span>OVERRIDE</span>
                    </button>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Action Modal Dialog */}
      {selectedItem && (
        <ReviewActionModal
          isOpen={modalAction !== null}
          action={modalAction}
          recommendationId={selectedItem.recommendation_id}
          reviewerToken={reviewerToken}
          sourceCode={sourceDetail?.source_material_code}
          candidateCode={candidateDetail?.source_material_code}
          onClose={() => setModalAction(null)}
          onSuccess={handleActionSuccess}
        />
      )}
    </div>
  );
};

