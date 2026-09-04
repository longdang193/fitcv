import React, { useState, useEffect, useCallback } from 'react';
import { Button, LoadingState, EmptyState, ErrorState, StatusBadge } from '../../components';
import { ApiClientError } from '../../lib/api-client';
import { fetchSynonymProcessingRuns } from './api';
import type { SynonymProcessingResource } from './types';
import { formatTimestamp } from '../../lib/format';

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
      const msg = err instanceof ApiClientError ? err.message : 'Failed to load synonym processing summary.';
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
    <div className='synonym-processing-summary-log'>
      <div className='table-card processing-summary-header'>
        <div>
          <h3>Processing Summary Log</h3>
          <p>Review totals and successfully added mappings for each processing action.</p>
        </div>
        <Button variant='secondary' size='compact' onClick={loadRuns} disabled={loading}>
          Refresh Summary Log
        </Button>
      </div>

      {loading ? (
        <LoadingState message='Loading processing summary...' />
      ) : error ? (
        <ErrorState message={error} onRetry={loadRuns} />
      ) : runs.length === 0 ? (
        <div className='table-card processing-summary-empty'>
          <EmptyState
            title='No Processing Summary'
            description='No synonym processing activity has been recorded yet.'
          />
        </div>
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
                      {formatTimestamp(run.processed_at, 'N/A')}
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
