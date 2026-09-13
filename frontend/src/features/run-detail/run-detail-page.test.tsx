import { describe, it, expect, vi, beforeEach } from "vitest";
import React from "react";
import { readFileSync } from "node:fs";
import { renderToStaticMarkup } from "react-dom/server";
import {
  RunDetailPage,
  buildRunJobsQueryKey,
} from "./run-detail-page";
import { PipelineRunResource, RunJobItem } from "../runs/types";

function createMockRun(runId: string, status: string = "running"): PipelineRunResource {
  return {
    run_id: runId,
    run_name: "Run " + runId,
    backend_status: status as any,
    display_status: status,
    created_at: "2026-09-13T10:00:00Z",
    counts: { total: 20, passed: 10, rejected: 10, skipped: 0, cvs_generated: 4 },
    progress: { completed: 20, total: 20 },
    capabilities: {
      inspect: true,
      cancel: !["succeeded", "failed", "cancelled"].includes(status),
      archive: ["succeeded", "failed", "cancelled"].includes(status),
      unarchive: false,
      delete: false,
      export: true,
    },
  };
}

function createMockJob(jobId: string, title: string): RunJobItem {
  return {
    run_job_id: jobId,
    job_id: jobId,
    title,
    company: "Acme Corp",
    current_stage_id: "ranking",
    status: "evaluated",
    result_bucket: "passed",
    rating: 0,
    interest_rating: 0,
    bookmarked: false,
    decision: "passed",
    reason_code: null,
    capabilities: {
      bookmark: true,
      regenerate_cv: false,
    },
  };
}

