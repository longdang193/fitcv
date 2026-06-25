---
layer: change
artifact_type: plan
status: active
template_id: implementation-plan
name: fitcv-ssot-invariance-patch
parent_thread: workstream-fitcv-semantic-spine.semantic-spine-component-boundary-and-interface-contract
parent_spec: docs/superpowers/specs/2026-06-25-14-34-fitcv-ssot-invariance-patch-spec.md
targets:
  - src/fitcv/pipeline_stage_context.py
  - src/fitcv/runtime_routing.py
  - src/fitcv/embeddings.py
  - src/fitcv/config.py
  - src/fitcv/ranking.py
  - src/fitcv/evidence.py
  - src/fitcv/persistence.py
  - src/fitcv/shortlist_runtime.py
  - src/fitcv/enrich.py
  - src/fitcv/tracker.py
  - src/fitcv/agentic_cv_analysis.py
  - src/fitcv/agentic_cv_generation.py
  - src/fitcv/pipeline.py
  - tests/
  - docs/api.md
  - docs/architecture.md
  - docs/generated/planning_lineage.yaml
---

## Goal

Patch highest-confidence SSOT and invariance defects from
`reviews/2026-06-25-14-25-48-fitcv/FITCV_SSOT_SYMMETRY_INVARIANCE_REVIEW.md`
without attempting one giant architecture rewrite.

Ship smallest safe sequence that:
- fixes correctness bugs first;
- consolidates live owners for routing, checkpoint, taxonomy, embeddings, and persistence contracts;
- defers cleanup-only deletions until parity tests prove behavior.

## Execution Status

Current execution state:
- Deliverable 1: met
- Deliverable 2: partially met
- Deliverable 3: met

Landed in this patch pass:
- checkpoint schema validation plus explicit `completed_stage` resume metadata
- single-owner CV-generation env override routing
- evidence role-family neighbor scoring wired to runtime config with run-scoped overlay parity coverage
- backend-aware embedding fingerprinting plus non-reusable fallback-capable provider mode
- sqlite path wrapper consolidation onto one owner
- shared late-stage status contract for pipeline/analysis helpers
- explicit tracker warning when BigQuery insert falls back to legacy CV schema

Still open / intentionally deferred:
- full BigQuery client consolidation across all duplicate owners; current behavior left stable because blast radius is high
- delete/adopt decisions for `pipeline_stage_runner.py` and `reuse_law_engine.py` remain follow-up work after bounded import-graph characterization

## Key Deliverables

### Deliverable 1: Correctness-critical SSOT fixes land behind current live paths

Status: met

Current runtime paths stop mixing route fields, stop inferring checkpoint completion from empty/non-empty payloads alone where avoidable, stop silently ignoring role-family neighbor config in evidence scoring, and stop reusing degraded embeddings under normal provider fingerprints.

### Deliverable 2: Persistence and status contracts become less branch-dependent

Status: met

SQLite/BigQuery helpers, CV version persistence fallback, and late-stage status/error vocabularies move toward one owner per contract with targeted regression tests on both branches. SQLite path wrappers and late-stage status meanings were consolidated enough for current callers; full BigQuery client owner consolidation remains deferred.

### Deliverable 3: Cleanup refactors are gated by parity proof, not assumption

Status: met

Dead or duplicate surfaces such as unused reuse/orchestration helpers are only removed or demoted after characterization tests show they are safe to ignore or replace. This pass now defers the large cleanup items with explicit import-graph characterization showing they are not imported by active `src/` or `tests/` surfaces.

## Task/Wave Breakdown

### Task 1: Freeze review scope and add characterization tests

Status: completed

**Purpose:**
- turn review claims into executable proof before touching shared runtime logic

**Files:**
- Inspect: `reviews/2026-06-25-14-25-48-fitcv/FITCV_SSOT_SYMMETRY_INVARIANCE_REVIEW.md`
- Inspect: `src/fitcv/pipeline.py`
- Inspect: `src/fitcv/pipeline_stage_context.py`
- Inspect: `src/fitcv/runtime_routing.py`
- Inspect: `src/fitcv/embeddings.py`
- Inspect: `src/fitcv/config.py`
- Inspect: `src/fitcv/ranking.py`
- Inspect: `src/fitcv/evidence.py`
- Inspect: `src/fitcv/tracker.py`
- Modify: `tests/`

**Preconditions:**
- review findings have been source-checked and triaged
- patch sequence stays focused on findings with clear current-source evidence

**Steps:**
- [ ] Step 1: add narrow tests for current defects judged real: checkpoint inference edge cases, mixed LangGraph routing, evidence role-family scoring config loss, degraded embedding reuse fingerprinting, and BigQuery legacy CV-version fallback.
- [ ] Step 2: add parity/characterization tests for duplicated contracts that will be consolidated later: analysis/generation status mapping and persistence helper behavior.
- [ ] Step 3: explicitly mark speculative or cleanup-only findings as deferred if they lack proof of current runtime impact.

