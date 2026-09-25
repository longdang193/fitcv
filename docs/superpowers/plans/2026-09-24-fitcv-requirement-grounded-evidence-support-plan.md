---
layer: change
artifact_type: plan
status: completed
template_id: implementation-plan
contract_version: "1"
name: fitcv-requirement-grounded-evidence-support
targets:
  - src/fitcv/evidence.py
  - src/fitcv/contracts.py
  - src/fitcv/gap_analysis.py
  - src/fitcv/agentic_cv_analysis.py
  - src/fitcv/agentic_cv_generation.py
  - src/fitcv/cv_generator.py
  - src/fitcv/validator.py
  - src/fitcv/pipeline.py
  - config/policy/cv_analysis.yaml
  - docs/pipeline.md
  - scripts/benchmark_requirement_support.py
  - tests/test_evidence.py
  - tests/test_agentic_cv_analysis.py
  - tests/test_cv_generator.py
  - tests/test_validator.py
---

# FitCV — Requirement-Grounded Evidence Support Implementation Plan

## Goal

Turn retrieved `candidate-evidence.v1` items into requirement-specific support that is traceable, conservative, deterministic, and usable by CV analysis and generation.

P0 covers canonical required-skill requirements only. Keep candidate profile authority, evidence projection, four retrieval channels, and one global evidence budget. Do not change shortlist retrieval, add a graph database, or ask an LLM to invent support.

## Review Findings

- Current retrieval provides channel coverage, not requirement coverage. `_coverage_gain()` can select duplicate evidence for one skill while leaving another required skill uncovered.
- `_build_requirement_coverage()` conflates `compute_gap()` profile matching with evidence support and fabricates `evidence_support_count` from total selected evidence.
- `candidate-evidence.v1` is correct source projection. Requirement support must be a derived view, not another candidate-fact store.
- Semantic similarity is retrieval evidence, not verification. Docker similarity must not verify Production Kubernetes.
- Selected project and experience content is trimmed before generation. Final support IDs and source refs must come from final selected items.
- `verified` means verified against canonical, approved candidate evidence links. It does not mean externally verified real-world experience.
- Follow-up retrieval, SQLite relationship index, market intelligence, interview preparation, and shortlist RRF stay deferred.

## Implementation Outcomes

### Requirement support contract

`cv_analysis` emits one row per canonical required skill:

- `requirement_id`: deterministic ID from requirement type plus normalized canonical skill.
- `requirement`: canonical display text.
- `canonical_skill`: canonical identity used by retrieval and support mapping.
- `original_requirements`: original JD wordings collapsed into this canonical requirement.
- `requirement_type`: `required_skill`.
- `requirement_priority`: `must_have`.
- `profile_match`: `matched`, `partial`, or `missing`, preserving `compute_gap()` output.
- `retrieval_status`: `completed` or `no_candidates`.
- `pool_support`: `verified`, `relevant_unverified`, or `unsupported` for the merged retrieved pool.
- `selected_support`: `verified`, `relevant_unverified`, `not_selected`, or `unsupported` for final selected evidence.
- `pool_supporting_evidence_ids`: canonical-support IDs present in the merged pool.
- `supporting_evidence_ids`: only selected post-trim canonical-support IDs.
- `source_refs`: deduplicated refs from supporting evidence.
- `support_method`: `canonical_skill_link` or `none`.

`verified` requires explicit canonical skill linkage after existing projection rules. Channel match, text similarity, role alignment, and domain alignment alone never produce `verified`. `support_strength` remains a compatibility projection from `selected_support`: `supported` only for selected `verified`, `unsupported` for every other state. It is not a second calculation.

Pool support and selected support stay separate. A requirement with verified pool evidence but no selected evidence is a selection-budget limitation, not proof that the candidate lacks the qualification.

### Requirement-aware selection

Keep channel gain. Add requirement gain over the same merged/deduplicated pool. One item may support multiple requirements. One global `top_k` remains authoritative; no per-requirement quota.

### Downstream grounding

Generation consumes requirement support from analysis. Unsupported and relevant-but-unverified requirements remain non-authoritative. Existing `do_not_claim`, selected-evidence grounding, source traceability, and validation behavior remain intact.

## Execution Approach

