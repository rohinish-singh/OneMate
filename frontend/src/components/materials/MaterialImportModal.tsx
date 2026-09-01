import React, { useState, useRef } from 'react';
import {
  X,
  Upload,
  FileSpreadsheet,
  AlertCircle,
  CheckCircle2,
  AlertTriangle,
  Loader2,
  Trash2,
} from 'lucide-react';
import { api, ApiClientError } from '../../api/client';
import type { MaterialImportResponse } from '../../types/api';

interface MaterialImportModalProps {
  isOpen: boolean;
  cpseId: string;
  cpseName: string;
  cpseCode: string;
  onClose: () => void;
  onImportSuccess: () => void;
}

export const MaterialImportModal: React.FC<MaterialImportModalProps> = ({
  isOpen,
  cpseId,
  cpseName,
  cpseCode,
  onClose,
  onImportSuccess,
}) => {
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<MaterialImportResponse | null>(null);
  const [isDragOver, setIsDragOver] = useState<boolean>(false);

  if (!isOpen) return null;

  const handleClose = () => {
    if (uploading) return;
    setFile(null);
    setError(null);
    setResult(null);
    onClose();
  };

  const validateAndSetFile = (selectedFile: File) => {
    setError(null);
    const name = selectedFile.name.toLowerCase();
    if (!name.endsWith('.csv') && !name.endsWith('.xlsx')) {
      setError('Unsupported file format. Please upload a .csv or .xlsx file.');
      return;
    }
    if (selectedFile.size > 5 * 1024 * 1024) {
      setError('File too large. Maximum allowed size is 5MB.');
      return;
    }
    setFile(selectedFile);
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      validateAndSetFile(e.target.files[0]);
    }
  };

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragOver(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      validateAndSetFile(e.dataTransfer.files[0]);
    }
  };

  const handleDragOver = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragOver(true);
  };

  const handleDragLeave = () => {
    setIsDragOver(false);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) {
      setError('Please select a CSV or XLSX file to import.');
      return;
    }

    setUploading(true);
    setError(null);

    try {
      const response = await api.materials.import(cpseId, file);
      setResult(response);
      onImportSuccess();
    } catch (err: unknown) {
      if (err instanceof ApiClientError) {
        setError(err.message);
      } else if (err instanceof Error) {
        setError(err.message);
      } else {
        setError('An unexpected error occurred during material import.');
      }
    } finally {
      setUploading(false);
    }
  };

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="import-modal-title"
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-charcoal/40 overflow-y-auto"
      onClick={handleClose}
    >
      <div
        className="w-full max-w-lg max-h-[90vh] flex flex-col bg-surface rounded-panel border border-border shadow-xl p-5 sm:p-6 space-y-4 sm:space-y-5 select-text overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >

        {/* Header */}
        <div className="flex items-start justify-between gap-4">
          <div>
            <h3 id="import-modal-title" className="text-section-title text-charcoal">
              {result ? 'Import Summary' : 'Import Materials'}
            </h3>
            <p className="text-body-sm text-charcoal-muted mt-0.5">
              Enterprise: <strong className="text-charcoal font-semibold">{cpseName}</strong>{' '}
              <span className="font-mono text-xs text-charcoal-muted">({cpseCode})</span>
            </p>
          </div>
          <button
            type="button"
            onClick={handleClose}
            disabled={uploading}
            className="p-1 rounded-input text-charcoal-caption hover:text-charcoal hover:bg-surface-secondary transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        {!result ? (
          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Error Message */}
            {error && (
              <div className="rounded-panel border border-semantic-diff-border bg-semantic-diff-bg p-3.5 flex items-start gap-2.5 text-body-sm text-semantic-diff-text">
                <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
                <div className="flex-1 leading-snug">{error}</div>
              </div>
            )}

            {/* Dropzone */}
            <div
              onDrop={handleDrop}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onClick={() => fileInputRef.current?.click()}
              className={`p-6 border-2 border-dashed rounded-panel text-center cursor-pointer transition-colors ${
                isDragOver
                  ? 'border-brand bg-brand-tint/40'
                  : 'border-border hover:border-charcoal-muted bg-surface-secondary/30'
              }`}
            >
              <input
                ref={fileInputRef}
                type="file"
                accept=".csv, .xlsx, text/csv, application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                onChange={handleFileChange}
                className="hidden"
                disabled={uploading}
              />
              <div className="w-10 h-10 mx-auto rounded-input bg-surface-secondary flex items-center justify-center text-charcoal-muted mb-2">
                <Upload className="w-5 h-5" />
              </div>
              <p className="text-body font-medium text-charcoal">
                Click to browse or drag and drop material catalog
              </p>
              <p className="text-xs text-charcoal-caption mt-1">
                Supported formats: CSV, XLSX (maximum 5MB)
              </p>
            </div>

            {/* Selected File Display */}
            {file && (
              <div className="p-3 bg-surface rounded-input border border-border flex items-center justify-between gap-3">
                <div className="flex items-center gap-2.5 min-w-0">
                  <FileSpreadsheet className="w-4 h-4 text-brand shrink-0" />
                  <div className="flex flex-col min-w-0">
                    <span className="text-body-sm font-medium text-charcoal truncate">
                      {file.name}
                    </span>
                    <span className="text-[11px] text-charcoal-caption">
                      {formatFileSize(file.size)}
                    </span>
                  </div>
                </div>

                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    setFile(null);
                  }}
                  disabled={uploading}
                  className="p-1 rounded-input text-charcoal-caption hover:text-semantic-diff-text transition-colors"
                  title="Remove selected file"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            )}

            {/* Footer Buttons */}
            <div className="pt-3 flex items-center justify-end gap-3 border-t border-border/80">
              <button
                type="button"
                onClick={handleClose}
                disabled={uploading}
                className="px-3.5 py-2 rounded-input border border-border text-charcoal-muted hover:text-charcoal hover:bg-surface-secondary text-body font-medium transition-colors"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={uploading || !file}
                className="inline-flex items-center gap-1.5 px-4 py-2 rounded-input bg-brand text-white text-body font-medium hover:bg-brand-hover transition-colors disabled:opacity-50 shadow-xs"
              >
                {uploading ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span>Ingesting Catalog...</span>
                  </>
                ) : (
                  <>
                    <Upload className="w-4 h-4" />
                    <span>Upload & Ingest</span>
                  </>
                )}
              </button>
            </div>
          </form>
        ) : (
          /* RESULT VIEW */
          <div className="space-y-4">
            {/* Metric Summary Grid */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-center">
              <div className="p-3 rounded-input bg-surface-secondary/60 border border-border">
                <span className="text-xs text-charcoal-caption block">Total Rows</span>
                <span className="text-lg font-semibold text-charcoal font-mono">
                  {result.total_rows}
                </span>
              </div>

              <div className="p-3 rounded-input bg-semantic-same-bg border border-semantic-same-border">
                <span className="text-xs text-semantic-same-text block font-medium">Imported</span>
                <span className="text-lg font-semibold text-semantic-same-text font-mono">
                  {result.imported_rows}
                </span>
              </div>

              <div className="p-3 rounded-input bg-semantic-potential-bg border border-semantic-potential-border">
                <span className="text-xs text-semantic-potential-text block font-medium">Duplicates</span>
                <span className="text-lg font-semibold text-semantic-potential-text font-mono">
                  {result.duplicate_rows}
                </span>
              </div>

              <div className="p-3 rounded-input bg-semantic-diff-bg border border-semantic-diff-border">
                <span className="text-xs text-semantic-diff-text block font-medium">Rejected</span>
                <span className="text-lg font-semibold text-semantic-diff-text font-mono">
                  {result.rejected_rows}
                </span>
              </div>
            </div>

            {/* Error Listing */}
            {result.errors.length > 0 ? (
              <div className="space-y-2">
                <div className="flex items-center gap-1.5 text-body-sm font-semibold text-semantic-diff-text">
                  <AlertTriangle className="w-4 h-4" />
                  <span>Validation & Ingestion Issues ({result.errors.length})</span>
                </div>
                <div className="max-h-48 overflow-y-auto rounded-input border border-border bg-surface text-body-sm divide-y divide-border/60">
                  {result.errors.map((err, idx) => (
                    <div key={idx} className="p-2.5 flex items-start gap-2 text-charcoal">
                      <span className="font-mono text-xs bg-surface-secondary px-1.5 py-0.5 rounded-badge text-charcoal-muted shrink-0">
                        Row {err.row}
                      </span>
                      <span className="text-xs text-charcoal leading-snug">{err.error}</span>
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <div className="p-3 rounded-input bg-semantic-same-bg border border-semantic-same-border flex items-center gap-2 text-body-sm text-semantic-same-text">
                <CheckCircle2 className="w-4 h-4 shrink-0" />
                <span>All rows imported cleanly without validation errors.</span>
              </div>
            )}

            {/* Footer */}
            <div className="pt-3 flex justify-end border-t border-border/80">
              <button
                type="button"
                onClick={handleClose}
                className="px-4 py-2 rounded-input bg-brand text-white text-body font-medium hover:bg-brand-hover transition-colors shadow-xs"
              >
                Done
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
