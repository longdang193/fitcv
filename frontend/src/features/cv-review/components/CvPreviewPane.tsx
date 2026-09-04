import React, { useState, useEffect, useCallback } from "react";
import { CvVersionResource, CvPreviewResult } from "../types";
import { fetchCvPreview, downloadCvVersion } from "../api";
import { SafeMarkdownRenderer } from "../safe-renderer";
import { Button, LoadingState, ErrorState } from "../../../components";
import { notificationStore } from "../../../lib/notifications";

export interface CvPreviewPaneProps {
  version: CvVersionResource | null;
  onRegenerateRequest: () => void;
}

export const CvPreviewPane: React.FC<CvPreviewPaneProps> = ({
  version,
  onRegenerateRequest,
}) => {
  const [preview, setPreview] = useState<CvPreviewResult | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<{ message: string; action?: string; retryable?: boolean } | null>(null);
  const [rawMode, setRawMode] = useState<boolean>(false);
  const [downloading, setDownloading] = useState<boolean>(false);
  const [copied, setCopied] = useState<boolean>(false);

  const loadPreview = useCallback(async (versionId: string) => {
    setLoading(true);
    setError(null);
    setPreview(null);
    try {
      const data = await fetchCvPreview(versionId);
      setPreview(data);
    } catch (err: any) {
      setError({
        message: err.message || "Failed to load CV preview.",
        action: err.action,
        retryable: typeof err.retryable === "boolean" ? err.retryable : err.details?.retryable === true,
      });
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (version?.version_id) {
      loadPreview(version.version_id);
    } else {
      setPreview(null);
      setError(null);
    }
  }, [version?.version_id, loadPreview]);

  const handleDownload = async () => {
    if (!version) return;
    setDownloading(true);
    try {
      await downloadCvVersion(version.version_id, version.filename || `cv-${version.version_id.slice(0, 8)}.md`);
      notificationStore.notify({
        dedupe: `cv:download:${version.version_id}`,
        type: "success",
        title: "Download started",
        message: `Saved ${version.filename || "CV document"}.`,
      });
    } catch (err: any) {
      notificationStore.notify({
        dedupe: `cv:download:err:${Date.now()}`,
        type: "error",
        title: "Download failed",
        message: err.message || "Could not download CV file.",
      });
    } finally {
      setDownloading(false);
    }
  };

  const handleCopy = async () => {
    if (!preview?.content) return;
    try {
      await navigator.clipboard.writeText(preview.content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Clipboard write failed
    }
  };

  if (!version) {
    return (
      <div style={{ padding: 48, textAlign: "center", color: "var(--muted)", fontSize: 14 }}>
        Select a CV version to inspect preview and artifact details.
      </div>
    );
  }

  return (
    <div className="cv-preview-pane" style={{ display: "grid", gap: 16 }}>
      {/* Toolbar */}
      <div
        className="cv-preview-toolbar"
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: 12,
          padding: "12px 16px",
          background: "var(--surface)",
          border: "1px solid var(--border)",
          borderRadius: "var(--radius-lg)",
          flexWrap: "wrap",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 12, flexWrap: "wrap" }}>
          <div>
            <strong style={{ fontSize: 14 }}>v{version.ordinal || 1}</strong>{" "}
            <span style={{ fontSize: 12, color: "var(--muted)", fontFamily: "monospace" }}>
              ({version.version_id.slice(0, 8)})
            </span>
          </div>
          {version.content_checksum && (
            <span style={{ fontSize: 11, color: "var(--muted)" }} title={`SHA-256: ${version.content_checksum}`}>
              SHA: {version.content_checksum.slice(0, 10)}...
            </span>
          )}
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
          {/* View mode toggle */}
          <Button
            variant="secondary"
            size="compact"
            onClick={() => setRawMode((prev) => !prev)}
            disabled={loading || !preview}
          >
            {rawMode ? "Formatted View" : "Raw Text"}
          </Button>

          {/* Copy markdown */}
          <Button
            variant="secondary"
            size="compact"
            onClick={handleCopy}
            disabled={loading || !preview}
          >
            {copied ? "Copied ✓" : "Copy"}
          </Button>

          {/* Download button */}
          <Button
            variant="primary"
            size="compact"
            onClick={handleDownload}
            disabled={downloading || !version.capabilities?.download}
            title={version.capabilities?.download ? "Download attachment" : "Download not available"}
          >
            {downloading ? "Downloading..." : "Download CV"}
          </Button>

          {/* Regenerate button */}
          <Button
            variant="secondary"
            size="compact"
            onClick={onRegenerateRequest}
            disabled={!version.capabilities?.regenerate}
            title={version.capabilities?.regenerate ? "Queue new CV version" : "Regeneration not available"}
          >
            Regenerate CV
          </Button>
        </div>
      </div>

      {/* Main Preview Container */}
      <div
        className="cv-preview-content-container"
        style={{
          minHeight: 380,
          border: "1px solid var(--border)",
          borderRadius: "var(--radius-lg)",
          background: "var(--surface)",
          padding: "24px 28px",
          overflowX: "auto",
        }}
      >
        {loading && <LoadingState message="Fetching immutable CV preview bytes..." />}

        {!loading && error && (
          <ErrorState
            title={error.retryable ? "CV Generation Pending" : "Preview Unavailable"}
            message={error.message}
            actionLabel={error.retryable ? "Retry Preview" : (error.action || "Retry")}
            onRetry={error.retryable ? () => loadPreview(version.version_id) : undefined}
          />
        )}

        {!loading && !error && preview && (
          <SafeMarkdownRenderer
            content={preview.content}
            mediaType={preview.media_type}
            rawMode={rawMode}
          />
        )}
      </div>
    </div>
  );
};