- Mode: `inline sequential`
- Coordination: `none`
- Required skills: `skill-writing-plans`, `skill-using-git-worktrees`, `skill-backend-verification`, `skill-test-driven-development`, `skill-verification-before-completion`
- Isolation: `task-specific isolated worktree for implementation; current workspace only for this plan artifact`
- Commit policy: `no commits during execution`
- Preauthorized local actions: edit listed source, config, docs, and tests; run focused pytest and static checks
- User-approval actions: push, merge, publication, destructive cleanup, discard unrelated changes
- Parallel ownership: `none`
- Sequential fallback: contract/tests, verifier, selector, downstream wiring, final proof

## Task Breakdown

### Task 1: Freeze requirement and support semantics

**Purpose:** Replace implicit profile/evidence conflation with explicit support semantics.

**Task Function:** Define requirement identity, support states, and backward-compatible output behavior.

**Template Profile:** `normal`

**Selection Basis:** Ordinary contract work with existing helpers and bounded ambiguity.

**Validator Profile:** `none`

**Specification Coverage:** Separate `profile_match` from pool/selected support; preserve `candidate-evidence.v1` as candidate-fact authority; keep unsupported claims out of support and scoring.

**Required Skills:** `skill-using-git-worktrees`, `skill-test-driven-development`

**Files And Symbols:**
- Inspect: `src/fitcv/evidence.py:_collect_base_items`, `src/fitcv/evidence.py:_merge_channel_pools`, `src/fitcv/evidence.py:_extract_canonical_entities`, `src/fitcv/agentic_cv_analysis.py:_build_requirement_coverage`, `src/fitcv/gap_analysis.py:compute_gap`
- Modify: `tests/test_agentic_cv_analysis.py`, `tests/test_evidence.py`, `docs/pipeline.md`

**Dependencies:** Existing `candidate-evidence.v1` projection and `compute_gap()` behavior.

**Authority:**
- Preauthorized local actions: edit contract tests, pipeline docs, and directly related source needed to make tests executable
- Stop for: required-skill input shape cannot be derived from canonical job fields without changing normalize/enrich ownership

**Steps:**
- [x] Add fixtures for matched profile with unrelated evidence, missing profile with relevant-only evidence, direct canonical support, duplicate skill evidence, empty pool, and duplicate requirement text.
- [x] Run `git status --short --branch` and record the existing dirty-worktree boundary; isolate implementation work before source edits.
- [x] Define deterministic requirement descriptors from `required_skill_entities`, then `required_skills_canonical`, then raw `required_skills`, preserving original wording and reusing `evidence.py:_extract_canonical_entities`, `gap_analysis.py:classify_skill_match`, and `rule_filter.canonicalize_skill` only.
- [x] Preserve `matched`, `partial`, and `missing` profile states; define pool support separately from selected support without mutating job snapshots.
- [x] Document profile match, retrieval relevance, and verified support as separate facts in `docs/pipeline.md`.

**Verification:**
- [x] `uv run pytest -q tests/test_agentic_cv_analysis.py tests/test_evidence.py`
- Expected: new requirement-contract tests and existing evidence/analysis tests pass.

**Exit Criteria:** Requirement IDs, state meanings, and authority boundaries are explicit in tests and docs.

### Task 2: Build deterministic requirement support mapping

**Purpose:** Map canonical required skills to candidate evidence without treating similarity as proof.

**Task Function:** Implement requirement annotation and final support-map construction over projected evidence.

**Template Profile:** `normal`

**Selection Basis:** Deterministic mapping over existing projection and canonicalization paths.

**Validator Profile:** `none`

**Specification Coverage:** `verified` requires canonical skill linkage; `relevant_unverified` records relevance without claim authority; final support references survive trimming.

**Required Skills:** `skill-backend-verification`, `skill-test-driven-development`

**Files And Symbols:**
- Inspect: `src/fitcv/evidence.py:project_candidate_evidence`, `src/fitcv/evidence.py:_select_channel_candidates`, `src/fitcv/evidence.py:_finalize_selected_item`
- Modify: `src/fitcv/evidence.py`, `src/fitcv/agentic_cv_analysis.py`, `tests/test_evidence.py`, `tests/test_agentic_cv_analysis.py`

**Dependencies:** Task 1 contract and fixtures; projected `skills`, `evidence_id`, `source_refs`, channel metadata, and trimming.

