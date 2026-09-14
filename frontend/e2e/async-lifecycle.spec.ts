import { test, expect } from "@playwright/test";

const runId = "run-async-proof";

function runResource(backend_status: string) {
  const terminal = ["succeeded", "failed", "cancelled"].includes(backend_status);
  return {
    run_id: runId,
    run_name: "Async Lifecycle Proof",
    backend_status,
    display_status: backend_status === "succeeded" ? "Succeeded" : "Running",
    created_at: "2026-09-14T09:00:00Z",
    finished_at: terminal ? "2026-09-14T09:02:00Z" : null,
    counts: { total: 1, passed: terminal ? 1 : 0, rejected: 0, skipped: 0, cvs_generated: 0 },
    progress: { completed: terminal ? 1 : 0, total: 1 },
    capabilities: {
      inspect: true,
      cancel: !terminal,
      archive: terminal,
      unarchive: false,
      delete: false,
      export: true,
    },
  };
}

function jobsPage(title: string) {
  return {
    data: [
      {
        run_job_id: `${runId}-job`,
        job_id: `${runId}-job`,
        title,
        company: "Async Corp",
        current_stage_id: "ranking",
        status: "evaluated",
        result_bucket: "passed",
        rating: 1,
        interest_rating: 1,
        bookmarked: false,
        decision: "passed",
        reason_code: null,
        capabilities: { bookmark: true, regenerate_cv: false },
      },
    ],
    page: { number: 1, size: 10, total_items: 1, total_pages: 1 },
    meta: { total_evaluated: 1, passed: 1, rejected: 0, skipped: 0 },
  };
}

function eventsPage(events: unknown[], next_cursor: string | null) {
  return {
    data: events,
    meta: { next_cursor, total_count: events.length, integrity_conflicts: 0 },
  };
}

function scanResource(scanId: string, execution_status = "running") {
  const terminal = ["succeeded", "failed", "cancelled"].includes(execution_status);
  return {
    scan_id: scanId,
    scan_name: `Scan ${scanId}`,
    execution_status,
    lifecycle: "active",
    row_revision: 1,
    created_at: "2026-09-14T09:00:00Z",
    finished_at: terminal ? "2026-09-14T09:02:00Z" : null,
    company_count: 1,
    output_record_count: terminal ? 0 : null,
    capabilities: {
      inspect: true,
      cancel: !terminal,
      run_again: terminal,
      download: terminal,
      archive: terminal,
      unarchive: false,
      delete: false,
      use_for_run: true,
    },
    warnings: [],
  };
}

function scansPage(scanId: string) {
  return {
    data: [scanResource(scanId, "succeeded")],
    page: { number: Number(scanId.slice(-1)), size: 20, total_items: 2, total_pages: 2 },
    meta: { active_count: 2, archived_count: 0 },
  };
}

function scanEventsPage(events: unknown[], next_cursor: string | null) {
  return {
    data: { events, next_cursor, total_count: events.length },
  };
}

function runsPage(name: string) {
  return {
    data: [{
      run_id: `run-${name.toLowerCase().replace(/\s+/g, "-")}`,
      run_name: name,
      backend_status: "succeeded",
      display_status: "Succeeded",
      created_at: "2026-09-14T09:00:00Z",
      finished_at: "2026-09-14T09:02:00Z",
      counts: { total: 1, passed: 1, rejected: 0, skipped: 0, cvs_generated: 0 },
      progress: { completed: 1, total: 1 },
      capabilities: { inspect: true, cancel: false, archive: true, unarchive: false, delete: false, export: true },
    }],
    page: { number: 1, size: 20, total_items: 1, total_pages: 1 },
    meta: { active_count: 0, archived_count: 1 },
  };
}

function candidateProfilesPage(items: unknown[], view: string) {
  return {
    data: items,
    page: { number: 1, size: 20, total_items: items.length, total_pages: 1 },
    meta: { active_count: view === "active" ? items.length : 0, archived_count: view === "archived" ? items.length : 0 },
  };
}

function candidateProfile(profileId: string, displayName: string, lifecycle = "active") {
  return {
    profile_id: profileId,
    profile_name: displayName,
    display_name: displayName,
    lifecycle,
    revision: 1,
    canonical: {},
    capabilities: { archive: lifecycle === "active", delete: lifecycle === "archived" },
    creation: null,
  };
}

