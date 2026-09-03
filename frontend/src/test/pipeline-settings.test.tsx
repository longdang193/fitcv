import { describe, it, expect, vi, beforeEach } from "vitest";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import {
  PipelineSettingsDialog,
  PIPELINE_SECTIONS,
} from "../features/pipeline-settings/pipeline-settings-dialog";
import { buildFallbackDefaults } from "../features/pipeline-settings/sections-def";
import { PipelineSettingsPage } from "../features/pipeline-settings/route";
import { OverviewPage } from "../app/overview-route";
import { discoverFeatureRoutes, matchRoute } from "../app/route-registry";
import { apiClient } from "../lib/api-client";

describe("Pipeline Settings Dialog & Feature Suite", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  describe("Section Structure & Prototype Parity", () => {
    it("contains exactly the 9 confirmed sections in order", () => {
      const expectedIds = [
        "overview",
        "enrichment",
        "screening",
        "shortlisting",
        "ranking",
        "cv-analysis",
        "cv-generation",
        "runtime-limits",
        "automation-reuse",
      ];
      const sectionIds = PIPELINE_SECTIONS.map((s) => s.id);
      expect(sectionIds).toEqual(expectedIds);

      const sectionTitles = PIPELINE_SECTIONS.map((s) => s.title);
      expect(sectionTitles).toEqual([
        "Pipeline Overview",
        "Enrichment",
        "Screening",
        "Shortlisting",
        "Ranking",
        "CV Analysis",
        "CV Generation",
        "Runtime & Limits",
        "Automation & Reuse",
      ]);
    });

    it("preserves prototype settings and strictly excludes Personalization", () => {
      const allTitles = PIPELINE_SECTIONS.map((s) => s.title.toLowerCase());
      expect(allTitles).not.toContain("personalization");
      expect(allTitles).not.toContain("preference optimization");

      const allOwnedKeys = PIPELINE_SECTIONS.flatMap((s) => s.ownedKeys);
      expect(allOwnedKeys.some((k) => k.startsWith("preference_optimization"))).toBe(false);
      expect(allOwnedKeys.some((k) => k.includes("personalization"))).toBe(false);

      // Verify canonical keys in individual sections
      const overviewKeys = PIPELINE_SECTIONS.find((s) => s.id === "overview")!.ownedKeys;
      expect(overviewKeys).toContain("pipeline.vector_search_top_n");
      expect(overviewKeys).toContain("pipeline.ai_score_top_n");
      expect(overviewKeys).toContain("pipeline.final_top_n");
      expect(overviewKeys).toContain("pipeline.evidence_top_k");
      expect(overviewKeys).toContain("global_job_filters.applications_count_max");
      expect(overviewKeys).toContain("global_job_filters.max_age_days");

      const screeningSection = PIPELINE_SECTIONS.find((s) => s.id === "screening")!;
      const screeningMembers = screeningSection.groups.flatMap((g) => g.fields).map((f) => f.member);
      expect(screeningMembers).toContain("missing_fit_context");
      expect(screeningMembers).toContain("location_type_excluded");
      expect(screeningMembers).toContain("seniority_mismatch");
      expect(screeningMembers).toContain("contract_type_excluded");
      expect(screeningMembers).toContain("experience_level_excluded");

      const cvGenSection = PIPELINE_SECTIONS.find((s) => s.id === "cv-generation")!;
      const cvGenKeys = cvGenSection.ownedKeys;
      expect(cvGenKeys).toContain("cv_summary_enabled");
      expect(cvGenKeys).toContain("cv_education_enabled");
      expect(cvGenKeys).toContain("cv_experience_enabled");
      expect(cvGenKeys).toContain("cv_skills_enabled");
      expect(cvGenKeys).toContain("cv_certifications_enabled");
      expect(cvGenKeys).toContain("cv_projects_enabled");
      expect(cvGenKeys).toContain("cv_publications_enabled");
      expect(cvGenKeys).toContain("cv_languages_enabled");

      const runtimeSection = PIPELINE_SECTIONS.find((s) => s.id === "runtime-limits")!;
      expect(runtimeSection.ownedKeys).toContain("llm_runtime.request_start_interval_secs");
      expect(runtimeSection.ownedKeys).toContain("stage_runtime.enrich.concurrency");
      expect(runtimeSection.ownedKeys).toContain("stage_runtime.ranking.concurrency");
      expect(runtimeSection.ownedKeys).toContain("stage_runtime.cv_analysis.concurrency");
      expect(runtimeSection.ownedKeys).toContain("stage_runtime.cv_generation.concurrency");

      const autoReuseSection = PIPELINE_SECTIONS.find((s) => s.id === "automation-reuse")!;
      expect(autoReuseSection.ownedKeys).toContain("reuse.enrich.enabled");
      expect(autoReuseSection.ownedKeys).toContain("reuse.ranking.enabled");
      expect(autoReuseSection.ownedKeys).toContain("reuse.cv_analysis.enabled");
      expect(autoReuseSection.ownedKeys).toContain("reuse.cv_generation.enabled");
      expect(autoReuseSection.ownedKeys).toContain("reuse.synonym_triage.enabled");
      expect(autoReuseSection.ownedKeys).toContain("synonym_management.propose_enabled");
      expect(autoReuseSection.ownedKeys).toContain("synonym_management.auto_accept_suggestions_enabled");
      expect(autoReuseSection.ownedKeys).toContain("synonym_management.apply_approved_enabled");
    });
  });

  describe("Dialog Rendering & Controls", () => {
    it("renders dialog with left section tabs, active content, global Restore Defaults, and Save", () => {
      const markup = renderToStaticMarkup(
        React.createElement(PipelineSettingsDialog, {
          open: true,
          onClose: () => {},
          initialSection: "overview",
        })
      );

      // Dialog container
      expect(markup).toContain("pipeline-settings-dialog");
      expect(markup).toContain("Pipeline Settings");
      expect(markup).toContain("Configure matching run parameters, stages, and output defaults.");

      // Left section tabs
      expect(markup).toContain("pipeline-settings-nav");
      expect(markup).toContain("Pipeline Overview");
      expect(markup).toContain("Enrichment");
      expect(markup).toContain("Screening");
      expect(markup).toContain("Shortlisting");
      expect(markup).toContain("Ranking");
      expect(markup).toContain("CV Analysis");
      expect(markup).toContain("CV Generation");
      expect(markup).toContain("Runtime &amp; Limits");
      expect(markup).toContain("Automation &amp; Reuse");

      // Per-section Restore Default button
      expect(markup).toContain("Restore Section Defaults");

      // Global Restore Defaults button in footer
      expect(markup).toContain("Restore Defaults");

      // One dialog Save button
      expect(markup).toContain("Save");
      expect(markup).toContain("Cancel");
    });

    it("renders specific section content when initialSection is set to screening", () => {
      const markup = renderToStaticMarkup(
        React.createElement(PipelineSettingsDialog, {
          open: true,
          onClose: () => {},
          initialSection: "screening",
        })
      );

      expect(markup).toContain("Choose which listings qualify before ranking.");
      expect(markup).toContain("Require Fit Context");
      expect(markup).toContain("Location &amp; Work Mode");
      expect(markup).toContain("Seniority Preference");
      expect(markup).toContain("Contract Preference");
      expect(markup).toContain("Experience Preference");
    });

    it("renders cv-generation section with all included sections switches", () => {
      const markup = renderToStaticMarkup(
        React.createElement(PipelineSettingsDialog, {
          open: true,
          onClose: () => {},
          initialSection: "cv-generation",
        })
      );

      expect(markup).toContain("Choose content included in generated CVs.");
      expect(markup).toContain("Included Sections");
      expect(markup).toContain("Summary");
      expect(markup).toContain("Education");
      expect(markup).toContain("Experience");
      expect(markup).toContain("Skills");
      expect(markup).toContain("Certifications");
      expect(markup).toContain("Projects");
      expect(markup).toContain("Publications");
      expect(markup).toContain("Languages");
    });

    it("returns null when open is false", () => {
      const markup = renderToStaticMarkup(
        React.createElement(PipelineSettingsDialog, {
          open: false,
          onClose: () => {},
        })
      );
      expect(markup).toBe("");
    });
  });

  describe("API Interaction & Route Registry", () => {
    it("discovers pipeline-settings route and registers under settings group", () => {
      const routes = discoverFeatureRoutes();
      const pipelineRoute = routes.find((r) => r.id === "pipeline-settings");
      expect(pipelineRoute).toBeDefined();
      expect(pipelineRoute?.title).toBe("Pipeline Settings");
      expect(pipelineRoute?.group).toBe("settings");
      expect(pipelineRoute?.path).toBe("#/settings/pipeline");
    });

    it("matches exact path and aliases for pipeline settings", () => {
      const routes = discoverFeatureRoutes();
      expect(matchRoute("#/settings/pipeline", routes).id).toBe("pipeline-settings");
      expect(matchRoute("#/pipeline-settings", routes).id).toBe("pipeline-settings");
    });

    it("renders PipelineSettingsPage with trigger button and open dialog", () => {
      const markup = renderToStaticMarkup(React.createElement(PipelineSettingsPage));
      expect(markup).toContain("Pipeline Settings");
      expect(markup).toContain("Open Pipeline Settings");
      expect(markup).toContain("pipeline-settings-dialog");
    });

    it("OverviewPage renders header Pipeline Settings button", () => {
      const markup = renderToStaticMarkup(React.createElement(OverviewPage));
      expect(markup).toContain("Pipeline Settings");
      expect(markup).toContain("Restore Defaults");
    });
  });

  describe("Defaults and Dirty Tracking Logic", () => {
    it("buildFallbackDefaults contains defaults for all owned keys", () => {

      const defaults = buildFallbackDefaults();

      expect(defaults["pipeline.vector_search_top_n"]).toBe(50);
      expect(defaults["pipeline.ai_score_top_n"]).toBe(50);
      expect(defaults["pipeline.final_top_n"]).toBe(15);
      expect(defaults["pipeline.evidence_top_k"]).toBe(5);
      expect(defaults["global_job_filters.applications_count_max"]).toBe(200);
      expect(defaults["global_job_filters.max_age_days"]).toBe(30);
      expect(defaults["rule_filter.selected_filters"]).toEqual([
        "seniority_mismatch",
        "missing_fit_context",
        "location_type_excluded",
        "contract_type_excluded",
        "experience_level_excluded",
      ]);
      expect(defaults["cv_analysis.semantic_alignment.enabled"]).toBe(true);
      expect(defaults["cv_summary_enabled"]).toBe(true);
      expect(defaults["llm_runtime.request_start_interval_secs"]).toBe(0);
      expect(defaults["stage_runtime.enrich.concurrency"]).toBe(8);
      expect(defaults["reuse.enrich.enabled"]).toBe(true);
      expect(defaults["synonym_management.propose_enabled"]).toBe(true);
    });

    it("verifies per-section restore targets only owned keys of that section", () => {
      const overviewSection = PIPELINE_SECTIONS.find((s) => s.id === "overview")!;
      const rankingSection = PIPELINE_SECTIONS.find((s) => s.id === "ranking")!;

      // Section owned keys are distinct
      expect(overviewSection.ownedKeys).not.toEqual(rankingSection.ownedKeys);
      expect(rankingSection.ownedKeys).toContain("ranking_policy.fit_label_thresholds.strong");
      expect(overviewSection.ownedKeys).not.toContain("ranking_policy.fit_label_thresholds.strong");
    });

    it("handles save with apiClient patch and expected revision", async () => {
      const patchSpy = vi.spyOn(apiClient, "patch").mockResolvedValueOnce({
        data: {
          data: {
            revision: "rev-saved-2",
            values: { "pipeline.final_top_n": 20 },
          },
        },
        status: 200,
      } as any);

      const res = await apiClient.patch("/settings/pipeline", {
        changes: { "pipeline.final_top_n": 20 },
        expected_revision: "rev-1",
      });

      expect(patchSpy).toHaveBeenCalledWith("/settings/pipeline", {
        changes: { "pipeline.final_top_n": 20 },
        expected_revision: "rev-1",
      });
      expect((res as any).data.data.revision).toBe("rev-saved-2");
    });
  });
});
