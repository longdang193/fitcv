import { describe, it, expect } from "vitest";
import { discoverFeatureRoutes, matchRoute } from "../app/route-registry";

describe("route registry and navigation", () => {
  it("discovers default routes with valid paths and groups", () => {
    const routes = discoverFeatureRoutes();
    expect(routes.length).toBeGreaterThan(0);

    const overview = routes.find((r) => r.id === "overview");
    expect(overview).toBeDefined();
    expect(overview?.path).toBe("#/overview");
    expect(overview?.group).toBe("workspace");
  });

  it("matches hash routes correctly", () => {
    const routes = discoverFeatureRoutes();
    const matched = matchRoute("#/overview", routes);
    expect(matched.id).toBe("overview");

    const fallback = matchRoute("#/unknown-route", routes);
    expect(fallback.id).toBe("overview");
  });
});

import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import {
  Dialog,
  Tabs,
  DataTable,
  SelectionBar,
  ZeroResultsState,
} from "../components";

describe("shared accessible component contracts", () => {
  it("renders Dialog with accessibility labels and modal attributes", () => {
    const markup = renderToStaticMarkup(
      React.createElement(Dialog, {
        open: true,
        onClose: () => {},
        title: "Test Dialog",
        description: "Accessible dialog description",
        children: React.createElement("p", null, "Dialog body content"),
      })
    );
    expect(markup).toContain("<dialog");
    expect(markup).toContain("Test Dialog");
    expect(markup).toContain("Accessible dialog description");
    expect(markup).toContain("aria-labelledby=");
    expect(markup).toContain("aria-describedby=");
  });

  it("renders Tabs with tablist role, orientation, and keyboard attributes", () => {
    const items = [
      { id: "tab-1", label: "First Tab" },
      { id: "tab-2", label: "Second Tab", count: 3 },
    ];
    const markup = renderToStaticMarkup(
      React.createElement(Tabs, {
        items,
        activeId: "tab-1",
        onChange: () => {},
        orientation: "vertical",
        ariaLabel: "Test tablist",
      })
    );
    expect(markup).toContain('role="tablist"');
    expect(markup).toContain('aria-orientation="vertical"');
    expect(markup).toContain('aria-label="Test tablist"');
    expect(markup).toContain('role="tab"');
    expect(markup).toContain('aria-selected="true"');
    expect(markup).toContain('tabindex="0"');
    expect(markup).toContain('aria-selected="false"');
    expect(markup).toContain('tabindex="-1"');
    expect(markup).toContain("(3)");
  });

  it("renders SelectionBar with count-aware bulk action region and polite live count", () => {
    const markup = renderToStaticMarkup(
      React.createElement(SelectionBar, {
        count: 5,
        label: "job",
        description: "Selected jobs can be archived or deleted.",
        actions: React.createElement("button", { type: "button" }, "Archive 5 jobs"),
      })
    );
    expect(markup).toContain('role="region"');
    expect(markup).toContain('aria-label="Bulk actions for 5 selected jobs"');
    expect(markup).toContain('aria-live="polite"');
    expect(markup).toContain("5 jobs selected");
    expect(markup).toContain("Archive 5 jobs");
  });

  it("renders ZeroResultsState with query, status role, and clear action", () => {
    const markup = renderToStaticMarkup(
      React.createElement(ZeroResultsState, {
        query: "nonexistent",
        onClear: () => {},
        clearLabel: "Reset all filters",
      })
    );
    expect(markup).toContain('role="status"');
    expect(markup).toContain('aria-live="polite"');
    expect(markup).toContain('No results for &quot;nonexistent&quot;');
    expect(markup).toContain("Reset all filters");
  });

  it("renders DataTable with labelled scroll cue, caption, emptyState, and bulkActions", () => {
    const columns = [{ key: "name", header: "Name" }];
    const markupEmpty = renderToStaticMarkup(
      React.createElement(DataTable, {
        columns,
        data: [],
        keyField: "name",
        caption: "Candidate applications",
        emptyState: React.createElement(ZeroResultsState, { query: "empty" }),
      })
    );
    expect(markupEmpty).toContain('<caption class="sr-only">Candidate applications</caption>');
    expect(markupEmpty).toContain('aria-label="Candidate applications, scrollable table"');
    expect(markupEmpty).toContain('No results for &quot;empty&quot;');

    const markupBulk = renderToStaticMarkup(
      React.createElement(DataTable, {
        columns,
        data: [{ name: "A" }, { name: "B" }],
        keyField: "name",
        selectedKeys: new Set(["A", "B"]),
        onToggleSelect: () => {},
        bulkActions: (count: number) =>
          React.createElement("button", { type: "button" }, `Delete ${count} items`),
      })
    );
    expect(markupBulk).toContain('Bulk actions for 2 selected items');
    expect(markupBulk).toContain('Delete 2 items');
  });
});