function synonymPolicy(type: string, editorText: string, draftRevision: number) {
  return {
    data: {
      synonym_type: type,
      editor_text: editorText,
      normalized_policy: {},
      issues: [],
      validation_status: "valid",
      draft_revision: draftRevision,
      active_type_revision_id: `${type}-active`,
      active_type_revision: draftRevision,
      active_bundle_revision_id: "bundle-1",
      active_bundle_revision: 1,
      mirror_status: "in_sync",
      mirror_error_code: null,
    },
  };
}

function pipelineSettings(revision: string, vectorSearchTopN: number) {
  return {
    data: {
      values: {
        "pipeline.vector_search_top_n": vectorSearchTopN,
        "pipeline.ai_score_top_n": 50,
        "pipeline.final_top_n": 15,
        "pipeline.evidence_top_k": 5,
        "global_job_filters.applications_count_max": 200,
        "global_job_filters.max_age_days": 30,
      },
      defaults: {},
      revision,
    },
  };
}

test.describe("Run Detail async lifecycle", () => {
  test("renders terminal status before final refresh settles and retries only unfinished operations", async ({ page }) => {
    let runReads = 0;
    let terminalAccepted = false;
    let finalJobsReads = 0;
    let finalEventReads = 0;
    let resolveFinalJobsStarted: (() => void) | null = null;
    const finalJobsStarted = new Promise<void>((resolve) => {
      resolveFinalJobsStarted = resolve;
    });

    await page.route(`**/runs/${runId}`, async (route) => {
      runReads += 1;
      const resource = runResource(runReads <= 2 ? "running" : "succeeded");
      terminalAccepted = resource.backend_status === "succeeded";
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ data: resource }),
      });
    });

    await page.route(`**/runs/${runId}/jobs**`, async (route) => {
      if (!terminalAccepted) {
        await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(jobsPage("Initial Job")) });
        return;
      }
      finalJobsReads += 1;
      if (finalJobsReads === 1) {
        resolveFinalJobsStarted?.();
        await new Promise((resolve) => setTimeout(resolve, 700));
        await route.fulfill({ status: 503, contentType: "application/json", body: JSON.stringify({ detail: "jobs still settling" }) });
        return;
      }
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(jobsPage("Terminal Job")) });
    });

    await page.route(`**/runs/${runId}/events**`, async (route) => {
      const requestUrl = new URL(route.request().url());
      if (!requestUrl.searchParams.has("cursor")) {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify(eventsPage([], "final-cursor")),
        });
        return;
      }
      finalEventReads += 1;
      if (finalEventReads === 1) {
        await route.fulfill({ status: 503, contentType: "application/json", body: JSON.stringify({ detail: "events still settling" }) });
        return;
      }
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(eventsPage([{
          event_id: "terminal-event",
          time: "2026-09-14T09:02:00Z",
          stage_id: "ranking",
          level: "info",
          operation: "run",
          state: "succeeded",
          message: "Terminal event arrived",
        }], null)),
      });
    });

    await page.goto(`/app/#/runs?run_id=${runId}`);
    await finalJobsStarted;
    await expect(page.locator(".drawer-status")).toContainText("Succeeded", { timeout: 500 });
    await expect(page.getByText("Terminal Job", { exact: true })).toBeVisible();
    await expect(page.locator(".notice.error")).toHaveCount(0, { timeout: 5000 });
    expect(finalJobsReads).toBe(2);
    expect(finalEventReads).toBe(2);

    await expect(page.getByText("Terminal Job", { exact: true })).toBeVisible();
    await page.getByText("Console Log", { exact: true }).click();
    await expect(page.getByText("Terminal event arrived", { exact: true })).toBeVisible();
  });

  test("rereads retained final event cursor without replaying initial page", async ({ page }) => {
    let initialEventReads = 0;
    let cursorReads = 0;
    let resolveCursorRead: (() => void) | null = null;
    const cursorRead = new Promise<void>((resolve) => {
      resolveCursorRead = resolve;
    });

    await page.route(`**/runs/${runId}`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ data: runResource("running") }),
      });
    });
    await page.route(`**/runs/${runId}/jobs**`, async (route) => {
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(jobsPage("Live Job")) });
    });
    await page.route(`**/runs/${runId}/events**`, async (route) => {
      const requestUrl = new URL(route.request().url());
      if (!requestUrl.searchParams.has("cursor")) {
        initialEventReads += 1;
        await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(eventsPage([], "retained-cursor")) });
        return;
      }
      cursorReads += 1;
      resolveCursorRead?.();
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(eventsPage([{
          event_id: "late-event",
          time: "2026-09-14T09:01:00Z",
          stage_id: "ranking",
          level: "info",
          operation: "run",
          state: "progress",
          message: "Late event discovered from retained cursor",
        }], null)),
      });
    });

    await page.goto(`/app/#/runs?run_id=${runId}`);
    await cursorRead;
    await expect(page.getByText("Console Log", { exact: true })).toBeVisible();
    await page.getByText("Console Log", { exact: true }).click();
    await expect(page.getByText("Late event discovered from retained cursor", { exact: true })).toBeVisible();
    expect(initialEventReads).toBeGreaterThan(0);
    expect(cursorReads).toBeGreaterThan(0);
  });
});

