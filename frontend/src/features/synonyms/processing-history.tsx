import React, { useState, useEffect, useCallback } from 'react';
import { Button, LoadingState, EmptyState, ErrorState, StatusBadge } from '../../components';
import { ApiClientError } from '../../lib/api-client';
import { fetchSynonymProcessingRuns } from './api';
import type { SynonymProcessingResource } from './types';

export const ProcessingHistory: React.FC = () => {
  const [runs, setRuns] = useState<SynonymProcessingResource[]>([]);
  const [total, setTotal] = useState<number>(0);
  const [page, setPage] = useState<number>(1);
  const pageSize = 20;
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const loadRuns = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchSynonymProcessingRuns(page, pageSize);
      setRuns(data.items);
      setTotal(data.total);
    } catch (err: any) {
      const msg = err instanceof ApiClientError ? err.message : 'Failed to load synonym processing history.';
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, [page, pageSize]);

  useEffect(() => {
    loadRuns();
  }, [loadRuns]);

  const totalPages = Math.ceil(total / pageSize) || 1;

  return (
    <div className='synonym-processing-history' style={{ display: 'grid', gap: 16 }}>
      <div
        className='table-card'
        style={{
          padding: 16,
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
        }}
      >
        <div>
          <h3 style={{ margin: '0 0 2px', fontSize: 15 }}>Automated & Batch Processing History</h3>
          <p style={{ margin: 0, fontSize: 13, color: 'var(--muted)' }}>
            Audit log of synonym ingestions, batch reviews, and policy activation cycles.
          </p>
        </div>
        <Button variant='secondary' size='compact' onClick={loadRuns} disabled={loading}>
          Refresh History
        </Button>
      </div>

      {loading ? (
        <LoadingState message='Loading processing history...' />
      ) : error ? (
        <ErrorState message={error} onRetry={loadRuns} />
      ) : runs.length === 0 ? (
        <EmptyState
          title='No Processing Runs'
          description='No synonym processing runs or auto-accept cycles have been recorded yet.'
        />
      ) : (
        <div className='table-card'>
          <div className='table-scroll' tabIndex={0} role='region' aria-label='Processing runs table'>
            <table className='data-table'>
              <thead>
                <tr>
                  <th>Processing Run ID</th>
                  <th>Timestamp</th>
                  <th>Source Operation</th>
                  <th>Total Processed</th>
                  <th>Approved</th>
                  <th>Declined</th>
                  <th>Added to Policy</th>
                  <th>Issues</th>
                </tr>
              </thead>
              <tbody>
                {runs.map((run) => (
                  <tr key={run.processing_run_id}>
                    <td style={{ fontFamily: 'monospace', fontSize: 12, fontWeight: 600 }}>
                      {run.processing_run_id}
                    </td>
                    <td style={{ fontSize: 12, color: 'var(--muted)' }}>
                      {run.processed_at ? new Date(run.processed_at).toLocaleString() : 'N/A'}
                    </td>
                    <td>
                      <span style={{ fontSize: 12, fontWeight: 500 }}>
                        {run.source_operation || 'Manual / Batch'}
                      </span>
                    </td>
                    <td style={{ fontSize: 13, fontWeight: 600 }}>{run.total_processed}</td>
                    <td style={{ fontSize: 13, color: 'var(--success, #16a34a)' }}>
                      {run.approved_count}
                    </td>
                    <td style={{ fontSize: 13, color: 'var(--danger, #dc2626)' }}>
                      {run.declined_count}
                    </td>
                    <td style={{ fontSize: 13, fontWeight: 600 }}>
                      {run.successfully_added_count}
                    </td>
                    <td>
                      {run.issue_count > 0 ? (
                        <StatusBadge status='danger' label={run.issue_count + ' issues'} />
                      ) : (
                        <StatusBadge status='neutral' label='0 issues' />
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

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
              Showing {runs.length} of {total} processing records
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
    </div>
  );
};