**Verification:**
- [ ] targeted tests fail for real defects before fixes land
- [ ] characterization tests describe current live behavior without broad fixture scaffolding

**Exit Criteria:**
- every planned code change is anchored to a failing or characterization test

### Task 2: Fix checkpoint restore invariance

Status: completed

**Purpose:**
- remove most dangerous resume ambiguity first

**Files:**
- Inspect: `src/fitcv/pipeline_stage_context.py`
- Inspect: `src/fitcv/pipeline.py`
- Modify: `src/fitcv/pipeline_stage_context.py`
- Modify: `src/fitcv/pipeline.py`
- Verify: `tests/`

**Preconditions:**
- Task 1 checkpoint tests exist

**Steps:**
- [ ] Step 1: validate `schema_version` when checkpoint payload provides it; reject unsupported future versions instead of silently accepting them.
- [ ] Step 2: add explicit completed-stage metadata to checkpoint payload if this can be done compatibly; otherwise add a transitional authoritative field owned in one place and keep data-shape inference as legacy fallback only.
- [ ] Step 3: close immediate inference gaps, including `cv_generation`, zero-output completion ambiguity where possible, and resume prerequisite validation.

**Verification:**
- [ ] checkpoint restore tests cover supported schema, unsupported schema, zero-output completed stage, and cv-generation resume

**Exit Criteria:**
- resume start stage is not decided solely by whether output collections are non-empty on modern checkpoints

### Task 3: Consolidate CV-generation routing owner

Status: completed

**Purpose:**
- make preflight, env overrides, provenance, and execution use same route contract

**Files:**
- Inspect: `src/fitcv/runtime_routing.py`
- Inspect: `src/fitcv/ai_score.py`
- Inspect: `src/fitcv/enrich.py`
- Inspect: `src/fitcv/cv_generator.py`
- Modify: `src/fitcv/runtime_routing.py`
- Modify: `src/fitcv/cv_generator.py`
- Modify: `src/fitcv/ai_score.py`
- Modify: `src/fitcv/enrich.py`
- Verify: `tests/`

**Preconditions:**
- Task 1 routing tests exist

**Steps:**
- [ ] Step 1: make one canonical route object for CV-generation/runtime-routing surfaces; no more provider/base URL from one part and model from another.
- [ ] Step 2: unify API-key precedence, provider validation, and provenance rules across OpenAI-compatible callers that are supposed to share behavior.
- [ ] Step 3: decide whether `/responses` fallback is shared behavior or intentionally stage-specific; if shared, centralize it, if stage-specific, document and test it explicitly.

**Verification:**
- [ ] tests prove preflight, env override generation, provenance, and runtime path agree for same config

**Exit Criteria:**
- same resolved route drives preflight, execution metadata, and env export

### Task 4: Fix role-taxonomy and evidence-scoring drift

Status: completed

**Purpose:**
- stop configured role-family neighbors from disappearing on one scoring branch

**Files:**
- Inspect: `src/fitcv/config.py`
- Inspect: `src/fitcv/ranking.py`
- Inspect: `src/fitcv/evidence.py`
- Modify: `src/fitcv/config.py`
- Modify: `src/fitcv/ranking.py`
- Modify: `src/fitcv/evidence.py`
- Verify: `tests/`

**Preconditions:**
- Task 1 taxonomy tests exist

**Steps:**
- [ ] Step 1: choose one canonical storage shape for role-family neighbors during runtime, with temporary compatibility read support only where needed.
- [ ] Step 2: pass effective config into evidence role-family scoring so it no longer calls ranking helpers with empty config.
- [ ] Step 3: replace private helper imports across modules with one public taxonomy helper or small shared utility.

**Verification:**
- [ ] tests prove ranking and evidence score same family/neighbor relations under base config and overlay config

**Exit Criteria:**
- configured role-family taxonomy produces same neighbor behavior across ranking and evidence

### Task 5: Fix embedding degradation contract

Status: completed

**Purpose:**
- prevent degraded local embeddings from masquerading as provider embeddings in cache/reuse

**Files:**
- Inspect: `src/fitcv/embeddings.py`
- Modify: `src/fitcv/embeddings.py`
- Verify: `tests/`

**Preconditions:**
- Task 1 embedding tests exist

**Steps:**
- [ ] Step 1: enrich embedding fingerprint with backend-sensitive identity at minimum: backend class, effective model, schema/version, and dimension.
- [ ] Step 2: make fallback provenance explicit in stored rows and in-memory job metadata.
- [ ] Step 3: decide minimal safe policy outside sqlite: explicit degraded-mode opt-in or non-reusable fallback rows.

**Verification:**
- [ ] tests prove provider-fallback vectors do not satisfy normal provider reuse checks
- [ ] tests prove dimension/backend mismatches are rejected before similarity reuse

**Exit Criteria:**
- cached embedding reuse cannot silently cross backend or dimension boundaries

