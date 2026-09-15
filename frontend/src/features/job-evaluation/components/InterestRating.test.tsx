import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { InterestRating, getInterestRatingDisabledReason } from "./InterestRating";

describe("InterestRating", () => {
  it("explains why unrated jobs cannot be rated", () => {
    const reason = getInterestRatingDisabledReason({
      capabilities: { rate: false },
      reason_code: "not_selected_by_shortlist",
    });
    const markup = renderToStaticMarkup(
      <InterestRating
        rating={null}
        disabled
        disabledReason={reason}
        onChange={() => {}}
      />
    );

    expect(reason).toBe(
      "Rating unavailable: this job was not selected for shortlist decision feedback."
    );
    expect(markup).toContain(reason);
    expect(markup).toContain('aria-label="Application interest: Unrated. ' + reason + '"');
  });
});
