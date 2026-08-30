import { test, expect } from "@playwright/test";

test.describe("Runs Feature Journey", () => {
  test("navigates to Runs list, checks tabs, new run modal", async ({ page }) => {
    await page.goto("/app/#/runs");

    // Header and title checks
    await expect(page.locator("main h1:has-text('Runs')")).toBeVisible();
    await expect(page.locator("button:has-text('New Run')")).toBeVisible();

    // Check tabs
    const activeTab = page.locator("button[role='tab']:has-text('Active')");
    await expect(activeTab).toBeVisible();

    const archivedTab = page.locator("button[role='tab']:has-text('Archived')");
    await expect(archivedTab).toBeVisible();

    await page.locator("button[role='tab']:has-text('All Runs')").click();
    await expect(page).toHaveURL(/#\/runs\?view=all$/);
    await page.evaluate(() => {
      window.location.hash = "#/runs";
    });
    await expect(page).toHaveURL(/#\/runs$/);
    await expect(activeTab).toHaveAttribute("aria-selected", "true");

    // Open New Run Dialog
    await page.click("button:has-text('New Run')");
    await expect(page.locator("dialog.new-run-dialog")).toBeVisible();
    await expect(page.locator(".dialog-title")).toHaveText("Trigger New Run");

    // Check source options
    await expect(page.locator("label:has-text('File Upload')")).toBeVisible();
    await expect(page.locator("label:has-text('Scan Outputs')")).toBeVisible();
    await expect(page.locator("label:has-text('Combined (File + Scans)')")).toBeVisible();

    // Close Dialog
    await page.click(".new-run-dialog button:has-text('Cancel')");
    await expect(page.locator("dialog.new-run-dialog")).not.toBeVisible();
  });

  test("handles missing run with graceful error notice and navigation back", async ({ page }) => {
    await page.goto("/app/#/runs?run_id=mock-missing-run");

    // Error notice rendered for missing run
    await expect(page.locator(".notice.error")).toBeVisible();
    await expect(page.locator("button:has-text('Back to Runs')")).toBeVisible();

    // Check back to runs button
    await page.click("button:has-text('Back to Runs')");
    await expect(page.locator("main h1:has-text('Runs')")).toBeVisible();
  });
});
