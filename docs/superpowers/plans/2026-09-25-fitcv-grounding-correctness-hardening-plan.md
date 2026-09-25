---
layer: change
artifact_type: plan
status: completed
template_id: implementation-plan
contract_version: "1"
name: fitcv-grounding-correctness-hardening
targets:
  - src/fitcv/evidence.py
  - src/fitcv/agentic_cv_analysis.py
  - src/fitcv/validator.py
  - src/fitcv/contracts.py
  - src/fitcv/cv_generator.py
  - docs/pipeline.md
  - scripts/benchmark_requirement_support.py
  - tests/test_evidence.py
  - tests/test_agentic_cv_analysis.py
  - tests/test_validator.py
  - tests/test_cv_generator.py
  - tests/test_pipeline.py
  - tests/test_pipeline_agentic_late_stage.py
---

# FitCV — Grounding Correctness Hardening Implementation Plan

## Goal

Close remaining requirement-grounding correctness gaps after PR #46 without
adding new retrieval infrastructure. Preserve `candidate-evidence.v1` as the
candidate-fact authority, keep one global evidence budget, and make every
requirement-to-evidence relationship identity-safe, reuse-safe, and validated
at the structured CV boundary.

## Review Verdict

The supplied verdict is accepted with three scope corrections:

- Requirement identity, evidence-sensitive reuse, and structured validation are
  P0 correctness work and must land before retrieval optimization.
- Retrieval recall is a separate measurement experiment. Do not change channel
  truncation or add follow-up retrieval in this correctness patch.
- The declared `pool_support` states must match emitted behavior. Prefer a
  smaller truthful contract over adding an unneeded relevance classifier.

Full-suite failures remain a separate baseline question. Compare the same
  failing test IDs at parent `7263fbafd1b759ace235e2cc90d20ddd99062dbe` and
  merged PR head `90f20f61c4cd11d2f0efbf12ab4209029e3bfe4c` before attributing
  them to this initiative.

## Implementation Outcomes

### Identity-safe requirement support

`build_required_skill_descriptors()` never pairs independently produced raw and
canonical arrays by position. Validated entity mappings remain authoritative;
raw requirements are canonicalized independently when entity mappings are
absent; canonical-only input remains supported. Duplicate aliases collapse into
one requirement while preserving original wording. Nontechnical requirements
excluded by existing enrichment policy remain excluded from required-skill
support.

### Reuse-safe evidence analysis

CV-analysis reuse identity includes the canonical evidence projection that the
analysis consumes. Education, certifications, volunteering, source references,
and approved claim-to-evidence links invalidate reuse when they change. One
projection and one projection fingerprint are shared by reuse validation and
fresh evidence retrieval for each analysis attempt.

### Structured, ID-verified grounding

Requirement grounding uses structured CV skill items when available and keeps
Markdown extraction only as a legacy fallback. A `verified` requirement row is
authoritative only when each supporting ID resolves to final selected evidence
whose canonical skill links contain that requirement. Invalid IDs, mismatched
skill links, and unsupported claims fail validation.

### Truthful diagnostics and reproducible measurement

Evidence support diagnostics describe only states the implementation emits.
The benchmark calculates assignment correctness from expected pairs, labels
token counts as estimates, separates retrieval/prompt/validation latency, and
keeps selector comparisons separate from correctness comparisons.

## Execution Approach

- Mode: `inline sequential`
- Coordination: `none`
- Required skills: `skill-systematic-debugging`, `skill-test-driven-development`, `skill-backend-verification`, `skill-using-git-worktrees`, `skill-verification-before-completion`
- Isolation: `task-specific isolated worktree; current dirty main remains untouched`
- Commit policy: `no commits during execution`
- Preauthorized local actions: edit listed source, tests, docs, and benchmark; run focused tests, baseline comparisons, and static checks
- User-approval actions: push, merge, publication, destructive cleanup, discard unrelated changes
- Parallel ownership: `none; shared contracts and validation require ordered edits`
- Sequential fallback: `identity contract → reuse identity → structured validation → diagnostics/benchmark → final proof`

