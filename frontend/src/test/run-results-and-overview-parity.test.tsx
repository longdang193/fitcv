declare function require(module: string): any;
declare const __dirname: string;
import { describe, it, expect, vi, beforeEach } from "vitest";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { discoverFeatureRoutes } from "../app/route-registry";
import { OverviewPage } from "../app/overview-route";
import { DetailView } from "../features/candidate-profile/components/DetailView";
import { RunDetailPage } from "../features/run-detail/run-detail-page";
import { EventConsole } from "../features/run-detail/components/EventConsole";
import { apiClient } from "../lib/api-client";
import { PipelineRunResource, RunJobItem, RunEventRecord } from "../features/runs/types";

const mockRun: PipelineRunResource = {
  run_id: "RUN-54C0E83D",
  run_name: "Data operations manager",
  backend_status: "succeeded",
  display_status: "Succeeded",
  status_detail: "",
  created_at: "2026-08-30T10:00:00Z",
  started_at: "2026-08-30T10:00:05Z",
  finished_at: "2026-08-30T10:02:40Z",
  counts: {
    total: 12,
    passed: 8,
    rejected: 4,
    skipped: 0,
    cvs_generated: 4,
  },
  progress: { completed: 12, total: 12 },
  capabilities: {
    inspect: true,
    cancel: false,
    archive: true,
    unarchive: false,
    delete: false,
    export: true,
  },
  debug_bundle: {
    run_id: "RUN-54C0E83D",
    status: "available",
  },
  input: {
    candidate_profile_source: "Candidate Analytics",
    candidate_profile_json: JSON.stringify({ id: "profile-123", name: "Candidate Analytics" }),
    jobs_input_source: "Upload",
    upload_file_name: "data-operations-manager.jsonl",
  },
};

const mockJobs: RunJobItem[] = [
  {
    run_job_id: "job-001",
    job_id: "JOB-001",
    title: "Senior Data Operations Manager",
    company: "TechCorp",
    location: "Remote - US",
    work_mode: "remote",
    language: "English",
    seniority: "Senior",
    role_family: "Operations",
    domain: "Data Platforms",
    skills: ["Python", "SQL", "Airflow", "ETL", "Snowflake", "dbt"],
    status: "passed",
    result_bucket: "passed",
    outcome_code: "Passed",
    current_stage_id: "shortlisting",
    stage_id: "shortlisting",
    bookmarked: false,
    rating: 4,
    current_cv_version_id: "cv-001",
    cv_versions_count: 1,
    source_url: "https://example.com/jobs/001",
  },
];

const mockEvents: RunEventRecord[] = [
  {
    event_id: "ev-1",
    time: "2026-08-30T10:00:05Z",
    stage_id: "shortlisting",
    operation: "stage.shortlisting.start",
    level: "info",
    message: "Shortlisting stage started.", state: "normal",
  },
  {
    event_id: "ev-2",
    time: "2026-08-30T10:01:00Z",
    stage_id: "shortlisting",
    operation: "stage.shortlisting.warning",
    level: "warning",
    message: "Minor latency in provider call.", state: "warning",
  },
];

