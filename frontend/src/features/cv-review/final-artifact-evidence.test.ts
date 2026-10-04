import { describe, expect, it } from "vitest";
import { hasVerifiedNativeOnePageRender } from "./final-artifact-evidence";

describe("final artifact evidence", () => {
  it("rejects legacy passed evidence without native one-page proof", () => {
    expect(hasVerifiedNativeOnePageRender({ evidence_state: "passed" })).toBe(false);
  });

  it("accepts complete native one-page proof", () => {
    expect(hasVerifiedNativeOnePageRender({
      evidence_state: "passed",
      page_count: 1,
      page_fit_status: "pass",
      render_acceptance: "passed",
    })).toBe(true);
  });
});
