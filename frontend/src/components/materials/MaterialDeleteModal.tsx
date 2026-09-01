import React, { useState, useEffect } from 'react';
import { Trash2, X, AlertCircle, Loader2, KeyRound, Package } from 'lucide-react';
import { api, ApiClientError } from '../../api/client';
import type { MaterialListItem, MaterialDetailResponse } from '../../types/api';

interface MaterialDeleteModalProps {
  isOpen: boolean;
  material: MaterialListItem | MaterialDetailResponse | null;
  onClose: () => void;
  onSuccess: (deletedId: string) => void;
}

export const MaterialDeleteModal: React.FC<MaterialDeleteModalProps> = ({
  isOpen,
  material,
  onClose,
  onSuccess,
}) => {
  const [reviewerToken, setReviewerToken] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen) {
      setReviewerToken('');
      setError(null);
      setLoading(false);
    }
  }, [isOpen]);

  if (!isOpen || !material) {
    return null;
  }

  const handleDelete = async (e: React.FormEvent) => {
    e.preventDefault();
    const token = reviewerToken.trim();
    if (!token) {
      setError('Reviewer token is required to delete a material.');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      await api.materials.delete(material.id, token);
      onSuccess(material.id);
      onClose();
    } catch (err: unknown) {
      if (err instanceof ApiClientError) {
        setError(err.message);
      } else if (err instanceof Error) {
        setError(err.message);
      } else {
        setError('Failed to delete material.');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="delete-material-title"
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 overflow-y-auto"
    >
      <div className="w-full max-w-md max-h-[90vh] flex flex-col bg-surface rounded-panel border border-border shadow-md overflow-hidden animate-in fade-in zoom-in-95 duration-150">
        {/* Header */}
        <div className="flex items-center justify-between px-5 sm:px-6 py-4 border-b border-border bg-surface-secondary/40 shrink-0">
          <div className="flex items-center gap-2 text-semantic-diff-text">
            <Trash2 className="w-5 h-5" />
            <h3 id="delete-material-title" className="text-card-title text-charcoal">
              Delete this material?
            </h3>
          </div>
          <button
            type="button"
            onClick={onClose}
            disabled={loading}
            className="p-1 rounded-input text-charcoal-caption hover:text-charcoal hover:bg-surface-secondary transition-colors disabled:opacity-50"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <form onSubmit={handleDelete} className="p-5 sm:p-6 space-y-4 overflow-y-auto">

          {/* Target Material Identification */}
          <div className="p-3 bg-surface-secondary/60 rounded-panel border border-border space-y-1">
            <div className="flex items-center gap-1.5 text-xs text-charcoal-caption">
              <Package className="w-3.5 h-3.5" />
              <span>Target Material</span>
            </div>
            <div className="font-mono font-semibold text-charcoal text-body">
              {material.source_material_code}
            </div>
            <div className="text-body-sm text-charcoal-muted line-clamp-2" title={material.source_description}>
              {material.source_description}
            </div>
          </div>

          {/* Description & Preservation Notice */}
          <div className="space-y-1 text-body-sm text-charcoal-muted leading-relaxed">
            <p>This removes its matching and mapping records.</p>
            <p className="text-xs text-charcoal-caption pt-1 border-t border-border/50">
              National Materials and audit history are preserved.
            </p>
          </div>

          {/* Error Banner */}
          {error && (
            <div className="p-3 rounded-input bg-semantic-diff-bg border border-semantic-diff-border text-semantic-diff-text text-body-sm flex items-start gap-2">
              <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
              <div className="flex-1 leading-snug">{error}</div>
            </div>
          )}

          {/* Reviewer Token Input */}
          <div className="space-y-1.5 pt-1">
            <label
              htmlFor="material-reviewer-token"
              className="block text-body-sm font-semibold text-charcoal"
            >
              Reviewer Token <span className="text-semantic-diff-text">*</span>
            </label>
            <div className="relative">
              <KeyRound className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-charcoal-caption" />
              <input
                id="material-reviewer-token"
                type="password"
                value={reviewerToken}
                onChange={(e) => setReviewerToken(e.target.value)}
                placeholder="Enter reviewer token..."
                disabled={loading}
                className="w-full pl-9 pr-3 py-2 text-body font-mono rounded-input border border-border bg-surface text-charcoal placeholder:text-charcoal-disabled focus:border-border-strong focus:outline-none transition-colors disabled:opacity-50"
              />
            </div>
          </div>

          {/* Actions */}
          <div className="flex items-center justify-end gap-3 pt-3 border-t border-border">
            <button
              type="button"
              onClick={onClose}
              disabled={loading}
              className="px-4 py-2 rounded-input border border-border text-charcoal text-body font-medium hover:bg-surface-secondary transition-colors disabled:opacity-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading || !reviewerToken.trim()}
              className="inline-flex items-center gap-1.5 px-4 py-2 rounded-input bg-semantic-diff-text text-white text-body font-medium hover:opacity-90 transition-opacity disabled:opacity-50 shadow-xs"
            >
              {loading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Deleting Material...</span>
                </>
              ) : (
                <>
                  <Trash2 className="w-4 h-4" />
                  <span>Delete Material</span>
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

