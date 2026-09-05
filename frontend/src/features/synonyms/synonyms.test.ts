import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import {
  fetchSynonymPolicy,
  updateSynonymPolicy,
  fetchSynonymSuggestions,
  fetchSynonymSuggestionDetail,
  approveSynonymSuggestions,
  declineSynonymSuggestions,
  clearSynonymSuggestions,
  fetchSynonymProcessingRuns,
  importSynonymBackup,
  exportSynonymBackup,
} from "./api";
import { route } from "./route";
import { discoverFeatureRoutes, matchRoute } from "../../app/route-registry";
import { apiClient } from "../../lib/api-client";
import { renderToStaticMarkup } from "react-dom/server";
import { SynonymsPage } from "./synonyms-page";
import React from "react";
import { SuggestionQueue, hasActiveSynonymFilters } from "./suggestion-queue";

describe("Synonyms Feature API", () => {
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    vi.restoreAllMocks();
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  it("fetchSynonymPolicy requests correct endpoint and returns envelope data", async () => {
    const mockPolicy = {
      synonym_type: "skills",
      editor_text: "ts: typescript",
      normalized_policy: { ts: "typescript" },
      issues: [],
      validation_status: "valid",
      draft_revision: 2,
      active_type_revision_id: "rev-skill-1",
      active_type_revision: 1,
      active_bundle_revision_id: "rev-bundle-1",
      active_bundle_revision: 1,
      mirror_status: "in_sync",
      mirror_error_code: null,
    };

    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      headers: new Headers({ "content-type": "application/json" }),
      json: async () => ({ data: mockPolicy }),
    });

    const result = await fetchSynonymPolicy("skills");
    expect(result).toEqual(mockPolicy);
    expect(result.validation_status).toBe("valid");

    const [calledPath, calledInit] = (globalThis.fetch as any).mock.calls[0];
    expect(calledPath).toBe("/synonym-policies/skills");
    expect(calledInit.method).toBe("GET");
  });

  it("updateSynonymPolicy sends PUT with idempotency key and revisions", async () => {
    const mockUpdated = {
      synonym_type: "domain",
      editor_text: "fintech: financial services",
      normalized_policy: { fintech: "financial services" },
      issues: [],
      validation_status: "valid",
      draft_revision: 3,
      active_type_revision_id: "rev-domain-2",
      active_type_revision: 2,
      active_bundle_revision_id: "rev-bundle-2",
      active_bundle_revision: 2,
      mirror_status: "in_sync",
      mirror_error_code: null,
    };

    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      headers: new Headers({ "content-type": "application/json" }),
      json: async () => ({ data: mockUpdated }),
    });

    const result = await updateSynonymPolicy("domain", {
      editor_text: "fintech: financial services",
      expected_draft_revision: 2,
      expected_active_bundle_revision_id: "rev-bundle-1",
    });

    expect(result.draft_revision).toBe(3);
    const [calledPath, calledInit] = (globalThis.fetch as any).mock.calls[0];
    expect(calledPath).toBe("/synonym-policies/domain");
    expect(calledInit.method).toBe("PUT");
    expect(calledInit.headers["Idempotency-Key"]).toBeDefined();
    const parsedBody = JSON.parse(calledInit.body);
    expect(parsedBody.expected_draft_revision).toBe(2);
    expect(parsedBody.expected_active_bundle_revision_id).toBe("rev-bundle-1");
  });

  it("fetchSynonymSuggestions handles query params and collection envelope", async () => {
    const mockCollection = {
      data: [
        {
          suggestion_id: "sug-1",
          synonym_type: "skills",
          alias: "py",
          canonical: "python",
          normalized_alias: "py",
          normalized_canonical: "python",
          review_status: "pending",
          confidence: 0.95,
          candidate_canonicals: ["python"],
          source_count: 3,
          updated_at: "2026-08-30T10:00:00Z",
          created_at: "2026-08-30T09:00:00Z",
        },
      ],
      page: {
        page: 1,
        page_size: 20,
        total_items: 1,
        total_pages: 1,
        has_next: false,
        has_previous: false,
      },
      meta: {
        counts: {
          skills: { pending: 1, approved: 0, declined: 0, total: 1 },
          domain: { pending: 0, approved: 0, declined: 0, total: 0 },
          role_family: { pending: 0, approved: 0, declined: 0, total: 0 },
        },
      },
    };

    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      headers: new Headers({ "content-type": "application/json" }),
      json: async () => mockCollection,
    });

    const res = await fetchSynonymSuggestions({
      type: "skills",
      status: "pending",
      search: "py",
      page: 1,
      pageSize: 20,
    });

    expect(res.items).toHaveLength(1);
    expect(res.items[0].alias).toBe("py");
    expect(res.total).toBe(1);
    expect(res.counts.skills.pending).toBe(1);

    const [calledPath] = (globalThis.fetch as any).mock.calls[0];
    expect(calledPath).toContain("/synonym-suggestions?");
    expect(calledPath).toContain("type=skills");
    expect(calledPath).toContain("status=pending");
    expect(calledPath).toContain("search=py");
  });

  it("fetchSynonymSuggestionDetail requests detail with evidence pagination", async () => {
    const mockDetail = {
      suggestion_id: "sug-42",
      synonym_type: "domain",
      alias: "ecom",
      canonical: "e-commerce",
      normalized_alias: "ecom",
      normalized_canonical: "e-commerce",
      review_status: "pending",
      confidence: 0.9,
      candidate_canonicals: [],
      source_count: 2,
      updated_at: "2026-08-30T10:00:00Z",
      created_at: "2026-08-30T09:00:00Z",
      sources: [
        {
          run_id: "run-101",
          occurrence_count: 2,
          run_name: "Tech CV Run",
          first_seen_at: "2026-08-30T09:00:00Z",
          last_seen_at: "2026-08-30T10:00:00Z",
          evidence_json: '{"context": "ecom platforms"}',
        },
      ],
    };

    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      headers: new Headers({ "content-type": "application/json" }),
      json: async () => ({ data: mockDetail }),
    });

    const detail = await fetchSynonymSuggestionDetail("sug-42", 1, 20);
    expect(detail.suggestion_id).toBe("sug-42");
    expect(detail.sources).toHaveLength(1);
    expect(detail.sources![0].run_id).toBe("run-101");

    const [calledPath] = (globalThis.fetch as any).mock.calls[0];
    expect(calledPath).toBe("/synonym-suggestions/sug-42?evidence_page=1&evidence_page_size=20");
  });

  it("batch actions approve, decline, and clear execute against canonical endpoints", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      headers: new Headers({ "content-type": "application/json" }),
      json: async () => ({ data: { applied_count: 2, approved_count: 2 } }),
    });

    const approveRes = await approveSynonymSuggestions(["sug-1", "sug-2"], 1, "bundle-1");
    expect(approveRes.approved_count).toBe(2);

    let [calledPath, calledInit] = (globalThis.fetch as any).mock.calls[0];
    expect(calledPath).toBe("/synonym-suggestions/actions/approve");
    expect(calledInit.method).toBe("POST");
    expect(JSON.parse(calledInit.body).suggestion_ids).toEqual(["sug-1", "sug-2"]);

    const declineRes = await declineSynonymSuggestions(["sug-3"]);
    expect(declineRes).toBeDefined();
    [calledPath, calledInit] = (globalThis.fetch as any).mock.calls[1];
    expect(calledPath).toBe("/synonym-suggestions/actions/decline");
    expect(calledInit.method).toBe("POST");

    const clearRes = await clearSynonymSuggestions(["sug-3"]);
    expect(clearRes).toBeDefined();
    [calledPath, calledInit] = (globalThis.fetch as any).mock.calls[2];
    expect(calledPath).toBe("/synonym-suggestions/actions/clear");
    expect(calledInit.method).toBe("POST");
  });

  it("fetchSynonymProcessingRuns fetches audit log with pagination", async () => {
    const mockRuns = {
      data: [
        {
          processing_run_id: "proc-1",
          processed_at: "2026-08-30T11:00:00Z",
          total_processed: 5,
          approved_count: 4,
          declined_count: 1,
          pending_count: 0,
          successfully_added_count: 4,
          source_operation: "batch_review",
          issue_count: 0,
        },
      ],
      page: {
        page: 1,
        page_size: 20,
        total_items: 1,
        total_pages: 1,
        has_next: false,
        has_previous: false,
      },
      meta: {},
    };

    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      headers: new Headers({ "content-type": "application/json" }),
      json: async () => mockRuns,
    });

    const result = await fetchSynonymProcessingRuns(1, 20);
    expect(result.items).toHaveLength(1);
    expect(result.items[0].processing_run_id).toBe("proc-1");
    expect(result.items[0].approved_count).toBe(4);
  });

  it("importSynonymBackup posts FormData with Idempotency-Key", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      headers: new Headers({ "content-type": "application/json" }),
      json: async () => ({ data: { bundle_revision_id: "imported-rev-1" } }),
    });

    const file = new File(["fake zip"], "backup.zip", { type: "application/zip" });
    const result = await importSynonymBackup(file, "expected-rev-id");
    expect(result.bundle_revision_id).toBe("imported-rev-1");

    const [calledPath, calledInit] = (globalThis.fetch as any).mock.calls[0];
    expect(calledPath).toBe("/synonym-backups/import");
    expect(calledInit.method).toBe("POST");
    expect(calledInit.headers["Idempotency-Key"]).toBeDefined();
    expect(calledInit.body).toBeInstanceOf(FormData);
  });

  it("exportSynonymBackup invokes apiClient.download with backup path", async () => {
    const downloadSpy = vi.spyOn(apiClient, "download").mockResolvedValue(undefined);
    await exportSynonymBackup();
    expect(downloadSpy).toHaveBeenCalledWith("/synonym-backups/export.zip", "fitcv-synonyms-backup.zip");
  });
});

