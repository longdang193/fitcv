import { test, expect } from "@playwright/test";

test.describe("FitCV Frontend Smoke & Shell", () => {
  test("loads application shell and renders navigation and header", async ({ page }) => {
    await page.goto("/app/#/overview");

    // Check title and shell
    await expect(page).toHaveTitle(/FitCV/);
    await expect(page.locator(".brand strong")).toHaveText("FitCV");

    // Check navigation
    await expect(page.locator("nav[aria-label='Main Navigation']")).toBeVisible();
    await expect(page.locator(".nav-link.active")).toContainText("Overview");

    // Check theme switch
    const initialTheme = await page.evaluate(() =>
      document.documentElement.getAttribute("data-theme")
    );
    expect(initialTheme).toBe("light");
  });
});
