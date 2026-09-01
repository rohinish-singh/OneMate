import React, { useState, useEffect, useCallback } from 'react';
import {
  ShieldCheck,
  RefreshCw,
  Search,
  Check,
} from 'lucide-react';
import { api, ApiClientError } from '../api/client';
import type { NationalMaterialListItem } from '../types/api';
import { LoadingState } from '../components/common/LoadingState';
import { ErrorState } from '../components/common/ErrorState';
import { EmptyState } from '../components/common/EmptyState';
import { Badge } from '../components/common/Badge';
import { NationalMaterialInspector } from '../components/national-materials/NationalMaterialInspector';

export const NationalMaterialsPage: React.FC = () => {
  const [items, setItems] = useState<NationalMaterialListItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState<string>('');
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const fetchItems = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.nationalMaterials.list(0, 100);
      setItems(data);
    } catch (err: unknown) {
      if (err instanceof ApiClientError) {
        setError(err.message);
      } else if (err instanceof Error) {
        setError(err.message);
      } else {
        setError('Failed to fetch National Materials catalog.');
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchItems();
  }, [fetchItems]);

  const filteredItems = items.filter((item) => {
    const q = search.toLowerCase().trim();
    if (!q) return true;
    return (
      item.national_code.toLowerCase().includes(q) ||
      item.canonical_description.toLowerCase().includes(q) ||
      (item.status && item.status.toLowerCase().includes(q))
    );
  });

  return (
    <div className="p-4 sm:p-6 lg:p-8 max-w-7xl w-full mx-auto space-y-6 flex flex-col min-h-[calc(100vh-4rem)]">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 shrink-0">
        <div>
          <h1 className="text-page-title text-charcoal">National Material Registry</h1>
          <p className="text-body text-charcoal-muted mt-1">
            Standardized material catalog
          </p>
        </div>

        <div className="flex flex-col sm:flex-row sm:items-center gap-3">
          <div className="relative w-full sm:w-auto">
            <Search className="w-3.5 h-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-charcoal-caption" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search by code or description..."
              className="pl-8 pr-3 py-1.5 text-body-sm rounded-input border border-border bg-surface text-charcoal placeholder:text-charcoal-disabled focus:border-border-strong focus:outline-none transition-colors w-full sm:w-64"
            />
          </div>

          <button
            type="button"
            onClick={fetchItems}
            disabled={loading}
            title="Refresh registry"
            className="p-2 rounded-input border border-border bg-surface text-charcoal-muted hover:text-charcoal hover:bg-surface-secondary transition-colors disabled:opacity-50 self-end sm:self-auto"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>


      {/* Main Workspace Area */}
      {loading && items.length === 0 ? (
        <LoadingState message="Loading National Material registry..." className="py-20" />
      ) : error ? (
        <ErrorState
          title="Unable to load National Materials"
          message={error}
          onRetry={fetchItems}
        />
      ) : items.length === 0 ? (
        <EmptyState
          icon={<ShieldCheck className="w-5 h-5" />}
          title="No National Materials registered"
          description="The standardized national catalog is currently empty."
        />
      ) : (
        <div className="flex-1 flex flex-col lg:flex-row gap-0 rounded-panel border border-border bg-surface overflow-hidden shadow-xs min-h-[480px]">
          {/* Master Table */}
          <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
            <div className="flex-1 overflow-auto">
              <table className="w-full text-left border-collapse">
                <thead className="sticky top-0 z-10 bg-surface-secondary/80 border-b border-border text-table-header text-charcoal-caption uppercase">
                  <tr>
                    <th scope="col" className="py-2.5 px-4 font-medium w-10 text-center">
                      #
                    </th>
                    <th scope="col" className="py-2.5 px-4 font-medium min-w-[160px]">
                      National Code
                    </th>
                    <th scope="col" className="py-2.5 px-4 font-medium min-w-[320px]">
                      Canonical Description
                    </th>
                    <th scope="col" className="py-2.5 px-4 font-medium w-28 text-right">
                      Status
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border/60 text-body">
                  {filteredItems.map((item, idx) => {
                    const isSelected = selectedId === item.id;

                    return (
                      <tr
                        key={item.id}
                        onClick={() => setSelectedId(item.id)}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter' || e.key === ' ') {
                            e.preventDefault();
                            setSelectedId(item.id);
                          }
                        }}
                        tabIndex={0}
                        className={`group cursor-pointer transition-colors outline-none focus-visible:bg-surface-secondary ${
                          isSelected
                            ? 'bg-brand-tint/60 ring-1 ring-inset ring-brand/20'
                            : 'hover:bg-surface-hover'
                        }`}
                      >
                        {/* Index */}
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

                        {/* National Code */}
                        <td className="py-3 px-4 whitespace-nowrap">
                          <span
                            className="font-mono text-body-sm font-semibold text-charcoal bg-surface-secondary/80 px-2 py-0.5 rounded-badge border border-border/60"
                            title={item.national_code}
                          >
                            {item.national_code}
                          </span>
                        </td>

                        {/* Canonical Description */}
                        <td className="py-3 px-4 text-charcoal leading-snug max-w-lg">
                          <span className="line-clamp-2" title={item.canonical_description}>
                            {item.canonical_description}
                          </span>
                        </td>

                        {/* Status */}
                        <td className="py-3 px-4 text-right whitespace-nowrap">
                          {item.status ? (
                            <Badge variant={item.status === 'ACTIVE' ? 'same' : 'neutral'}>
                              {item.status}
                            </Badge>
                          ) : (
                            <span className="text-charcoal-disabled italic text-xs">ACTIVE</span>
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
                Standardized items in catalog:{' '}
                <strong className="font-medium text-charcoal">{items.length}</strong>
                {filteredItems.length !== items.length && (
                  <span className="ml-1 text-xs">({filteredItems.length} matching search)</span>
                )}
              </span>
              <span className="text-xs">
                {selectedId
                  ? 'Viewing specification in inspector'
                  : 'Click any row to inspect standardized attributes'}
              </span>
            </div>
          </div>

          {/* Inspector Panel */}
          {selectedId && (
            <NationalMaterialInspector
              nationalMaterialId={selectedId}
              onClose={() => setSelectedId(null)}
            />
          )}
        </div>
      )}
    </div>
  );
};

