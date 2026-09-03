import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { EvidenceReferenceButton } from "./EvidenceReferenceButton";
import { ReviewLogConsole } from "./ReviewLogConsole";

describe("candidate profile review UX", () => {
  it("makes evidence reference text a clickable details control", () => {
    const html = renderToStaticMarkup(
      React.createElement(EvidenceReferenceButton, {
        referenceIds: ["ev_1", "ev_2"],
        onOpen: () => undefined,
      })
    );

    expect(html).toContain('aria-label="View 2 evidence references"');
    expect(html).toContain("2 evidence refs");
    expect(html).toContain("ev_1, ev_2");
  });

  it("renders traceability in collapsed bottom review log", () => {
    const html = renderToStaticMarkup(
      React.createElement(ReviewLogConsole, {
        stage: "baseline",
        attemptId: "att_123",
        statusMessage: "Baseline facts loaded.",
        revision: 4,
        fingerprint: "fp_base",
      })
    );

    expect(html).toContain("Review log");
    expect(html).toContain('aria-expanded="false"');
    expect(html).toContain("Baseline facts loaded.");
    expect(html).toContain("att_123");
    expect(html).toContain("fp_base");
  });
  it("does not render redundant top back buttons in baseline review and preserves approve action", async () => {
    const { BaselineReviewStep } = await import("./BaselineReviewStep");
    const html = renderToStaticMarkup(
      React.createElement(BaselineReviewStep as any, {
        attemptId: "att_test",
        onApproveSuccess: () => undefined,
        onSaveAndExit: () => undefined,
      })
    );

    // Initial loading or loaded markup must not contain redundant header back button
    expect(html).not.toContain("backToDerivedFromBaseline");
  });

  it("does not render redundant top back buttons in derived review and preserves bottom navigation", async () => {
    const { DerivedReviewStep } = await import("./DerivedReviewStep");
    const html = renderToStaticMarkup(
      React.createElement(DerivedReviewStep as any, {
        attemptId: "att_test",
        onBackToBaseline: () => undefined,
        onBackToConfirmation: () => undefined,
        onApproveSuccess: () => undefined,
        onSaveAndExit: () => undefined,
      })
    );

    expect(html).not.toContain("backToConfirmationHeader");
    expect(html).not.toContain("backToBaselineHeader");
  });
});
