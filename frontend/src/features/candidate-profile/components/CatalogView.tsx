import React, { useEffect, useState, useCallback } from "react";
import { Button, DataTable, LoadingState, Tabs, StatusBadge, LiveStatus, Dialog } from "../../../components";
import {
  fetchCreationAttempts,
  fetchProfiles,
  archiveProfile,
  deleteProfile,
  retryAttempt,
} from "../api";
import { CandidateProfile, CreationAttempt } from "../types";

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

  // Load drafts and profiles
  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    setSelectedKeys(new Set());

    try {
      const [draftsRes, profsRes] = await Promise.all([
        fetchCreationAttempts({ page: 1, page_size: 20 }),
        fetchProfiles({ lifecycle: activeTab, page, page_size: pageSize }),
      ]);

      const drafts = (draftsRes as any)?.data?.items || (draftsRes as any)?.items || draftsRes.data || [];
      setAttempts(drafts);

      const profileItems = (profsRes as any)?.data?.items || (profsRes as any)?.items || profsRes.data || [];
      setProfiles(profileItems);
      setTotalItems(profsRes.total_items || profileItems.length);

      const meta = profsRes.meta || {};
      setActiveCount(meta.active_count ?? (activeTab === "active" ? profsRes.total_items : 0));
      setArchivedCount(meta.archived_count ?? (activeTab === "archived" ? profsRes.total_items : 0));

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
    const selectedProfiles = profiles.filter((p) => selectedKeys.has(p.profile_id));
    if (selectedProfiles.length === 0) return;

    setActionLoading(true);
    setError(null);
    setStatusMessage(`Archiving ${selectedProfiles.length} profile(s)...`);

    try {
      for (const p of selectedProfiles) {
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
      onResumeAttempt(retried.attempt_id, retried.next_action === "review_derived" ? "derived" : "baseline");
    } catch (err: any) {
      setError(err.message || "Failed to retry draft.");
      setActionLoading(false);
    }
  };

  const selectedList = profiles.filter((p) => selectedKeys.has(p.profile_id));
  const hasNonDeletable = activeTab === "archived" && selectedList.some((p) => !p.capabilities?.delete);

  return (
    <div className="candidate-profiles-catalog">
      {/* Page Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 24, flexWrap: "wrap", gap: 16 }}>
        <div>
          <span style={{ fontSize: 11, fontWeight: 700, letterSpacing: "0.08em", textTransform: "uppercase", color: "var(--accent)" }}>
            Workspace
          </span>
          <h2 style={{ margin: "4px 0", fontSize: 24, fontFamily: "var(--display-font)" }}>
            Candidate Profiles
          </h2>
          <p style={{ margin: 0, color: "var(--muted)", fontSize: 13 }}>
            Create and review canonical profiles used by matching runs. Drafts stay outside pipeline selection until confirmed.
          </p>
        </div>

        <Button variant="primary" onClick={onOpenCreate}>
          + Create Profile
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
      <section className="table-card" style={{ padding: 20, marginBottom: 24 }} aria-labelledby="creation-drafts-heading">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
          <div>
            <h3 id="creation-drafts-heading" style={{ margin: 0, fontSize: 15 }}>
              Creation Drafts
            </h3>
            <span style={{ fontSize: 12, color: "var(--muted)" }}>
              Paused and failed creation attempts remain outside pipeline runs.
            </span>
          </div>
          <span style={{ fontSize: 12, color: "var(--muted)", fontWeight: 600 }}>
            {attempts.length} {attempts.length === 1 ? "draft" : "drafts"}
          </span>
        </div>

        {attempts.length === 0 ? (
          <div style={{ padding: "16px 0", color: "var(--muted)", fontSize: 13, fontStyle: "italic" }}>
            No creation drafts. Upload Markdown, DOCX, or YAML to start a new profile review.
          </div>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            {attempts.map((att) => {
              const statusLabel =
                att.next_action === "confirm"
                  ? "Ready to confirm"
                  : att.next_action === "review_derived"
                  ? "Derived review"
                  : att.creation_status === "failed"
                  ? "Needs attention"
                  : "Baseline review";

              const stageParam =
                att.next_action === "confirm"
                  ? "confirm"
                  : att.next_action === "review_derived"
                  ? "derived"
                  : "baseline";

              return (
                <div
                  key={att.attempt_id}
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    padding: "10px 14px",
                    background: "var(--surface-2)",
                    borderRadius: "var(--radius-md)",
                    flexWrap: "wrap",
                    gap: 8,
                  }}
                >
                  <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                    <StatusBadge
                      status={att.creation_status === "failed" ? "danger" : "info"}
                      label={statusLabel}
                    />
                    <div>
                      <strong style={{ display: "block", fontSize: 13 }}>{att.profile_name}</strong>
                      <span style={{ fontSize: 11, color: "var(--muted)" }}>
                        {att.source_document?.original_filename || "candidate.md"} · Updated {att.updated_at || "recently"}
                      </span>
                    </div>
                  </div>

                  <div style={{ display: "flex", gap: 8 }}>
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
                    ) : att.profile_id ? (
                      <Button size="compact" onClick={() => onOpenDetail(att.profile_id!)}>
                        View Profile
                      </Button>
                    ) : (
                      <Button size="compact" variant="primary" onClick={() => onResumeAttempt(att.attempt_id, stageParam)}>
                        Resume review
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
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              padding: "12px 16px",
              background: "var(--surface-2)",
              borderRadius: "var(--radius-md)",
              border: "1px solid var(--border)",
              marginBottom: 12,
            }}
          >
            <div>
              <strong style={{ fontSize: 13 }}>
                {selectedKeys.size} {activeTab === "archived" ? "archived " : ""}profile(s) selected
              </strong>
              <span style={{ display: "block", fontSize: 11, color: "var(--muted)" }}>
                {activeTab === "active"
                  ? "Archived profiles remain available to historical runs."
                  : "Delete permanently only profiles with no related Runs."}
              </span>
            </div>

            <div style={{ display: "flex", gap: 8 }}>
              {activeTab === "active" ? (
                <Button size="compact" onClick={handleArchiveSelected} disabled={actionLoading}>
                  Archive Profile(s)
                </Button>
              ) : (
                <Button
                  size="compact"
                  variant="danger"
                  onClick={() => setDeleteConfirmOpen(true)}
                  disabled={actionLoading || hasNonDeletable}
                  title={hasNonDeletable ? "Some selected profiles cannot be deleted because they are used by historical Runs." : undefined}
                >
                  Delete Profile(s)
                </Button>
              )}
            </div>
          </div>
        )}

        {loading ? (
          <LoadingState message="Loading profiles..." />
        ) : (
          <DataTable<CandidateProfile>
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
                    className="btn-subtle"
                    style={{
                      fontFamily: "var(--font-mono)",
                      fontSize: 12,
                      color: "var(--accent)",
                      fontWeight: 600,
                      padding: 0,
                      cursor: "pointer",
                      border: 0,
                      background: "transparent",
                    }}
                    onClick={() => onOpenDetail(item.profile_id)}
                  >
                    {item.profile_id}
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
                  <span style={{ fontSize: 12, color: "var(--muted)" }}>
                    {item.created_at_display || item.created_at}
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
    </div>
  );
};
