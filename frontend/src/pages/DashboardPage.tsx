import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  RefreshCw,
  ArrowRight,
  Building2,
} from 'lucide-react';
import { api, ApiClientError } from '../api/client';
import type { DashboardResponse } from '../types/api';
import { LoadingState } from '../components/common/LoadingState';
import { ErrorState } from '../components/common/ErrorState';

export const DashboardPage: React.FC = () => {
  const navigate = useNavigate();
  const [data, setData] = useState<DashboardResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchDashboard = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await api.dashboard.get();
      setData(response);
    } catch (err: unknown) {
      if (err instanceof ApiClientError) {
        setError(err.message);
      } else if (err instanceof Error) {
        setError(err.message);
      } else {
        setError('Failed to fetch dashboard metrics.');
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchDashboard();
  }, [fetchDashboard]);

  if (loading && !data) {
    return (
      <div className="p-8 max-w-7xl w-full mx-auto space-y-6">
        <div>
          <h1 className="text-page-title text-charcoal">Material Operations</h1>
        </div>
        <LoadingState message="Loading operational metrics..." className="py-24" />
      </div>
    );
  }

  if (error && !data) {
    return (
      <div className="p-8 max-w-7xl w-full mx-auto space-y-6">
        <div>
          <h1 className="text-page-title text-charcoal">Material Operations</h1>
        </div>
        <ErrorState
          title="Unable to load dashboard"
          message={error}
          onRetry={fetchDashboard}
        />
      </div>
    );
  }

  const inventory = data?.inventory ?? { total_materials: 0, total_cpses: 0 };
  const harmonization = data?.harmonization ?? {
    total_national_materials: 0,
    total_mapped_materials: 0,
    automation_rate_percentage: 0,
  };
  const review = data?.review ?? { pending_reviews: 0, completed_reviews: 0 };
  const breakdown = data?.cpse_breakdown ?? [];

  return (
    <div className="p-4 sm:p-6 lg:p-8 max-w-7xl w-full mx-auto space-y-6 sm:space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-page-title text-charcoal">Material Operations</h1>
          <p className="text-body text-charcoal-muted mt-0.5">
            Operational catalog overview and metrics
          </p>
        </div>

        <button
          type="button"
          onClick={fetchDashboard}
          disabled={loading}
          title="Refresh metrics"
          className="p-2 rounded-input border border-border bg-surface text-charcoal-muted hover:text-charcoal hover:bg-surface-secondary transition-colors disabled:opacity-50"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
        </button>
      </div>

      {/* Editorial Typographic Summary Strip */}
      <div className="rounded-panel border border-border bg-border shadow-xs grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-px overflow-hidden">
        {/* 1. Materials */}
        <div className="p-4 sm:p-5 bg-surface flex flex-col justify-between space-y-2">
          <div>
            <span className="text-xs font-semibold text-charcoal-caption uppercase tracking-wider block">
              Materials
            </span>
            <div className="font-mono text-2xl lg:text-3xl font-bold text-charcoal mt-1">
              {inventory.total_materials.toLocaleString()}
            </div>
          </div>
          <p className="text-xs text-charcoal-muted truncate" title={`across ${inventory.total_cpses.toLocaleString()} CPSEs`}>
            across {inventory.total_cpses.toLocaleString()} CPSEs
          </p>
        </div>

        {/* 2. Mapped */}
        <div className="p-4 sm:p-5 bg-surface flex flex-col justify-between space-y-2">
          <div>
            <span className="text-xs font-semibold text-charcoal-caption uppercase tracking-wider block">
              Mapped
            </span>
            <div className="font-mono text-2xl lg:text-3xl font-bold text-charcoal mt-1">
              {harmonization.total_mapped_materials.toLocaleString()}
            </div>
          </div>
          <p className="text-xs text-charcoal-muted">
            active mappings
          </p>
        </div>

        {/* 3. National Materials */}
        <div className="p-4 sm:p-5 bg-surface flex flex-col justify-between space-y-2">
          <div>
            <span className="text-xs font-semibold text-charcoal-caption uppercase tracking-wider block">
              National Materials
            </span>
            <div className="font-mono text-2xl lg:text-3xl font-bold text-charcoal mt-1">
              {harmonization.total_national_materials.toLocaleString()}
            </div>
          </div>
          <p className="text-xs text-charcoal-muted">
            canonical items
          </p>
        </div>

        {/* 4. Automation */}
        <div className="p-4 sm:p-5 bg-surface flex flex-col justify-between space-y-2">
          <div>
            <span className="text-xs font-semibold text-charcoal-caption uppercase tracking-wider block">
              Automation
            </span>
            <div className="font-mono text-2xl lg:text-3xl font-bold text-charcoal mt-1">
              {harmonization.automation_rate_percentage}%
            </div>
          </div>
          <p className="text-xs text-charcoal-muted">
            auto-harmonized
          </p>
        </div>

        {/* 5. Pending Review */}
        <div className="p-4 sm:p-5 bg-surface-secondary/40 flex flex-col justify-between space-y-2">
          <div>
            <span className="text-xs font-semibold text-charcoal-caption uppercase tracking-wider block">
              Pending Review
            </span>
            <div className={`font-mono text-2xl lg:text-3xl font-bold mt-1 ${
              review.pending_reviews > 0 ? 'text-amber-800' : 'text-charcoal'
            }`}>
              {review.pending_reviews.toLocaleString()}
            </div>
          </div>
          <button
            type="button"
            onClick={() => navigate('/review')}
            className="inline-flex items-center gap-1 text-xs font-semibold text-brand hover:underline text-left"
          >
            <span>Review Queue</span>
            <ArrowRight className="w-3 h-3" />
          </button>
        </div>

        {/* 6. Decisions Recorded */}
        <div className="p-4 sm:p-5 bg-surface flex flex-col justify-between space-y-2">
          <div>
            <span className="text-xs font-semibold text-charcoal-caption uppercase tracking-wider block">
              Decisions Recorded
            </span>
            <div className="font-mono text-2xl lg:text-3xl font-bold text-charcoal mt-1">
              {review.completed_reviews.toLocaleString()}
            </div>
          </div>
          <p className="text-xs text-charcoal-muted">
            governance log
          </p>
        </div>
      </div>


      {/* CPSE Breakdown Table */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h3 className="text-section-title text-charcoal">CPSE Catalog Breakdown</h3>
          <button
            type="button"
            onClick={() => navigate('/cpses')}
            className="text-xs font-semibold text-brand hover:underline"
          >
            Manage CPSEs →
          </button>
        </div>

        <div className="rounded-panel border border-border bg-surface overflow-hidden shadow-xs">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-surface-secondary/80 border-b border-border text-table-header text-charcoal-caption uppercase">
                  <th scope="col" className="py-2.5 px-4 font-medium w-10 text-center">
                    #
                  </th>
                  <th scope="col" className="py-2.5 px-4 font-medium min-w-[240px]">
                    Enterprise
                  </th>
                  <th scope="col" className="py-2.5 px-4 font-medium min-w-[130px] text-right">
                    Materials
                  </th>
                  <th scope="col" className="py-2.5 px-4 font-medium min-w-[130px] text-right">
                    Mapped
                  </th>
                  <th scope="col" className="py-2.5 px-4 font-medium min-w-[160px] text-right">
                    Progress
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border/60 text-body">
                {breakdown.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="py-8 text-center text-xs text-charcoal-muted">
                      No CPSE enterprises registered.
                    </td>
                  </tr>
                ) : (
                  breakdown.map((item, idx) => {
                    const percent =
                      item.total_materials > 0
                        ? Math.min(100, Math.round((item.mapped_materials / item.total_materials) * 100))
                        : 0;

                    return (
                      <tr key={item.cpse_id} className="hover:bg-surface-hover transition-colors">
                        {/* Index */}
                        <td className="py-3 px-4 text-center text-xs text-charcoal-caption">
                          {idx + 1}
                        </td>

                        {/* CPSE Name */}
                        <td className="py-3 px-4">
                          <div className="flex items-center gap-2 max-w-md">
                            <Building2 className="w-3.5 h-3.5 text-charcoal-muted shrink-0" />
                            <span className="font-semibold text-charcoal truncate" title={item.cpse_name}>
                              {item.cpse_name}
                            </span>
                          </div>
                        </td>

                        {/* Total Materials */}
                        <td className="py-3 px-4 font-mono text-body-sm text-charcoal text-right">
                          {item.total_materials.toLocaleString()}
                        </td>

                        {/* Mapped Materials */}
                        <td className="py-3 px-4 font-mono text-body-sm text-charcoal text-right">
                          {item.mapped_materials.toLocaleString()}
                        </td>

                        {/* Progress */}
                        <td className="py-3 px-4 text-right">
                          <div className="inline-flex items-center justify-end gap-2.5">
                            <div className="w-20 h-1.5 bg-surface-secondary rounded-full overflow-hidden border border-border/60 hidden sm:block">
                              <div
                                className="h-full bg-brand rounded-full transition-all duration-300"
                                style={{ width: `${percent}%` }}
                              />
                            </div>
                            <span className="font-mono text-xs font-semibold text-charcoal w-10 text-right">
                              {percent}%
                            </span>
                          </div>
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>

          {/* Table Footer */}
          <div className="px-4 py-2.5 bg-surface-secondary/30 border-t border-border flex items-center justify-between text-body-sm text-charcoal-caption shrink-0">
            <span>
              Participating enterprises: <strong className="font-medium text-charcoal">{breakdown.length}</strong>
            </span>
            <span className="text-xs">
              Central catalog ledger
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};