## Task Breakdown

### Task 1: Remove positional requirement identity fallback

**Purpose:** Prevent reordered or incomplete requirement arrays from assigning
the wrong raw wording, canonical skill, profile match, or evidence IDs.

**Task Function:** Harden requirement descriptor construction while preserving
technical-skill boundary and existing canonicalization policy.

**Template Profile:** `normal`

**Selection Basis:** Bounded contract correction with existing helpers and
moderate edge-case risk.

**Validator Profile:** `none`

**Specification Coverage:** Identity-safe requirement support outcome.

**Required Skills:** `skill-systematic-debugging`, `skill-test-driven-development`

**Files And Symbols:**
- Inspect: `src/fitcv/evidence.py:build_required_skill_descriptors`, `src/fitcv/evidence.py:_extract_canonical_entities`, `src/fitcv/rule_filter.py:canonicalize_skill`, `src/fitcv/agentic_cv_analysis.py:_build_requirement_coverage`
- Modify: `src/fitcv/evidence.py:build_required_skill_descriptors`, `tests/test_evidence.py`, `tests/test_agentic_cv_analysis.py`, `docs/pipeline.md`
- Verify: `src/fitcv/evidence.py`, `src/fitcv/agentic_cv_analysis.py`

**Dependencies:** PR #46 requirement-support schema; existing enrichment rules
for technical required skills.

**Authority:**
- Preauthorized local actions: edit requirement descriptor code, directly related tests, and contract documentation
- Stop for: canonical-skill ownership is unclear, input shape changes outside listed files, or nontechnical JD requirements would be promoted into required skills

**Steps:**
- [x] Step 1: Add failing tests for reordered raw/canonical arrays, alias deduplication, canonical-only input, duplicate raw wording, incomplete entity rows, and excluded nontechnical requirements.
- [x] Step 2: Keep valid `required_skill_entities` as first authority; otherwise canonicalize each raw skill independently and group by canonical identity; use canonical-only descriptors when raw wording is absent.
- [x] Step 3: Preserve `original_requirements`, deterministic `requirement_id`, and downstream `profile_match` semantics without positional assumptions.
- [x] Step 4: Update the requirement-support contract documentation and run focused tests.

**Verification:**
- [x] `uv run pytest -q tests/test_evidence.py tests/test_agentic_cv_analysis.py`
- Expected: new identity cases fail before implementation and pass after it; existing support rows remain stable.

**Exit Criteria:** No descriptor can associate a raw requirement with a canonical skill solely because both occupy the same array index.

### Task 2: Bind analysis reuse to one canonical evidence projection

**Purpose:** Prevent stale CV analysis when evidence-bearing profile sections or
approved evidence links change after a previous analysis was stored.

**Task Function:** Make projection identity part of analysis reuse and share one
projection result between reuse validation and retrieval.

**Template Profile:** `normal`

**Selection Basis:** Cross-function lifecycle change with cache and reuse risk.

**Validator Profile:** `none`

**Specification Coverage:** Reuse-safe evidence analysis outcome.

**Required Skills:** `skill-systematic-debugging`, `skill-test-driven-development`, `skill-backend-verification`

**Files And Symbols:**
- Inspect: `src/fitcv/evidence.py:_cv_analysis_profile_payload`, `src/fitcv/evidence.py:build_cv_analysis_input_fingerprint`, `src/fitcv/evidence.py:project_candidate_evidence`, `src/fitcv/evidence.py:retrieve_evidence_bundle`, `src/fitcv/agentic_cv_analysis.py:analyze_ranked_job`, `src/fitcv/contracts.py:CV_ANALYSIS_REUSE_SCHEMA_VERSION`
- Modify: `src/fitcv/evidence.py`, `src/fitcv/agentic_cv_analysis.py`, `src/fitcv/contracts.py`, `tests/test_evidence.py`, `tests/test_agentic_cv_analysis.py`
- Verify: `src/fitcv/pipeline.py` reuse and retrieval handoff paths

