import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  GitCompare,
  Building2,
  ArrowRight,
  RefreshCw,
  Search,
  Check,
  ChevronDown,
  ChevronRight,
  FileCode,
  Sparkles,
  ShieldCheck,
  CheckSquare,
} from 'lucide-react';
import { api, ApiClientError } from '../api/client';
import type {
  MaterialListItem,
  MaterialDetailResponse,
  MatchResponse,
  MatchRecommendationItem,
} from '../types/api';
import { useCpse } from '../context/CpseContext';
import { LoadingState } from '../components/common/LoadingState';
import { ErrorState } from '../components/common/ErrorState';
import { EmptyState } from '../components/common/EmptyState';
import { Badge, type BadgeVariant } from '../components/common/Badge';
import { AttributeComparisonTable } from '../components/matching/AttributeComparisonTable';

export const MatchingPage: React.FC = () => {
  const navigate = useNavigate();
  const { selectedCpse } = useCpse();

  // Source materials state (for active CPSE investigation)
  const [materials, setMaterials] = useState<MaterialListItem[]>([]);
  const [loadingMaterials, setLoadingMaterials] = useState<boolean>(false);
  const [materialsError, setMaterialsError] = useState<string | null>(null);
  const [materialSearch, setMaterialSearch] = useState<string>('');

  // Selected source & detail
  const [selectedSource, setSelectedSource] = useState<MaterialListItem | null>(null);
  const [sourceDetail, setSourceDetail] = useState<MaterialDetailResponse | null>(null);

  // Matching execution & recommendations for single material
  const [matchLoading, setMatchLoading] = useState<boolean>(false);
  const [matchError, setMatchError] = useState<string | null>(null);
  const [matchResult, setMatchResult] = useState<MatchResponse | null>(null);

  // Selected recommendation & candidate detail
  const [selectedRec, setSelectedRec] = useState<MatchRecommendationItem | null>(null);
  const [candidateDetail, setCandidateDetail] = useState<MaterialDetailResponse | null>(null);
  const [candidateLoading, setCandidateLoading] = useState<boolean>(false);
  const [candidateError, setCandidateError] = useState<string | null>(null);

  // Collapsible raw payloads
  const [showRawComparison, setShowRawComparison] = useState<boolean>(false);

  // 1. Fetch materials for selected CPSE

  const fetchMaterials = useCallback(async () => {
    if (!selectedCpse) return;
    setLoadingMaterials(true);
    setMaterialsError(null);
    try {
      const data = await api.materials.listByCpse(selectedCpse.id);
      setMaterials(data);
    } catch (err: unknown) {
      if (err instanceof ApiClientError) {
        setMaterialsError(err.message);
      } else if (err instanceof Error) {
        setMaterialsError(err.message);
      } else {
        setMaterialsError('Failed to load enterprise materials.');
      }
    } finally {
      setLoadingMaterials(false);
    }
  }, [selectedCpse]);

  useEffect(() => {
    setSelectedSource(null);
    setSourceDetail(null);
    setMatchResult(null);
    setSelectedRec(null);
    setCandidateDetail(null);
    if (selectedCpse) {
      fetchMaterials();
    } else {
      setMaterials([]);
    }
  }, [selectedCpse, fetchMaterials]);

  // 2. Fetch source detail when source selected
  useEffect(() => {
    if (!selectedSource) {
      setSourceDetail(null);
      return;
    }
    let isCancelled = false;
    api.materials
      .get(selectedSource.id)
      .then((data) => {
        if (!isCancelled) setSourceDetail(data);
      })
      .catch(() => {
        // Source detail load fallback
      });
    return () => {
      isCancelled = true;
    };
  }, [selectedSource]);

  // 3. Fetch candidate detail when recommendation selected
  useEffect(() => {
    if (!selectedRec) {
      setCandidateDetail(null);
      setCandidateError(null);
      return;
    }
    let isCancelled = false;
    setCandidateLoading(true);
    setCandidateError(null);
    api.materials
      .get(selectedRec.candidate_id)
      .then((data) => {
        if (!isCancelled) setCandidateDetail(data);
      })
      .catch((err: unknown) => {
        if (!isCancelled) {
          if (err instanceof ApiClientError) {
            setCandidateError(err.message);
          } else if (err instanceof Error) {
            setCandidateError(err.message);
          } else {
            setCandidateError('Unable to load candidate material details.');
          }
        }
      })
      .finally(() => {
        if (!isCancelled) setCandidateLoading(false);
      });
    return () => {
      isCancelled = true;
    };
  }, [selectedRec]);

  // 4. Run single material match action for investigation
  const handleRunMatch = async () => {
    if (!selectedSource) return;
    setMatchLoading(true);
    setMatchError(null);
    setSelectedRec(null);
    setCandidateDetail(null);

    try {
      const res = await api.materials.match(selectedSource.id);
      setMatchResult(res);
      if (res.recommendations && res.recommendations.length > 0) {
        setSelectedRec(res.recommendations[0]);
      }
    } catch (err: unknown) {
      if (err instanceof ApiClientError) {
        setMatchError(err.message);
      } else if (err instanceof Error) {
        setMatchError(err.message);
      } else {
        setMatchError('Matching engine execution failed.');
      }
    } finally {
      setMatchLoading(false);
    }
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

  // Filtered materials
  const filteredMaterials = materials.filter((m) => {
    const q = materialSearch.toLowerCase().trim();
    if (!q) return true;
    return (
      m.source_material_code.toLowerCase().includes(q) ||
      m.source_description.toLowerCase().includes(q) ||
      (m.category && m.category.toLowerCase().includes(q))
    );
  });

  // Empty state if no CPSE selected
  if (!selectedCpse) {
    return (
      <div className="p-8 max-w-7xl w-full mx-auto space-y-6">
        <div>
          <h1 className="text-page-title text-charcoal">Investigate Material Matches</h1>
          <p className="text-body text-charcoal-muted mt-1">
            Cross-CPSE deterministic matching engine & technical comparison workspace
          </p>
        </div>

        <EmptyState
          icon={<Building2 className="w-5 h-5" />}
          title="No CPSE selected for attribute comparison"
          description="Choose a CPSE from the directory to inspect individual technical matches and attribute alignments."
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

  const isSourceMapped = sourceDetail?.mapping_status === 'MAPPED';
  const nationalMaterialCode = sourceDetail?.national_material_code;

  return (
    <div className="p-4 sm:p-6 lg:p-8 max-w-7xl w-full mx-auto space-y-6 flex flex-col min-h-[calc(100vh-4rem)]">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 shrink-0">
        <div>
          <h1 className="text-page-title text-charcoal">Investigate Material Matches</h1>
          <p className="text-body text-charcoal-muted mt-1">
            Cross-CPSE diagnostic investigation for {selectedCpse.name}{' '}
            <span className="font-mono text-xs text-charcoal-muted bg-surface-secondary px-1.5 py-0.5 rounded-badge border border-border">
              {selectedCpse.code}
            </span>
          </p>
        </div>

        <div className="flex items-center gap-2.5 flex-wrap">
          <button
            type="button"
            onClick={fetchMaterials}
            disabled={loadingMaterials}
            title="Refresh materials"
            className="p-2 rounded-input border border-border bg-surface text-charcoal-muted hover:text-charcoal hover:bg-surface-secondary transition-colors disabled:opacity-50"
          >
            <RefreshCw className={`w-4 h-4 ${loadingMaterials ? 'animate-spin' : ''}`} />
          </button>

          {/* Single Material Evaluation Action */}
          <button
            type="button"
            onClick={handleRunMatch}
            disabled={!selectedSource || matchLoading}
            className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-input bg-brand text-white text-body-sm font-medium hover:bg-brand-hover transition-colors disabled:opacity-50 shadow-xs"
          >
            <GitCompare className={`w-4 h-4 ${matchLoading ? 'animate-spin' : ''}`} />
            <span>{matchLoading ? 'Running...' : 'Match Selected'}</span>
          </button>
        </div>
      </div>



      {/* Main Workspace Split Layout */}
      {loadingMaterials && materials.length === 0 ? (
        <LoadingState message="Loading enterprise materials..." className="py-20" />
      ) : materialsError ? (
        <ErrorState
          title="Unable to load materials"
          message={materialsError}
          onRetry={fetchMaterials}
        />
      ) : materials.length === 0 ? (
        <EmptyState
          icon={<GitCompare className="w-5 h-5" />}
          title="No materials available"
          description={`No materials exist for ${selectedCpse.name}. Import catalog records in the Materials Explorer first.`}
          action={
            <button
              type="button"
              onClick={() => navigate('/materials')}
              className="inline-flex items-center gap-1.5 px-4 py-2 rounded-input bg-brand text-white text-body font-medium hover:bg-brand-hover transition-colors shadow-xs"
            >
              <span>Go to Materials Explorer</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          }
        />
      ) : (
        <div className="flex-1 grid grid-cols-1 lg:grid-cols-12 gap-6 items-start min-h-[560px]">
          {/* LEFT COLUMN: Source Selector & Recommendations List (4 cols) */}
          <div className="lg:col-span-4 space-y-6 flex flex-col">
            {/* 1. Source Material Selector Panel */}
            <div className="rounded-panel border border-border bg-surface overflow-hidden shadow-xs flex flex-col">
              <div className="p-3.5 border-b border-border bg-surface-secondary/40 flex items-center justify-between">
                <div>
                  <h3 className="text-body-sm font-semibold text-charcoal">Source Material</h3>
                  <p className="text-[11px] text-charcoal-caption">Select material from active CPSE</p>
                </div>
                {selectedSource && (
                  <span className="font-mono text-xs font-semibold text-charcoal bg-brand-tint px-2 py-0.5 rounded-badge border border-border">
                    {selectedSource.source_material_code}
                  </span>
                )}
              </div>

              {/* Search input */}
              <div className="p-2.5 border-b border-border/80 bg-surface">
                <div className="relative">
                  <Search className="w-3.5 h-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-charcoal-caption" />
                  <input
                    type="text"
                    value={materialSearch}
                    onChange={(e) => setMaterialSearch(e.target.value)}
                    placeholder="Search by code or description..."
                    className="w-full pl-8 pr-3 py-1.5 rounded-input border border-border bg-surface text-charcoal text-body-sm placeholder:text-charcoal-disabled focus:border-border-strong focus:outline-none transition-colors"
                  />
                </div>
              </div>

              {/* Material List */}
              <div className="max-h-56 overflow-y-auto divide-y divide-border/60">
                {filteredMaterials.length === 0 ? (
                  <div className="p-4 text-center text-xs text-charcoal-muted">
                    No matching source materials found.
                  </div>
                ) : (
                  filteredMaterials.map((m) => {
                    const isSelected = selectedSource?.id === m.id;
                    return (
                      <button
                        key={m.id}
                        type="button"
                        onClick={() => {
                          setSelectedSource(m);
                          setMatchResult(null);
                          setSelectedRec(null);
                          setCandidateDetail(null);
                        }}
                        className={`w-full text-left p-3 flex items-start justify-between gap-2 transition-colors ${
                          isSelected
                            ? 'bg-brand-tint/60 ring-1 ring-inset ring-brand/20'
                            : 'hover:bg-surface-hover'
                        }`}
                      >
                        <div className="min-w-0 flex-1">
                          <div className="flex items-center gap-1.5 mb-0.5">
                            <span className="font-mono text-xs font-semibold text-charcoal">
                              {m.source_material_code}
                            </span>
                            {m.category && (
                              <span className="font-mono text-[10px] text-charcoal-muted uppercase bg-surface-secondary px-1 py-0.2 rounded-badge border border-border/60">
                                {m.category}
                              </span>
                            )}
                          </div>
                          <p className="text-xs text-charcoal-muted truncate leading-snug">
                            {m.source_description}
                          </p>
                        </div>
                        {isSelected && (
                          <span className="w-4 h-4 rounded-full bg-brand text-white flex items-center justify-center shrink-0 mt-0.5">
                            <Check className="w-2.5 h-2.5 stroke-[3]" />
                          </span>
                        )}
                      </button>
                    );
                  })
                )}
              </div>
            </div>

            {/* 2. Recommendations List Panel */}
            {matchLoading ? (
              <div className="rounded-panel border border-border bg-surface p-8 shadow-xs">
                <LoadingState message="Executing deterministic matching algorithm..." />
              </div>
            ) : matchError ? (
              <ErrorState
                title="Match Generation Failed"
                message={matchError}
                onRetry={handleRunMatch}
              />
            ) : matchResult ? (
              <div className="rounded-panel border border-border bg-surface overflow-hidden shadow-xs flex flex-col">
                <div className="p-3.5 border-b border-border bg-surface-secondary/40 flex items-center justify-between">
                  <div>
                    <h3 className="text-body-sm font-semibold text-charcoal">
                      Candidate Recommendations
                    </h3>
                    <p className="text-[11px] text-charcoal-caption">
                      {matchResult.recommendations.length} candidate(s) evaluated
                    </p>
                  </div>
                  <span className="font-mono text-xs text-charcoal-muted bg-surface px-1.5 py-0.5 rounded-badge border border-border">
                    Backend Verified
                  </span>
                </div>

                <div className="divide-y divide-border/60 max-h-80 overflow-y-auto">
                  {matchResult.recommendations.length === 0 ? (
                    <div className="p-6 text-center text-xs text-charcoal-muted">
                      No candidate recommendations found for this material.
                    </div>
                  ) : (
                    matchResult.recommendations.map((rec, idx) => {
                      const isSelected = selectedRec?.candidate_id === rec.candidate_id;

                      return (
                        <button
                          key={`${rec.candidate_id}-${idx}`}
                          type="button"
                          onClick={() => setSelectedRec(rec)}
                          className={`w-full text-left p-3.5 flex flex-col gap-2 transition-colors ${
                            isSelected
                              ? 'bg-brand-tint/60 ring-1 ring-inset ring-brand/20'
                              : 'hover:bg-surface-hover'
                          }`}
                        >
                          <div className="flex items-center justify-between gap-2">
                            <Badge variant={getClassificationBadgeVariant(rec.classification)}>
                              {rec.classification}
                            </Badge>
                            <span className="font-mono text-xs font-semibold text-charcoal">
                              {Math.round(rec.confidence * 100)}% Match
                            </span>
                          </div>

                          {rec.explanation && (
                            <p className="text-xs text-charcoal-muted leading-relaxed line-clamp-2">
                              {rec.explanation}
                            </p>
                          )}
                        </button>
                      );
                    })
                  )}
                </div>
              </div>
            ) : selectedSource ? (
              <div className="rounded-panel border border-dashed border-border bg-surface-secondary/20 p-6 text-center space-y-2">
                <Sparkles className="w-5 h-5 text-charcoal-muted mx-auto" />
                <p className="text-body-sm font-medium text-charcoal">
                  Ready to evaluate matches
                </p>
                <p className="text-xs text-charcoal-caption">
                  Click &ldquo;Find Matches&rdquo; above to query candidate equivalence.
                </p>
              </div>
            ) : null}
          </div>

          {/* RIGHT COLUMN: Side-by-Side Comparison Workspace (8 cols) */}
          <div className="lg:col-span-8 space-y-6">
            {!selectedSource ? (
              <div className="rounded-panel border border-border bg-surface p-16 text-center space-y-3 shadow-xs">
                <GitCompare className="w-8 h-8 text-charcoal-muted mx-auto stroke-[1.5]" />
                <h3 className="text-section-title text-charcoal">Select a Source Material</h3>
                <p className="text-body-sm text-charcoal-muted max-w-md mx-auto">
                  Choose a material from the left panel to inspect its engineering attributes and run deterministic matching against candidate catalogs.
                </p>
              </div>
            ) : !selectedRec ? (
              <div className="rounded-panel border border-border bg-surface p-16 text-center space-y-3 shadow-xs">
                <Sparkles className="w-8 h-8 text-charcoal-muted mx-auto stroke-[1.5]" />
                <h3 className="text-section-title text-charcoal">No Recommendation Selected</h3>
                <p className="text-body-sm text-charcoal-muted max-w-md mx-auto">
                  {matchResult
                    ? 'Select a candidate recommendation from the list on the left to compare engineering identity attributes.'
                    : 'Click "Find Matches" to execute the matching engine.'}
                </p>
              </div>
            ) : candidateLoading ? (
              <div className="rounded-panel border border-border bg-surface p-16 shadow-xs">
                <LoadingState message="Loading candidate material specifications..." />
              </div>
            ) : candidateError ? (
              <ErrorState
                title="Unable to load candidate"
                message={candidateError}
                onRetry={() => {
                  if (selectedRec) {
                    api.materials.get(selectedRec.candidate_id).then(setCandidateDetail);
                  }
                }}
              />
            ) : (
              <div className="space-y-6">
                {/* 1. OPERATIONAL OUTCOME & GOVERNANCE NAVIGATION CARD */}
                {isSourceMapped ? (
                  <div className="p-4 rounded-panel border border-semantic-same-border bg-semantic-same-bg shadow-xs flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <Badge variant="same" className="font-semibold text-xs">
                          MAPPED
                        </Badge>
                        {selectedRec.confidence !== null && (
                          <span className="font-mono text-xs font-bold text-semantic-same-text">
                            {Math.round(selectedRec.confidence * 100)}% Match
                          </span>
                        )}
                      </div>
                      <p className="text-body-sm text-semantic-same-text font-medium">
                        Active National Material mapping established in catalog.
                      </p>
                      {nationalMaterialCode && (
                        <div className="flex items-center gap-2 pt-1 text-xs">
                          <span className="text-charcoal-muted">National Material:</span>
                          <span className="font-mono font-bold text-brand bg-surface px-2 py-0.5 rounded-badge border border-semantic-same-border">
                            {nationalMaterialCode}
                          </span>
                        </div>
                      )}
                    </div>
                    <button
                      type="button"
                      onClick={() => navigate('/national-materials')}
                      className="inline-flex items-center justify-center gap-1.5 px-3.5 py-2 rounded-input bg-surface border border-semantic-same-border text-charcoal text-body-sm font-semibold hover:bg-surface-secondary transition-colors shrink-0 shadow-xs"
                    >
                      <ShieldCheck className="w-4 h-4 text-brand" />
                      <span>View National Material</span>
                      <ArrowRight className="w-3.5 h-3.5 text-charcoal-caption" />
                    </button>
                  </div>
                ) : selectedRec.classification === 'POTENTIALLY_EQUIVALENT' ? (
                  <div className="p-4 rounded-panel border border-semantic-potential-border bg-semantic-potential-bg shadow-xs flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <Badge variant="potential" className="font-semibold text-xs">
                          POTENTIALLY_EQUIVALENT
                        </Badge>
                        {selectedRec.confidence !== null && (
                          <span className="font-mono text-xs font-bold text-semantic-potential-text">
                            {Math.round(selectedRec.confidence * 100)}% Match
                          </span>
                        )}
                      </div>
                      <p className="text-body-sm text-semantic-potential-text font-medium">
                        Unresolved candidate match requires human review and governance.
                      </p>
                    </div>
                    <button
                      type="button"
                      onClick={() => navigate(`/review?cpseId=${selectedCpse.id}`)}
                      className="inline-flex items-center justify-center gap-1.5 px-3.5 py-2 rounded-input bg-surface border border-semantic-potential-border text-charcoal text-body-sm font-semibold hover:bg-surface-secondary transition-colors shrink-0 shadow-xs"
                    >
                      <CheckSquare className="w-4 h-4 text-semantic-potential-text" />
                      <span>Open Review Queue</span>
                      <ArrowRight className="w-3.5 h-3.5 text-charcoal-caption" />
                    </button>
                  </div>
                ) : selectedRec.classification === 'DIFFERENT' ? (
                  <div className="p-4 rounded-panel border border-semantic-diff-border bg-semantic-diff-bg shadow-xs space-y-2">
                    <div className="flex items-center justify-between gap-2">
                      <div className="flex items-center gap-2">
                        <Badge variant="diff" className="font-semibold text-xs">
                          DIFFERENT
                        </Badge>
                        {selectedRec.confidence !== null && (
                          <span className="font-mono text-xs font-bold text-semantic-diff-text">
                            {Math.round(selectedRec.confidence * 100)}% Confidence
                          </span>
                        )}
                      </div>
                      <span className="text-xs font-medium text-charcoal-caption">No Harmonization Required</span>
                    </div>
                    <p className="text-body-sm text-semantic-diff-text font-medium">
                      Classified as distinct engineering material.
                    </p>
                  </div>
                ) : (
                  <div className="p-4 rounded-panel border border-border bg-surface-secondary/40 shadow-xs flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <Badge variant="same" className="font-semibold text-xs">
                          SAME
                        </Badge>
                        {selectedRec.confidence !== null && (
                          <span className="font-mono text-xs font-bold text-charcoal">
                            {Math.round(selectedRec.confidence * 100)}% Match
                          </span>
                        )}
                      </div>
                      <p className="text-body-sm text-charcoal font-medium">
                        High-confidence candidate match identified.
                      </p>
                    </div>
                    <button
                      type="button"
                      onClick={() => navigate(`/review?cpseId=${selectedCpse.id}`)}
                      className="inline-flex items-center justify-center gap-1.5 px-3.5 py-2 rounded-input bg-surface border border-border text-charcoal text-body-sm font-semibold hover:bg-surface-secondary transition-colors shrink-0 shadow-xs"
                    >
                      <CheckSquare className="w-4 h-4 text-charcoal" />
                      <span>Open Review Queue</span>
                      <ArrowRight className="w-3.5 h-3.5 text-charcoal-caption" />
                    </button>
                  </div>
                )}

                {/* 2. MATCH DECISION & BACKEND EXPLANATION CARD */}
                <div className="p-4 rounded-panel border border-border bg-surface shadow-xs space-y-3">
                  <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border/80 pb-3">
                    <div className="flex items-center gap-2.5">
                      <span className="text-xs font-semibold uppercase tracking-wider text-charcoal-caption">
                        Backend Classification:
                      </span>
                      <Badge
                        variant={getClassificationBadgeVariant(selectedRec.classification)}
                        className="text-xs px-2.5 py-0.5"
                      >
                        {selectedRec.classification}
                      </Badge>
                    </div>

                    <div className="flex items-center gap-2">
                      <span className="text-xs text-charcoal-caption font-medium">Confidence Score:</span>
                      <span className="font-mono text-body font-bold text-charcoal">
                        {Math.round(selectedRec.confidence * 100)}%
                      </span>
                    </div>
                  </div>

                  {selectedRec.explanation && (
                    <div className="p-3 bg-surface-secondary/40 rounded-input border border-border/80 text-body-sm text-charcoal leading-relaxed">
                      <span className="text-xs font-semibold text-charcoal-muted block mb-0.5">
                        Deterministic Decision Explanation
                      </span>
                      &ldquo;{selectedRec.explanation}&rdquo;
                    </div>
                  )}
                </div>


                {/* 2. SIDE-BY-SIDE ENTITY SUMMARY HEADERS */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {/* Left: Source Entity */}
                  <div className="p-4 rounded-panel border border-border bg-surface shadow-xs space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-[11px] font-semibold text-charcoal-caption uppercase tracking-wider">
                        Source Material (Active CPSE)
                      </span>
                      <span className="font-mono text-xs font-semibold text-charcoal bg-surface-secondary px-1.5 py-0.5 rounded-badge border border-border">
                        {sourceDetail?.source_material_code || selectedSource.source_material_code}
                      </span>
                    </div>
                    <p className="text-body-sm font-medium text-charcoal leading-snug">
                      {sourceDetail?.source_description || selectedSource.source_description}
                    </p>
                    <div className="flex items-center gap-2 text-xs text-charcoal-caption pt-1 border-t border-border/60">
                      <Building2 className="w-3.5 h-3.5" />
                      <span>{selectedCpse.name}</span>
                    </div>
                  </div>

                  {/* Right: Candidate Entity */}
                  <div className="p-4 rounded-panel border border-border bg-surface shadow-xs space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-[11px] font-semibold text-charcoal-caption uppercase tracking-wider">
                        Candidate Material
                      </span>
                      <span className="font-mono text-xs font-semibold text-charcoal bg-surface-secondary px-1.5 py-0.5 rounded-badge border border-border">
                        {candidateDetail?.source_material_code || 'CANDIDATE'}
                      </span>
                    </div>
                    <p className="text-body-sm font-medium text-charcoal leading-snug">
                      {candidateDetail?.source_description || 'Loading candidate description...'}
                    </p>
                    <div className="flex items-center gap-2 text-xs text-charcoal-caption pt-1 border-t border-border/60">
                      <Building2 className="w-3.5 h-3.5" />
                      <span>Enterprise Catalog Pair</span>
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
                      Aligned engineering attributes
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
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

