import React, { useEffect, useState, useRef } from "react";
import { Dialog, Button, LoadingState, ErrorState } from "../../../components";
import { fetchSourceBlock } from "../api";
import { SourceBlock } from "../types";

export interface SourceDialogProps {
  open: boolean;
  onClose: () => void;
  attemptId: string;
  title: string;
  description?: string;
  sourceBlockId?: string;
  sourceRefs?: Array<{ document_id?: string; locator?: Record<string, any> }>;
  reviewedValue?: string;
  evidenceItems?: Array<{
    id: string;
    title?: string;
    text?: string;
    kind?: string;
    start?: string;
    end?: string;
    source_refs?: Array<{ document_id?: string; locator?: Record<string, any> }>;
  }>;
}

export const SourceDialog: React.FC<SourceDialogProps> = ({
  open,
  onClose,
  attemptId,
  title,
  description = "Source evidence citation and locators.",
  sourceBlockId,
  sourceRefs,
  reviewedValue,
  evidenceItems,
}) => {
  const [sourceBlock, setSourceBlock] = useState<SourceBlock | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const triggerElementRef = useRef<HTMLElement | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  // Focus return & keydown (Escape & Focus Containment) management
  useEffect(() => {
    if (open) {
      triggerElementRef.current = document.activeElement as HTMLElement;

      const handleKeyDown = (e: KeyboardEvent) => {
        if (e.key === "Escape") {
          e.preventDefault();
          e.stopPropagation();
          onClose();
          return;
        }

        if (e.key === "Tab" && containerRef.current) {
          const root = containerRef.current.closest("dialog") || containerRef.current;
          const focusable = root.querySelectorAll<HTMLElement>(
            "button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex=\"-1\"])"
          );
          if (focusable.length === 0) {
            e.preventDefault();
            return;
          }

          const first = focusable[0];
          const last = focusable[focusable.length - 1];

          if (e.shiftKey) {
            if (document.activeElement === first || !root.contains(document.activeElement)) {
              e.preventDefault();
              last.focus();
            }
          } else {
            if (document.activeElement === last || !root.contains(document.activeElement)) {
              e.preventDefault();
              first.focus();
            }
          }
        }
      };

      window.addEventListener("keydown", handleKeyDown, true);

      return () => {
        window.removeEventListener("keydown", handleKeyDown, true);
        if (triggerElementRef.current && typeof triggerElementRef.current.focus === "function") {
          triggerElementRef.current.focus();
        }
      };
    }
  }, [open, onClose]);

  // Fetch source block data when dialog opens
  useEffect(() => {
    if (!open || !sourceBlockId) {
      setSourceBlock(null);
      setError(null);
      return;
    }

    let isMounted = true;
    setLoading(true);
    setError(null);

    fetchSourceBlock(attemptId, sourceBlockId)
      .then((data) => {
        if (isMounted) {
          setSourceBlock(data);
          setLoading(false);
        }
      })
      .catch((err) => {
        if (isMounted) {
          setError(err.message || "Failed to load source block");
          setLoading(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, [open, attemptId, sourceBlockId]);

  function formatLocator(locator?: Record<string, any>): string {
    if (!locator) return "unresolved";
    if (locator.kind === "markdown_lines") {
      return `Markdown: lines ${locator.start}-${locator.end}`;
    }
    if (locator.kind === "docx_paragraph") {
      return `Word DOCX: paragraph ${locator.paragraph}`;
    }
    return JSON.stringify(locator);
  }

  return (
    <Dialog
      open={open}
      onClose={onClose}
      title={title}
      description={description}
      footer={
        <Button variant="primary" onClick={onClose} autoFocus>
          Close
        </Button>
      }
    >
      <div ref={containerRef} style={{ display: "flex", flexDirection: "column", gap: 16, fontSize: 13 }}>
        {reviewedValue && (
          <div style={{ padding: "12px 14px", background: "var(--surface-2)", borderRadius: "var(--radius-md)" }}>
            <strong style={{ display: "block", fontSize: 11, textTransform: "uppercase", color: "var(--muted)", marginBottom: 4 }}>
              Reviewed Value
            </strong>
            <div style={{ whiteSpace: "pre-wrap", color: "var(--text)" }}>{reviewedValue}</div>
          </div>
        )}

        {loading && <LoadingState message="Fetching source evidence..." />}
        {error && (
          <ErrorState
            message={error}
            actionLabel="Retry"
            onRetry={() => sourceBlockId && fetchSourceBlock(attemptId, sourceBlockId)}
          />
        )}

        {sourceBlock && (
          <div style={{ border: "1px solid var(--border)", borderRadius: "var(--radius-md)", overflow: "hidden" }}>
            <div
              style={{
                padding: "8px 12px",
                background: "var(--surface-2)",
                borderBottom: "1px solid var(--border)",
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
              }}
            >
              <code style={{ fontSize: 12, color: "var(--accent)" }}>{sourceBlock.source_block_id}</code>
              <span style={{ fontSize: 11, color: "var(--muted)" }}>{formatLocator(sourceBlock.locator)}</span>
            </div>
            <div
              style={{
                padding: 12,
                background: "var(--surface)",
                fontFamily: "var(--font-mono)",
                fontSize: 12,
                whiteSpace: "pre-wrap",
                maxHeight: 240,
                overflowY: "auto",
              }}
            >
              {sourceBlock.text}
            </div>
          </div>
        )}

        {sourceRefs && sourceRefs.length > 0 && !sourceBlock && (
          <div>
            <strong style={{ display: "block", fontSize: 12, color: "var(--muted)", marginBottom: 6 }}>
              Document Locators
            </strong>
            <ul style={{ margin: 0, paddingLeft: 20, color: "var(--text)" }}>
              {sourceRefs.map((ref, idx) => (
                <li key={idx}>
                  <code>{formatLocator(ref.locator)}</code>
                  {ref.document_id && <span style={{ marginLeft: 8, color: "var(--muted)", fontSize: 11 }}>({ref.document_id})</span>}
                </li>
              ))}
            </ul>
          </div>
        )}

        {evidenceItems && evidenceItems.length > 0 && (
          <div>
            <strong style={{ display: "block", fontSize: 12, color: "var(--muted)", marginBottom: 8 }}>
              Referenced Baseline Evidence ({evidenceItems.length})
            </strong>
            <div style={{ display: "flex", flexDirection: "column", gap: 8, maxHeight: 280, overflowY: "auto" }}>
              {evidenceItems.map((ev) => (
                <div
                  key={ev.id}
                  style={{
                    padding: "10px 12px",
                    border: "1px solid var(--border)",
                    borderRadius: "var(--radius-md)",
                    background: "var(--surface)",
                  }}
                >
                  <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
                    <code style={{ fontSize: 12, color: "var(--accent)" }}>{ev.id}</code>
                    {ev.title && <span style={{ fontSize: 12, fontWeight: 600 }}>{ev.title}</span>}
                  </div>
                  {ev.text && <p style={{ margin: 0, fontSize: 12, color: "var(--text)", whiteSpace: "pre-wrap" }}>{ev.text}</p>}
                  {ev.source_refs && ev.source_refs.length > 0 && (
                    <div style={{ marginTop: 6, fontSize: 11, color: "var(--muted)" }}>
                      <span>Source: </span>
                      <code>{formatLocator(ev.source_refs[0].locator)}</code>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </Dialog>
  );
};