**Dependencies:** Task 1 descriptor contract; existing `projection_fingerprint`
field in retrieval diagnostics.

**Authority:**
- Preauthorized local actions: edit reuse fingerprinting, projection handoff, schema version, and focused tests
- Stop for: cached `_projected_evidence_pool` has no trustworthy source revision, or fixing it requires changing persistence ownership outside this plan

**Steps:**
- [x] Step 1: Add failing tests showing education, certifications, volunteering, source references, and approved claim-to-evidence changes reject exact-match reuse; unchanged inputs still reuse.
- [x] Step 2: Add one projection result/fingerprint handoff for each analysis attempt. Reuse validation and fresh retrieval consume that same projection rather than independently traversing the profile.
- [x] Step 3: Include projection identity in `build_cv_analysis_input_fingerprint()` and bump `CV_ANALYSIS_REUSE_SCHEMA_VERSION` only if the persisted contract changes.
- [x] Step 4: Reject or recompute cached `_projected_evidence_pool` when its associated candidate/projection identity is absent or mismatched; preserve compatibility for uncached profiles.
- [x] Step 5: Verify reused and fresh records expose matching projection fingerprints and no stale support map survives a source change.

**Verification:**
- [x] `uv run pytest -q tests/test_evidence.py tests/test_agentic_cv_analysis.py tests/test_pipeline.py`
- Expected: unchanged profile/job reuses exact record; every changed evidence-bearing input forces fresh analysis and retrieval.

**Exit Criteria:** Analysis reuse cannot remain valid when canonical evidence projection changes, and fresh analysis performs one shared projection per attempt.

### Task 3: Validate requirement grounding from structured claims and selected IDs

**Purpose:** Stop formatting-dependent Markdown parsing or forged support labels
from authorizing unsupported required-skill claims.

**Task Function:** Centralize normalized claimed-skill extraction and verify
requirement rows against final selected evidence.

**Template Profile:** `normal`

**Selection Basis:** Material backend validation behavior with security-like
false-authorization risk.

**Validator Profile:** `none`

**Specification Coverage:** Structured, ID-verified grounding outcome.

**Required Skills:** `skill-systematic-debugging`, `skill-test-driven-development`, `skill-backend-verification`

**Files And Symbols:**
- Inspect: `src/fitcv/validator.py:AnalysisGroundingPayload`, `src/fitcv/validator.py:_check_requirement_grounding`, `src/fitcv/validator.py:_extract_skill_section_tokens`, `src/fitcv/validator.py:_normalize_analysis_grounding`, `src/fitcv/validator.py:run_all_validations`, `src/fitcv/agentic_cv_generation.py:_build_validation_grounding_payload`, `src/fitcv/cv_generator.py:build_structured_generation_prompt`
- Modify: `src/fitcv/validator.py`, `src/fitcv/agentic_cv_generation.py`, `src/fitcv/cv_generator.py`, `tests/test_validator.py`, `tests/test_cv_generator.py`, `tests/test_pipeline_agentic_late_stage.py`, `tests/test_pipeline.py`
- Verify: generation-to-validation payload construction and final selected evidence projection

**Dependencies:** Tasks 1 and 2; existing structured CV schema and selected
evidence trimming behavior.

**Authority:**
- Preauthorized local actions: edit grounding normalization, validation payload wiring, prompt contract, and regression tests
- Stop for: structured CV schema cannot expose skill items without changing its canonical owner, or legacy Markdown fallback behavior would be removed