**Authority:**
- Preauthorized local actions: edit evidence mapping, analysis mapping, and focused tests; run deterministic local checks
- Stop for: canonical skill linkage is absent from projected evidence or requires changing candidate-profile ownership

**Steps:**
- [x] Add one internal helper that builds canonical requirement descriptors from existing job fields and preserves `original_requirements`; do not add a synonym resolver.
- [x] Annotate merged-pool evidence with internal requirement IDs supported by exact canonical skill linkage; keep channel metadata separate.
- [x] Compute pool support before selection and selected support after selection plus trimming. Mark verified pool evidence that was not selected as `not_selected`, not `unsupported`.
- [x] Replace `_build_requirement_coverage()` use of `max(1, len(evidence))` with derived counts. Preserve `do_not_claim` and profile-match states from gap analysis.
- [x] Keep `requirement_coverage` as the sole authoritative analysis result; expose any compatibility fields as projections from its rows.

**Verification:**
- [x] `uv run pytest -q tests/test_evidence.py tests/test_agentic_cv_analysis.py -k "requirement or support or coverage"`
- Expected: direct support yields `verified` with exact IDs; unrelated evidence yields zero support; relevant-only evidence yields `relevant_unverified`.

**Exit Criteria:** Every required-skill row has truthful support count and traceable evidence IDs.

### Task 3: Add requirement gain to global selection

**Purpose:** Prefer evidence that increases verified requirement coverage without replacing channel-aware ranking or adding quotas.

**Task Function:** Extend existing greedy selection with requirement coverage gain.

**Template Profile:** `low`

**Selection Basis:** Narrow bounded selector change with existing deterministic tests.

**Validator Profile:** `none`

**Specification Coverage:** Preserve one global selection budget, multi-requirement evidence reuse, channel gain, and deterministic `evidence_id` tie order.

**Required Skills:** `skill-test-driven-development`

**Files And Symbols:**
- Inspect: `src/fitcv/evidence.py:_coverage_gain`, `src/fitcv/evidence.py:_select_final_evidence`, `src/fitcv/evidence.py:_EvidenceSelectionEngine`
- Modify: `src/fitcv/evidence.py`, `config/policy/cv_analysis.yaml`, `tests/test_evidence.py`

**Dependencies:** Task 2 requirement annotations.

**Authority:**
- Preauthorized local actions: edit selector, selection-policy defaults, and evidence tests
- Stop for: requirement gain needs a second budget, per-requirement quota, or shortlist retrieval change

**Steps:**
- [x] Add requirement gain using uncovered verified requirement IDs; retain channel gain and residual relevance.
- [x] Add `requirement_gain_weight` with production default `0.10`; permit `0.0` for exact baseline-mode comparison and record effective value in diagnostics.
- [x] Include requirement support IDs in selection reasons/debug samples without treating them as canonical profile facts.
- [x] Add duplicate-vs-broad fixture: `top_k=2` selects broad support plus uncovered requirements when scores are otherwise comparable.
- [x] Assert `top_k <= 0`, empty pools, deterministic ties, existing channel behavior, and exact baseline selection when `requirement_gain_weight=0.0`.

**Verification:**
- [x] `uv run pytest -q tests/test_evidence.py`
- Expected: selector contracts pass and distinct verified-requirement coverage improves under same global budget.

**Exit Criteria:** Requirement-aware selection changes only evidence selection; shortlist and projection contracts remain unchanged.

### Task 4: Wire analysis and generation grounding

**Purpose:** Make downstream analysis and CV generation consume truthful requirement support.

**Task Function:** Carry the derived map through analysis records, reuse handling, prompt grounding, and validation inputs.

**Template Profile:** `high`

**Selection Basis:** Crosses analysis, reuse, generation, and validator contracts; stale-cache risk is material.

**Validator Profile:** `none`

**Specification Coverage:** Analysis owns requirement support; generation uses selected evidence without inventing facts; reuse and failure envelopes remain valid.

**Required Skills:** `skill-backend-verification`, `skill-test-driven-development`

