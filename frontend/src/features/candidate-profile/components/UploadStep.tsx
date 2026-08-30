import React, { useState, useRef } from "react";
import { Button, Field, LiveStatus } from "../../../components";
import { createCreationAttempt } from "../api";
import { CreationAttempt } from "../types";

export interface UploadStepProps {
  onSuccess: (attempt: CreationAttempt) => void;
  onCancel: () => void;
}

export const UploadStep: React.FC<UploadStepProps> = ({ onSuccess, onCancel }) => {
  const [profileName, setProfileName] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [statusMessage, setStatusMessage] = useState("Choose one candidate document to continue.");
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileChange = (selectedFile: File | null) => {
    if (!selectedFile) return;

    const ext = selectedFile.name.toLowerCase().split(".").pop();
    if (!["md", "docx", "yaml", "yml"].includes(ext || "")) {
      setError("Please select a supported file format: Markdown (.md), Word (.docx), or YAML (.yaml).");
      return;
    }

    setFile(selectedFile);
    setError(null);
    setStatusMessage(`Selected: ${selectedFile.name} (${(selectedFile.size / 1024).toFixed(1)} KB)`);

    // Suggest default profile name from filename if empty
    if (!profileName) {
      const baseName = selectedFile.name.replace(/\.[^/.]+$/, "");
      setProfileName(baseName.substring(0, 120));
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFileChange(e.dataTransfer.files[0]);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) {
      setError("Please select a candidate document file.");
      return;
    }
    const trimmedName = profileName.trim();
    if (!trimmedName) {
      setError("Profile name is required.");
      return;
    }

    setLoading(true);
    setError(null);
    setStatusMessage("Uploading and starting deterministic mapping pipeline...");

    try {
      const attempt = await createCreationAttempt(trimmedName, file);
      onSuccess(attempt);
    } catch (err: any) {
      setError(err.message || "Failed to create candidate profile creation attempt.");
      setStatusMessage("Upload failed.");
      setLoading(false);
    }
  };

  return (
    <div className="upload-step-container">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 20 }}>
        <div>
          <button
            type="button"
            className="btn-subtle"
            style={{ fontSize: 13, padding: "4px 8px", cursor: "pointer", border: 0, background: "transparent", color: "var(--muted)" }}
            onClick={onCancel}
          >
            ← Back to Candidate Profiles
          </button>
          <h2 style={{ margin: "8px 0 4px", fontSize: 22, fontFamily: "var(--display-font)" }}>
            Upload candidate document
          </h2>
          <p style={{ margin: 0, color: "var(--muted)", fontSize: 13 }}>
            Define Profile Name once; every supported format follows the same extraction, review, and derivation pipeline.
          </p>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="table-card" style={{ padding: 28 }}>
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))",
            gap: 24,
            alignItems: "start",
          }}
        >
          {/* Dropzone */}
          <div
            onDragOver={(e) => {
              e.preventDefault();
              setIsDragging(true);
            }}
            onDragLeave={() => setIsDragging(false)}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
            style={{
              border: isDragging
                ? "2px dashed var(--accent)"
                : file
                ? "2px solid var(--accent)"
                : "2px dashed var(--border)",
              borderRadius: "var(--radius-lg)",
              padding: "40px 20px",
              textAlign: "center",
              cursor: "pointer",
              background: isDragging ? "var(--accent-soft)" : "var(--surface-2)",
              transition: "all var(--motion-fast)",
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              justifyContent: "center",
              gap: 12,
            }}
            role="button"
            tabIndex={0}
            aria-label="Upload candidate document file dropzone"
            onKeyDown={(e) => {
              if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                fileInputRef.current?.click();
              }
            }}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept=".md,.docx,.yaml,.yml,text/markdown,application/vnd.openxmlformats-officedocument.wordprocessingml.document,application/yaml,text/yaml"
              style={{ display: "none" }}
              onChange={(e) => handleFileChange(e.target.files?.[0] || null)}
            />
            <div style={{ fontSize: 32 }}>📄</div>
            <div>
              <strong style={{ display: "block", fontSize: 14, color: "var(--text)" }}>
                {file ? file.name : "Drop candidate document here or click to browse"}
              </strong>
              <span style={{ display: "block", fontSize: 12, color: "var(--muted)", marginTop: 4 }}>
                Markdown (.md), Word (.docx), or YAML (.yaml)
              </span>
            </div>
            {file && (
              <span
                style={{
                  fontSize: 11,
                  background: "var(--surface)",
                  padding: "4px 10px",
                  borderRadius: "var(--radius-pill)",
                  border: "1px solid var(--border)",
                  color: "var(--accent)",
                  fontWeight: 600,
                }}
              >
                {(file.size / 1024).toFixed(1)} KB — Ready
              </span>
            )}
          </div>

          {/* Form Fields & Info */}
          <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            <Field
              label="Profile Name"
              placeholder="e.g. Alex Morgan — Senior Analyst"
              value={profileName}
              onChange={(e) => setProfileName(e.target.value)}
              required
              hint="Workspace label for this candidate profile (max 120 characters)."
            />

            <div
              style={{
                padding: "14px 16px",
                background: "var(--surface-2)",
                borderRadius: "var(--radius-md)",
                border: "1px solid var(--border-soft)",
                fontSize: 12,
                color: "var(--muted)",
                lineHeight: 1.5,
              }}
            >
              <strong style={{ display: "block", color: "var(--text)", marginBottom: 4, fontSize: 13 }}>
                One staged hybrid pipeline
              </strong>
              Deterministic readers preserve source text and locators. AI assists only with ambiguous mapping,
              normalization, and controlled derivation during the review stages.
            </div>

            {error && (
              <div
                role="alert"
                style={{
                  padding: "10px 14px",
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

            <LiveStatus message={statusMessage} />

            <div style={{ display: "flex", gap: 10, marginTop: 8 }}>
              <Button variant="secondary" onClick={onCancel} disabled={loading}>
                Cancel
              </Button>
              <Button
                type="submit"
                variant="primary"
                loading={loading}
                disabled={loading || !file || !profileName.trim()}
              >
                Process document
              </Button>
            </div>
          </div>
        </div>
      </form>
    </div>
  );
};
