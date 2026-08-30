import { test, expect } from "@playwright/test";

test.describe("Candidate Profile Feature Journey", () => {
  test("navigates to Candidate Profile catalog, checks tabs and upload view", async ({ page }) => {
    // Route to candidate profile catalog
    await page.goto("/app/#/candidate-profile");

    // Header and title checks
    await expect(page.locator("h2")).toContainText("Candidate Profiles");
    await expect(page.locator("button:has-text('Create Profile')")).toBeVisible();

    // Check tabs
    const activeTab = page.locator("button[role='tab'][data-profile-tab='active'], button[role='tab']:has-text('Active')");
    await expect(activeTab).toBeVisible();

    const archivedTab = page.locator("button[role='tab'][data-profile-tab='archived'], button[role='tab']:has-text('Archived')");
    await expect(archivedTab).toBeVisible();

    // Navigate to Create Profile view
    await page.click("button:has-text('Create Profile')");
    await expect(page.locator("h2")).toContainText("Upload candidate document");
    await expect(page.locator("label:has-text('Profile Name')")).toBeVisible();
    await expect(page.locator("button:has-text('Process document')")).toBeVisible();

    // Cancel back to catalog
    await page.click("button:has-text('Back to Candidate Profiles'), button:has-text('Cancel')");
    await expect(page.locator("h2")).toContainText("Candidate Profiles");
  });
});
