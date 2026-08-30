import { test, expect } from "@playwright/test";

test.describe("CV Review Feature Journey", () => {
  test("navigates to CV Review route and displays header and controls", async ({ page }) => {
    await page.goto("/app/#/cv-review");

    // Verify heading
    await expect(page.locator("h2:has-text('CV Review & Artifacts')")).toBeVisible();
    await expect(page.locator("text=Grounded CV Generation & Review")).toBeVisible();

    // Select run & job controls
    await expect(page.locator("label:has-text('Select Run')")).toBeVisible();
    await expect(page.locator("label:has-text('Select Job')")).toBeVisible();
    await expect(page.locator("button:has-text('Refresh History')")).toBeVisible();
  });

  test("renders version history, safe markdown preview, download, and review state", async ({ page }) => {
    // Mock runs API
    await page.route("**/runs?**", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          data: [
            {
              run_id: "run-mock-1",
              run_name: "Frontend Engineer Scan Run",
              status: "succeeded",
              counts: { total: 1, passed: 1, cvs_generated: 2 },
            },
          ],
          total_items: 1,
        }),
      });
    });

    // Mock run jobs API
    await page.route("**/runs/run-mock-1/jobs?**", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          data: [
            {
              run_job_id: "job-mock-1",
              job_id: "job-1",
              title: "Senior Full Stack Engineer",
              company: "Tech Corp",
              current_stage_id: "cv-generation",
              cv_versions_count: 2,
            },
          ],
          total_items: 1,
        }),
      });
    });

    // Mock CV versions history API
    await page.route("**/runs/run-mock-1/jobs/job-mock-1/cvs", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          data: [
            {
              version_id: "cv-ver-2",
              run_id: "run-mock-1",
              run_job_id: "job-mock-1",
              job_url: "https://techcorp.example/jobs/1",
              ordinal: 2,
              generation_status: "generated",
              content_checksum: "a1b2c3d4e5f67890123456789abcdef0123456789abcdef0123456789abcdef0",
              content_length: 154,
              media_type: "text/markdown; charset=utf-8",
              filename: "cv-tailored-v2.md",
              parent_cv_version_id: "cv-ver-1",
              created_at: "2026-08-30T11:00:00Z",
              review_state: "approved",
              evaluation: {
                cv_evaluation_id: "eval-2",
                fit_classification: "strong",
                recommendation: "Strong match on full-stack TypeScript and Python.",
                strengths: ["10+ years TypeScript", "FastAPI and React expertise"],
                weaknesses: [],
              },
              capabilities: { download: true, preview: true, regenerate: true },
            },
            {
              version_id: "cv-ver-1",
              run_id: "run-mock-1",
              run_job_id: "job-mock-1",
              job_url: "https://techcorp.example/jobs/1",
              ordinal: 1,
              generation_status: "generated",
              content_checksum: "f1e2d3c4b5a67890123456789abcdef0123456789abcdef0123456789abcdef0",
              content_length: 120,
              media_type: "text/markdown; charset=utf-8",
              filename: "cv-tailored-v1.md",
              parent_cv_version_id: null,
              created_at: "2026-08-30T10:00:00Z",
              review_state: "none",
              capabilities: { download: true, preview: true, regenerate: true },
            },
          ],
        }),
      });
    });

    // Mock CV preview API
    const sampleCvMarkdown = `# Jane Developer
**Senior Full Stack Engineer**

## Summary
Experienced engineer specializing in React, TypeScript, and Python.

## Experience
- **Tech Lead** at Acme (2022 - Present)
`;

    await page.route("**/cv-versions/cv-ver-2/preview", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "text/markdown; charset=utf-8",
        headers: {
          "content-type": "text/markdown; charset=utf-8",
          "etag": '"a1b2c3d4e5f67890123456789abcdef0123456789abcdef0123456789abcdef0"',
          "content-length": String(sampleCvMarkdown.length),
          "x-cv-version-id": "cv-ver-2",
          "content-disposition": "inline",
        },
        body: sampleCvMarkdown,
      });
    });

    await page.goto("/app/#/cv-review?run_id=run-mock-1&job_id=job-mock-1");

    // Check version items in left history pane
    await expect(page.locator("button.cv-version-item:has-text('v2 · cv-ver-2')")).toBeVisible();
    await expect(page.locator("button.cv-version-item:has-text('v1 · cv-ver-1')")).toBeVisible();

    // Check safe rendered preview in main container
    await expect(page.locator(".safe-cv-renderer h1:has-text('Jane Developer')")).toBeVisible();
    await expect(page.locator(".safe-cv-renderer h2:has-text('Summary')")).toBeVisible();
    await expect(page.locator(".safe-cv-renderer strong:has-text('Senior Full Stack Engineer')")).toBeVisible();

    // Check separate evaluation & review state card
    await expect(page.locator(".cv-evaluation-card h3:has-text('Evaluation & Review Truth')")).toBeVisible();
    await expect(page.locator(".cv-evaluation-card:has-text('Fit: strong')")).toBeVisible();
    await expect(page.locator(".cv-evaluation-card:has-text('Review: approved')")).toBeVisible();
    await expect(page.locator(".cv-evaluation-card:has-text('10+ years TypeScript')")).toBeVisible();

    // Check toolbar buttons
    await expect(page.locator("button:has-text('Raw Text')")).toBeVisible();
    await expect(page.locator("button:has-text('Copy')")).toBeVisible();
    await expect(page.locator("button:has-text('Download CV')")).toBeVisible();
    await expect(page.locator("button:has-text('Regenerate CV')")).toBeVisible();

    // Toggle to raw text view
    await page.click("button:has-text('Raw Text')");
    await expect(page.locator("pre.cv-plain-text")).toContainText("# Jane Developer");
    await page.click("button:has-text('Formatted View')");
    await expect(page.locator(".safe-cv-renderer h1")).toBeVisible();

    // Test Regenerate Dialog open and close
    await page.click("button:has-text('Regenerate CV')");
    await expect(page.locator("dialog.native-dialog")).toBeVisible();
    await expect(page.locator(".dialog-title")).toHaveText("Regenerate Grounded CV");
    await page.click("dialog.native-dialog button:has-text('Cancel')");
    await expect(page.locator("dialog.native-dialog")).not.toBeVisible();
  });

  test("handles retryable pending state and error handling", async ({ page }) => {
    await page.route("**/runs?**", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          data: [{ run_id: "run-pending", run_name: "Pending Run", counts: { cvs_generated: 1 } }],
        }),
      });
    });

    await page.route("**/runs/run-pending/jobs?**", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          data: [{ run_job_id: "job-pending-1", title: "Pending Job", cv_versions_count: 1 }],
        }),
      });
    });

    await page.route("**/runs/run-pending/jobs/job-pending-1/cvs", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          data: [
            {
              version_id: "cv-ver-pending",
              run_id: "run-pending",
              run_job_id: "job-pending-1",
              ordinal: 1,
              generation_status: "pending",
              created_at: "2026-08-30T10:00:00Z",
              review_state: "none",
              capabilities: { download: false, preview: false, regenerate: true },
            },
          ],
        }),
      });
    });

    await page.route("**/cv-versions/cv-ver-pending/preview", async (route) => {
      await route.fulfill({
        status: 409,
        contentType: "application/json",
        body: JSON.stringify({
          error: {
            code: "artifact_not_available",
            message: "CV preview is not available for this version.",
            retryable: true,
            action: "Wait for generation and retry.",
          },
        }),
      });
    });

    await page.goto("/app/#/cv-review?run_id=run-pending&job_id=job-pending-1");

    // Check error state with retry guidance
    await expect(page.locator(".error-state")).toBeVisible();
    await expect(page.locator(".error-state h3")).toHaveText("CV Generation Pending");
    await expect(page.locator(".error-state button:has-text('Retry Preview')")).toBeVisible();
  });
});
