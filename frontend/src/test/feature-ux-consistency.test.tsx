import { describe, it, expect } from "vitest";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { RunsListPage } from "../features/runs/runs-list";
import { ScansListPage } from "../features/scans/scans-list";
import { BookmarksTable } from "../features/bookmarks/components/BookmarksTable";
import { PipelineSettingsPage } from "../features/pipeline-settings/route";
import { getNextFilterTabIndex } from "../features/run-detail/components/FilterTabs";

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

  it("preserves keyboard navigation in FilterTabs", () => {
    expect(getNextFilterTabIndex("ArrowRight", 0, 3)).toBe(1);
    expect(getNextFilterTabIndex("ArrowRight", 2, 3)).toBe(0);
    expect(getNextFilterTabIndex("ArrowLeft", 0, 3)).toBe(2);
    expect(getNextFilterTabIndex("Home", 2, 3)).toBe(0);
    expect(getNextFilterTabIndex("End", 0, 3)).toBe(2);
  });
});
