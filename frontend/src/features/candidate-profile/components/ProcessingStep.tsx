import React, { useEffect, useState, useRef } from "react";
import { Button, LoadingState, ErrorState, LiveStatus } from "../../../components";
import { fetchCreationAttempt, retryAttempt } from "../api";
import { CreationAttempt } from "../types";

export interface ProcessingStepProps {
  attemptId: string;
  targetStage: "review_baseline" | "review_derived" | "confirm";
  onReady: (attempt: CreationAttempt) => void;
  onCancel: () => void;
}

export const ProcessingStep: React.FC<ProcessingStepProps> = ({
  attemptId,
  targetStage,
  onReady,
  onCancel,
}) => {
  const [attempt, setAttempt] = useState<CreationAttempt | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isRetrying, setIsRetrying] = useState(false);
  const [statusMessage, setStatusMessage] = useState("Processing candidate document...");
  const pollTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const isMountedRef = useRef(true);

  useEffect(() => {
    isMountedRef.current = true;

    async function poll() {
      try {
        const data = await fetchCreationAttempt(attemptId);
        if (!isMountedRef.current) return;

        setAttempt(data);

        if (data.creation_status === "failed") {
          setError(data.failure?.message || "Processing failed.");
          setStatusMessage("Candidate profile processing failed.");
          return;
        }

        if (data.next_action === targetStage || data.creation_status === "base_review" || data.creation_status === "derived_review" || data.creation_status === "confirmed") {
          setStatusMessage("Ready for review!");
          onReady(data);
          return;
        }

        setStatusMessage(
          data.creation_status === "base_mapping"
            ? "Extracting baseline document structure and locators..."
            : data.creation_status === "derived_claims"
            ? "Inferring derived claims and evidence references..."
            : "Processing candidate document..."
        );

        pollTimerRef.current = setTimeout(poll, 1000);
      } catch (err: any) {
        if (!isMountedRef.current) return;
        setError(err.message || "Failed to check processing status.");
      }
    }

    poll();

    return () => {
      isMountedRef.current = false;
      if (pollTimerRef.current) {
        clearTimeout(pollTimerRef.current);
      }
    };
  }, [attemptId, targetStage, onReady]);

  const handleRetry = async () => {
    if (!attempt) return;
    setIsRetrying(true);
    setError(null);
    setStatusMessage("Retrying processing...");

    try {
      const res = await retryAttempt(attempt.attempt_id, attempt.revision);
      setAttempt(res);
      setIsRetrying(false);
      pollTimerRef.current = setTimeout(() => {
        if (isMountedRef.current) {
          fetchCreationAttempt(attemptId).then((d) => onReady(d));
        }
      }, 1000);
    } catch (err: any) {
      setError(err.message || "Failed to retry processing.");
      setIsRetrying(false);
    }
  };

  return (
    <div className="table-card" style={{ padding: 48, textAlign: "center" }}>
      {!error ? (
        <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 16 }}>
          <LoadingState message={statusMessage} />
          <LiveStatus message={statusMessage} />
          <p style={{ margin: 0, color: "var(--muted)", fontSize: 13, maxWidth: 460 }}>
            Deterministic document ingestion in progress. Source blocks are being registered and locators mapped.
          </p>
          <Button variant="secondary" onClick={onCancel} style={{ marginTop: 8 }}>
            Exit to Candidate Profiles
          </Button>
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 16 }}>
          <ErrorState
            title="Processing Failed"
            message={error}
            actionLabel={attempt?.capabilities?.retry ? (isRetrying ? "Retrying..." : "Retry Processing") : "Start New Upload"}
            onRetry={attempt?.capabilities?.retry ? handleRetry : onCancel}
          />
          <LiveStatus message={`Error: ${error}`} level="assertive" />
          <Button variant="secondary" onClick={onCancel}>
            Return to Candidate Profiles
          </Button>
        </div>
      )}
    </div>
  );
};
