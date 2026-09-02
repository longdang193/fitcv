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

  test("polls a cancelling run until it is cancelled", async ({ page }) => {
    let reads = 0;
    const run = (backend_status: string, cancel: boolean) => ({
      run_id: "run-cancel-poll",
      run_name: "Cancel Poll Run",
      backend_status,
      display_status: backend_status === "cancelled" ? "Failed" : "Running",
      created_at: "2026-09-02T10:00:00Z",
      counts: { total: 0, passed: 0, rejected: 0, skipped: 0, cvs_generated: 0 },
      progress: { completed: 0, total: 0 },
      capabilities: {
        inspect: true,
        cancel,
        archive: false,
        unarchive: false,
        delete: false,
        export: false,
      },
    });

    await page.route("**/runs?*", async (route) => {
      reads += 1;
      const current = reads === 1 ? run("queued", true) : reads === 2 ? run("cancelling", false) : run("cancelled", false);
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ data: [current], total_items: 1 }),
      });
    });
    await page.route("**/runs/run-cancel-poll/actions/cancel", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ data: run("cancelling", false) }),
      });
    });

    await page.goto("/app/#/runs");
    const row = page.locator("tbody tr");
    await expect(row.getByRole("button", { name: "Cancel", exact: true })).toBeVisible();
    await row.getByRole("button", { name: "Cancel", exact: true }).click();
    await page.getByRole("button", { name: "Confirm", exact: true }).click();
    await expect(row).toContainText("Cancelled", { timeout: 5000 });
    await expect(row.getByRole("button", { name: "Cancel", exact: true })).toHaveCount(0);
  });

  test("shows cancellation refresh failure without claiming success", async ({ page }) => {
    let reads = 0;
    const queuedRun = {
      run_id: "run-cancel-refresh-failure",
      run_name: "Cancel Refresh Failure",
      backend_status: "queued",
      display_status: "Running",
      created_at: "2026-09-02T10:00:00Z",
      counts: { total: 0, passed: 0, rejected: 0, skipped: 0, cvs_generated: 0 },
      progress: { completed: 0, total: 0 },
      capabilities: { inspect: true, cancel: true, archive: false, unarchive: false, delete: false, export: false },
    };
    await page.route("**/runs?*", async (route) => {
      reads += 1;
      if (reads > 1) {
        await route.fulfill({ status: 503, contentType: "application/json", body: JSON.stringify({ detail: "refresh failed" }) });
        return;
      }
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ data: [queuedRun], total_items: 1 }),
      });
    });
    await page.route("**/runs/run-cancel-refresh-failure/actions/cancel", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ data: { ...queuedRun, capabilities: { ...queuedRun.capabilities, cancel: false } } }),
      });
    });

    await page.goto("/app/#/runs");
    const row = page.locator("tbody tr");
    await row.getByRole("button", { name: "Cancel", exact: true }).click();
    await page.getByRole("button", { name: "Confirm", exact: true }).click();
    await expect(page.locator(".notice.error")).toContainText("refresh failed");
    await expect(page.locator(".notice.success")).toHaveCount(0);
  });
});
