import React, { useEffect, useState, useCallback } from "react";
import { Button, DataTable, LoadingState, SelectionBar, Tabs, StatusBadge, LiveStatus, Dialog } from "../../../components";
import {
  fetchCreationAttempts,
  fetchProfiles,
  archiveProfile,
  deleteProfile,
  discardCreationAttempt,
  retryAttempt,
} from "../api";
import { CandidateProfile, CreationAttempt } from "../types";
import { notificationStore } from "../../../lib/notifications";
import { formatIdentifier, formatTimestamp } from "../../../lib/format";

export interface CatalogViewProps {
  onOpenCreate: () => void;
  onResumeAttempt: (attemptId: string, stage?: string) => void;
  onOpenDetail: (profileId: string) => void;
}

export const CatalogView: React.FC<CatalogViewProps> = ({
  onOpenCreate,
  onResumeAttempt,
  onOpenDetail,
}) => {
  const [activeTab, setActiveTab] = useState<"active" | "archived">("active");
  const [attempts, setAttempts] = useState<CreationAttempt[]>([]);
  const [profiles, setProfiles] = useState<CandidateProfile[]>([]);
  const [activeCount, setActiveCount] = useState(0);
  const [archivedCount, setArchivedCount] = useState(0);
  const [page, setPage] = useState(1);
  const [totalItems, setTotalItems] = useState(0);
  const [pageSize] = useState(20);
  const [selectedKeys, setSelectedKeys] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [statusMessage, setStatusMessage] = useState("");
  const [deleteConfirmOpen, setDeleteConfirmOpen] = useState(false);
  const [draftDeleteTarget, setDraftDeleteTarget] = useState<CreationAttempt | null>(null);

  // Load drafts and profiles
  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    setSelectedKeys(new Set());

    try {
      const [draftsRes, profsRes] = await Promise.all([
        fetchCreationAttempts({ page: 1, page_size: 20 }),
        fetchProfiles({ view: activeTab, page, page_size: pageSize }),
      ]);

      const drafts = (draftsRes as any)?.data?.items || (draftsRes as any)?.items || draftsRes.data || [];
      setAttempts(
        drafts.filter(
          (attempt: CreationAttempt) =>
            attempt.creation_status !== "succeeded" && attempt.next_action !== "view_profile"
        )
      );

      const profileItems = (profsRes as any)?.data?.items || (profsRes as any)?.items || profsRes.data || [];
      setProfiles(profileItems);
      setTotalItems(profsRes.page?.total_items ?? profsRes.total_items ?? profsRes.total ?? profileItems.length);

      const meta = profsRes.meta || {};
      const total = profsRes.page?.total_items ?? profsRes.total_items ?? profsRes.total ?? profileItems.length;
      setActiveCount(meta.active_count ?? (activeTab === "active" ? total : 0));
      setArchivedCount(meta.archived_count ?? (activeTab === "archived" ? total : 0));

      setLoading(false);
    } catch (err: any) {
      setError(err.message || "Failed to load candidate profiles.");
      setLoading(false);
    }
  }, [activeTab, page, pageSize]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // Row selection toggle
  const handleToggleSelect = (key: string) => {
    setSelectedKeys((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  };

  const handleSelectAll = () => {
    if (selectedKeys.size === profiles.length) {
      setSelectedKeys(new Set());
    } else {
      setSelectedKeys(new Set(profiles.map((p) => p.profile_id)));
    }
  };

  // Lifecycle bulk actions
  const handleArchiveSelected = async () => {
    const archivableProfiles = profiles
      .filter((p) => selectedKeys.has(p.profile_id))
      .filter((p) => p.capabilities?.archive === true);
    if (archivableProfiles.length === 0) return;

    setActionLoading(true);
    setError(null);
    setStatusMessage(`Archiving ${archivableProfiles.length} profile(s)...`);

    try {
      for (const p of archivableProfiles) {
        await archiveProfile(p.profile_id, p.revision);
      }
      setStatusMessage("Profiles archived.");
      setActionLoading(false);
      await loadData();
    } catch (err: any) {
      setError(err.message || "Failed to archive selected profiles.");
      setActionLoading(false);
    }
  };

  const handleDeleteSelected = async () => {
    const selectedProfiles = profiles.filter((p) => selectedKeys.has(p.profile_id));
    if (selectedProfiles.length === 0) return;

    setActionLoading(true);
    setError(null);
    setStatusMessage(`Deleting ${selectedProfiles.length} profile(s)...`);

    try {
      for (const p of selectedProfiles) {
        await deleteProfile(p.profile_id, p.revision);
      }
      setDeleteConfirmOpen(false);
      setStatusMessage("Profiles deleted.");
      setActionLoading(false);
      await loadData();
    } catch (err: any) {
      setError(err.message || "Failed to delete selected profiles.");
      setActionLoading(false);
    }
  };

  const handleRetryDraft = async (attempt: CreationAttempt) => {
    setActionLoading(true);
    setStatusMessage("Retrying creation draft...");
    try {
      const retried = await retryAttempt(attempt.attempt_id, attempt.revision);
      setActionLoading(false);
      onResumeAttempt(retried.attempt_id);
    } catch (err: any) {
      setError(err.message || "Failed to retry draft.");
      setActionLoading(false);
    }
  };

  const handleDeleteDraft = async () => {
    if (!draftDeleteTarget) return;
    setActionLoading(true);
    setError(null);
    setStatusMessage(`Deleting draft ${draftDeleteTarget.profile_name}...`);
    try {
      await discardCreationAttempt(draftDeleteTarget.attempt_id, draftDeleteTarget.revision);
      setDraftDeleteTarget(null);
      setStatusMessage("Draft deleted.");
      notificationStore.notify({
        dedupe: `candidate-profile:draft-deleted:${draftDeleteTarget.attempt_id}`,
        type: "success",
        title: "Draft deleted",
        message: `${draftDeleteTarget.profile_name || "Candidate profile draft"} was removed.`,
      });
      await loadData();
    } catch (err: any) {
      setError(err.message || "Failed to delete draft.");
      notificationStore.notify({
        dedupe: `candidate-profile:draft-delete-failed:${draftDeleteTarget.attempt_id}`,
        type: "error",
        title: "Draft deletion failed",
        message: err.message || "Could not delete candidate profile draft.",
      });
    } finally {
      setActionLoading(false);
    }
  };

  const selectedList = profiles.filter((p) => selectedKeys.has(p.profile_id));
  const hasNonArchivable = activeTab === "active" && selectedList.some((p) => !p.capabilities?.archive);
  const hasNonDeletable = activeTab === "archived" && selectedList.some((p) => !p.capabilities?.delete);

  return (
    <div className="candidate-profiles-catalog">
      {/* Page Header */}
      <div className="page-head">
        <div>
          <p className="eyebrow">Workspace</p>
          <h2>Candidate Profiles</h2>
          <p>Create and review profiles used by matching runs.</p>
        </div>

        <Button variant="primary" onClick={onOpenCreate}>
          Create Profile
        </Button>
      </div>

      {error && (
        <div
          role="alert"
          style={{
            padding: "12px 16px",
            marginBottom: 20,
            background: "var(--danger-soft)",
            color: "var(--danger)",
            borderRadius: "var(--radius-md)",
            fontSize: 13,
            fontWeight: 500,
          }}
        >
          {error}
        </div>
      )}

      {statusMessage && <LiveStatus message={statusMessage} />}

      {/* Creation Drafts Section */}
      <section className="section-card creation-drafts" aria-labelledby="creation-drafts-heading">
        <div className="creation-drafts-head">
          <div>
            <h3 id="creation-drafts-heading">
              Creation Drafts
            </h3>
            <span>
              Paused and failed creation attempts remain outside pipeline runs.
            </span>
          </div>
          <span>
            {attempts.length} {attempts.length === 1 ? "draft" : "drafts"}
          </span>
        </div>

        {attempts.length === 0 ? (
          <div className="creation-draft creation-draft-empty">
            No creation drafts. Upload Markdown, DOCX, or YAML to start a new profile review.
          </div>
        ) : (
          <div className="creation-draft-list">
            {attempts.map((att) => {
              const statusLabel =
                att.creation_status === "succeeded" || att.next_action === "view_profile"
                  ? "Completed"
                  : att.next_action === "confirm" || att.creation_status === "ready_to_confirm"
                  ? "Ready to confirm"
                  : att.next_action === "review_derived" || att.creation_status === "derived_review"
                  ? "Derived review"
                  : att.next_action === "review_baseline" || att.creation_status === "base_review"
                  ? "Baseline review"
                  : att.creation_status === "failed"
                  ? "Needs attention"
                  : "Processing";

              const stageParam =
                att.next_action === "confirm" || att.creation_status === "ready_to_confirm"
                  ? "confirm"
                  : att.next_action === "review_derived" || att.creation_status === "derived_review"
                  ? "derived"
                  : att.next_action === "review_baseline" || att.creation_status === "base_review"
                  ? "baseline"
                  : undefined;

              return (
                <div key={att.attempt_id} className="creation-draft">
                  <StatusBadge
                    status={
                      att.creation_status === "failed"
                        ? "danger"
                        : att.creation_status === "succeeded"
                        ? "success"
                        : "info"
                    }
                    label={statusLabel}
                  />
                  <div className="creation-draft-copy">
                    <strong>{att.profile_name}</strong>
                    <span>
                      {att.source_document?.original_filename || "candidate.md"} · Updated {formatTimestamp(att.updated_at, "recently")}
                    </span>
                  </div>
                  <div className="creation-draft-actions">
                    {att.creation_status === "failed" ? (
                      att.capabilities?.retry ? (
                        <Button size="compact" onClick={() => handleRetryDraft(att)} disabled={actionLoading}>
                          Retry & Resume
                        </Button>
                      ) : (
                        <Button size="compact" onClick={onOpenCreate}>
                          Start new upload
                        </Button>
                      )
                    ) : att.profile_id && (att.creation_status === "succeeded" || att.next_action === "view_profile") ? (
                      <Button size="compact" onClick={() => onOpenDetail(att.profile_id!)}>
                        View Profile
                      </Button>
                    ) : stageParam ? (
                      <Button size="compact" variant="primary" onClick={() => onResumeAttempt(att.attempt_id, stageParam)}>
                        Resume review
                      </Button>
                    ) : (
                      <Button size="compact" onClick={() => onResumeAttempt(att.attempt_id)}>
                        View progress
                      </Button>
                    )}
                    {att.capabilities?.discard && (
                      <Button
                        size="compact"
                        variant="danger"
                        onClick={() => setDraftDeleteTarget(att)}
                        disabled={actionLoading}
                        aria-label={`Delete draft ${att.profile_name || att.attempt_id}`}
                      >
                        Delete draft
                      </Button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </section>

      {/* Profiles Tabs & Table */}
      <Tabs
        activeId={activeTab}
        onChange={(tabId) => {
          setActiveTab(tabId as "active" | "archived");
          setPage(1);
        }}
        items={[
          { id: "active", label: "Active", count: activeCount },
          { id: "archived", label: "Archived", count: archivedCount },
        ]}
      >
        {/* Selection Bar */}
        {selectedKeys.size > 0 && (
          <SelectionBar
            className="run-selection"
            count={selectedKeys.size}
            label={activeTab === "archived" ? "archived profile" : "profile"}
            description={
              activeTab === "active"
                ? "Archived profiles remain available to historical runs."
                : "Delete permanently only profiles with no related Runs."
            }
            actions={
              <>
              {activeTab === "active" ? (
                <Button
                  size="compact"
                  onClick={handleArchiveSelected}
                  disabled={actionLoading || hasNonArchivable || selectedList.length === 0}
                  title={hasNonArchivable ? "Some selected profiles cannot be archived." : undefined}
                >
                  Archive Profile(s)
                </Button>
              ) : (
                <Button
                  size="compact"
                  variant="danger"
                  onClick={() => setDeleteConfirmOpen(true)}
                  disabled={actionLoading || hasNonDeletable || selectedList.length === 0}
                  title={hasNonDeletable ? "Some selected profiles cannot be deleted because they are used by historical Runs." : undefined}
                >
                  Delete Profile(s)
                </Button>
              )}
              </>
            }
          />
        )}

        {loading ? (
          <LoadingState message="Loading profiles..." />
        ) : (
          <DataTable<CandidateProfile>
            className="profile-table-card"
            data={profiles}
            keyField="profile_id"
            selectedKeys={selectedKeys}
            onToggleSelect={handleToggleSelect}
            onSelectAll={handleSelectAll}
            isAllSelected={profiles.length > 0 && selectedKeys.size === profiles.length}
            page={page}
            pageSize={pageSize}
            total={totalItems}
            onPageChange={setPage}
            emptyMessage={
              activeTab === "active"
                ? "No active candidate profiles found. Create a profile to get started."
                : "No archived candidate profiles."
            }
            columns={[
              {
                key: "profile_id",
                header: "Profile ID",
                render: (item) => (
                  <button
                    type="button"
                    className="btn-subtle profile-id-link"
                    onClick={() => onOpenDetail(item.profile_id)}
                  >
                    <span title={item.profile_id}>{formatIdentifier(item.profile_id)}</span>
                  </button>
                ),
              },
              {
                key: "status",
                header: "Status",
                render: (item) => (
                  <StatusBadge
                    status={item.lifecycle === "active" ? "success" : "neutral"}
                    label={item.lifecycle === "active" ? "Active" : "Archived"}
                  />
                ),
              },
              {
                key: "display_name",
                header: "Profile Name",
                render: (item) => <strong>{item.display_name || item.profile_name}</strong>,
              },
              {
                key: "created_at",
                header: "Created Time",
                render: (item) => (
                  <span className="profile-created-time">
                    {formatTimestamp(item.created_at, "Unknown date")}
                  </span>
                ),
              },
            ]}
          />
        )}
      </Tabs>

      {/* Delete Confirmation Dialog */}
      <Dialog
        open={deleteConfirmOpen}
        onClose={() => setDeleteConfirmOpen(false)}
        title="Delete Selected Archived Profiles?"
        description="This will permanently delete the selected candidate profile(s). This action cannot be undone."
        footer={
          <div style={{ display: "flex", gap: 10 }}>
            <Button variant="secondary" onClick={() => setDeleteConfirmOpen(false)} disabled={actionLoading}>
              Cancel
            </Button>
            <Button variant="danger" onClick={handleDeleteSelected} loading={actionLoading}>
              Delete permanently
            </Button>
          </div>
        }
      >
        <p style={{ margin: 0, fontSize: 13, color: "var(--text)" }}>
          Are you sure you want to permanently delete {selectedKeys.size} archived profile(s)?
        </p>
      </Dialog>

      <Dialog
        open={Boolean(draftDeleteTarget)}
        onClose={() => setDraftDeleteTarget(null)}
        title="Delete Candidate Draft?"
        description="Only this unconfirmed draft and its source data will be deleted. Confirmed profiles and historical Runs stay unchanged."
        footer={
          <div style={{ display: "flex", gap: 10 }}>
            <Button variant="secondary" onClick={() => setDraftDeleteTarget(null)} disabled={actionLoading}>
              Cancel
            </Button>
            <Button variant="danger" onClick={handleDeleteDraft} loading={actionLoading}>
              Delete draft
            </Button>
          </div>
        }
      >
        <p style={{ margin: 0, fontSize: 13, color: "var(--text)" }}>
          Delete <strong>{draftDeleteTarget?.profile_name}</strong>? This cannot be undone.
        </p>
      </Dialog>
    </div>
  );
};
