import { apiClient } from '../../lib/api-client';
import type {
  SynonymType,
  SynonymPolicyResource,
  SynonymPolicyEnvelope,
  SynonymPolicyUpdateRequest,
  SynonymSuggestionResource,
  SynonymSuggestionCollectionEnvelope,
  SynonymSuggestionEnvelope,
  SynonymProcessingResource,
  SynonymProcessingCollectionEnvelope,
  SynonymSuggestionQuery,
  SynonymActionResult,
} from './types';

function createIdempotencyKey(prefix: string): string {
  return prefix + '-' + Date.now() + '-' + Math.random().toString(36).slice(2, 9);
}

export async function fetchSynonymPolicy(type: SynonymType): Promise<SynonymPolicyResource> {
  const res = await apiClient.get<SynonymPolicyEnvelope>('/synonym-policies/' + type);
  return res.data.data;
}

export async function updateSynonymPolicy(
  type: SynonymType,
  payload: SynonymPolicyUpdateRequest
): Promise<SynonymPolicyResource> {
  const res = await apiClient.put<SynonymPolicyEnvelope>('/synonym-policies/' + type, payload, {
    idempotencyKey: createIdempotencyKey('synonym-policy-' + type),
  });
  return res.data.data;
}

export async function fetchSynonymSuggestions(query: SynonymSuggestionQuery = {}): Promise<{
  items: SynonymSuggestionResource[];
  page: number;
  pageSize: number;
  total: number;
  counts: Record<string, { pending?: number; approved?: number; declined?: number; total?: number }>;
}> {
  const params = new URLSearchParams();
  if (query.type && query.type !== 'all') {
    params.set('type', query.type);
  }
  if (query.status && query.status !== 'all') {
    params.set('status', query.status);
  }
  if (query.search && query.search.trim()) {
    params.set('search', query.search.trim());
  }
  if (query.page) {
    params.set('page', String(query.page));
  }
  if (query.pageSize) {
    params.set('page_size', String(query.pageSize));
  }
  params.set('sort', query.sort || 'updated_desc');

  const qs = params.toString();
  const path = '/synonym-suggestions' + (qs ? '?' + qs : '');
  const res = await apiClient.get<SynonymSuggestionCollectionEnvelope>(path);

  return {
    items: res.data.data || [],
    page: res.data.page?.page ?? 1,
    pageSize: res.data.page?.page_size ?? 20,
    total: res.data.page?.total_items ?? 0,
    counts: res.data.meta?.counts || {},
  };
}

export async function fetchSynonymSuggestionDetail(
  suggestionId: string,
  evidencePage: number = 1,
  evidencePageSize: number = 20
): Promise<SynonymSuggestionResource> {
  const res = await apiClient.get<SynonymSuggestionEnvelope>(
    '/synonym-suggestions/' + encodeURIComponent(suggestionId) + '?evidence_page=' + evidencePage + '&evidence_page_size=' + evidencePageSize
  );
  return res.data.data;
}

export async function approveSynonymSuggestions(
  suggestionIds: string[],
  expectedDraftRevision: number,
  expectedActiveBundleRevisionId: string | null
): Promise<SynonymActionResult> {
  const res = await apiClient.post<{ data: SynonymActionResult }>(
    '/synonym-suggestions/actions/approve',
    {
      suggestion_ids: suggestionIds,
      expected_draft_revision: expectedDraftRevision,
      expected_active_bundle_revision_id: expectedActiveBundleRevisionId,
    },
    {
      idempotencyKey: createIdempotencyKey('synonym-approve'),
    }
  );
  return res.data?.data || (res.data as unknown as SynonymActionResult) || {};
}

export async function declineSynonymSuggestions(
  suggestionIds: string[]
): Promise<SynonymActionResult> {
  const res = await apiClient.post<{ data: SynonymActionResult }>(
    '/synonym-suggestions/actions/decline',
    {
      suggestion_ids: suggestionIds,
    },
    {
      idempotencyKey: createIdempotencyKey('synonym-decline'),
    }
  );
  return res.data?.data || (res.data as unknown as SynonymActionResult) || {};
}

export async function clearSynonymSuggestions(
  suggestionIds: string[]
): Promise<SynonymActionResult> {
  const res = await apiClient.post<{ data: SynonymActionResult }>(
    '/synonym-suggestions/actions/clear',
    {
      suggestion_ids: suggestionIds,
    },
    {
      idempotencyKey: createIdempotencyKey('synonym-clear'),
    }
  );
  return res.data?.data || (res.data as unknown as SynonymActionResult) || {};
}

export async function fetchSynonymProcessingRuns(
  page: number = 1,
  pageSize: number = 20
): Promise<{ items: SynonymProcessingResource[]; total: number; page: number; pageSize: number }> {
  const res = await apiClient.get<SynonymProcessingCollectionEnvelope>(
    '/synonym-processing-runs?page=' + page + '&page_size=' + pageSize
  );
  return {
    items: res.data.data || [],
    total: res.data.page?.total_items ?? 0,
    page: res.data.page?.page ?? 1,
    pageSize: res.data.page?.page_size ?? 20,
  };
}

export async function exportSynonymBackup(): Promise<void> {
  await apiClient.download('/synonym-backups/export.zip', 'fitcv-synonyms-backup.zip');
}

export async function importSynonymBackup(
  file: File,
  expectedActiveBundleRevisionId?: string | null
): Promise<any> {
  const formData = new FormData();
  formData.append('backup_file', file);
  if (expectedActiveBundleRevisionId) {
    formData.append('expected_active_bundle_revision_id', expectedActiveBundleRevisionId);
  }
  const res = await apiClient.post<{ data: any }>('/synonym-backups/import', formData, {
    idempotencyKey: createIdempotencyKey('synonym-import'),
  });
  return res.data?.data || res.data;
}
