---
layer: change
artifact_type: plan
status: proposed
template_id: implementation-plan
name: runtime-throughput-ssot-symmetry-invariance-optimization-plan
parent_thread: workstream-pipeline-efficiency-and-reuse.efficiency-reuse-exact-match-contract
parent_spec: docs/superpowers/specs/2026-05-19-16-45-runtime-throughput-ssot-symmetry-invariance-optimization-spec.md
targets:
  - src/fitcv/pipeline.py
  - src/fitcv/ai_score.py
  - src/fitcv/enrich.py
  - src/fitcv/config.py
  - src/fitcv_cp/templates/admin_pipeline_settings.html
  - src/fitcv_cp/static/js/admin_pipeline_settings.js
  - tests/test_pipeline.py
  - tests/test_pipeline_agentic_late_stage.py
  - tests/test_ai_score.py
  - tests/test_config.py
  - docs/configuration.md
related_features:
  - settings_system
  - inspection_debugging
  - pipeline_performance
related_stages:
  - enrich
  - ranking
  - cv_analysis
  - cv_generation
---

## Goal

Execute SSOT/symmetry/invariance optimization so runtime throughput behavior across `ranking`, `cv_analysis`, and `cv_generation` is structurally consistent, canonical config ownership is unambiguous, and settings UX exposes one editable canonical surface with compatibility read-only mapping.

## Key Deliverables

### Deliverable 1: Canonical throughput contract enforced in runtime

`stage_runtime.<stage>` becomes authoritative throughput source for affected stages, with legacy keys handled only via compatibility projection and deprecation-safe reads where required.

### Deliverable 2: Symmetric bounded-parallel execution in late stages

`ranking` and `cv_generation` execute per-unit workloads through bounded worker semantics aligned with existing `cv_analysis` concurrency model, while preserving deterministic output order and per-unit failure isolation.

### Deliverable 3: Invariant status/observability payload semantics

Equivalent started/result/decision events across affected stages share a canonical payload-core contract and equivalent outcome status vocabulary.

### Deliverable 4: SSOT settings UX with compatibility read-only lane

Control-plane runtime-throughput configuration offers one canonical editable surface; compatibility aliases are collapsed by default and rendered read-only with migration/status diagnostics.

### Deliverable 5: Regression-safe verification + handoff evidence

Targeted tests and validator runs prove correctness, invariants, and non-regression, and produce closure-ready evidence for downstream execution context packs.

## Task/Wave Breakdown

### Task 1: Baseline contract capture and execution seam mapping

**Purpose:**
- lock current stage throughput semantics and identify exact refactor seams before behavior changes

**Files:**
- Inspect: `src/fitcv/pipeline.py`
- Inspect: `src/fitcv/ai_score.py`
- Inspect: `src/fitcv/enrich.py`
- Inspect: `src/fitcv/config.py`
- Verify: `tests/test_pipeline.py`
- Verify: `tests/test_ai_score.py`

**Preconditions:**
- parent spec is approved for execution planning
- GitNexus freshness checked; stale graph treated advisory-only

**Steps:**
- [ ] Step 1: capture current concurrency/read paths by stage (`ranking`, `cv_analysis`, `cv_generation`, `enrich`) and mark canonical vs compatibility reads.
- [ ] Step 2: define bounded-parallel unit contract for `ranking` and `cv_generation` with deterministic order retention strategy.
- [ ] Step 3: define canonical status/event field matrix used by all affected late-stage event families.

**Verification:**
- [ ] `rg -n "stage_runtime|rerank_sleep_secs|cv_generation.*concurrency|ThreadPoolExecutor|layer4_cv_generation_started|layer4_cv_generation_result" src/fitcv/pipeline.py src/fitcv/ai_score.py src/fitcv/config.py`
- [ ] design notes map every changed behavior to explicit source location and spec decision

**Exit Criteria:**
- implementation seam map complete and no downstream task depends on undocumented assumptions

### Task 2: Canonical throughput read-path normalization

**Purpose:**
- enforce SSOT for throughput settings in runtime code while preserving bounded compatibility behavior

**Files:**
- Modify: `src/fitcv/config.py`
- Modify: `src/fitcv/ai_score.py`
- Modify: `src/fitcv/pipeline.py`
- Verify: `tests/test_config.py`
- Verify: `tests/test_ai_score.py`

**Preconditions:**
- Task 1 seam map approved

**Steps:**
- [ ] Step 1: centralize throughput getters/resolution so stage code consumes canonical `stage_runtime` paths.
- [ ] Step 2: keep legacy key projection as compatibility-only bridge and add explicit compatibility semantics in code comments/metadata where needed.
- [ ] Step 3: update config tests to assert canonical precedence and compatibility fallback boundaries.

**Verification:**
- [ ] `pytest -q tests/test_config.py -k "stage_runtime or compatibility or cv_generation_model or ranking"`
- [ ] `pytest -q tests/test_ai_score.py -k "stage_runtime or rerank_sleep_secs"`

**Exit Criteria:**
- affected runtime throughput reads are canonicalized and tested

### Task 3: Parallelize ranking with deterministic output ordering

**Purpose:**
- remove sequential bottleneck in ranking AI scoring while preserving ordering and failure semantics

**Files:**
- Modify: `src/fitcv/ai_score.py`
- Modify: `src/fitcv/pipeline.py`
- Verify: `tests/test_ai_score.py`
- Verify: `tests/test_pipeline.py`

**Preconditions:**
- Task 2 complete
- stage runtime throughput contract available to ranking path