**Steps:**
- [x] Step 1: Add failing tests for `SQL · Python`, Markdown bullets, and structured skill items; add forged `verified` rows whose IDs point to wrong or unselected evidence.
- [x] Step 2: Normalize structured skill groups first; use existing Markdown extraction only when structured output is unavailable.
- [x] Step 3: Build a selected-evidence ID map and canonical skill set. Require every `verified` requirement row to resolve all supporting IDs to final selected items carrying the same canonical requirement link.
- [x] Step 4: Make `_check_requirement_grounding()` consume the normalized claims and verified support result; preserve profile fallback when no analysis grounding exists.
- [x] Step 5: Keep unsupported and `relevant_unverified` requirements non-authoritative in generation prompts and validation.

**Verification:**
- [x] `uv run pytest -q tests/test_validator.py tests/test_cv_generator.py tests/test_pipeline_agentic_late_stage.py tests/test_pipeline.py`
- Expected: matching structured claims pass; unsupported, wrong-ID, unselected-ID, and wrong-canonical-ID claims fail deterministically.

**Exit Criteria:** A requirement claim cannot pass solely because `selected_support == "verified"` or because Markdown happened to tokenize favorably.

### Task 4: Reconcile diagnostics and benchmark metrics

**Purpose:** Make support diagnostics and measurement claims match actual
behavior, without adding a new relevance classifier or evaluation platform.

**Task Function:** Narrow emitted contracts where needed and make benchmark
metrics independently calculated and attributable.

**Template Profile:** `normal`

**Selection Basis:** Bounded contract/documentation and measurement correction.

**Validator Profile:** `none`

**Specification Coverage:** Truthful diagnostics and reproducible measurement
outcome.

**Required Skills:** `skill-test-driven-development`, `skill-verification-before-completion`

**Files And Symbols:**
- Inspect: `src/fitcv/evidence.py:_build_retrieve_evidence_bundle_payload`, `docs/pipeline.md`, `scripts/benchmark_requirement_support.py`
- Modify: `src/fitcv/evidence.py` or its contract docs, `docs/pipeline.md`, `scripts/benchmark_requirement_support.py`, and focused benchmark tests if present
- Verify: benchmark output JSON and support-state assertions

**Dependencies:** Tasks 1–3; final selected-support semantics are stable.

**Authority:**
- Preauthorized local actions: edit diagnostic labels, benchmark calculations, and measurement documentation
- Stop for: metric correctness needs production telemetry or external datasets not available in the repository

**Steps:**
- [x] Step 1: Choose truthful `pool_support` states actually needed by consumers; remove undocumented unused states instead of adding speculative relevance logic.
- [x] Step 2: Add expected requirement-to-evidence pairs to the deterministic fixture and calculate incorrect assignments from actual output.
- [x] Step 3: Rename token and latency metrics to reflect estimates and measured retrieval/prompt/validation phases; keep generation marked prompt-only.
- [x] Step 4: Emit separate comparison records for parent-vs-hardened correctness and selector weight `0.0` vs `0.10`.

**Verification:**
- [x] `uv run python scripts/benchmark_requirement_support.py --weight 0 --output .tmp/benchmark-baseline.json`
- [x] `uv run python scripts/benchmark_requirement_support.py --weight 0.10 --output .tmp/benchmark-requirement-aware.json`
- Expected: assignment errors derive from fixture expectations; coverage and selector effects remain separately attributable; no grounding failures.

**Exit Criteria:** Benchmark output cannot report hardcoded correctness or call prompt-only timing end-to-end generation latency.

### Task 5: Measure retrieval recall as a separate follow-up experiment

**Purpose:** Identify whether valid requirement support is lost in channel
truncation or global selection before changing retrieval behavior.

**Task Function:** Add deterministic observability for canonical-pool,
retrieved-pool, and selected-pool support loss.

**Template Profile:** `normal`

**Selection Basis:** Measurement-first performance work; no production behavior
change until evidence identifies a bottleneck.

**Validator Profile:** `none`

**Specification Coverage:** P1 retrieval efficiency and recall roadmap item.

**Required Skills:** `skill-performance-optimization`, `skill-test-driven-development`

