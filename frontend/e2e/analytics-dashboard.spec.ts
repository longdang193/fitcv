import { test, expect } from "@playwright/test";

test.describe("Analytics dashboard", () => {
  test("shows coverage and source-posting traceability", async ({ page }) => {
    await page.goto("/app/#/analytics");
    await expect(page.locator("main h2", { hasText: "Analytics" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Coverage" })).toBeVisible();
    await expect(page.getByText("Sample: 2.")).toBeVisible();

    await page.getByLabel("Posting ID").fill("posting-hash");
    await page.getByRole("button", { name: "Inspect source" }).click();
    await expect(page.locator("pre")).toContainText("posting-hash");
  });

  test("renders unavailable coverage without fallback claims", async ({ page }) => {
    await page.route("**/analytics/semantic-metrics", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          data: {
            coverage: {
              status: "unavailable",
              sample_size: 0,
              source_mix: [],
              collection_window: { start: null, end: null },
              candidate_revisions: [],
              unavailable_reasons: ["published_source_commit_stale"],
            },
            metadata: {},
            opportunity_landscape: [],
            requirement_demand: [],
            candidate_evidence_gaps: [],
          },
        }),
      });
    });
    await page.goto("/app/#/analytics");
    await expect(page.locator(".notice.warn")).toContainText("Published analytics unavailable");
    await expect(page.getByText("published_source_commit_stale")).toBeVisible();
  });
});
