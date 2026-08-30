import React, { useState, useEffect, useCallback } from 'react';
import { Button, StatusBadge, LoadingState, EmptyState, ErrorState } from '../../components';
import { ApiClientError } from '../../lib/api-client';
import {
  fetchSynonymSuggestions,
  approveSynonymSuggestions,
  declineSynonymSuggestions,
  clearSynonymSuggestions,
  fetchSynonymPolicy,
} from './api';
import { SuggestionDetailDialog } from './suggestion-detail-dialog';
import type {
  SynonymType,
  ReviewStatus,
  SynonymSuggestionResource,
  SynonymSuggestionQuery,
} from './types';

export interface SuggestionQueueProps {
  onQueueChanged?: () => void;
}

export const SuggestionQueue: React.FC<SuggestionQueueProps> = ({ onQueueChanged }) => {
  const [items, setItems] = useState<SynonymSuggestionResource[]>([]);
  const [total, setTotal] = useState<number>(0);
  const [page, setPage] = useState<number>(1);
  const [pageSize, setPageSize] = useState<10 | 20 | 50>(20);
  const [selectedType, setSelectedType] = useState<SynonymType | 'all'>('all');
  const [selectedStatus, setSelectedStatus] = useState<ReviewStatus | 'all'>('pending');
  const [search, setSearch] = useState<string>('');
  const [counts, setCounts] = useState<Record<string, { pending?: number; approved?: number; declined?: number; total?: number }>>({});

  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [feedback, setFeedback] = useState<string | null>(null);
  const [acting, setActing] = useState<boolean>(false);

  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [detailSuggestionId, setDetailSuggestionId] = useState<string | null>(null);
  const [isDetailOpen, setIsDetailOpen] = useState<boolean>(false);

  const loadSuggestions = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const query: SynonymSuggestionQuery = {
        type: selectedType,
        status: selectedStatus,
        search: search.trim() || undefined,
        page,
        pageSize,
      };
      const result = await fetchSynonymSuggestions(query);
      setItems(result.items);
      setTotal(result.total);
      setCounts(result.counts || {});
      setSelectedIds(new Set());
    } catch (err: any) {
      const msg = err instanceof ApiClientError ? err.message : 'Failed to load synonym suggestions.';
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, [selectedType, selectedStatus, search, page, pageSize]);

  useEffect(() => {
    loadSuggestions();
  }, [loadSuggestions]);

  const toggleSelect = (id: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  const toggleSelectAll = () => {
    if (selectedIds.size === items.length && items.length > 0) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(items.map((i) => i.suggestion_id)));
    }
  };

  const handleBatchApprove = async () => {
    const ids = Array.from(selectedIds);
    if (ids.length === 0) return;

    setActing(true);
    setError(null);
    setFeedback(null);

    try {
      const selectedItems = items.filter((i) => ids.includes(i.suggestion_id));
      const groupedByType: Record<string, string[]> = {};
      for (const item of selectedItems) {
        if (!groupedByType[item.synonym_type]) {
          groupedByType[item.synonym_type] = [];
        }
        groupedByType[item.synonym_type].push(item.suggestion_id);
      }

      let totalApproved = 0;
      for (const [type, typeIds] of Object.entries(groupedByType)) {
        const policy = await fetchSynonymPolicy(type as SynonymType);
        await approveSynonymSuggestions(typeIds, policy.draft_revision, policy.active_bundle_revision_id);
        totalApproved += typeIds.length;
      }

      setFeedback('Approved ' + totalApproved + ' synonym suggestion(s).');
      if (onQueueChanged) onQueueChanged();
      await loadSuggestions();
    } catch (err: any) {
      const msg = err instanceof ApiClientError ? err.message : 'Failed to approve selected suggestions.';
      setError(msg);
    } finally {
      setActing(false);
    }
  };

  const handleBatchDecline = async () => {
    const ids = Array.from(selectedIds);
    if (ids.length === 0) return;

    setActing(true);
    setError(null);
    setFeedback(null);

    try {
      await declineSynonymSuggestions(ids);
      setFeedback('Declined ' + ids.length + ' synonym suggestion(s).');
      if (onQueueChanged) onQueueChanged();
      await loadSuggestions();
    } catch (err: any) {
      const msg = err instanceof ApiClientError ? err.message : 'Failed to decline selected suggestions.';
      setError(msg);
    } finally {
      setActing(false);
    }
  };

  const handleBatchClear = async () => {
    const ids = Array.from(selectedIds);
    if (ids.length === 0) return;

    setActing(true);
    setError(null);
    setFeedback(null);

    try {
      await clearSynonymSuggestions(ids);
      setFeedback('Reset ' + ids.length + ' synonym suggestion(s) to pending.');
      if (onQueueChanged) onQueueChanged();
      await loadSuggestions();
    } catch (err: any) {
      const msg = err instanceof ApiClientError ? err.message : 'Failed to reset selected suggestions.';
      setError(msg);
    } finally {
      setActing(false);
    }
  };

  const handleQuickApprove = async (item: SynonymSuggestionResource) => {
    setActing(true);
    setError(null);
    setFeedback(null);
    try {
      const policy = await fetchSynonymPolicy(item.synonym_type);
      await approveSynonymSuggestions(
        [item.suggestion_id],
        policy.draft_revision,
        policy.active_bundle_revision_id
      );
      setFeedback('Approved: ' + item.alias + ' -> ' + item.canonical);
      if (onQueueChanged) onQueueChanged();
      await loadSuggestions();
    } catch (err: any) {
      const msg = err instanceof ApiClientError ? err.message : 'Failed to approve suggestion.';
      setError(msg);
    } finally {
      setActing(false);
    }
  };

  const handleQuickDecline = async (item: SynonymSuggestionResource) => {
    setActing(true);
    setError(null);
    setFeedback(null);
    try {
      await declineSynonymSuggestions([item.suggestion_id]);
      setFeedback('Declined: ' + item.alias + ' -> ' + item.canonical);
      if (onQueueChanged) onQueueChanged();
      await loadSuggestions();
    } catch (err: any) {
      const msg = err instanceof ApiClientError ? err.message : 'Failed to decline suggestion.';
      setError(msg);
    } finally {
      setActing(false);
    }
  };

  const openDetail = (suggestionId: string) => {
    setDetailSuggestionId(suggestionId);
    setIsDetailOpen(true);
  };

  const totalPages = Math.ceil(total / pageSize) || 1;
  const isAllSelected = items.length > 0 && selectedIds.size === items.length;

  const totalPending =
    (counts.skills?.pending || 0) + (counts.domain?.pending || 0) + (counts.role_family?.pending || 0);

  return (
    <div className='synonym-suggestion-queue' style={{ display: 'grid', gap: 16 }}>
      {/* Feedback message */}
      {feedback && (
        <div
          role='status'
          style={{
            padding: '10px 14px',
            borderRadius: 'var(--radius)',
            backgroundColor: 'rgba(34, 197, 94, 0.1)',
            color: 'var(--success, #16a34a)',
            fontSize: 13,
            fontWeight: 500,
          }}
        >
          {feedback}
        </div>
      )}

      {/* Error message */}
      {error && (
        <div
          role='alert'
          style={{
            padding: '10px 14px',
            borderRadius: 'var(--radius)',
            backgroundColor: 'rgba(239, 68, 68, 0.1)',
            color: 'var(--danger, #dc2626)',
            fontSize: 13,
          }}
        >
          {error}
        </div>
      )}

      {/* Filters Bar */}
      <div
        className='table-card'
        style={{
          padding: 16,
          display: 'flex',
          flexWrap: 'wrap',
          gap: 12,
          alignItems: 'center',
          justifyContent: 'space-between',
        }}
      >
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10, alignItems: 'center' }}>
          {/* Type Filter */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <label htmlFor='synonym-type-filter' style={{ fontSize: 12, fontWeight: 600, color: 'var(--muted)' }}>
              Type:
            </label>
            <select
              id='synonym-type-filter'
              className='field-select'
              value={selectedType}
              onChange={(e) => {
                setSelectedType(e.target.value as any);
                setPage(1);
              }}
              style={{ fontSize: 13, padding: '4px 8px' }}
            >
              <option value='all'>All Types</option>
              <option value='skills'>Skills ({counts.skills?.total || 0})</option>
              <option value='domain'>Domain ({counts.domain?.total || 0})</option>
              <option value='role_family'>Role Family ({counts.role_family?.total || 0})</option>
            </select>
          </div>

          {/* Status Filter */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <label htmlFor='synonym-status-filter' style={{ fontSize: 12, fontWeight: 600, color: 'var(--muted)' }}>
              Status:
            </label>
            <select
              id='synonym-status-filter'
              className='field-select'
              value={selectedStatus}
              onChange={(e) => {
                setSelectedStatus(e.target.value as any);
                setPage(1);
              }}
              style={{ fontSize: 13, padding: '4px 8px' }}
            >
              <option value='pending'>Pending ({totalPending})</option>
              <option value='approved'>Approved</option>
              <option value='declined'>Declined</option>
              <option value='all'>All Statuses</option>
            </select>
          </div>

          {/* Search Input */}
          <div style={{ display: 'flex', alignItems: 'center' }}>
            <input
              type='search'
              placeholder='Search alias or canonical...'
              value={search}
              onChange={(e) => {
                setSearch(e.target.value);
                setPage(1);
              }}
              style={{
                fontSize: 13,
                padding: '5px 10px',
                borderRadius: 'var(--radius)',
                border: '1px solid var(--border)',
                minWidth: 200,
              }}
            />
          </div>
        </div>

        {/* Page size & Refresh */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <select
            value={pageSize}
            onChange={(e) => {
              setPageSize(Number(e.target.value) as any);
              setPage(1);
            }}
            style={{ fontSize: 12, padding: '4px 6px', border: '1px solid var(--border)', borderRadius: 'var(--radius)' }}
            aria-label='Page size'
          >
            <option value={10}>10 / page</option>
            <option value={20}>20 / page</option>
            <option value={50}>50 / page</option>
          </select>
          <Button variant='secondary' size='compact' onClick={loadSuggestions} disabled={loading}>
            Refresh
          </Button>
        </div>
      </div>

      {/* Batch Action Toolbar */}
      {selectedIds.size > 0 && (
        <div
          className='table-card'
          style={{
            padding: '12px 16px',
            backgroundColor: 'var(--accent-soft, rgba(59, 130, 246, 0.08))',
            borderColor: 'var(--accent)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            flexWrap: 'wrap',
            gap: 12,
          }}
        >
          <div style={{ fontSize: 13, fontWeight: 600 }}>
            {selectedIds.size} suggestion(s) selected
          </div>
          <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
            <Button
              variant='primary'
              size='compact'
              onClick={handleBatchApprove}
              loading={acting}
              disabled={acting}
            >
              Approve Selected ({selectedIds.size})
            </Button>
            <Button
              variant='danger'
              size='compact'
              onClick={handleBatchDecline}
              loading={acting}
              disabled={acting}
            >
              Decline Selected ({selectedIds.size})
            </Button>
            <Button
              variant='secondary'
              size='compact'
              onClick={handleBatchClear}
              loading={acting}
              disabled={acting}
            >
              Reset to Pending
            </Button>
            <Button
              variant='subtle'
              size='compact'
              onClick={() => setSelectedIds(new Set())}
            >
              Clear Selection
            </Button>
          </div>
        </div>
      )}

      {/* Main Table */}
      {loading ? (
        <LoadingState message='Loading synonym review queue...' />
      ) : error && items.length === 0 ? (
        <ErrorState message={error} onRetry={loadSuggestions} />
      ) : items.length === 0 ? (
        <EmptyState
          title='No Synonym Suggestions'
          description={
            search
              ? 'No suggestions matched your query   + search +  .'
              : 'No suggestions found for current filter.'
          }
          actionLabel='Reset Filters'
          onAction={() => {
            setSelectedType('all');
            setSelectedStatus('all');
            setSearch('');
            setPage(1);
          }}
        />
      ) : (
        <div className='table-card'>
          <div className='table-scroll' tabIndex={0} role='region' aria-label='Synonym suggestions table'>
            <table className='data-table'>
              <thead>
                <tr>
                  <th style={{ width: 40 }}>
                    <input
                      type='checkbox'
                      aria-label='Select all suggestions on current page'
                      checked={isAllSelected}
                      onChange={toggleSelectAll}
                    />
                  </th>
                  <th>Type</th>
                  <th>Alias</th>
                  <th>Canonical Term</th>
                  <th>Status</th>
                  <th>Sources</th>
                  <th>Updated</th>
                  <th style={{ textAlign: 'right' }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {items.map((item) => {
                  const isSelected = selectedIds.has(item.suggestion_id);
                  return (
                    <tr key={item.suggestion_id} className={isSelected ? 'is-selected' : undefined}>
                      <td>
                        <input
                          type='checkbox'
                          aria-label={'Select suggestion ' + item.alias}
                          checked={isSelected}
                          onChange={() => toggleSelect(item.suggestion_id)}
                        />
                      </td>
                      <td>
                        <span style={{ fontSize: 11, textTransform: 'uppercase', fontWeight: 700, color: 'var(--muted)' }}>
                          {item.synonym_type}
                        </span>
                      </td>
                      <td>
                        <code style={{ fontSize: 13, fontWeight: 600 }}>{item.alias}</code>
                      </td>
                      <td>
                        <code style={{ fontSize: 13, color: 'var(--accent)' }}>{item.canonical}</code>
                      </td>
                      <td>
                        <StatusBadge
                          status={
                            item.review_status === 'approved'
                              ? 'success'
                              : item.review_status === 'declined'
                              ? 'danger'
                              : 'warn'
                          }
                          label={item.review_status}
                        />
                      </td>
                      <td>
                        <span style={{ fontSize: 12 }}>{item.source_count ?? 1} run(s)</span>
                      </td>
                      <td>
                        <span style={{ fontSize: 12, color: 'var(--muted)' }}>
                          {item.updated_at ? new Date(item.updated_at).toLocaleDateString() : 'N/A'}
                        </span>
                      </td>
                      <td style={{ textAlign: 'right' }}>
                        <div style={{ display: 'inline-flex', gap: 6 }}>
                          <Button
                            variant='subtle'
                            size='compact'
                            onClick={() => openDetail(item.suggestion_id)}
                          >
                            Details
                          </Button>
                          {item.review_status !== 'approved' && (
                            <Button
                              variant='primary'
                              size='compact'
                              onClick={() => handleQuickApprove(item)}
                              disabled={acting}
                            >
                              Approve
                            </Button>
                          )}
                          {item.review_status === 'pending' && (
                            <Button
                              variant='danger'
                              size='compact'
                              onClick={() => handleQuickDecline(item)}
                              disabled={acting}
                            >
                              Decline
                            </Button>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {/* Pagination Footer */}
          <div
            style={{
              padding: '12px 16px',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              borderTop: '1px solid var(--border)',
              fontSize: 13,
            }}
          >
            <div style={{ color: 'var(--muted)' }}>
              Showing {items.length} of {total} total suggestions (Page {page} of {totalPages})
            </div>
            <div style={{ display: 'flex', gap: 8 }}>
              <Button
                variant='secondary'
                size='compact'
                disabled={page <= 1 || loading}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
              >
                Previous
              </Button>
              <Button
                variant='secondary'
                size='compact'
                disabled={page >= totalPages || loading}
                onClick={() => setPage((p) => p + 1)}
              >
                Next
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Suggestion Detail Dialog */}
      <SuggestionDetailDialog
        suggestionId={detailSuggestionId}
        open={isDetailOpen}
        onClose={() => {
          setIsDetailOpen(false);
          setDetailSuggestionId(null);
        }}
        onActionComplete={() => {
          loadSuggestions();
          if (onQueueChanged) onQueueChanged();
        }}
      />
    </div>
  );
};