**Files And Symbols:**
- Inspect: `src/fitcv/evidence.py:_collect_base_items`, `src/fitcv/evidence.py:_select_channel_candidates`, `src/fitcv/evidence.py:_EvidenceSelectionEngine`, `src/fitcv/evidence.py:_annotate_requirement_support`
- Modify: benchmark/diagnostic surfaces only after Tasks 1–4 pass; do not change retrieval defaults in this plan
- Verify: fixed fixtures with canonical support deliberately ranked fifth in every channel

**Dependencies:** Tasks 1–4 complete; requirement identity and support IDs are trusted.

**Authority:**
- Preauthorized local actions: add bounded measurement fields and experiment fixtures without changing production selection defaults
- Stop for: any proposed bypass of channel truncation, increased generation budget, or agentic follow-up retrieval

**Steps:**
- [x] Step 1: Record support coverage at canonical pool, merged retrieved pool, and final selected evidence layers.
- [x] Step 2: Measure repeated canonicalization cost in `_annotate_requirement_support()` before optimizing.
- [x] Step 3: Compare current channel pool size with a bounded larger pool and, only if justified, a small direct-link candidate union.
- [x] Step 4: Report recall, latency, and context-size deltas; leave production defaults unchanged until a separate approved plan exists.

**Verification:**
- [x] Focused fixture run reports each support loss layer and stable final `top_k`.
- Expected: experiment distinguishes retrieval loss from selection-budget loss without changing generation context budget.

**Exit Criteria:** Follow-up optimization has measured evidence and remains independently attributable from correctness fixes.

## Verification

- `uv run pytest -q tests/test_evidence.py tests/test_agentic_cv_analysis.py tests/test_validator.py tests/test_cv_generator.py tests/test_pipeline.py tests/test_pipeline_agentic_late_stage.py`
- `uv run python scripts/benchmark_requirement_support.py --weight 0 --output .tmp/benchmark-baseline.json`
- `uv run python scripts/benchmark_requirement_support.py --weight 0.10 --output .tmp/benchmark-requirement-aware.json`
- `git diff --check`
- Compare the recorded failing test IDs at parent `7263fbafd1b759ace235e2cc90d20ddd99062dbe` and merged head `90f20f61c4cd11d2f0efbf12ab4209029e3bfe4c`; classify, do not silently absorb, unrelated baseline failures.
- Run direct backend boundary probes for fresh analysis, exact reuse, changed evidence invalidation, selected-ID mismatch rejection, and structured-skill fallback.

## Completion Criteria

The plan is ready for completion verification when:

1. Reordered, missing, alias, duplicate, and canonical-only requirement inputs produce correct stable identities.
2. Changes to every evidence-bearing profile section invalidate analysis reuse; unchanged inputs retain exact reuse.
3. Reuse validation and retrieval share one projection result and fingerprint per analysis attempt.
4. Structured skills are preferred for grounding, Markdown fallback remains compatible, and verified support IDs resolve to final selected evidence with matching canonical skills.
5. Diagnostic states and benchmark metrics match emitted behavior and independently calculated expectations.
6. Retrieval recall measurements are recorded separately and no unapproved retrieval behavior change is included.
7. Focused tests and backend probes pass; full-suite failures are classified against both parent and merged heads.
8. No unrelated dirty files are staged, rewritten, discarded, or cleaned.

## Completion Evidence

- Focused suite: 347 passed.
- Benchmark weights 0 and 0.10: passed; metrics now distinguish estimated tokens and retrieval/prompt/validation phases.
- Recall probe: canonical, retrieved, and selected support layers plus annotation cost, latency, and context-size observations; production defaults unchanged.
- Parent 7263fbafd1b759ace235e2cc90d20ddd99062dbe and merged 90f20f61c4cd11d2f0efbf12ab4209029e3bfe4c each retain same 38 baseline failures; current worktree retains same IDs.
- Direct backend probes: fresh analysis, exact reuse, changed evidence invalidation, valid structured support, and wrong-ID rejection passed.