test.describe("Runs list async lifecycle", () => {
  test("rejects late response from prior query", async ({ page }) => {
    let releaseInitial: () => void = () => {};
    const initialHeld = new Promise<void>((resolve) => {
      releaseInitial = resolve;
    });

    await page.route("**/runs**", async (route) => {
      const requestUrl = new URL(route.request().url());
      const search = requestUrl.searchParams.get("search") || "";
      if (!search) {
        await initialHeld;
        await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(runsPage("Old Query Run")) });
        return;
      }
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(runsPage("New Query Run")) });
    });

    await page.goto("/app/#/runs");
    const searchInput = page.getByPlaceholder("Search runs by ID, name, input...");
    await searchInput.fill("new");
    await page.getByRole("button", { name: "Search" }).click();
    await expect(page.getByText("New Query Run")).toBeVisible();

    releaseInitial?.();
    await expect(page.getByText("Old Query Run")).toHaveCount(0);
  });
});

test.describe("Scan async lifecycle", () => {
  test("rejects stale list page responses after URL page changes", async ({ page }) => {
    let releasePageOne = () => {};
    const pageOneReleased = new Promise<void>((resolve) => {
      releasePageOne = resolve;
    });

    await page.route("**/scans?**", async (route) => {
      const requestUrl = new URL(route.request().url());
      if (requestUrl.searchParams.get("page") === "1") {
        await pageOneReleased;
      }
      const scanId = requestUrl.searchParams.get("page") === "2" ? "scan-2" : "scan-1";
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(scansPage(scanId)),
      });
    });

    await page.goto("/app/#/scans?page=1");
    await page.waitForTimeout(100);
    await page.evaluate(() => {
      window.location.hash = "#/scans?page=2";
    });
    await expect(page.getByText("Scan scan-2", { exact: true })).toBeVisible();
    releasePageOne();
    await page.waitForTimeout(100);
    await expect(page.getByText("Scan scan-2", { exact: true })).toBeVisible();
    await expect(page.getByText("Scan scan-1", { exact: true })).toHaveCount(0);
  });

  test("retains final event cursor and does not poll after detail disposal", async ({ page }) => {
    const scanId = "scan-async";
    let detailReads = 0;
    let cursorReads = 0;
    let resolveCursorRead: (() => void) | null = null;
    const cursorRead = new Promise<void>((resolve) => {
      resolveCursorRead = resolve;
    });

    await page.route(`**/scans/${scanId}`, async (route) => {
      detailReads += 1;
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ data: scanResource(scanId) }),
      });
    });
    await page.route(`**/scans/${scanId}/events**`, async (route) => {
      const requestUrl = new URL(route.request().url());
      if (!requestUrl.searchParams.has("cursor")) {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify(scanEventsPage([], "scan-final-cursor")),
        });
        return;
      }
      cursorReads += 1;
      resolveCursorRead?.();
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(scanEventsPage([{
          event_id: "scan-late-event",
          process_type: "scan",
          process_id: scanId,
          operation: "acquire",
          state: "progress",
          level: "info",
          message: "Late scan event",
          recorded_at: "2026-09-14T09:01:00Z",
        }], null)),
      });
    });

    await page.goto(`/app/#/scans?scan_id=${scanId}`);
    await cursorRead;
    await expect(page.getByText("Late scan event", { exact: true })).toBeVisible();
    expect(cursorReads).toBeGreaterThan(0);

    await page.getByText("← Back to Scans", { exact: true }).click();
    const readsAfterBack = detailReads;
    await page.waitForTimeout(3200);
    expect(detailReads).toBe(readsAfterBack);
  });
});