**Steps:**
- [ ] Step 1: implement bounded worker execution path for `run_ai_scoring` with configurable concurrency.
- [ ] Step 2: preserve deterministic order by original shortlist index regardless of completion order.
- [ ] Step 3: preserve per-item exception isolation and parser/runtime status semantics.

**Verification:**
- [ ] `pytest -q tests/test_ai_score.py`
- [ ] `pytest -q tests/test_pipeline.py -k "ranking or ai_score"`

**Exit Criteria:**
- ranking path supports real bounded concurrency with deterministic ordering guarantees

### Task 4: Parallelize CV generation unit execution with invariant status/events

**Purpose:**
- replace sequential generation loop with bounded parallel execution while preserving domain outcomes and observability invariants

**Files:**
- Modify: `src/fitcv/pipeline.py`
- Verify: `tests/test_pipeline_agentic_late_stage.py`
- Verify: `tests/test_pipeline.py`

**Preconditions:**
- Task 2 complete
- Task 3 order/invariant patterns reusable

**Steps:**
- [ ] Step 1: refactor generation-ready record processing into bounded worker unit execution.
- [ ] Step 2: keep deterministic publish/store/debug ordering by canonical generation index.
- [ ] Step 3: enforce invariant event payload core (`configured_concurrency`, `worker_slot`, `started_at`, `finished_at`, `attempt_count`, `retry_count`) across started/result emissions.
- [ ] Step 4: preserve review-required, validation-failed, generation-failed, persistence-failed semantics with per-unit isolation.

**Verification:**
- [ ] `pytest -q tests/test_pipeline_agentic_late_stage.py`
- [ ] `pytest -q tests/test_pipeline.py -k "cv_generation or cv_analysis_concurrency or event_payload"`

**Exit Criteria:**
- cv_generation executes bounded parallel units and invariant event/status contracts remain green

### Task 5: SSOT settings UI consolidation and compatibility read-only lane

**Purpose:**
- eliminate duplicate editable surfaces and make compatibility mapping explicit and non-authoritative

**Files:**
- Modify: `src/fitcv_cp/templates/admin_pipeline_settings.html`
- Modify: `src/fitcv_cp/static/js/admin_pipeline_settings.js`
- Modify: `docs/configuration.md`
- Verify: control-plane settings tests/snapshots if present

**Preconditions:**
- Task 2 canonical contract finalized

**Steps:**
- [ ] Step 1: keep one editable canonical Runtime Throughput surface for stage knobs.
- [ ] Step 2: move legacy aliases to collapsed compatibility section with read-only mapping and migration/status indicators.
- [ ] Step 3: ensure submit/save path persists only canonical keys for scoped throughput settings.
- [ ] Step 4: update docs to reflect SSOT ownership and compatibility policy.

**Verification:**
- [ ] `rg -n "Runtime Throughput|Legacy Compatibility|readonly|disabled|stage_runtime" src/fitcv_cp/templates/admin_pipeline_settings.html src/fitcv_cp/static/js/admin_pipeline_settings.js docs/configuration.md`
- [ ] run relevant UI/unit tests for settings surface (if present in repo)

**Exit Criteria:**
- no duplicate editable throughput controls remain; compatibility section read-only and collapsed by default

### Task 6: Invariance regression matrix, validators, and execution handoff updates

**Purpose:**
- prove no regression and synchronize lifecycle/handoff artifacts for downstream execution

**Files:**
- Modify: `tests/test_pipeline.py`
- Modify: `tests/test_pipeline_agentic_late_stage.py`
- Modify: `tests/test_ai_score.py`
- Modify: `docs/superpowers/execution_context_packs/<lane-id>/latest.md`
- Optional mirror: `artifacts/execution_context_pack.md`
- Verify: validator scripts and targeted pytest suites

**Preconditions:**
- Tasks 1-5 complete

**Steps:**
- [ ] Step 1: add/adjust table-driven invariance tests for status/event fields and deterministic ordering under parallel completion.
- [ ] Step 2: run targeted runtime test matrix for conservative/baseline/aggressive throughput settings where feasible.
- [ ] Step 3: refresh plan progress + canonical context pack state with completed evidence references.
- [ ] Step 4: run required validators and record outcomes for closure gate.

**Verification:**
- [ ] `pytest -q tests/test_ai_score.py tests/test_pipeline_agentic_late_stage.py tests/test_pipeline.py`
- [ ] `python scripts/validate_planning_lifecycle.py --strict`
- [ ] `python scripts/validate_checkpoint_packs.py`
- [ ] `python scripts/validate_repo_contracts.py --fast`

**Exit Criteria:**
- verification evidence complete, lifecycle validators pass, handoff artifacts synchronized

## Verification

- `python scripts/hooks/run_validator.py --fast`
- `pytest -q tests/test_config.py tests/test_ai_score.py tests/test_pipeline_agentic_late_stage.py`
- `pytest -q tests/test_pipeline.py -k "ranking or cv_generation or concurrency or event_payload"`
- `python scripts/validate_planning_lifecycle.py --strict`
- `python scripts/validate_checkpoint_packs.py`
- `python scripts/validate_repo_contracts.py --fast`

## Completion Criteria

1. all Key Deliverables are satisfied
2. all scoped execution tasks are terminal (`completed` or `dropped`) with evidence
3. canonical context pack for lane is current and aligned with plan state
4. closure gate validators pass with no unresolved checklist items in scoped artifacts

Canonical source-of-truth:

<LINK>
- `docs/operating_system/governance/repo-governance.md`
- `scripts/validate_planning_lifecycle.py`
</LINK>
