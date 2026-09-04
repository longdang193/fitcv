import { test, expect } from "@playwright/test";

test.describe("Candidate Profile Feature Journey", () => {
  test("navigates to Candidate Profile catalog, checks tabs and upload view", async ({ page }) => {
    // Route to candidate profile catalog
    await page.goto("/app/#/candidate-profile");

    // Header and title checks
    await expect(page.locator("h2")).toContainText("Candidate Profiles");
    await expect(page.locator("button:has-text('Create Profile')")).toBeVisible();

    // Check tabs
    const activeTab = page.locator("button[role='tab']:has-text('Active')");
    await expect(activeTab).toBeVisible();

    const archivedTab = page.locator("button[role='tab']:has-text('Archived')");
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

  test("deep-links directly to creation upload stage and back", async ({ page }) => {
    await page.goto("/app/#/candidate-profile/create");
    await expect(page.locator("h2")).toContainText("Upload candidate document");
    await expect(page.locator("input[placeholder*='Alex Morgan']")).toBeVisible();

    await page.click("button:has-text('Back to Candidate Profiles')");
    await expect(page.locator("h2")).toContainText("Candidate Profiles");
  });

  test("keeps candidate profile detail within 390px viewport", async ({ page }) => {
    await page.route("**/candidate-profiles/profile_mobile", async (route) => {
      await route.fulfill({
        contentType: "application/json",
        body: JSON.stringify({
          data: {
            profile_id: "profile_mobile",
            profile_name: "Mobile Profile",
            display_name: "A very long candidate profile name that must wrap on mobile",
            lifecycle: "active",
            creation_status: "succeeded",
            revision: 1,
            created_at: "2026-09-04T00:00:00Z",
            capabilities: { archive: false, edit: false },
            canonical: {},
          },
        }),
      });
    });

    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto("/app/#/candidate-profile/profile_mobile");
    await expect(page.locator("h2")).toContainText("very long candidate profile name");
    await expect(page.locator("main")).toHaveJSProperty("scrollWidth", 390);
  });
});