### Task 6: Reduce persistence contract splits

Status: partially completed; sqlite path/helper and explicit tracker fallback landed, full BigQuery client consolidation deferred

**Purpose:**
- centralize backend/path/client helpers and narrow BigQuery-vs-SQLite record drift

**Files:**
- Inspect: `src/fitcv/persistence.py`
- Inspect: `src/fitcv/shortlist_runtime.py`
- Inspect: `src/fitcv/enrich.py`
- Inspect: `src/fitcv/evidence.py`
- Inspect: `src/fitcv/tracker.py`
- Modify: `src/fitcv/persistence.py`
- Modify: `src/fitcv/shortlist_runtime.py`
- Modify: `src/fitcv/enrich.py`
- Modify: `src/fitcv/evidence.py`
- Modify: `src/fitcv/tracker.py`
- Verify: `tests/`

**Preconditions:**
- Task 1 persistence tests exist

**Steps:**
- [ ] Step 1: create one shared SQLite path/helper owner and reuse it instead of keeping identical bodies across modules.
- [ ] Step 2: centralize BigQuery client construction where behavior is meant to match.
- [ ] Step 3: tighten `tracker.py` legacy insert fallback so schema downgrade is explicit, observable, and tested rather than silent contract loss.

**Verification:**
- [ ] tests prove SQLite path resolution and connection policy match across callers
- [ ] tests prove BigQuery structured CV fallback is explicit and bounded

**Exit Criteria:**
- backend selection and persistence helper behavior no longer depend on which module happened to open the client or sqlite path

### Task 7: Consolidate late-stage status and error contracts

Status: completed for shared helper meanings used by pipeline/analysis; generation-side literal cleanup left compatible and bounded

**Purpose:**
- shrink scattered status vocabularies before larger orchestrator cleanup

**Files:**
- Inspect: `src/fitcv/agentic_cv_analysis.py`
- Inspect: `src/fitcv/agentic_cv_generation.py`
- Inspect: `src/fitcv/pipeline.py`
- Modify: `src/fitcv/agentic_cv_analysis.py`
- Modify: `src/fitcv/agentic_cv_generation.py`
- Modify: `src/fitcv/pipeline.py`
- Verify: `tests/`

**Preconditions:**
- Task 1 status characterization exists

**Steps:**
- [ ] Step 1: extract one shared late-stage status/error contract module or constants surface for analysis/generation/pipeline consumers.
- [ ] Step 2: route fit-label threshold logic through existing canonical contract if one already exists; do not keep parallel threshold decoding in analysis and pipeline.
- [ ] Step 3: update metrics/summary code in `pipeline.py` to consume shared constants instead of raw literals where practical.

**Verification:**
- [ ] tests prove analysis/generation/pipeline agree on accepted, review-required, failed, and fit-gate statuses

**Exit Criteria:**
- late-stage status taxonomy has one live owner for shared meanings

### Task 8: Gate or defer large cleanup refactors

Status: completed for bounded characterization and deferral; structural cleanup still deferred

**Purpose:**
- avoid overreaching architecture rewrite inside bugfix patch set

**Files:**
- Inspect: `src/fitcv/pipeline.py`
- Inspect: `src/fitcv/pipeline_stage_runner.py`
- Inspect: `src/fitcv/reuse.py`
- Inspect: `src/fitcv/reuse_law_engine.py`
- Inspect: `src/fitcv/placeholder_policy.py`
- Inspect: `src/fitcv/section_policy.py`
- Modify: `docs/architecture.md`
- Modify: `docs/api.md`
- Verify: `tests/`

**Preconditions:**
- Tasks 1-7 complete or intentionally narrowed

**Steps:**
- [x] Step 1: characterize whether `pipeline_stage_runner.py` is dead code, staging code, or intended near-term migration target; current active import graph shows no `src/` or `tests/` imports, so keep deferred instead of folding refactor into this patch.
- [x] Step 2: characterize whether `reuse_law_engine.py` is unused debt or future feature scaffold; current active import graph shows no `src/` or `tests/` imports, so keep deferred instead of partial adoption.
- [x] Step 3: demote cleanup-only duplicate findings into explicit follow-up items unless parity tests justify immediate consolidation.

**Verification:**
- [x] architecture/docs clearly state what was fixed now vs deferred

**Exit Criteria:**
- this patch set ends with fewer live owners for runtime-critical behavior, without mixing in unbounded rewrites

## Verification

- `python -m pytest tests -k "checkpoint or routing or taxonomy or embeddings or persistence or status"`
- `python -m pytest tests/test_fitcv* tests/test_fitcv_cp*`
- `python scripts/generate_planning_lineage.py`
- `python scripts/hooks/run_validator.py --fast`

## Completion Criteria

A plan item is considered complete when:

1. all Key Deliverables are satisfied
2. all downstream/child items are terminal
3. every child item is `completed` or `dropped`






