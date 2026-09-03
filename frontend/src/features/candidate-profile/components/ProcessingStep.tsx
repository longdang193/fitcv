import React, { useEffect, useState, useRef, useCallback } from "react";
import { Button, LoadingState, ErrorState, LiveStatus } from "../../../components";
import { fetchCreationAttempt, retryAttempt } from "../api";
import { CreationAttempt } from "../types";

export interface CandidateProfileFailurePresentation {
  title: string;
  message: string;
  requiresProviderSetup: boolean;
}

export function getCandidateProfileFailurePresentation(
  failure?: CreationAttempt["failure"]
): CandidateProfileFailurePresentation {
  if (failure?.code === "candidate_profile_llm_unavailable") {
    return {
      title: "Provider setup required",
      message:
        "Candidate Profile cannot regenerate AI-assisted fields because its LLM route is unavailable. Open Provider Settings, verify a provider connection, add a validated model, set Default Route, then return and retry processing.",
      requiresProviderSetup: true,
    };
  }

  return {
    title: "Processing Failed",
    message: failure?.message || "Processing failed.",
    requiresProviderSetup: false,
  };
}

export interface ProcessingStepProps {
  attemptId: string;
  targetStage?: "review_baseline" | "review_derived" | "confirm" | string;
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

  const isTerminalOrReady = useCallback((data: CreationAttempt) => {
    if (data.creation_status === "failed") {
      return true;
    }
    if (
      data.creation_status === "succeeded" ||
      data.next_action === "view_profile" ||
      Boolean(data.profile_id && data.creation_status === "succeeded") ||
      data.next_action === "review_baseline" ||
      data.next_action === "review_derived" ||
      data.next_action === "confirm" ||
      data.creation_status === "base_review" ||
      data.creation_status === "derived_review" ||
      data.creation_status === "ready_to_confirm" ||
      data.creation_status === "confirmed" ||
      (targetStage && data.next_action === targetStage)
    ) {
      return true;
    }
    return false;
  }, [targetStage]);

  const scheduleNextPoll = useCallback((delayMs = 1000) => {
    if (pollTimerRef.current) {
      clearTimeout(pollTimerRef.current);
    }
    pollTimerRef.current = setTimeout(async () => {
      if (!isMountedRef.current) return;
      try {
        const data = await fetchCreationAttempt(attemptId);
        if (!isMountedRef.current) return;
        setAttempt(data);

        if (data.creation_status === "failed") {
          setError(data.failure?.message || "Processing failed.");
          setStatusMessage("Candidate profile processing failed.");
          return;
        }

        if (isTerminalOrReady(data)) {
          setStatusMessage("Ready for review!");
          onReady(data);
          return;
        }

        setStatusMessage(
          data.creation_status === "base_mapping" || data.creation_status === "extracting_base"
            ? "Extracting baseline document structure and locators..."
            : data.creation_status === "derived_claims" || data.creation_status === "deriving"
            ? "Inferring derived claims and evidence references..."
            : "Processing candidate document..."
        );

        const nextDelay =
          typeof data.poll_after_ms === "number" && data.poll_after_ms > 0
            ? data.poll_after_ms
            : 1000;
        scheduleNextPoll(nextDelay);
      } catch (err: any) {
        if (!isMountedRef.current) return;
        setError(err.message || "Failed to check processing status.");
      }
    }, delayMs);
  }, [attemptId, onReady, isTerminalOrReady]);

  useEffect(() => {
    isMountedRef.current = true;
    setError(null);
    setStatusMessage("Processing candidate document...");

    async function initialPoll() {
      try {
        const data = await fetchCreationAttempt(attemptId);
        if (!isMountedRef.current) return;
        setAttempt(data);

        if (data.creation_status === "failed") {
          setError(data.failure?.message || "Processing failed.");
          setStatusMessage("Candidate profile processing failed.");
          return;
        }

        if (isTerminalOrReady(data)) {
          setStatusMessage("Ready for review!");
          onReady(data);
          return;
        }

        setStatusMessage(
          data.creation_status === "base_mapping" || data.creation_status === "extracting_base"
            ? "Extracting baseline document structure and locators..."
            : data.creation_status === "derived_claims" || data.creation_status === "deriving"
            ? "Inferring derived claims and evidence references..."
            : "Processing candidate document..."
        );

        const nextDelay =
          typeof data.poll_after_ms === "number" && data.poll_after_ms > 0
            ? data.poll_after_ms
            : 1000;
        scheduleNextPoll(nextDelay);
      } catch (err: any) {
        if (!isMountedRef.current) return;
        setError(err.message || "Failed to check processing status.");
      }
    }

    initialPoll();

    return () => {
      isMountedRef.current = false;
      if (pollTimerRef.current) {
        clearTimeout(pollTimerRef.current);
      }
    };
  }, [attemptId, scheduleNextPoll, onReady, isTerminalOrReady]);

  const handleRetry = async () => {
    if (!attempt) return;
    setIsRetrying(true);
    setError(null);
    setStatusMessage("Retrying processing...");

    try {
      const res = await retryAttempt(attempt.attempt_id, attempt.revision);
      if (!isMountedRef.current) return;
      setAttempt(res);
      setIsRetrying(false);

      if (res.creation_status === "failed") {
        setError(res.failure?.message || "Processing failed.");
        setStatusMessage("Candidate profile processing failed.");
        return;
      }

      if (isTerminalOrReady(res)) {
        setStatusMessage("Ready for review!");
        onReady(res);
        return;
      }

      setStatusMessage("Processing candidate document...");
      const nextDelay =
        typeof res.poll_after_ms === "number" && res.poll_after_ms > 0
          ? res.poll_after_ms
          : 1000;
      scheduleNextPoll(nextDelay);
    } catch (err: any) {
      if (!isMountedRef.current) return;
      setError(err.message || "Failed to retry processing.");
      setIsRetrying(false);
    }
  };

  const failurePresentation = getCandidateProfileFailurePresentation(attempt?.failure);

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
            title={failurePresentation.title}
            message={failurePresentation.requiresProviderSetup ? failurePresentation.message : error}
            actionLabel={attempt ? (isRetrying ? "Retrying..." : "Retry Processing") : "Start New Upload"}
            onRetry={attempt ? handleRetry : onCancel}
          />
          {failurePresentation.requiresProviderSetup && (
            <a
              href="#/settings/providers"
              className="btn btn-primary"
              style={{ textDecoration: "none" }}
            >
              Open Provider Settings
            </a>
          )}
          <LiveStatus message={`Error: ${error}`} level="assertive" />
          <Button variant="secondary" onClick={onCancel}>
            Return to Candidate Profiles
          </Button>
        </div>
      )}
    </div>
  );
};
