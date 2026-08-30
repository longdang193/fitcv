import React, { useState, useEffect, useCallback } from "react";
import { CatalogView } from "./components/CatalogView";
import { UploadStep } from "./components/UploadStep";
import { ProcessingStep } from "./components/ProcessingStep";
import { BaselineReviewStep } from "./components/BaselineReviewStep";
import { DerivedReviewStep } from "./components/DerivedReviewStep";
import { ConfirmationStep } from "./components/ConfirmationStep";
import { DetailView } from "./components/DetailView";
import { CreationStepper, CreationStage } from "./components/CreationStepper";
import { CreationAttempt } from "./types";

export interface ParsedCandidateRoute {
  view: "catalog" | "create_upload" | "create_processing" | "create_baseline" | "create_derived" | "create_confirm" | "detail";
  attemptId?: string;
  profileId?: string;
}

export function parseCandidateRoute(hash: string): ParsedCandidateRoute {
  const clean = (hash || "").replace(/^#\/?/, "").split("?")[0];
  const parts = clean.split("/").filter(Boolean);

  if (parts.length === 0 || parts[0] !== "candidate-profile") {
    return { view: "catalog" };
  }

  if (parts.length === 1) {
    return { view: "catalog" };
  }

  if (parts[1] === "create") {
    if (parts.length === 2) {
      return { view: "create_upload" };
    }
    const attemptId = decodeURIComponent(parts[2]);
    const sub = parts[3];

    if (sub === "baseline") {
      return { view: "create_baseline", attemptId };
    }
    if (sub === "derived") {
      return { view: "create_derived", attemptId };
    }
    if (sub === "confirm") {
      return { view: "create_confirm", attemptId };
    }
    return { view: "create_processing", attemptId };
  }

  // Otherwise it is a profileId
  const profileId = decodeURIComponent(parts[1]);
  return { view: "detail", profileId };
}

export const CandidateProfileRoute: React.FC = () => {
  const [currentHash, setCurrentHash] = useState<string>(() => {
    if (typeof window !== "undefined" && window.location.hash) {
      return window.location.hash;
    }
    return "#/candidate-profile";
  });

  useEffect(() => {
    const onHash = () => {
      setCurrentHash(window.location.hash || "#/candidate-profile");
    };
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);

  const navigate = useCallback((targetHash: string) => {
    window.location.hash = targetHash;
    setCurrentHash(targetHash);
  }, []);

  const routeState = parseCandidateRoute(currentHash);

  // Navigation handlers
  const handleOpenCreate = () => {
    navigate("#/candidate-profile/create");
  };

  const handleResumeAttempt = (attemptId: string, stage = "baseline") => {
    navigate(`#/candidate-profile/create/${encodeURIComponent(attemptId)}/${stage}`);
  };

  const handleOpenDetail = (profileId: string) => {
    navigate(`#/candidate-profile/${encodeURIComponent(profileId)}`);
  };

  const handleUploadSuccess = (attempt: CreationAttempt) => {
    if (attempt.next_action === "review_baseline" || attempt.creation_status === "base_review") {
      navigate(`#/candidate-profile/create/${encodeURIComponent(attempt.attempt_id)}/baseline`);
    } else {
      navigate(`#/candidate-profile/create/${encodeURIComponent(attempt.attempt_id)}`);
    }
  };

  const handleProcessingReady = (attempt: CreationAttempt) => {
    if (attempt.next_action === "review_derived" || attempt.creation_status === "derived_review") {
      navigate(`#/candidate-profile/create/${encodeURIComponent(attempt.attempt_id)}/derived`);
    } else if (attempt.next_action === "confirm" || attempt.creation_status === "confirmed") {
      navigate(`#/candidate-profile/create/${encodeURIComponent(attempt.attempt_id)}/confirm`);
    } else {
      navigate(`#/candidate-profile/create/${encodeURIComponent(attempt.attempt_id)}/baseline`);
    }
  };

  const handleBaselineApproved = (attemptId: string) => {
    navigate(`#/candidate-profile/create/${encodeURIComponent(attemptId)}/derived`);
  };

  const handleDerivedApproved = (attemptId: string) => {
    navigate(`#/candidate-profile/create/${encodeURIComponent(attemptId)}/confirm`);
  };

  const handleProfileConfirmed = (profileId: string) => {
    navigate(`#/candidate-profile/${encodeURIComponent(profileId)}`);
  };

  const handleBackToCatalog = () => {
    navigate("#/candidate-profile");
  };

  // Determine current stepper stage if in creation flow
  const stepperStage: CreationStage | null =
    routeState.view === "create_upload"
      ? "upload"
      : routeState.view === "create_baseline"
      ? "baseline"
      : routeState.view === "create_derived"
      ? "derived"
      : routeState.view === "create_confirm"
      ? "confirm"
      : null;

  return (
    <div className="content-container candidate-profile-feature">
      {stepperStage && <CreationStepper currentStage={stepperStage} />}

      {routeState.view === "catalog" && (
        <CatalogView
          onOpenCreate={handleOpenCreate}
          onResumeAttempt={handleResumeAttempt}
          onOpenDetail={handleOpenDetail}
        />
      )}

      {routeState.view === "create_upload" && (
        <UploadStep
          onSuccess={handleUploadSuccess}
          onCancel={handleBackToCatalog}
        />
      )}

      {routeState.view === "create_processing" && routeState.attemptId && (
        <ProcessingStep
          attemptId={routeState.attemptId}
          targetStage="review_baseline"
          onReady={handleProcessingReady}
          onCancel={handleBackToCatalog}
        />
      )}

      {routeState.view === "create_baseline" && routeState.attemptId && (
        <BaselineReviewStep
          attemptId={routeState.attemptId}
          onApproveSuccess={() => handleBaselineApproved(routeState.attemptId!)}
          onSaveAndExit={handleBackToCatalog}
        />
      )}

      {routeState.view === "create_derived" && routeState.attemptId && (
        <DerivedReviewStep
          attemptId={routeState.attemptId}
          onApproveSuccess={() => handleDerivedApproved(routeState.attemptId!)}
          onSaveAndExit={handleBackToCatalog}
        />
      )}

      {routeState.view === "create_confirm" && routeState.attemptId && (
        <ConfirmationStep
          attemptId={routeState.attemptId}
          onConfirmed={handleProfileConfirmed}
          onCancel={handleBackToCatalog}
        />
      )}

      {routeState.view === "detail" && routeState.profileId && (
        <DetailView
          profileId={routeState.profileId}
          onBack={handleBackToCatalog}
        />
      )}
    </div>
  );
};

export const route = {
  id: "candidate-profile",
  path: "#/candidate-profile",
  title: "Candidate Profile",
  group: "workspace" as const,
  order: 20,
  component: CandidateProfileRoute,
};

export default route;
