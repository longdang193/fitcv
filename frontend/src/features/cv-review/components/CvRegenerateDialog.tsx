import React, { useState } from "react";
import { Dialog, Button } from "../../../components";
import { CvVersionResource } from "../types";

export interface CvRegenerateDialogProps {
  open: boolean;
  onClose: () => void;
  onConfirm: (parentVersionId: string | null) => Promise<void>;
  currentVersion: CvVersionResource | null;
  runId: string;
  runJobId: string;
}

export const CvRegenerateDialog: React.FC<CvRegenerateDialogProps> = ({
  open,
  onClose,
  onConfirm,
  currentVersion,
  runId,
  runJobId,
}) => {
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleRegenerate = async () => {
    setSubmitting(true);
    setError(null);
    try {
      await onConfirm(currentVersion?.version_id || null);
      onClose();
    } catch (err: any) {
      setError(err.message || "Failed to start CV regeneration.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Dialog
      open={open}
      onClose={onClose}
      title="Regenerate Grounded CV"
      description="Queue a fresh CV generation artifact for this job using the current candidate profile and job requirements."
      footer={
        <div style={{ display: "flex", justifyContent: "flex-end", gap: 8 }}>
          <Button variant="secondary" onClick={onClose} disabled={submitting}>
            Cancel
          </Button>
          <Button variant="primary" onClick={handleRegenerate} disabled={submitting}>
            {submitting ? "Queueing..." : "Confirm Regeneration"}
          </Button>
        </div>
      }
    >
      <div style={{ display: "grid", gap: 12 }}>
        <div style={{ padding: 12, background: "var(--surface-2)", borderRadius: "var(--radius-md)", fontSize: 13 }}>
          <div><strong>Run ID:</strong> {runId}</div>
          <div><strong>Job ID:</strong> {runJobId}</div>
          {currentVersion && (
            <div>
              <strong>Parent Version:</strong> {currentVersion.version_id.slice(0, 8)} (v{currentVersion.ordinal})
            </div>
          )}
        </div>

        <p style={{ margin: 0, fontSize: 13, color: "var(--muted)" }}>
          A new immutable CV version artifact will be created. The existing CV version history and reviews are preserved.
        </p>

        {error && (
          <div style={{ padding: 8, background: "var(--danger-soft)", color: "var(--danger)", borderRadius: "var(--radius-sm)", fontSize: 12 }}>
            {error}
          </div>
        )}
      </div>
    </Dialog>
  );
};
