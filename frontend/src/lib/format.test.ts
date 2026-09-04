import { describe, expect, it } from "vitest";
import { formatIdentifier, formatTimestamp, formatOutcomeCode, formatOutcomeReason } from "./format";

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

    // Falls back to empty string when no reason exists
    expect(formatOutcomeReason({}))
      .toBe("");
  });
});