describe("Synonyms Route Registration", () => {
  it("defines valid FeatureRoute descriptor", () => {
    expect(route.id).toBe("synonyms");
    expect(route.path).toBe("#/synonyms");
    expect(route.title).toBe("Synonyms");
    expect(route.group).toBe("settings");
    expect(route.order).toBe(40);
    expect(typeof route.component).toBe("function");
  });

  it("is discovered by route-registry without modifying shared registration files", () => {
    const routes = discoverFeatureRoutes();
    const synonymRoute = routes.find((r) => r.id === "synonyms");
    expect(synonymRoute).toBeDefined();
    expect(synonymRoute?.path).toBe("#/synonyms");
    expect(synonymRoute?.group).toBe("settings");

    const matched = matchRoute("#/synonyms", routes);
    expect(matched.id).toBe("synonyms");
  });
});

describe("Synonyms page layout", () => {
  it("renders processing summary log below review queue", () => {
    const markup = renderToStaticMarkup(React.createElement(SynonymsPage));
    const queuePosition = markup.indexOf("Loading synonym review queue...");
    const summaryPosition = markup.indexOf("Processing Summary Log");

    expect(queuePosition).toBeGreaterThanOrEqual(0);
    expect(summaryPosition).toBeGreaterThan(queuePosition);
    expect(markup).not.toContain("Processing History");
  });

  it("treats search and non-default status filters as zero-result context", () => {
    expect(hasActiveSynonymFilters("   ", "all", "pending")).toBe(false);
    expect(hasActiveSynonymFilters("typescript", "all", "pending")).toBe(true);
    expect(hasActiveSynonymFilters("", "skills", "pending")).toBe(true);
    expect(hasActiveSynonymFilters("", "all", "approved")).toBe(true);
    expect(renderToStaticMarkup(React.createElement(SuggestionQueue))).toContain(
      "Loading synonym review queue..."
    );
  });
});