test.describe("Candidate Profile async lifecycle", () => {
  test("rejects a late processing response after switching attempt", async ({ page }) => {
    let releaseFirst: () => void = () => {};
    const firstHeld = new Promise<void>((resolve) => { releaseFirst = resolve; });
    let firstStarted: () => void = () => {};
    const firstRequestStarted = new Promise<void>((resolve) => { firstStarted = resolve; });

    await page.route("**/candidate-profile-creation-attempts/**", async (route) => {
      const attemptId = new URL(route.request().url()).pathname.split("/").pop();
      if (attemptId === "attempt-a") {
        firstStarted();
        await firstHeld;
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            data: {
              attempt_id: "attempt-a",
              profile_name: "Attempt A",
              creation_status: "failed",
              revision: 1,
              next_action: "none",
              failure: { message: "Attempt A failed" },
              capabilities: { retry: true, cancel: false, discard: true },
            },
          }),
        });
        return;
      }

      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          data: {
            attempt_id: "attempt-b",
            profile_name: "Attempt B",
            creation_status: "extracting_base",
            revision: 1,
            next_action: "wait",
            poll_after_ms: 60_000,
            capabilities: { retry: true, cancel: true, discard: true },
          },
        }),
      });
    });

    await page.goto("/app/#/candidate-profile/create/attempt-a");
    await firstRequestStarted;
    await page.evaluate(() => { window.location.hash = "#/candidate-profile/create/attempt-b"; });
    await expect(page.getByText("Extracting baseline document structure and locators...", { exact: true })).toBeVisible();
    releaseFirst();
    await page.waitForTimeout(150);
    await expect(page.getByText("Attempt A failed", { exact: true })).toHaveCount(0);
  });

  test("rejects a late source-block response after switching attempt", async ({ page }) => {
    let releaseFirst: () => void = () => {};
    const firstHeld = new Promise<void>((resolve) => { releaseFirst = resolve; });
    let firstStarted: () => void = () => {};
    const firstRequestStarted = new Promise<void>((resolve) => { firstStarted = resolve; });

    await page.route("**/candidate-profile-field-schema", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          data: {
            schema_version: "1",
            schema_revision: 1,
            checksum: "schema",
            date_grammar: { format: "YYYY-MM", present_value: "present", optional: true },
            evidence_kinds: [],
            sections: [{
              id: "identity",
              stage: "baseline",
              shape: "object",
              label: "Identity",
              fields: { name: { shape: "text", label: "Name" } },
            }],
          },
        }),
      });
    });

    await page.route("**/candidate-profile-creation-attempts/**", async (route) => {
      const pathname = new URL(route.request().url()).pathname;
      if (pathname.includes("/source-blocks/")) {
        if (pathname.includes("/attempt-a/")) {
          firstStarted();
          await firstHeld;
          await route.fulfill({
            status: 200,
            contentType: "application/json",
            body: JSON.stringify({ data: { source_block_id: "block-a", text: "Source A", locator: { kind: "markdown_lines", start: 1, end: 1 } } }),
          });
          return;
        }
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({ data: { source_block_id: "block-a", text: "Source B", locator: { kind: "markdown_lines", start: 2, end: 2 } } }),
        });
        return;
      }

      if (pathname.endsWith("/baseline")) {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            data: {
              attempt_id: pathname.includes("attempt-b") ? "attempt-b" : "attempt-a",
              stage: "baseline",
              revision: 1,
              fingerprint: "fingerprint",
              document: { name: "Candidate" },
              annotations: { "/name": { source_block_ids: ["block-a"] } },
              validation: { valid: true, errors: [] },
              capabilities: { patch: true, approve: true },
            },
          }),
        });
        return;
      }

      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ data: {
          attempt_id: pathname.includes("attempt-b") ? "attempt-b" : "attempt-a",
          profile_name: "Candidate",
          creation_status: "base_review",
          revision: 1,
          next_action: "review_baseline",
          capabilities: { retry: true, cancel: true, discard: true },
        } }),
      });
    });

    await page.goto("/app/#/candidate-profile/create/attempt-a/baseline");
    await page.getByRole("button", { name: "Source", exact: true }).click();
    await firstRequestStarted;
    await page.evaluate(() => { window.location.hash = "#/candidate-profile/create/attempt-b/baseline"; });
    await expect(page.getByText("Source B", { exact: true })).toBeVisible();
    releaseFirst();
    await expect(page.getByText("Source A", { exact: true })).toHaveCount(0);
  });

  test("rejects a late baseline response after switching attempt", async ({ page }) => {
    let releaseFirst: () => void = () => {};
    const firstHeld = new Promise<void>((resolve) => { releaseFirst = resolve; });
    let firstStarted: () => void = () => {};
    const firstRequestStarted = new Promise<void>((resolve) => { firstStarted = resolve; });

    await page.route("**/candidate-profile-field-schema", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ data: {
          schema_version: "1",
          schema_revision: 1,
          checksum: "schema",
          date_grammar: { format: "YYYY-MM", present_value: "present", optional: true },
          evidence_kinds: [],
          sections: [{ id: "identity", stage: "baseline", shape: "object", label: "Identity", fields: { name: { shape: "text", label: "Name" } } }],
        } }),
      });
    });

    await page.route("**/candidate-profile-creation-attempts/**", async (route) => {
      const pathname = new URL(route.request().url()).pathname;
      const attemptId = pathname.includes("attempt-b") ? "attempt-b" : "attempt-a";
      if (pathname.endsWith("/baseline")) {
        if (attemptId === "attempt-a") {
          firstStarted();
          await firstHeld;
        }
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({ data: {
            attempt_id: attemptId,
            stage: "baseline",
            revision: 1,
            fingerprint: "fingerprint",
            document: { name: attemptId === "attempt-a" ? "Name A" : "Name B" },
            annotations: {},
            validation: { valid: true, errors: [] },
            capabilities: { patch: true, approve: true },
          } }),
        });
        return;
      }

      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ data: {
          attempt_id: attemptId,
          profile_name: "Candidate",
          creation_status: "base_review",
          revision: 1,
          next_action: "review_baseline",
          capabilities: { retry: true, cancel: true, discard: true },
        } }),
      });
    });

    await page.goto("/app/#/candidate-profile/create/attempt-a/baseline");
    await firstRequestStarted;
    await page.evaluate(() => { window.location.hash = "#/candidate-profile/create/attempt-b/baseline"; });
    const nameInput = page.getByLabel("Name");
    await expect(nameInput).toHaveValue("Name B");
    releaseFirst();
    await expect(nameInput).toHaveValue("Name B");
  });

  test("keeps catalog attempts independent from delayed profile tab responses", async ({ page }) => {
    let releaseActive: () => void = () => {};
    const activeHeld = new Promise<void>((resolve) => {
      releaseActive = resolve;
    });
    let attemptReads = 0;

    await page.route("**/candidate-profile-creation-attempts**", async (route) => {
      attemptReads += 1;
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ data: [] }) });
    });
    await page.route("**/candidate-profiles**", async (route) => {
      const requestUrl = new URL(route.request().url());
      if (requestUrl.pathname.endsWith("/candidate-profiles")) {
        const view = requestUrl.searchParams.get("view") || "active";
        if (view === "active") await activeHeld;
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify(candidateProfilesPage([candidateProfile(`profile-${view}`, `${view} profile`)], view)),
        });
      }
    });

    await page.goto("/app/#/candidate-profile");
    await page.waitForTimeout(100);
    await page.evaluate(() => { window.location.hash = "#/candidate-profile"; });
    await page.getByRole("tab", { name: "Archived" }).click();
    await expect(page.getByText("archived profile", { exact: true })).toBeVisible();
    await expect(page.getByText("No creation drafts.", { exact: false })).toBeVisible();
    releaseActive();
    await expect(page.getByText("archived profile", { exact: true })).toBeVisible();
    await expect(page.getByText("active profile", { exact: true })).toHaveCount(0);
    expect(attemptReads).toBe(1);
  });

  test("rejects late detail response after rapid profile switch", async ({ page }) => {
    let releaseFirst: () => void = () => {};
    const firstHeld = new Promise<void>((resolve) => { releaseFirst = resolve; });
    let resolveFirstStarted: (() => void) = () => {};
    const firstStarted = new Promise<void>((resolve) => { resolveFirstStarted = resolve; });
    await page.route("**/candidate-profiles/*", async (route) => {
      const profileId = new URL(route.request().url()).pathname.split("/").pop();
      if (profileId === "profile-a") {
        resolveFirstStarted();
        await firstHeld;
      }
      const profile = profileId === "profile-b" ? candidateProfile("profile-b", "Profile B") : candidateProfile("profile-a", "Profile A");
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ data: profile }) });
    });

    await page.goto("/app/#/candidate-profile/profile-a");
    await firstStarted;
    await page.evaluate(() => { window.location.hash = "#/candidate-profile/profile-b"; });
    await expect(page.getByRole("heading", { name: "Profile B" })).toBeVisible();
    releaseFirst();
    await expect(page.getByRole("heading", { name: "Profile A" })).toHaveCount(0);
  });
});