**Files And Symbols:**
- Inspect: `src/fitcv/agentic_cv_analysis.py:build_cv_analysis_record`, `src/fitcv/agentic_cv_analysis.py:analyze_ranked_job`, `src/fitcv/agentic_cv_generation.py:_augmented_gap_summary_from_analysis`, `src/fitcv/agentic_cv_generation.py:_build_validation_grounding_payload`, `src/fitcv/cv_generator.py:_build_generation_prompt_context`, `src/fitcv/cv_generator.py:build_structured_generation_prompt`, `src/fitcv/validator.py:AnalysisGroundingPayload`, `src/fitcv/validator.py:run_all_validations`, `src/fitcv/agentic_cv_analysis.py:_build_cv_analysis_trace_record`, `src/fitcv/pipeline.py:_build_validation_grounding_payload`
- Modify: `src/fitcv/agentic_cv_analysis.py`, `src/fitcv/agentic_cv_generation.py`, `src/fitcv/cv_generator.py`, `src/fitcv/validator.py`, `src/fitcv/pipeline.py`, `src/fitcv/contracts.py`, `tests/test_agentic_cv_analysis.py`, `tests/test_cv_generator.py`, `tests/test_validator.py`, `tests/test_pipeline.py`

**Dependencies:** Tasks 2–3 produce final support IDs and requirement-aware evidence.

**Authority:**
- Preauthorized local actions: edit analysis/generation contracts and tests; run direct boundary checks
- Stop for: consumer requires persistence/schema migration outside current analysis artifact ownership

**Steps:**
- [x] Extend existing `requirement_coverage` rows; do not introduce a separately calculated `requirement_support` field.
- [x] Keep `gap_summary` profile facts unchanged; inject support as separate derived data.
- [x] Update prompt construction to prioritize selected `verified`, omit `unsupported` and `not_selected`, and mark `relevant_unverified` non-authoritative.
- [x] Extend `AnalysisGroundingPayload` with requirement coverage and implement Guarantee A only: deterministically check required-skill claims against selected verified support. Preserve existing broader textual/semantic grounding checks; do not promise universal statement-level provenance.
- [x] Bump `CV_ANALYSIS_REUSE_SCHEMA_VERSION` to invalidate stale requirement-coverage semantics; verify generation fingerprints change through the analysis fingerprint.
- [x] Add fresh, reused, skipped-fit, empty-evidence, and prompt-output tests.

**Verification:**
- [x] `uv run pytest -q tests/test_agentic_cv_analysis.py tests/test_cv_generator.py tests/test_pipeline.py -k "analysis or evidence or requirement or grounding"`
- Expected: support survives analysis-to-generation handoff and profile match alone never creates evidence support.

**Exit Criteria:** Generation receives one truthful support map and cannot treat semantic relevance as verified proof.

### Task 5: Add observability and complete verification

**Purpose:** Prove behavior, measure tradeoffs, and document operational boundaries.

**Task Function:** Add deterministic trace fields, run focused checks, and reconcile deferred scope.

**Template Profile:** `review`

**Selection Basis:** Independent verification and benchmark review require specialized review profile.

**Validator Profile:** `none`

**Specification Coverage:** Make support observable and benchmarkable without changing shortlist retrieval or candidate-profile authority.

**Required Skills:** `skill-verification-before-completion`, `skill-backend-verification`

**Files And Symbols:**
- Inspect: `src/fitcv/agentic_cv_analysis.py:build_analysis_trace`, `src/fitcv/evidence.py:_build_retrieve_evidence_bundle_payload`
- Modify: `src/fitcv/agentic_cv_analysis.py`, `src/fitcv/evidence.py`, `tests/test_agentic_cv_analysis.py`, `tests/test_evidence.py`, `scripts/benchmark_requirement_support.py`, `docs/pipeline.md`

**Dependencies:** Tasks 1–4 complete.

**Authority:**
- Preauthorized local actions: run deterministic tests/benchmarks; edit trace fields and docs needed to describe final behavior
- Stop for: unrelated failures, changed working-tree ownership, network dependency, or policy tuning beyond this plan

**Steps:**
- [x] Record requirement count, verified count, unresolved count, selected support IDs, and requirement-gain weight in diagnostics.
- [x] Assert verified-support precision, direct-link recall, false-positive prevention, and distinct-requirement coverage.
- [x] Add a deterministic paired benchmark with identical profile, job, budget, embeddings, ranking inputs, and generation settings: baseline four-channel selector versus treatment with requirement gain.
- [x] Measure verified coverage, incorrect assignments, duplicate evidence, retrieved count, provider calls, input tokens, retrieval latency, end-to-end CV latency, and grounding failures separately.
- [x] Record current `git rev-parse HEAD` as benchmark baseline; current baseline is `7263fbafd1b759ace235e2cc90d20ddd99062dbe`.
- [x] Run focused suites, then relevant full unit suites; separate unrelated failures.
- [x] Review diff and confirm no edits touch shortlist vector retrieval, candidate profile authority, persistence schema, or unrelated user changes.

