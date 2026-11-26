# Proposal

## Why

Stage 7 currently treats selected job evidence as a global content allowlist and allows empty sections to become `Not provided.`. That can remove valid canonical education, employment, projects, certifications, and skills when only a subset of job evidence is selected. This change refines CV analysis and generation so each section has its own source of truth, tailoring behavior, minimum content, and validation rule.

## What Changes

- Define section-specific CV composition policies for Header, Summary, Education, Experience, Projects, Certifications, and Skills.
- Generate the CV from the complete canonical candidate profile plus selected job evidence. Selected evidence may tailor wording and support job-specific claims, but it SHALL NOT erase canonical profile facts.
- Replace the implicit global `approved_claims` content allowlist with a provenance-preserving composition plan that separates baseline profile records, selected job support, supported claims, unsupported requirements, render records, and hidden audit metadata.
- Make section presence source-driven: mandatory sections must be non-empty, while genuinely empty optional sections are omitted rather than rendered with placeholders.
- Remove visible `Not provided`, `N/A`, `Unknown`, and equivalent placeholders, and keep evidence IDs and provenance outside recruiter-facing content.
- Preserve the reference `mycvs_v1` Markdown grammar, empty YAML front matter, Pandoc definition-list rows, deterministic audit metadata, checksum scope, bundled renderer, and one-page/page-fit acceptance.
- Add regression coverage for mixed evidence, zero approved claims, partial requirement support, selected-only Skills, suppressed Certifications, visible evidence IDs, placeholders, definition-list formatting, and one-page PDF rendering.
- Preserve valid ranked rows when a ranking batch is partial: invalid or unscored rows remain explicit diagnostics, while usable ranked rows may continue to CV analysis and generation without being reported as a complete ranking.
- Treat finite AI compatibility scores as authoritative even when non-authoritative explanatory metadata is missing or malformed; retain the metadata defect as a diagnostic instead of discarding the score.

### Explicitly preserved behavior

- Existing ranking order, Pareto-front admission/promotion, shortlist ownership, score domain, score-state values, and ranking-to-CV handoff fail-closed requirements remain unchanged. This revision only changes downstream eligibility for usable partial ranking output and the treatment of non-authoritative explanatory metadata.
- No individual project or profile record receives extra space, stronger wording, or suppression merely because its evidence was selected; any ordering or optional-detail budget must be an explicit section policy applied symmetrically.
- Historic ranking and CV artifacts remain readable and are not rewritten or deleted.

## Capabilities

### New Capabilities

- None. This refinement updates the existing `cv-analysis-generation` change scope.

### Modified Capabilities

- `cv-analysis-generation`: Add section-specific composition, source-driven section presence, placeholder rejection, provenance separation, and PDF layout acceptance.
- `ai-ranking`: Allow usable partial ranking output to continue downstream while retaining partial diagnostics, and keep finite authoritative scores rankable when explanatory metadata is incomplete.


## Impact

- CV analysis/generation: `src/fitcv/agentic_cv_analysis.py`, `src/fitcv/agentic_cv_generation.py`, `src/fitcv/cv_generator.py`, `src/fitcv/cv_presets.py`, and stage/checkpoint persistence.
- Ranking execution and score diagnostics: `src/fitcv/ai_score.py`, `src/fitcv/pipeline_stage_artifacts.py`, `src/fitcv_cp/worker_job.py`, and the ranking/worker regression suites.
- Configuration: the active CV preset and external `myCVs` converter integration must be versioned and pinned before release.
- Tests and observability: add contract tests for invalid scores, provenance, handoff completeness, deterministic Markdown, independent status transitions, converter failure, and historic-artifact compatibility.
- Ranking order and shortlist/Pareto ownership remain out of scope; only ranking-stage continuation eligibility and explanatory-field diagnostics are refined.
- No new service or dependency is required. The existing evidence projection, stage runner, persistence, and PDF boundary remain the implementation substrate.
