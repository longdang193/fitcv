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
    await expect(page.locator("main h2:has-text('Runs')")).toBeVisible();

    // Bookmarks
    await page.click("a.nav-link:has-text('Bookmarks')");
    await expect(page).toHaveURL(/#\/bookmarks/);
    await expect(page.locator("h2:has-text('Bookmarks')")).toBeVisible();

    // Synonyms
    await page.click("a.nav-link:has-text('Synonyms')");
    await expect(page).toHaveURL(/#\/synonyms/);
    await expect(page.locator("h2:has-text('Taxonomy & Synonyms')")).toBeVisible();

    // Preference Optimization
    await page.click("a.nav-link:has-text('Preference Optimization')");
    await expect(page).toHaveURL(/#\/preference-optimization/);
    await expect(page.locator("h2:has-text('Preference Optimization')")).toBeVisible();
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

    const notifBtn = page.locator("button[aria-label*='Notifications']");
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


test.describe("Scan Provider Catalog Discovery & Track Flow", () => {
  test("supports catalog discovery, tracking, disabled Wellfound state, and mobile layout at /app/#/scans", async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });

    await page.route("**/company-catalog/actions/track", async (route) => {
      await route.fulfill({
        status: 201,
        contentType: "application/json",
        body: JSON.stringify({
          data: {
            company_id: "comp-ashby-demo",
            company_name: "Ashby Demo Inc",
            careers_url: "https://jobs.ashbyhq.com/ashbydemo",
            provider_id: "ashby",
            provider_label: "Ashby",
            catalog_id: "company-ashby-demo",
            catalog_source: "bundled",
            catalog_revision: "2026-09-08-v1",
            row_revision: 1,
            created_at: "2026-09-08T12:00:00Z",
            updated_at: "2026-09-08T12:00:00Z",
          },
        }),
      });
    });

    await page.route("**/company-catalog*", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          data: [
            {
              catalog_id: "company-ashby-demo",
              company_name: "Ashby Demo Inc",
              careers_url: "https://jobs.ashbyhq.com/ashbydemo",
              provider_id: "ashby",
              provider_label: "Ashby",
              provider_config: { schema_version: 1, provider_id: "ashby", host: "jobs.ashbyhq.com", region: "global", board_slug: "ashbydemo" },
              catalog_source: "bundled",
              catalog_revision: "2026-09-08-v1",
              trackable: true,
              discovery_only: false,
              is_tracked: false,
              tracked_company_id: null,
            },
            {
              catalog_id: "company-wellfound-demo",
              company_name: "Wellfound Demo Inc",
              careers_url: "https://wellfound.com/jobs",
              provider_id: "wellfound",
              provider_label: "Wellfound",
              provider_config: null,
              catalog_source: "bundled",
              catalog_revision: "2026-09-08-v1",
              trackable: false,
              discovery_only: true,
              is_tracked: false,
              tracked_company_id: null,
            },
          ],
          page: { number: 1, size: 20, total_items: 2, total_pages: 1 },
          meta: {},
        }),
      });
    });

    await page.route("**/tracked-companies*", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          data: [
            {
              company_id: "comp-initial-1",
              company_name: "Initial Corp",
              careers_url: "https://careers.initial.com",
              provider_id: "greenhouse",
              provider_label: "Greenhouse",
              row_revision: 1,
              created_at: "2026-09-08T00:00:00Z",
              updated_at: "2026-09-08T00:00:00Z",
            },
          ],
        }),
      });
    });

    await page.route("**/scans*", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          data: [],
          page: 1,
          page_size: 20,
          total_items: 0,
          meta: { active_count: 0, archived_count: 0 },
        }),
      });
    });

    await page.goto("/app/#/scans");
    await expect(page.locator("h1:has-text('Scans')")).toBeVisible();

    const pageScrollWidth = await page.evaluate(() => document.documentElement.scrollWidth);
    const pageClientWidth = await page.evaluate(() => document.documentElement.clientWidth);
    expect(pageScrollWidth).toBeLessThanOrEqual(pageClientWidth);

    await page.click("button:has-text('New Scan')");
    await expect(page.locator("dialog[open] h2:has-text('New Scan')")).toBeVisible();

    await page.click("button:has-text('Manage')");
    await expect(page.locator("dialog[open] h2:has-text('Manage Tracked Companies')")).toBeVisible();

    const dialogScrollWidth = await page.evaluate(() => {
      const d = document.querySelector("dialog[open]");
      return d ? d.scrollWidth : 0;
    });
    const dialogClientWidth = await page.evaluate(() => {
      const d = document.querySelector("dialog[open]");
      return d ? d.clientWidth : 0;
    });
    expect(dialogScrollWidth).toBeLessThanOrEqual(dialogClientWidth);

    await page.click("button[role='tab']:has-text('Company Catalog')");

    const catalogInput = page.locator("input[placeholder*='Search catalog']");
    await catalogInput.fill("demo");

    const wellfoundRow = page.locator(".catalog-item-row[data-catalog-id='company-wellfound-demo']");
    await expect(wellfoundRow).toBeVisible();
    await expect(wellfoundRow.locator("text=Marketplace / Discovery only")).toBeVisible();
    const wellfoundTrackBtn = wellfoundRow.locator("button:has-text('Track')");
    await expect(wellfoundTrackBtn).toBeDisabled();

    const ashbyRow = page.locator(".catalog-item-row[data-catalog-id='company-ashby-demo']");
    await expect(ashbyRow).toBeVisible();
    await expect(ashbyRow.locator("text=ATS / Source: Ashby")).toBeVisible();
    const ashbyTrackBtn = ashbyRow.locator("button:has-text('Track')");
    await expect(ashbyTrackBtn).toBeEnabled();

    await ashbyTrackBtn.click();
    await expect(ashbyRow.locator("button:has-text('Tracked')")).toBeVisible();

    await page.click("button:has-text('Done')");
    await expect(page.locator("text=Ashby Demo Inc")).toBeVisible();
  });

  test("supports catalog discovery, tracking, disabled Wellfound state, and mobile layout at /admin/scans", async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });

    await page.route("**/company-catalog/actions/track", async (route) => {
      await route.fulfill({
        status: 201,
        contentType: "application/json",
        body: JSON.stringify({
          data: {
            company_id: "comp-ashby-demo",
            company_name: "Ashby Demo Inc",
            careers_url: "https://jobs.ashbyhq.com/ashbydemo",
            provider_id: "ashby",
            provider_label: "Ashby",
            catalog_id: "company-ashby-demo",
            catalog_source: "bundled",
            catalog_revision: "2026-09-08-v1",
            row_revision: 1,
            created_at: "2026-09-08T12:00:00Z",
            updated_at: "2026-09-08T12:00:00Z",
          },
        }),
      });
    });

    await page.route("**/company-catalog*", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          data: [
            {
              catalog_id: "company-ashby-demo",
              company_name: "Ashby Demo Inc",
              careers_url: "https://jobs.ashbyhq.com/ashbydemo",
              provider_id: "ashby",
              provider_label: "Ashby",
              provider_config: { schema_version: 1, provider_id: "ashby", host: "jobs.ashbyhq.com", region: "global", board_slug: "ashbydemo" },
              catalog_source: "bundled",
              catalog_revision: "2026-09-08-v1",
              trackable: true,
              discovery_only: false,
              is_tracked: false,
              tracked_company_id: null,
            },
            {
              catalog_id: "company-wellfound-demo",
              company_name: "Wellfound Demo Inc",
              careers_url: "https://wellfound.com/jobs",
              provider_id: "wellfound",
              provider_label: "Wellfound",
              provider_config: null,
              catalog_source: "bundled",
              catalog_revision: "2026-09-08-v1",
              trackable: false,
              discovery_only: true,
              is_tracked: false,
              tracked_company_id: null,
            },
          ],
          page: { number: 1, size: 20, total_items: 2, total_pages: 1 },
          meta: {},
        }),
      });
    });

    await page.route("**/tracked-companies*", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          data: [
            {
              company_id: "comp-initial-1",
              company_name: "Initial Corp",
              careers_url: "https://careers.initial.com",
              provider_id: "greenhouse",
              provider_label: "Greenhouse",
              row_revision: 1,
              created_at: "2026-09-08T00:00:00Z",
              updated_at: "2026-09-08T00:00:00Z",
            },
          ],
        }),
      });
    });

    await page.goto("/admin/scans");

    const pageScrollWidth = await page.evaluate(() => document.documentElement.scrollWidth);
    const pageClientWidth = await page.evaluate(() => document.documentElement.clientWidth);
    expect(pageScrollWidth).toBeLessThanOrEqual(pageClientWidth);

    await page.click("#open-new-scan");
    await expect(page.locator("#new-scan-dialog[open]")).toBeVisible();

    await page.click("#manage-scan-companies");
    await expect(page.locator("#company-picker-dialog[open]")).toBeVisible();

    const dialogScrollWidth = await page.evaluate(() => {
      const d = document.getElementById("company-picker-dialog");
      return d ? d.scrollWidth : 0;
    });
    const dialogClientWidth = await page.evaluate(() => {
      const d = document.getElementById("company-picker-dialog");
      return d ? d.clientWidth : 0;
    });
    expect(dialogScrollWidth).toBeLessThanOrEqual(dialogClientWidth);

    await page.click("#company-picker-catalog-tab");
    await page.fill("#company-catalog-search", "demo");

    await expect(page.locator("#company-catalog-list :text('Wellfound Demo Inc')")).toBeVisible();
    await expect(page.locator("#company-catalog-list :text('Marketplace / Discovery only')")).toBeVisible();
    const wellfoundTrack = page.locator("#company-catalog-list .managed-selection-item:has-text('Wellfound Demo Inc') button:has-text('Track')");
    await expect(wellfoundTrack).toBeDisabled();

    const ashbyItem = page.locator("#company-catalog-list .managed-selection-item:has-text('Ashby Demo Inc')");
    await expect(ashbyItem).toBeVisible();
    await expect(ashbyItem.locator(":text('ATS / Source: Ashby')")).toBeVisible();
    const ashbyTrack = ashbyItem.locator("button:has-text('Track')");
    await expect(ashbyTrack).toBeEnabled();

    await ashbyTrack.click();
    await expect(ashbyItem.locator("button:has-text('Tracked')")).toBeVisible();

    await page.click("#apply-company-selection");
    await expect(page.locator("#selected-company-preview")).toContainText("Ashby Demo Inc");
  });
});