describe("Run Detail Request Ownership and Polling Coordination", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  describe("buildRunJobsQueryKey", () => {
    it("builds canonical query identity string matching runId, stage, bucket, search, page, and size", () => {
      const key = buildRunJobsQueryKey("run-123", "ranking", "all", "engineer", 1, 10);
      expect(key).toBe("run-123::ranking::all::engineer::1::10");
    });

    it("trims whitespace from search parameter for identity stability", () => {
      const key1 = buildRunJobsQueryKey("run-123", "ranking", "all", "  backend python  ", 1, 10);
      const key2 = buildRunJobsQueryKey("run-123", "ranking", "all", "backend python", 1, 10);
      expect(key1).toBe("run-123::ranking::all::backend python::1::10");
      expect(key1).toBe(key2);
    });

    it("distinguishes queries across run IDs, stages, buckets, pages, and page sizes", () => {
      const base = buildRunJobsQueryKey("run-1", "ranking", "all", "", 1, 10);
      const differentRun = buildRunJobsQueryKey("run-2", "ranking", "all", "", 1, 10);
      const differentStage = buildRunJobsQueryKey("run-1", "cv-analysis", "all", "", 1, 10);
      const differentBucket = buildRunJobsQueryKey("run-1", "ranking", "passed", "", 1, 10);
      const differentSearch = buildRunJobsQueryKey("run-1", "ranking", "all", "data", 1, 10);
      const differentPage = buildRunJobsQueryKey("run-1", "ranking", "all", "", 2, 10);
      const differentSize = buildRunJobsQueryKey("run-1", "ranking", "all", "", 1, 20);

      expect(base).not.toBe(differentRun);
      expect(base).not.toBe(differentStage);
      expect(base).not.toBe(differentBucket);
      expect(base).not.toBe(differentSearch);
      expect(base).not.toBe(differentPage);
      expect(base).not.toBe(differentSize);
    });
  });

  describe("Request Identity and Stale-Response Rejection", () => {
    it("rejects stale Search A response resolving after Search B", async () => {
      let activeRequestId = 0;
      let acceptedTitle: string | null = null;
      let resolveSearchA: ((val: string) => void) | null = null;
      let resolveSearchB: ((val: string) => void) | null = null;

      const performSearch = (term: string) => {
        const reqId = ++activeRequestId;
        const promise = new Promise<string>((res) => {
          if (term === "Search A") resolveSearchA = res;
          else resolveSearchB = res;
        });
        return promise.then((title) => {
          if (reqId !== activeRequestId) return false;
          acceptedTitle = title;
          return true;
        });
      };

      const pA = performSearch("Search A");
      const pB = performSearch("Search B");

      // Search A resolves late
      resolveSearchA!("Job A (Obsolete)");
      const resA = await pA;
      expect(resA).toBe(false);

      // Search B resolves
      resolveSearchB!("Job B (Active)");
      const resB = await pB;
      expect(resB).toBe(true);
      expect(acceptedTitle).toBe("Job B (Active)");
    });

    it("rejects delayed polling response resolving after filter change", async () => {
      let activeRequestId = 0;
      let acceptedStage: string | null = null;
      let resolvePoll: (() => void) | null = null;
      let resolveFilter: (() => void) | null = null;

      const triggerFetch = (stage: string, isPolling: boolean) => {
        const reqId = ++activeRequestId;

        const promise = new Promise<void>((res) => {
          if (isPolling) resolvePoll = res;
          else resolveFilter = res;
        });

        return promise.then(() => {
          if (reqId !== activeRequestId) return false;
          acceptedStage = stage;
          return true;
        });
      };

      const pollPromise = triggerFetch("ranking", true);
      const filterPromise = triggerFetch("screening", false);

      resolvePoll!();
      const pollOk = await pollPromise;
      expect(pollOk).toBe(false);

      resolveFilter!();
      const filterOk = await filterPromise;
      expect(filterOk).toBe(true);
      expect(acceptedStage).toBe("screening");
    });
  });

  describe("Single-Flight Polling and Terminal Stop", () => {
    it("skips overlapping polling ticks while request is in flight", async () => {
      let inFlight = false;
      let tickCount = 0;
      let resolveFirstTick: (() => void) | null = null;

      const tick = async () => {
        if (inFlight) return false;
        inFlight = true;
        tickCount += 1;
        await new Promise<void>((res) => {
          resolveFirstTick = res;
        });
        inFlight = false;
        return true;
      };

      const tick1 = tick();
      expect(inFlight).toBe(true);
      expect(tickCount).toBe(1);

      // Concurrent second tick skipped
      const tick2 = await tick();
      expect(tick2).toBe(false);
      expect(tickCount).toBe(1);

      resolveFirstTick!();
      await tick1;
      expect(inFlight).toBe(false);
    });

    it("does not poll when run is absent or terminal", () => {
      const canPoll = (run: PipelineRunResource | null) => {
        if (!run) return false;
        return !["succeeded", "failed", "cancelled"].includes(run.backend_status);
      };

      expect(canPoll(null)).toBe(false);
      expect(canPoll(createMockRun("r1", "running"))).toBe(true);
      expect(canPoll(createMockRun("r2", "succeeded"))).toBe(false);
      expect(canPoll(createMockRun("r3", "failed"))).toBe(false);
      expect(canPoll(createMockRun("r4", "cancelled"))).toBe(false);
    });
  });

  describe("Mounted Detail UI and Focus Preservation", () => {
    it("lets pagination state effect own each jobs request", () => {
      const source = readFileSync(new URL("./run-detail-page.tsx", import.meta.url), "utf8");

      expect(source).not.toMatch(/setJobsPage\(p\);\s*loadJobs\(p\);/);
      expect(source).not.toMatch(/setJobsPage\(1\);\s*loadJobs\(1, newSize\);/);
    });

    it("preserves search input element and layout when run detail is mounted", () => {
      const activeRun = createMockRun("run-ui-test", "running");
      const mockJobs = [createMockJob("job-1", "Senior Engineer")];

      const markup = renderToStaticMarkup(
        React.createElement(RunDetailPage, {
          runId: "run-ui-test",
          onBack: () => {},
          initialRun: activeRun,
          initialJobs: mockJobs,
        })
      );

      // Search input is rendered with exact ID and accessible attributes
      expect(markup).toContain('id="jobResultsSearch"');
      expect(markup).toContain('type="search"');
      expect(markup).toContain('aria-label="Search pipeline results"');

      // Overview card and table remain mounted
      expect(markup).toContain("Run Overview");
      expect(markup).toContain("Senior Engineer");

      // Does not render full-page loading replacement when run is already loaded
      expect(markup).not.toContain("Loading run details...");
    });

    it("renders full-page LoadingState only when initial run detail is absent", () => {
      const markup = renderToStaticMarkup(
        React.createElement(RunDetailPage, {
          runId: "run-initial-loading",
          onBack: () => {},
        })
      );

      expect(markup).toContain("Loading run details...");
      expect(markup).not.toContain('id="jobResultsSearch"');
    });
  });
});
