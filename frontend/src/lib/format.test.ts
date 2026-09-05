import { describe, expect, it } from "vitest";
import {
  formatIdentifier,
  formatTimestamp,
  formatOutcomeCode,
  formatOutcomeReason,
  formatFactorLabel,
  formatFactorValue,
} from "./format";

describe("format helpers", () => {
  it("keeps IDs compact while retaining their namespace", () => {
    expect(formatIdentifier("profile_e3330a5ed3754d3fa5c46d568bfe37d6")).toBe("profile_e3330a5e…");
  });

  it("renders timestamps without raw ISO precision", () => {
    const formatted = formatTimestamp("2026-09-03T22:16:03.134823+00:00");
    expect(formatted).not.toContain("T");
    expect(formatted).not.toContain(".134823");
  });

  it("labels advanced outcomes as progressing to next stage", () => {
    expect(formatOutcomeCode("advanced")).toBe("Advanced to next stage");
  });

  it("prefers human-readable outcome detail and stage_outcome_reason over raw reason_code", () => {
    // Prefers outcome.detail
    expect(formatOutcomeReason({ outcome: { detail: "Matched all core qualifications." }, reason_code: "matched_all" }))
      .toBe("Matched all core qualifications.");

    // Prefers stage_outcome_reason over reason_code
    expect(formatOutcomeReason({ stage_outcome_reason: "Missing 3+ years experience.", reason_code: "disqualified_experience" }))
      .toBe("Missing 3+ years experience.");

    // Formats snake_case reason_code to readable sentence when detail is absent
    expect(formatOutcomeReason({ reason_code: "disqualified_seniority" }))
      .toBe("Disqualified seniority");

    // Formats mapped statuses and string codes cleanly
    expect(formatOutcomeReason("reranker_fit_below_threshold"))
      .toBe("Reranker fit below threshold");
    expect(formatOutcomeReason("ranked_blocked_by_reranker_fit"))
      .toBe("Blocked by reranker fit");

    // Falls back to empty string when no reason exists
    expect(formatOutcomeReason({}))
      .toBe("");
  });

  it("formats technical underscore identifiers into clear user-facing factor labels", () => {
    expect(formatFactorLabel("evidence_ref")).toBe("Evidence Reference");
    expect(formatFactorLabel("pipeline_status")).toBe("Pipeline Status");
    expect(formatFactorLabel("skip_is_terminal_rejection")).toBe("Skip Terminal Rejection");
    expect(formatFactorLabel("reranker_fit")).toBe("Reranker Fit");
    expect(formatFactorLabel("language_fit")).toBe("Language Fit");
    expect(formatFactorLabel("")).toBe("");
  });

  it("formats factor values preserving status meaning and metadata", () => {
    // Boolean flag
    expect(formatFactorValue(false)).toEqual({
      label: "No",
      variant: "neutral",
    });
    expect(formatFactorValue(true)).toEqual({
      label: "Yes",
      variant: "info",
    });

    // Pipeline statuses
    expect(formatFactorValue("ranked_no_cv")).toEqual({
      label: "Ranked without CV",
      variant: "neutral",
    });
    expect(formatFactorValue("ranked_with_cv")).toEqual({
      label: "Ranked with CV",
      variant: "success",
    });

    // Evidence ref artifact object
    expect(formatFactorValue({ artifact: "results.json" })).toEqual({
      label: "results.json",
      variant: "neutral",
      reason: undefined,
    });

    // Fit evaluation object with passed: false and reason
    expect(formatFactorValue({ passed: false, reason: "reranker_fit_below_threshold" })).toEqual({
      label: "✕ Missing / Below threshold",
      variant: "danger",
      reason: "Reranker fit below threshold",
    });
  });
});