**Verification:**
- `uv run pytest -q tests/test_evidence.py tests/test_agentic_cv_analysis.py tests/test_cv_generator.py tests/test_pipeline.py`
- `uv run pytest -q tests/test_gap_analysis.py tests/test_embeddings.py tests/test_candidate_profile_ingest.py`
- `uv run python scripts/benchmark_requirement_support.py --weight 0.0 --output .tmp/benchmarks/requirement-support/baseline.json`
- `uv run python scripts/benchmark_requirement_support.py --weight 0.10 --output .tmp/benchmarks/requirement-support/treatment.json`
- Expected: fresh tests prove direct support, false-positive prevention, global-budget selection, downstream grounding, and deterministic diagnostics.

**Exit Criteria:** Evidence supports implementation and no deferred capability entered patch.

## Verification

- `uv run pytest -q tests/test_evidence.py tests/test_agentic_cv_analysis.py tests/test_cv_generator.py tests/test_pipeline.py`
- `uv run pytest -q tests/test_gap_analysis.py tests/test_embeddings.py tests/test_candidate_profile_ingest.py`
- `uv run python scripts/benchmark_requirement_support.py --weight 0.0 --output .tmp/benchmarks/requirement-support/baseline.json`
- `uv run python scripts/benchmark_requirement_support.py --weight 0.10 --output .tmp/benchmarks/requirement-support/treatment.json`
- `git diff --check`
- `git status --short`; preserve unrelated existing changes.
- Review `docs/pipeline.md` against source and test contracts.

## Completion Criteria

1. `cv_analysis` preserves `matched`, `partial`, and `missing` profile states while separating pool support from selected support.
2. Requirement identities reuse existing canonicalization and retain original JD wording.
3. Support IDs and source refs point only to selected post-trim `candidate-evidence.v1` items; pool-only support is not reported as a candidate gap.
4. `requirement_coverage` is the sole authoritative requirement-support result.
5. Global selection prefers uncovered verified requirements without per-requirement quotas, and weight `0.0` reproduces baseline selection exactly.
6. Guarantee A validates requirement-specific skill support; broader grounding checks remain unchanged and universal statement-level provenance is not claimed.
7. Reuse schema version invalidates stale analysis semantics; generation fingerprints remain downstream-consistent.
8. Paired baseline/treatment measurement reports quality and latency separately.
9. Projection, gap semantics, fit gates, reuse, and vector-only shortlist contracts remain intact.
10. Focused and relevant regression suites pass with fresh output.
11. Follow-up retrieval, SQLite relationship index, market intelligence, interview preparation, and shortlist RRF remain deferred.

## Verification Results

- Worktree: `C:\Users\HOANG PHI LONG DANG\.codex\worktrees\fitcv-requirement-grounded-evidence\JOB-PROJECT`.
- Base and verified `HEAD`: `7263fbafd1b759ace235e2cc90d20ddd99062dbe`; no commit created.
- `uv run pytest -q tests/test_evidence.py tests/test_agentic_cv_analysis.py tests/test_cv_generator.py tests/test_pipeline.py tests/test_validator.py`: `319 passed`.
- `uv run pytest -q tests/test_agentic_cv_analysis.py::test_real_canonical_profile_emits_requirement_coverage_without_mocks`: `1 passed`.
- `uv run pytest -q tests/test_gap_analysis.py tests/test_embeddings.py tests/test_candidate_profile_ingest.py`: `67 passed, 1 skipped`.
- Paired benchmark: weight `0.0` verified coverage `1`; weight `0.10` verified coverage `2`; duplicate evidence `0`; incorrect assignments `0`; grounding failures `0`.
- `git diff --check`: passed.
- Task-owned benchmark outputs remain under `.tmp/benchmarks/requirement-support/` for audit and are untracked. Unrelated main-workspace changes preserved.
