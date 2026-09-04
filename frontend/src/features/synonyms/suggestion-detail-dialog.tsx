import React, { useState, useEffect } from 'react';
import { Dialog, Button, StatusBadge, LoadingState } from '../../components';
import { ApiClientError } from '../../lib/api-client';
import {
  fetchSynonymSuggestionDetail,
  approveSynonymSuggestions,
  declineSynonymSuggestions,
  clearSynonymSuggestions,
  fetchSynonymPolicy,
} from './api';
import type { SynonymSuggestionResource, SynonymSuggestionSource } from './types';
import { formatIdentifier, formatTimestamp } from '../../lib/format';

export interface SuggestionDetailDialogProps {
  suggestionId: string | null;
  open: boolean;
  onClose: () => void;
  onActionComplete?: () => void;
}

export const SuggestionDetailDialog: React.FC<SuggestionDetailDialogProps> = ({
  suggestionId,
  open,
  onClose,
  onActionComplete,
}) => {
  const [detail, setDetail] = useState<SynonymSuggestionResource | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [acting, setActing] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [feedback, setFeedback] = useState<string | null>(null);
  const [evidencePage, setEvidencePage] = useState<number>(1);
  const [selectedSource, setSelectedSource] = useState<SynonymSuggestionSource | null>(null);

  useEffect(() => {
    if (!open || !suggestionId) {
      setDetail(null);
      setError(null);
      setFeedback(null);
      setSelectedSource(null);
      setEvidencePage(1);
      return;
    }

    const loadDetail = async () => {
      setLoading(true);
      setError(null);
      try {
        const data = await fetchSynonymSuggestionDetail(suggestionId, evidencePage, 20);
        setDetail(data);
      } catch (err: any) {
        const msg = err instanceof ApiClientError ? err.message : 'Failed to load suggestion detail.';
        setError(msg);
      } finally {
        setLoading(false);
      }
    };

    loadDetail();
  }, [open, suggestionId, evidencePage]);

  const handleApprove = async () => {
    if (!detail) return;
    setActing(true);
    setError(null);
    try {
      const policy = await fetchSynonymPolicy(detail.synonym_type);
      await approveSynonymSuggestions(
        [detail.suggestion_id],
        policy.draft_revision,
        policy.active_bundle_revision_id
      );
      setFeedback('Synonym suggestion approved and added to active policy.');
      if (onActionComplete) onActionComplete();
      const updated = await fetchSynonymSuggestionDetail(detail.suggestion_id, evidencePage, 20);
      setDetail(updated);
    } catch (err: any) {
      const msg = err instanceof ApiClientError ? err.message : 'Failed to approve suggestion.';
      setError(msg);
    } finally {
      setActing(false);
    }
  };

  const handleDecline = async () => {
    if (!detail) return;
    setActing(true);
    setError(null);
    try {
      await declineSynonymSuggestions([detail.suggestion_id]);
      setFeedback('Synonym suggestion declined.');
      if (onActionComplete) onActionComplete();
      const updated = await fetchSynonymSuggestionDetail(detail.suggestion_id, evidencePage, 20);
      setDetail(updated);
    } catch (err: any) {
      const msg = err instanceof ApiClientError ? err.message : 'Failed to decline suggestion.';
      setError(msg);
    } finally {
      setActing(false);
    }
  };

  const handleClear = async () => {
    if (!detail) return;
    setActing(true);
    setError(null);
    try {
      await clearSynonymSuggestions([detail.suggestion_id]);
      setFeedback('Synonym suggestion reset to pending.');
      if (onActionComplete) onActionComplete();
      const updated = await fetchSynonymSuggestionDetail(detail.suggestion_id, evidencePage, 20);
      setDetail(updated);
    } catch (err: any) {
      const msg = err instanceof ApiClientError ? err.message : 'Failed to reset suggestion.';
      setError(msg);
    } finally {
      setActing(false);
    }
  };

  const getStatusBadge = (status: string) => {
    if (status === 'approved') return <StatusBadge status='success' label='Approved' />;
    if (status === 'declined') return <StatusBadge status='danger' label='Declined' />;
    return <StatusBadge status='warn' label='Pending' />;
  };

  return (
    <Dialog
      open={open}
      onClose={onClose}
      title={detail ? 'Synonym: ' + detail.alias + ' -> ' + detail.canonical : 'Synonym Suggestion Details'}
      description={detail ? 'Type: ' + detail.synonym_type + ' | Status: ' + detail.review_status : undefined}
    >
      <div style={{ display: 'grid', gap: 16 }}>
        {feedback && (
          <div
            role='status'
            style={{
              padding: '8px 12px',
              borderRadius: 'var(--radius)',
              backgroundColor: 'rgba(34, 197, 94, 0.1)',
              color: 'var(--success, #16a34a)',
              fontSize: 13,
            }}
          >
            {feedback}
          </div>
        )}

        {error && (
          <div
            role='alert'
            style={{
              padding: '8px 12px',
              borderRadius: 'var(--radius)',
              backgroundColor: 'rgba(239, 68, 68, 0.1)',
              color: 'var(--danger, #dc2626)',
              fontSize: 13,
            }}
          >
            {error}
          </div>
        )}

        {loading ? (
          <LoadingState message='Loading suggestion details & evidence...' />
        ) : detail ? (
          <div style={{ display: 'grid', gap: 16 }}>
            {/* Metadata Summary */}
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))',
                gap: 12,
                padding: 12,
                backgroundColor: 'var(--surface-sunken, #f8fafc)',
                borderRadius: 'var(--radius)',
                fontSize: 13,
              }}
            >
              <div>
                <span style={{ color: 'var(--muted)', display: 'block', fontSize: 11 }}>Alias</span>
                <strong style={{ fontFamily: 'monospace' }}>{detail.alias}</strong>
              </div>
              <div>
                <span style={{ color: 'var(--muted)', display: 'block', fontSize: 11 }}>Canonical Term</span>
                <strong style={{ fontFamily: 'monospace' }}>{detail.canonical}</strong>
              </div>
              <div>
                <span style={{ color: 'var(--muted)', display: 'block', fontSize: 11 }}>Status</span>
                <div style={{ marginTop: 2 }}>{getStatusBadge(detail.review_status)}</div>
              </div>
              <div>
                <span style={{ color: 'var(--muted)', display: 'block', fontSize: 11 }}>Source Runs</span>
                <strong>{detail.source_count ?? (detail.sources?.length || 0)}</strong>
              </div>
              {detail.confidence !== undefined && detail.confidence !== null && (
                <div>
                  <span style={{ color: 'var(--muted)', display: 'block', fontSize: 11 }}>Confidence</span>
                  <strong>{Math.round(detail.confidence * 100)}%</strong>
                </div>
              )}
              {detail.updated_at && (
                <div>
                  <span style={{ color: 'var(--muted)', display: 'block', fontSize: 11 }}>Updated</span>
                  <span>{formatTimestamp(detail.updated_at)}</span>
                </div>
              )}
            </div>

            {/* Candidate canonicals if multiple */}
            {detail.candidate_canonicals && detail.candidate_canonicals.length > 0 && (
              <div style={{ fontSize: 13 }}>
                <span style={{ color: 'var(--muted)', display: 'block', marginBottom: 4 }}>
                  Other Proposed Alternatives:
                </span>
                <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                  {detail.candidate_canonicals.map((term: string) => (
                    <span
                      key={term}
                      style={{
                        padding: '2px 8px',
                        borderRadius: 'var(--radius-sm)',
                        backgroundColor: 'var(--surface)',
                        border: '1px solid var(--border)',
                        fontFamily: 'monospace',
                      }}
                    >
                      {term}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Evidence & Sources List */}
            <div style={{ display: 'grid', gap: 8 }}>
              <h4 style={{ margin: 0, fontSize: 14 }}>Evidence Sources</h4>
              {!detail.sources || detail.sources.length === 0 ? (
                <p style={{ fontSize: 13, color: 'var(--muted)', margin: 0 }}>No linked evidence records.</p>
              ) : (
                <div style={{ overflowX: 'auto' }}>
                  <table className='data-table' style={{ width: '100%', fontSize: 12 }}>
                    <thead>
                      <tr>
                        <th style={{ textAlign: 'left', padding: '6px 8px' }}>Run ID / Name</th>
                        <th style={{ textAlign: 'left', padding: '6px 8px' }}>Occurrences</th>
                        <th style={{ textAlign: 'left', padding: '6px 8px' }}>Seen At</th>
                        <th style={{ textAlign: 'left', padding: '6px 8px' }}>Evidence</th>
                      </tr>
                    </thead>
                    <tbody>
                      {detail.sources.map((src: SynonymSuggestionSource, idx: number) => (
                        <tr key={idx}>
                          <td style={{ padding: '6px 8px', fontFamily: 'monospace' }}>
                            {src.run_name || src.run_id}
                          </td>
                          <td style={{ padding: '6px 8px' }}>{src.occurrence_count}</td>
                          <td style={{ padding: '6px 8px' }}>
                            {formatTimestamp(src.last_seen_at, 'N/A')}
                          </td>
                          <td style={{ padding: '6px 8px' }}>
                            <Button
                              variant='subtle'
                              size='compact'
                              onClick={() => setSelectedSource(selectedSource === src ? null : src)}
                            >
                              {selectedSource === src ? 'Hide' : 'View'}
                            </Button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>

            {/* Selected Evidence JSON preview */}
            {selectedSource && (
              <div
                style={{
                  padding: 12,
                  backgroundColor: 'var(--surface-sunken, #0f172a)',
                  borderRadius: 'var(--radius)',
                  color: '#e2e8f0',
                  fontSize: 12,
                  overflowX: 'auto',
                }}
              >
                <div style={{ fontWeight: 600, marginBottom: 6 }}>
                  Evidence for Run: {formatIdentifier(selectedSource.run_id)}
                </div>
                <pre style={{ margin: 0, fontFamily: 'monospace', whiteSpace: 'pre-wrap' }}>
                  {selectedSource.evidence_json ||
                    (selectedSource.evidence ? JSON.stringify(selectedSource.evidence, null, 2) : 'No extra evidence payload')}
                </pre>
              </div>
            )}

            {/* Actions Bar */}
            <div
              style={{
                display: 'flex',
                gap: 8,
                justifyContent: 'flex-end',
                marginTop: 8,
                borderTop: '1px solid var(--border)',
                paddingTop: 12,
              }}
            >
              {detail.review_status !== 'approved' && (
                <Button variant='primary' size='compact' onClick={handleApprove} loading={acting} disabled={acting}>
                  Approve Suggestion
                </Button>
              )}
              {detail.review_status === 'pending' && (
                <Button variant='danger' size='compact' onClick={handleDecline} loading={acting} disabled={acting}>
                  Decline
                </Button>
              )}
              {detail.review_status !== 'pending' && (
                <Button variant='secondary' size='compact' onClick={handleClear} loading={acting} disabled={acting}>
                  Reset to Pending
                </Button>
              )}
            </div>
          </div>
        ) : null}
      </div>
    </Dialog>
  );
};
