import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import {
  RunsListPage,
  buildRunsQueryKey,
  RunsPollingCoordinator,
  isRunTerminal,
} from "../features/runs/runs-list";
import { PipelineRunResource, RunBackendStatus } from "../features/runs/types";

function createMockRun(runId: string, status: RunBackendStatus): PipelineRunResource {
  return {
    run_id: runId,
    run_name: "Run " + runId,
    backend_status: status,
    display_status: status,
    created_at: "2026-09-12T12:00:00Z",
    counts: { total: 10, passed: 5, rejected: 5, skipped: 0, cvs_generated: 2 },
    progress: { completed: 10, total: 10 },
    capabilities: {
      inspect: true,
      cancel: !isRunTerminal(status),
      archive: isRunTerminal(status),
      unarchive: false,
      delete: false,
      export: true,
    },
  };
}

describe("Runs List Polling and Query Identity", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  describe("buildRunsQueryKey", () => {
    it("builds canonical query identity string", () => {
      const key = buildRunsQueryKey("active", "python engineer", 2, 20);
      expect(key).toBe("active::python engineer::2::20");
    });

    it("trims whitespace from search parameter", () => {
      const key1 = buildRunsQueryKey("active", "  lead dev  ", 1, 20);
      const key2 = buildRunsQueryKey("active", "lead dev", 1, 20);
      expect(key1).toBe("active::lead dev::1::20");
      expect(key1).toBe(key2);
    });

    it("distinguishes queries across lifecycle views, pages, and filters", () => {
      const activeKey = buildRunsQueryKey("active", "", 1, 20);
      const archivedKey = buildRunsQueryKey("archived", "", 1, 20);
      const p2Key = buildRunsQueryKey("active", "", 2, 20);
      const searchKey = buildRunsQueryKey("active", "data", 1, 20);

      expect(activeKey).not.toBe(archivedKey);
      expect(activeKey).not.toBe(p2Key);
      expect(activeKey).not.toBe(searchKey);
    });
  });

  describe("RunsPollingCoordinator", () => {
    afterEach(() => {
      vi.useRealTimers();
    });

    it("enforces single in-flight request and skips overlapping timer ticks", async () => {
      const activeQuery = "active::::1::20";
      let fetchCallCount = 0;
      let resolveFirstFetch: ((val: boolean) => void) | null = null;
      const skippedReasons: string[] = [];

      const coordinator = new RunsPollingCoordinator({
        getQueryKey: () => activeQuery,
        hasActiveRuns: () => true,
        isDocumentVisible: () => true,
        fetchRuns: () => {
          fetchCallCount += 1;
          return new Promise<boolean>((resolve) => {
            resolveFirstFetch = resolve;
          });
        },
        onPollSkipped: (reason) => {
          skippedReasons.push(reason);
        },
      });

      // Start initial poll tick
      const firstTickPromise = coordinator.triggerTick();
      expect(coordinator.isInFlight).toBe(true);
      expect(fetchCallCount).toBe(1);

      // Concurrent second tick must be skipped while first is pending
      const secondTickPromise = coordinator.triggerTick();
      expect(await secondTickPromise).toBe(false);
      expect(fetchCallCount).toBe(1);
      expect(skippedReasons).toContain("in_flight");

      // Resolve first request
      resolveFirstFetch!(true);
      expect(await firstTickPromise).toBe(true);
      expect(coordinator.isInFlight).toBe(false);

      // Subsequent tick now proceeds
      const thirdTickPromise = coordinator.triggerTick();
      expect(fetchCallCount).toBe(2);
      resolveFirstFetch!(true);
      expect(await thirdTickPromise).toBe(true);

      coordinator.destroy();
    });

    it("supersedes obsolete responses when query identity changes during delayed response", async () => {
      let currentQueryKey = "active::::1::20";
      let resolveFirst: ((val: boolean) => void) | null = null;
      let resolveSecond: ((val: boolean) => void) | null = null;

      const coordinator = new RunsPollingCoordinator({
        getQueryKey: () => currentQueryKey,
        hasActiveRuns: () => true,
        isDocumentVisible: () => true,
        fetchRuns: ({ queryKey }) => {
          if (queryKey === "active::::1::20") {
            return new Promise<boolean>((res) => {
              resolveFirst = res;
            });
          }
          return new Promise<boolean>((res) => {
            resolveSecond = res;
          });
        },
      });

      // First query in flight
      const req1Promise = coordinator.load({ showLoading: true, isPolling: false });
      expect(coordinator.isInFlight).toBe(true);

      // Query changes (e.g. user changes search/page)
      currentQueryKey = "active::backend::1::20";
      const req2Promise = coordinator.load({ showLoading: true, isPolling: false });

      // First (delayed) response resolves late
      resolveFirst!(true);
      const req1Result = await req1Promise;
      expect(req1Result).toBe(false); // Obsolete response ignored!

      // Second response resolves
      resolveSecond!(true);
      const req2Result = await req2Promise;
      expect(req2Result).toBe(true); // Newer response accepted!

      coordinator.destroy();
    });

    it("pauses polling when tab is hidden and resumes on visibility restore", async () => {
      vi.useFakeTimers();
      let isVisible = true;
      let tickCount = 0;
      const skippedReasons: string[] = [];

      const coordinator = new RunsPollingCoordinator({
        getQueryKey: () => "active::::1::20",
        hasActiveRuns: () => true,
        isDocumentVisible: () => isVisible,
        fetchRuns: async () => {
          tickCount += 1;
          return true;
        },
        onPollSkipped: (reason) => {
          skippedReasons.push(reason);
        },
        cadenceMs: 1000,
      });

      coordinator.start();
      expect(coordinator.isPolling).toBe(true);

      // Advance 1s while visible -> tick runs
      await vi.advanceTimersByTimeAsync(1000);
      expect(tickCount).toBe(1);

      // Tab hidden
      isVisible = false;
      coordinator.sync();
      expect(coordinator.isPolling).toBe(false);

      // Advance 3s while hidden -> no new requests sent
      await vi.advanceTimersByTimeAsync(3000);
      expect(tickCount).toBe(1);

      // Tab becomes visible again -> resumes immediate request and restarts timer
      isVisible = true;
      coordinator.sync();
      await coordinator.triggerTick();
      expect(tickCount).toBe(2);

      await vi.advanceTimersByTimeAsync(1000);
      expect(tickCount).toBe(3);

      coordinator.destroy();
    });

    it("stops polling when all runs become terminal", async () => {
      const activeRun = createMockRun("run-active", "running");
      const doneRun = createMockRun("run-done", "succeeded");
      expect(isRunTerminal(activeRun.backend_status)).toBe(false);
      expect(isRunTerminal(doneRun.backend_status)).toBe(true);
      vi.useFakeTimers();
      let hasActive = true;
      let tickCount = 0;

      const coordinator = new RunsPollingCoordinator({
        getQueryKey: () => "active::::1::20",
        hasActiveRuns: () => hasActive,
        isDocumentVisible: () => true,
        fetchRuns: async () => {
          tickCount += 1;
          hasActive = false; // Run finished during this fetch
          return true;
        },
        cadenceMs: 1000,
      });

      coordinator.start();
      expect(coordinator.isPolling).toBe(true);

      await vi.advanceTimersByTimeAsync(1000);
      expect(tickCount).toBe(1);
      expect(coordinator.isPolling).toBe(false);

      // Subsequent time advances do not tick
      await vi.advanceTimersByTimeAsync(3000);
      expect(tickCount).toBe(1);

      coordinator.destroy();
    });

    it("cleans up timers and ignores responses on destroy", async () => {
      let resolveFetch: ((val: boolean) => void) | null = null;
      let fetchCalled = false;

      const coordinator = new RunsPollingCoordinator({
        getQueryKey: () => "active::::1::20",
        hasActiveRuns: () => true,
        isDocumentVisible: () => true,
        fetchRuns: () => {
          fetchCalled = true;
          return new Promise<boolean>((resolve) => {
            resolveFetch = resolve;
          });
        },
      });

      coordinator.start();
      const tickPromise = coordinator.triggerTick();
      expect(fetchCalled).toBe(true);

      // Destroy coordinator before fetch resolves
      coordinator.destroy();
      expect(coordinator.isPolling).toBe(false);

      // Resolve late fetch
      resolveFetch!(true);
      const result = await tickPromise;
      expect(result).toBe(false); // Ignored after destroy!

      // New ticks after destroy are rejected
      const nextTick = await coordinator.triggerTick();
      expect(nextTick).toBe(false);
    });
  });

  describe("RunsListPage Component Rendering", () => {
    it("renders page header, title, and New Run button", () => {
      const markup = renderToStaticMarkup(
        React.createElement(RunsListPage, {
          onSelectRun: () => {},
          view: "active",
          onViewChange: () => {},
          page: 1,
          onPageChange: () => {},
        })
      );

      expect(markup).toContain("Runs");
      expect(markup).toContain("Workspace");
      expect(markup).toContain("Trigger, monitor, cancel, and archive local runs.");
      expect(markup).toContain("New Run");
    });

    it("renders tabs for Active, Archived, and All Runs with search input", () => {
      const markup = renderToStaticMarkup(
        React.createElement(RunsListPage, {
          onSelectRun: () => {},
          view: "active",
          onViewChange: () => {},
          page: 1,
          onPageChange: () => {},
        })
      );

      expect(markup).toContain("Active");
      expect(markup).toContain("Archived");
      expect(markup).toContain("All Runs");
      expect(markup).toContain("Search runs by ID, name, input...");
    });
  });
});
