import React, { useState, useEffect } from 'react';
import {
  X,
  AlertCircle,
  Loader2,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Layers,
} from 'lucide-react';
import { api, ApiClientError } from '../../api/client';
import type {
  ReviewActionType,
  ReviewActionResponse,
  NationalMaterialListItem,
} from '../../types/api';

interface ReviewActionModalProps {
  isOpen: boolean;
  action: ReviewActionType | null;
  recommendationId: string;
  reviewerToken: string;
  sourceCode?: string;
  candidateCode?: string;
  onClose: () => void;
  onSuccess: (response: ReviewActionResponse) => void;
}

export const ReviewActionModal: React.FC<ReviewActionModalProps> = ({
  isOpen,
  action,
  recommendationId,
  reviewerToken,
  sourceCode,
  candidateCode,
  onClose,
  onSuccess,
}) => {
  const [reason, setReason] = useState<string>('');
  const [nationalMaterialId, setNationalMaterialId] = useState<string>('');
  const [nationalMaterials, setNationalMaterials] = useState<NationalMaterialListItem[]>([]);
  const [loadingNms, setLoadingNms] = useState<boolean>(false);
  const [submitting, setSubmitting] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Load National Materials if action is OVERRIDE
  useEffect(() => {
    if (isOpen && action === 'OVERRIDE') {
      setLoadingNms(true);
      api.nationalMaterials
        .list(0, 100)
        .then((items) => {
          setNationalMaterials(items);
          if (items.length > 0) {
            setNationalMaterialId(items[0].id);
          }
        })
        .catch(() => {
          setError('Unable to load National Materials catalog for override selection.');
        })
        .finally(() => {
          setLoadingNms(false);
        });
    }
  }, [isOpen, action]);

  useEffect(() => {
    if (isOpen) {
      setReason('');
      setError(null);
    }
  }, [isOpen, action]);

  if (!isOpen || !action) return null;

  const isReasonRequired = action === 'REJECT' || action === 'MARK_DIFFERENT' || action === 'OVERRIDE';

  const getActionConfig = () => {
    switch (action) {
      case 'ACCEPT':
        return {
          title: 'Confirm Material Equivalence (ACCEPT)',
          description:
            'Confirm that the source and candidate materials represent identical engineering specifications. The backend will establish an active national mapping.',
          icon: <CheckCircle2 className="w-5 h-5 text-semantic-same-text" />,
          btnText: 'Confirm ACCEPT',
          btnClass: 'bg-emerald-700 hover:bg-emerald-800 text-white',
        };
      case 'REJECT':
        return {
          title: 'Reject Recommendation (REJECT)',
          description:
            'Reject this match recommendation. No active national mapping will be created. A reason is required for governance audit logs.',
          icon: <XCircle className="w-5 h-5 text-semantic-diff-text" />,
          btnText: 'Confirm REJECT',
          btnClass: 'bg-rose-700 hover:bg-rose-800 text-white',
        };
      case 'MARK_DIFFERENT':
        return {
          title: 'Confirm Distinct Materials (MARK DIFFERENT)',
          description:
            'Record human confirmation that these materials are technically different. A reason is required for audit logs.',
          icon: <AlertTriangle className="w-5 h-5 text-amber-700" />,
          btnText: 'Confirm MARK DIFFERENT',
          btnClass: 'bg-amber-700 hover:bg-amber-800 text-white',
        };
      case 'OVERRIDE':
        return {
          title: 'Override Mapping (OVERRIDE)',
          description:
            'Explicitly map this source material to a designated National Material record. Both target selection and audit reason are required.',
          icon: <Layers className="w-5 h-5 text-brand" />,
          btnText: 'Confirm OVERRIDE',
          btnClass: 'bg-brand hover:bg-brand-hover text-white',
        };
    }
  };

  const config = getActionConfig();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const trimmedReason = reason.trim();

    if (isReasonRequired && !trimmedReason) {
      setError(`A reason is required by the backend for ${action}.`);
      return;
    }

    if (action === 'OVERRIDE' && !nationalMaterialId) {
      setError('A target National Material is required for OVERRIDE.');
      return;
    }

    setSubmitting(true);
    setError(null);

    try {
      const response = await api.reviews.performAction(
        recommendationId,
        {
          action,
          reason: trimmedReason || null,
          national_material_id: action === 'OVERRIDE' ? nationalMaterialId : null,
        },
        reviewerToken
      );

      onSuccess(response);
      onClose();
    } catch (err: unknown) {
      if (err instanceof ApiClientError) {
        setError(err.message);
      } else if (err instanceof Error) {
        setError(err.message);
      } else {
        setError('Review action failed.');
      }
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="action-modal-title"
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-charcoal/40 select-text overflow-y-auto"
      onClick={() => !submitting && onClose()}
    >
      <div
        className="w-full max-w-lg max-h-[90vh] flex flex-col bg-surface rounded-panel border border-border shadow-xl p-5 sm:p-6 space-y-4 sm:space-y-5 overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >

        {/* Header */}
        <div className="flex items-start justify-between gap-4">
          <div className="flex items-start gap-3">
            <div className="p-2 rounded-input bg-surface-secondary shrink-0 mt-0.5">
              {config.icon}
            </div>
            <div>
              <h3 id="action-modal-title" className="text-section-title text-charcoal">
                {config.title}
              </h3>
              <p className="text-body-sm text-charcoal-muted mt-1 leading-relaxed">
                {config.description}
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            disabled={submitting}
            className="p-1 rounded-input text-charcoal-caption hover:text-charcoal hover:bg-surface-secondary transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Pair Context Strip */}
        {(sourceCode || candidateCode) && (
          <div className="p-3 bg-surface-secondary/40 rounded-input border border-border flex items-center justify-between text-body-sm">
            <div>
              <span className="text-xs text-charcoal-muted block">Source</span>
              <span className="font-mono font-semibold text-charcoal">{sourceCode || 'SOURCE'}</span>
            </div>
            <span className="text-xs text-charcoal-caption font-mono">VS</span>
            <div className="text-right">
              <span className="text-xs text-charcoal-muted block">Candidate</span>
              <span className="font-mono font-semibold text-charcoal">{candidateCode || 'CANDIDATE'}</span>
            </div>
          </div>
        )}

        {/* Backend Error Alert */}
        {error && (
          <div className="rounded-panel border border-semantic-diff-border bg-semantic-diff-bg p-3.5 flex items-start gap-2.5 text-body-sm text-semantic-diff-text">
            <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
            <div className="flex-1 leading-snug">{error}</div>
          </div>
        )}

        {/* Form */}
        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Target National Material Selector (for OVERRIDE) */}
          {action === 'OVERRIDE' && (
            <div>
              <label
                htmlFor="target-nm-select"
                className="block text-body-sm font-medium text-charcoal mb-1"
              >
                Target National Material <span className="text-semantic-diff-text">*</span>
              </label>
              {loadingNms ? (
                <div className="p-2.5 text-body-sm text-charcoal-muted border border-border rounded-input bg-surface-secondary">
                  Loading National Materials catalog...
                </div>
              ) : nationalMaterials.length === 0 ? (
                <div className="p-2.5 text-body-sm text-semantic-diff-text border border-semantic-diff-border rounded-input bg-semantic-diff-bg">
                  No existing National Materials available in system.
                </div>
              ) : (
                <select
                  id="target-nm-select"
                  value={nationalMaterialId}
                  onChange={(e) => setNationalMaterialId(e.target.value)}
                  disabled={submitting}
                  className="w-full px-3 py-2 rounded-input border border-border bg-surface text-charcoal text-body-sm focus:border-border-strong focus:outline-none transition-colors"
                >
                  {nationalMaterials.map((nm) => (
                    <option key={nm.id} value={nm.id}>
                      {nm.national_code} — {nm.canonical_description}
                    </option>
                  ))}
                </select>
              )}
              <p className="text-xs text-charcoal-caption mt-1">
                Select the target standardized catalog item from existing National Materials.
              </p>
            </div>
          )}

          {/* Reason Textarea */}
          <div>
            <label
              htmlFor="action-reason"
              className="block text-body-sm font-medium text-charcoal mb-1"
            >
              Review Reason {isReasonRequired ? <span className="text-semantic-diff-text">*</span> : <span className="text-xs text-charcoal-caption font-normal">(Optional)</span>}
            </label>
            <textarea
              id="action-reason"
              rows={3}
              required={isReasonRequired}
              disabled={submitting}
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder={
                isReasonRequired
                  ? 'Enter specific justification for governance audit log (required)...'
                  : 'Optional notes or justification for this decision...'
              }
              className="w-full px-3 py-2 rounded-input border border-border bg-surface text-charcoal text-body-sm placeholder:text-charcoal-disabled focus:border-border-strong focus:outline-none transition-colors resize-none"
            />
            <p className="text-xs text-charcoal-caption mt-1">
              Recorded in the immutable governance audit trail.
            </p>
          </div>

          {/* Modal Footer */}
          <div className="pt-3 flex items-center justify-end gap-3 border-t border-border/80">
            <button
              type="button"
              onClick={onClose}
              disabled={submitting}
              className="px-3.5 py-2 rounded-input border border-border text-charcoal-muted hover:text-charcoal hover:bg-surface-secondary text-body-sm font-medium transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={submitting}
              className={`inline-flex items-center gap-1.5 px-4 py-2 rounded-input text-body-sm font-medium transition-colors disabled:opacity-50 shadow-xs ${config.btnClass}`}
            >
              {submitting ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Submitting Action...</span>
                </>
              ) : (
                <span>{config.btnText}</span>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