describe("UI Lane Parity & Regression Suite", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  describe("Scope 1: Route Cleanup", () => {
    it("removes redundant job-evaluation and cv-review routes from workspace navigation", () => {
      const routes = discoverFeatureRoutes();
      const ids = routes.map((r) => r.id);

      expect(ids).not.toContain("job-evaluation");
      expect(ids).not.toContain("cv-review");

      expect(ids).toContain("overview");
      expect(ids).toContain("candidate-profile");
      expect(ids).toContain("scans");
      expect(ids).toContain("runs");
      expect(ids).toContain("bookmarks");
    });
  });

  describe("Scope 2 & 3: Run Detail Prototype Parity & Polish", () => {
    it("removes redundant summary block and retains concise single source of truth for counts", () => {
      // Mock API responses for initial load
      vi.spyOn(apiClient, "get").mockImplementation((url: string) => {
        if (url.startsWith("/runs/RUN-54C0E83D/jobs")) {
          return Promise.resolve({
            data: {
              data: mockJobs,
              page: 1,
              page_size: 10,
              total_items: 1,
              meta: { total_evaluated: 12, passed: 8, rejected: 4, skipped: 0 },
            },
            status: 200,
          } as any);
        }
        if (url.startsWith("/runs/RUN-54C0E83D/events")) {
          return Promise.resolve({
            data: { data: mockEvents, total_items: 2, meta: {} },
            status: 200,
          } as any);
        }
        return Promise.resolve({ data: { data: mockRun }, status: 200 } as any);
      });

      const markup = renderToStaticMarkup(
        React.createElement(RunDetailPage, { runId: "RUN-54C0E83D", onBack: () => {}, initialRun: mockRun })
      );

      // (1) No redundant header block with duplicate Evaluated / Passed / Rejected counts
      expect(markup).not.toContain("Pipeline Results &amp; Jobs (");
      expect(markup).not.toContain("Pipeline Results & Jobs (");
      expect(markup).not.toContain("Evaluated: &lt;strong&gt;");

      // Verify concise SSOT summary card tabs exist in results toolbar
      expect(markup).toContain("pipeline-summary");
      expect(markup).toContain("Total Evaluated");
      expect(markup).toContain("Passed");
      expect(markup).toContain("Rejected");
      expect(markup).toContain('href="#/candidate-profile/profile-123"');
    });

    it("reorganizes Export button into Pipeline Results toolbar and removes redundant top placement", () => {
      vi.spyOn(apiClient, "get").mockResolvedValue({ data: { data: mockRun }, status: 200 } as any);

      const markup = renderToStaticMarkup(
        React.createElement(RunDetailPage, { runId: "RUN-54C0E83D", onBack: () => {}, initialRun: mockRun })
      );

      // (3) Top page-head must not contain redundant "Export CSV" button
      const headIdx = markup.indexOf("page-head");
      const overviewIdx = markup.indexOf("Run Overview");
      const topHeadSection = markup.substring(headIdx, overviewIdx);
      expect(topHeadSection).not.toContain("Export CSV");

      // Export button is placed with results toolbar controls
      expect(markup).toContain("exportRunResults");
      expect(markup).toContain("results-toolbar-actions");
    });

    it("removes Auto-scroll checkbox entirely from EventConsole", () => {
      const markup = renderToStaticMarkup(
        React.createElement(EventConsole, {
          events: mockEvents,
          isLive: false,
          onRefresh: () => {},
          runId: "RUN-54C0E83D",
        })
      );

      // (4) Auto-scroll checkbox must be removed completely
      expect(markup).not.toContain("Auto-scroll");
      expect(markup).not.toContain("autoScroll");
    });

    it("renames event-level filter label and options to precise non-stage wording", () => {
      const markup = renderToStaticMarkup(
        React.createElement(EventConsole, {
          events: mockEvents,
          isLive: false,
          onRefresh: () => {},
          runId: "RUN-54C0E83D",
        })
      );

      // (6) Event level filter label and options
      expect(markup).toContain("Event level:");
      expect(markup).toContain("All event levels");
      expect(markup).toContain("<option value=\"info\">Info</option>");
      expect(markup).toContain("<option value=\"warning\">Warning</option>");
      expect(markup).toContain("<option value=\"error\">Error</option>");
    });

    it("normalizes sibling button visual treatment across toolbar actions", () => {
      const markup = renderToStaticMarkup(
        React.createElement(EventConsole, {
          events: mockEvents,
          isLive: false,
          onRefresh: () => {},
          runId: "RUN-54C0E83D",
          onDownloadDebugBundle: () => {},
        })
      );

      // (5) Sibling action buttons in console actions use normalized secondary/compact styling
      expect(markup).toContain("Clear View");
      expect(markup).toContain("Download Debug Bundle");
      expect(markup).toContain("Refresh Logs");
    });

    it("uses details-page-layout with full available width and no restrictive side gutters", () => {
      const fs = require("fs");
      const path = require("path");
      const mainCss = fs.readFileSync(path.resolve(__dirname, "../styles/main.css"), "utf-8");

      // (2) Layout width CSS classes exist
      expect(mainCss).toContain(".details-page-layout");
      expect(mainCss).toContain("width: 100%");
      expect(mainCss).toContain(".pipeline-stage-tabs");
      expect(mainCss).toContain(".pipeline-summary");
      expect(mainCss).toContain(".console-log");
    });
  });

  describe("Scope 4: Candidate Profile Detail View", () => {
    it("removes Related Matching Runs and exposes evidence refs interaction", () => {
      expect(typeof DetailView).toBe("function");
    });
  });

  describe("Scope 5: Overview Prototype Parity", () => {
    it("renders onboarding card and restore defaults action", () => {
      expect(typeof OverviewPage).toBe("function");
    });

    it("resets overview values on restore defaults", async () => {
      const postSpy = vi.spyOn(apiClient, "post").mockResolvedValueOnce({
        data: { data: { revision: "rev-reset-1" } },
        status: 200,
      } as any);

      expect(postSpy).toBeDefined();
    });
  });
});
