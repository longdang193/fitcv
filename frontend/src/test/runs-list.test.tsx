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
import runsListSource from "../features/runs/runs-list.tsx?raw";

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
      expect(key).toBe("active::python engineer::2::20::today");
      const rangeKey = buildRunsQueryKey("active", "python engineer", 2, 20, "7d");
      expect(rangeKey).toBe("active::python engineer::2::20::7d");
    });

    it("trims whitespace from search parameter", () => {
      const key1 = buildRunsQueryKey("active", "  lead dev  ", 1, 20);
      const key2 = buildRunsQueryKey("active", "lead dev", 1, 20);
      expect(key1).toBe("active::lead dev::1::20::today");
      expect(key1).toBe(key2);
    });

    it("distinguishes queries across lifecycle views, pages, and filters", () => {
      const activeKey = buildRunsQueryKey("active", "", 1, 20);
      const archivedKey = buildRunsQueryKey("archived", "", 1, 20);
      const p2Key = buildRunsQueryKey("active", "", 2, 20);
      const searchKey = buildRunsQueryKey("active", "data", 1, 20);
      const rangeKey = buildRunsQueryKey("active", "", 1, 20, "30d");

      expect(activeKey).not.toBe(archivedKey);
      expect(activeKey).not.toBe(p2Key);
      expect(activeKey).not.toBe(searchKey);
      expect(activeKey).not.toBe(rangeKey);
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

    it("accepts only newest response when same query requests resolve out of order", async () => {
      const queryKey = "active::::1::20";
      let resolveFirst: ((value: string) => void) | null = null;
      let resolveSecond: ((value: string) => void) | null = null;
      const committed: string[] = [];
      const settled: number[] = [];

      const coordinator = new RunsPollingCoordinator({
        getQueryKey: () => queryKey,
        hasActiveRuns: () => true,
        fetchRuns: ({ showLoading }) => showLoading
          ? new Promise<string>((resolve) => { resolveFirst = resolve; })
          : new Promise<string>((resolve) => { resolveSecond = resolve; }),
        onResponse: (value) => committed.push(value as string),
        onSettled: ({ requestId }) => settled.push(requestId),
      });

      const first = coordinator.load({ showLoading: true });
      const second = coordinator.load({ showLoading: false });
      resolveSecond!("new");
      expect(await second).toBe(true);
      resolveFirst!("old");
      expect(await first).toBe(false);
      expect(committed).toEqual(["new"]);
      expect(settled).toEqual([2]);
      coordinator.destroy();
    });

    it("creates a live coordinator after StrictMode setup-cleanup-setup replay", async () => {
      let fetchCount = 0;
      const createCoordinator = () => new RunsPollingCoordinator({
        getQueryKey: () => "active::::1::20",
        hasActiveRuns: () => true,
        isDocumentVisible: () => true,
        fetchRuns: async () => {
          fetchCount += 1;
          return {};
        },
      });

      const firstSetup = createCoordinator();
      firstSetup.start();
      firstSetup.destroy();
      expect(firstSetup.isPolling).toBe(false);

      const secondSetup = createCoordinator();
      secondSetup.start();
      expect(secondSetup.isPolling).toBe(true);
      expect(await secondSetup.triggerTick()).toBe(true);
      expect(fetchCount).toBe(1);
      secondSetup.destroy();
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

    it("reloads on dateRange changes while retaining stale-response protection during deep-link race", async () => {
      let activeRange = "today";
      let loading = true;
      const committed: string[] = [];
      let resolveToday: ((data: unknown) => void) | null = null;
      let resolve7d: ((data: unknown) => void) | null = null;

      const coordinator = new RunsPollingCoordinator({
        getQueryKey: () => `active::::1::20::${activeRange}`,
        hasActiveRuns: () => true,
        isDocumentVisible: () => true,
        fetchRuns: ({ queryKey }) => {
          if (queryKey === "active::::1::20::today") {
            return new Promise((resolve) => {
              resolveToday = resolve;
            });
          }
          return new Promise((resolve) => {
            resolve7d = resolve;
          });
        },
        onRequestStart: ({ showLoading }) => {
          if (showLoading) loading = true;
        },
        onResponse: (data) => {
          committed.push((data as { tag: string }).tag);
        },
        onSettled: ({ showLoading }) => {
          if (showLoading) loading = false;
        },
      });

      const req1 = coordinator.load({ showLoading: true, isPolling: false });
      expect(loading).toBe(true);

      activeRange = "7d";
      const req2 = coordinator.load({ showLoading: true, isPolling: false });

      resolveToday!({ tag: "stale-today-data" });
      expect(await req1).toBe(false);
      expect(committed).toEqual([]);

      resolve7d!({ tag: "fresh-7d-data" });
      expect(await req2).toBe(true);
      expect(committed).toEqual(["fresh-7d-data"]);
      expect(loading).toBe(false);

      coordinator.destroy();
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

    it("renders tabs for Active, Archived, and All Runs with search input and DateRangeFilter", () => {
      const markup = renderToStaticMarkup(
        React.createElement(RunsListPage, {
          onSelectRun: () => {},
          view: "active",
          onViewChange: () => {},
          page: 1,
          onPageChange: () => {},
          dateRange: "7d",
          onDateRangeChange: () => {},
        })
      );

      expect(markup).toContain("Active");
      expect(markup).toContain("Archived");
      expect(markup).toContain("All Runs");
      expect(markup).toContain("Search runs by ID, name, input...");
      expect(markup).toContain("role=\"radiogroup\"");
      expect(markup).toContain("Today");
      expect(markup).toContain("24h");
      expect(markup).toContain("7D");
      expect(markup).toContain("30D");
      expect(markup).toContain("All");
    });

    it("keeps DateRangeFilter in a right-aligned row separate from tabs and search", () => {
      expect(runsListSource).toMatch(
        /<div style=\{\{ marginBottom: 16,[\s\S]*?<Tabs[\s\S]*?<DateRangeFilter[\s\S]*?\/>\s*<\/div>\s*<form className="page-search-form"/
      );
    });

    it("offers explicit Show All path in empty state when dateRange is filtered", () => {
      const markup = renderToStaticMarkup(
        React.createElement(RunsListPage, {
          onSelectRun: () => {},
          view: "active",
          onViewChange: () => {},
          page: 1,
          onPageChange: () => {},
          dateRange: "today",
          onDateRangeChange: () => {},
          initialLoading: false,
        })
      );

      expect(markup).toContain("No active runs found for this date range.");
      expect(markup).toContain("Show All");
    });

    it("reloads query when dateRange changes by including dateRange in query effect dependencies", () => {
      expect(runsListSource).toMatch(/useEffect\(\(\)\s*=>\s*\{[\s\S]*?coordinatorRef\.current\?\.load[\s\S]*?\},\s*\[[^\]]*dateRange[^\]]*\]/);
    });
  });
});
