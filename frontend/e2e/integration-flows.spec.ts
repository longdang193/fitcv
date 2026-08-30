import { test, expect } from "@playwright/test";

test.describe("Full Cross-Slice Integration & Shell Journeys", () => {
  test("navigates across all workspace and settings routes seamlessly", async ({ page }) => {
    await page.goto("/app/#/overview");

    // Overview
    await expect(page.locator(".brand strong")).toHaveText("FitCV");
    await expect(page.locator("h2:has-text('Overview')")).toBeVisible();

    // Candidate Profile
    await page.click("a.nav-link:has-text('Candidate Profile')");
    await expect(page).toHaveURL(/#\/candidate-profile/);
    await expect(page.locator("h2:has-text('Candidate Profiles')")).toBeVisible();

    // Scans
    await page.click("a.nav-link:has-text('Scans')");
    await expect(page).toHaveURL(/#\/scans/);
    await expect(page.locator("h1:has-text('Scans')")).toBeVisible();

    // Runs
    await page.click("a.nav-link:has-text('Runs')");
    await expect(page).toHaveURL(/#\/runs/);
    await expect(page.locator("main h1:has-text('Runs')")).toBeVisible();

    // Evaluation & Fit
    await page.click("a.nav-link:has-text('Evaluation & Fit')");
    await expect(page).toHaveURL(/#\/job-evaluation/);
    await expect(page.locator("h1:has-text('Evaluation & Fit')")).toBeVisible();

    // CV Review
    await page.click("a.nav-link:has-text('CV Review')");
    await expect(page).toHaveURL(/#\/cv-review/);
    await expect(page.locator("h2:has-text('CV Review & Artifacts')")).toBeVisible();

    // Bookmarks
    await page.click("a.nav-link:has-text('Bookmarks')");
    await expect(page).toHaveURL(/#\/bookmarks/);
    await expect(page.locator("h2:has-text('Bookmarks')")).toBeVisible();

    // Synonyms
    await page.click("a.nav-link:has-text('Synonyms')");
    await expect(page).toHaveURL(/#\/synonyms/);
    await expect(page.locator("h2:has-text('Taxonomy & Synonyms')")).toBeVisible();

    // Personalization
    await page.click("a.nav-link:has-text('Personalization')");
    await expect(page).toHaveURL(/#\/settings\/personalization/);
    await expect(page.locator("h2:has-text('Personalization')")).toBeVisible();
  });

  test("toggles theme and maintains accessibility state", async ({ page }) => {
    await page.goto("/app/#/overview");

    const html = page.locator("html");
    await expect(html).toHaveAttribute("data-theme", "light");

    // Click theme toggle
    await page.click("button[aria-label*='Switch to dark theme']");
    await expect(html).toHaveAttribute("data-theme", "dark");

    // Click theme toggle again
    await page.click("button[aria-label*='Switch to light theme']");
    await expect(html).toHaveAttribute("data-theme", "light");
  });

  test("manages transient notification dropdown and zero-badge rule", async ({ page }) => {
    await page.goto("/app/#/overview");

    const notifBtn = page.locator("button[aria-label='Notifications']");
    await expect(notifBtn).toBeVisible();

    // Initially zero unread, no badge rendered
    const badge = notifBtn.locator("span[aria-hidden='true']");
    await expect(badge).toHaveCount(0);

    // Open dropdown
    await notifBtn.click();
    const panel = page.locator(".dropdown-panel[aria-label='Notifications panel']");
    await expect(panel).toBeVisible();
    await expect(panel).toContainText("No notifications");

    // Close on Escape key
    await page.keyboard.press("Escape");
    await expect(panel).not.toBeVisible();
  });

  test("supports mobile navigation drawer and scrim closing", async ({ page }) => {
    await page.setViewportSize({ width: 400, height: 800 });
    await page.goto("/app/#/overview");

    const mobileToggle = page.locator("button.mobile-toggle-btn");
    await expect(mobileToggle).toBeVisible();

    // Open drawer
    await mobileToggle.click();
    const sidebar = page.locator("aside.sidebar.is-open");
    await expect(sidebar).toBeVisible();

    // Close drawer via Escape key
    await page.keyboard.press("Escape");
    await expect(sidebar).not.toBeVisible();
  });
});