test.describe("Pipeline settings and synonym draft lifecycle", () => {
  test("retains dirty settings through late refresh, exposes conflict, and preserves save conflict draft", async ({ page }) => {
    let getCount = 0;
    let releaseRefresh: () => void = () => {};
    const refreshHeld = new Promise<void>((resolve) => { releaseRefresh = resolve; });

    await page.route("**/settings/pipeline", async (route) => {
      if (route.request().method() === "PATCH") {
        await route.fulfill({
          status: 409,
          contentType: "application/json",
          body: JSON.stringify({ error: { code: "settings_revision_conflict", message: "Remote settings changed" } }),
        });
        return;
      }
      getCount += 1;
      if (getCount === 2) await refreshHeld;
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(pipelineSettings(getCount === 1 ? "rev-1" : "rev-2", getCount === 1 ? 50 : 60)) });
    });

    await page.goto("/app/#/settings/pipeline");
    const input = page.getByLabel("Initial Candidate Pool Size");
    await expect(input).toHaveValue("50");
    await input.fill("75");
    await page.getByRole("button", { name: "Cancel" }).click();
    await page.getByRole("button", { name: "Open Pipeline Settings" }).click();
    await expect(input).toHaveValue("75");
    releaseRefresh();
    await expect(page.getByText("Settings Conflict (409)")).toBeVisible();
    await expect(input).toHaveValue("75");
    await page.getByRole("button", { name: "Save" }).click();
    await expect(page.getByText("Remote settings changed")).toBeVisible();
    await expect(input).toHaveValue("75");
  });

  test("keeps synonym drafts bound to policy type during dirty switching", async ({ page }) => {
    await page.route("**/synonym-suggestions**", async (route) => {
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ data: [] }) });
    });
    await page.route("**/synonym-processing-runs**", async (route) => {
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ data: [] }) });
    });
    await page.route("**/synonym-policies/*", async (route) => {
      const type = new URL(route.request().url()).pathname.split("/").pop() || "skills";
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(synonymPolicy(type, `${type}: canonical`, 1)) });
    });

    await page.goto("/app/#/synonyms");
    await page.getByRole("tab", { name: "Policy Editors" }).click();
    const textarea = page.getByLabel("Policy Definitions (Format: alias: canonical)");
    await expect(textarea).toHaveValue("skills: canonical");
    await textarea.fill("skills: local draft");
    await page.getByRole("button", { name: "Domain Synonyms" }).click();
    await expect(textarea).toHaveValue("domain: canonical");
    await textarea.fill("domain: local draft");
    await page.getByRole("button", { name: "Skill Synonyms" }).click();
    await expect(textarea).toHaveValue("skills: local draft");
    await page.getByRole("button", { name: "Domain Synonyms" }).click();
    await expect(textarea).toHaveValue("domain: local draft");
  });
});
