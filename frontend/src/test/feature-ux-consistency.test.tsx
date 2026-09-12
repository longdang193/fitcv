import { describe, it, expect } from "vitest";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { RunsListPage } from "../features/runs/runs-list";
import { ScansListPage } from "../features/scans/scans-list";
import { BookmarksTable } from "../features/bookmarks/components/BookmarksTable";
import { PipelineSettingsPage } from "../features/pipeline-settings/route";
import { getNextFilterTabIndex } from "../features/run-detail/components/FilterTabs";
import { CvEvaluationCard } from "../features/cv-review/components/CvEvaluationCard";
import { CvVersionHistory } from "../features/cv-review/components/CvVersionHistory";
import type { CvVersionResource } from "../features/cv-review/types";

describe("frontend owned features UX consistency", () => {
  it("renders RunsListPage with canonical page-head, eyebrow, and truthful empty state", () => {
    const markup = renderToStaticMarkup(
      React.createElement(RunsListPage, {
        onSelectRun: () => {},
        view: "active",
        onViewChange: () => {},
        page: 1,
        onPageChange: () => {},
      })
    );

    expect(markup).toContain('class="page-head"');
    expect(markup).toContain('class="eyebrow"');
    expect(markup).toContain("Workspace");
    expect(markup).toContain("Trigger, monitor, cancel, and archive local runs.");
  });

  it("renders ScansListPage with canonical page-head and eyebrow", () => {
    const markup = renderToStaticMarkup(
      React.createElement(ScansListPage, {
        onSelectScan: () => {},
        lifecycle: "active",
        onTabChange: () => {},
        page: 1,
        onPageChange: () => {},
      })
    );

    expect(markup).toContain('class="page-head"');
    expect(markup).toContain('class="eyebrow"');
    expect(markup).toContain("Workspace");
    expect(markup).toContain("Create reusable job input from tracked companies.");
  });

  it("renders BookmarksTable with truthful empty state when filters are active", () => {
    const markup = renderToStaticMarkup(
      React.createElement(BookmarksTable, {
        bookmarks: [],
        loading: false,
        page: 1,
        pageSize: 20,
        total: 0,
        onPageChange: () => {},
        selectedJobIds: [],
        onToggleSelectJob: () => {},
        onToggleSelectAll: () => {},
        onRemoveSingle: () => {},
        onInspectEvidence: () => {},
        hasFilters: true,
      })
    );

    expect(markup).toContain("No bookmarks match this view.");
    expect(markup).toContain("Change the pipeline stage or search to see other bookmarked jobs.");
  });

  it("renders BookmarksTable with truthful empty state when no bookmarks exist overall", () => {
    const markup = renderToStaticMarkup(
      React.createElement(BookmarksTable, {
        bookmarks: [],
        loading: false,
        page: 1,
        pageSize: 20,
        total: 0,
        onPageChange: () => {},
        selectedJobIds: [],
        onToggleSelectJob: () => {},
        onToggleSelectAll: () => {},
        onRemoveSingle: () => {},
        onInspectEvidence: () => {},
        hasFilters: false,
      })
    );

    expect(markup).toContain("No bookmarked jobs yet. Add bookmarks from Run Details to collect jobs here.");
  });

  it("renders PipelineSettingsPage with canonical Pipeline eyebrow", () => {
    const markup = renderToStaticMarkup(React.createElement(PipelineSettingsPage));
    expect(markup).toContain('class="eyebrow"');
    expect(markup).toContain("Pipeline");
  });

  it("normalizes tab-to-content spacing between Taxonomy and Runs without magic inline margins", () => {
    const fs = require("fs");
    const path = require("path");
    const synonymsSource = fs.readFileSync(
      path.resolve(__dirname, "../features/synonyms/synonyms-page.tsx"),
      "utf-8"
    );
    const mainCss = fs.readFileSync(path.resolve(__dirname, "../styles/main.css"), "utf-8");

    expect(synonymsSource).toContain("content-container page-stack synonym-management-page");
    expect(synonymsSource).not.toContain("marginTop: 20");
    expect(mainCss).toMatch(/\.tabs-container\s*\{[^}]*gap:\s*18px/);
    expect(mainCss).not.toMatch(/\.candidate-profiles-catalog\s+\.tabs-container\s*\{[^}]*gap:\s*14px/);
    expect(mainCss).toMatch(/\.page-stack\s*>\s*\.page-head\s*\{[^}]*margin-bottom:\s*0/);
  });

  it("preserves keyboard navigation in FilterTabs", () => {
    expect(getNextFilterTabIndex("ArrowRight", 0, 3)).toBe(1);
    expect(getNextFilterTabIndex("ArrowRight", 2, 3)).toBe(0);
    expect(getNextFilterTabIndex("ArrowLeft", 0, 3)).toBe(2);
    expect(getNextFilterTabIndex("Home", 2, 3)).toBe(0);
    expect(getNextFilterTabIndex("End", 0, 3)).toBe(2);
  });

  it("renders CV warnings and blocking outcomes without hiding evidence state", () => {
    const baseVersion: CvVersionResource = {
      version_id: "cv-warning-1",
      run_id: "run-1",
      run_job_id: "job-1",
      job_url: "https://example.com/job-1",
      ordinal: 1,
      generation_status: "generated",
      outcome_status: "generated",
      evidence_state: "passed",
      created_at: "2026-09-12T00:00:00Z",
      review_state: "none",
      quality_warnings: { warnings: ["Missing preferred requirement evidence."] },
      capabilities: { download: true, preview: true, regenerate: true },
    };
    const warningMarkup = renderToStaticMarkup(
      React.createElement(CvEvaluationCard, { version: baseVersion })
    );
    expect(warningMarkup).toContain('aria-label="CV quality warnings"');
    expect(warningMarkup).toContain("Missing preferred requirement evidence.");

    const failedMarkup = renderToStaticMarkup(
      React.createElement(CvEvaluationCard, {
        version: { ...baseVersion, outcome_status: "failed", failure_code: "grounding_failed" },
      })
    );
    expect(failedMarkup).toContain('aria-label="CV generation failure"');
    expect(failedMarkup).toContain("grounding_failed");

    const historyMarkup = renderToStaticMarkup(
      React.createElement(CvVersionHistory, {
        versions: [{ ...baseVersion, outcome_status: "failed", failure_code: "grounding_failed" }],
        selectedVersionId: "cv-warning-1",
        onSelectVersion: () => {},
      })
    );
    expect(historyMarkup).toContain('<span>failed</span>');
  });
});
