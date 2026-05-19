---
layer: change
artifact_type: plan
status: completed
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
- [x] Step 1: capture current concurrency/read paths by stage (`ranking`, `cv_analysis`, `cv_generation`, `enrich`) and mark canonical vs compatibility reads.
- [x] Step 2: define bounded-parallel unit contract for `ranking` and `cv_generation` with deterministic order retention strategy.
- [x] Step 3: define canonical status/event field matrix used by all affected late-stage event families.

**Verification:**
- [x] `rg -n "stage_runtime|rerank_sleep_secs|cv_generation.*concurrency|ThreadPoolExecutor|layer4_cv_generation_started|layer4_cv_generation_result" src/fitcv/pipeline.py src/fitcv/ai_score.py src/fitcv/config.py`
- [x] design notes map every changed behavior to explicit source location and spec decision

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
- [x] Step 1: centralize throughput getters/resolution so stage code consumes canonical `stage_runtime` paths.
- [x] Step 2: keep legacy key projection as compatibility-only bridge and add explicit compatibility semantics in code comments/metadata where needed.
- [x] Step 3: update config tests to assert canonical precedence and compatibility fallback boundaries.

**Verification:**
- [x] `pytest -q tests/test_config.py -k "stage_runtime or compatibility or cv_generation_model or ranking"`
- [x] `pytest -q tests/test_ai_score.py -k "stage_runtime or rerank_sleep_secs"`

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
- [x] Step 1: implement bounded worker execution path for `run_ai_scoring` with configurable concurrency.
- [x] Step 2: preserve deterministic order by original shortlist index regardless of completion order.
- [x] Step 3: preserve per-item exception isolation and parser/runtime status semantics.

**Verification:**
- [x] `pytest -q tests/test_ai_score.py`
- [x] `pytest -q tests/test_pipeline.py -k "ranking or ai_score"`

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
- [x] Step 1: refactor generation-ready record processing into bounded worker unit execution.
- [x] Step 2: keep deterministic publish/store/debug ordering by canonical generation index.
- [x] Step 3: enforce invariant event payload core (`configured_concurrency`, `worker_slot`, `started_at`, `finished_at`, `attempt_count`, `retry_count`) across started/result emissions.
- [x] Step 4: preserve review-required, validation-failed, generation-failed, persistence-failed semantics with per-unit isolation.

**Verification:**
- [x] `pytest -q tests/test_pipeline_agentic_late_stage.py`
- [x] `pytest -q tests/test_pipeline.py -k "cv_generation or cv_analysis_concurrency or event_payload"`

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
- [x] Step 1: keep one editable canonical Runtime Throughput surface for stage knobs.
- [x] Step 2: move legacy aliases to collapsed compatibility section with read-only mapping and migration/status indicators.
- [x] Step 3: ensure submit/save path persists only canonical keys for scoped throughput settings.
- [x] Step 4: update docs to reflect SSOT ownership and compatibility policy.

**Verification:**
- [x] `rg -n "Runtime Throughput|Legacy Compatibility|readonly|disabled|stage_runtime" src/fitcv_cp/templates/settings.html docs/configuration.md`
- [x] run relevant UI/unit tests for settings surface (if present in repo)

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
- [x] Step 1: add/adjust table-driven invariance tests for status/event fields and deterministic ordering under parallel completion.
- [x] Step 2: run targeted runtime test matrix for conservative/baseline/aggressive throughput settings where feasible.
- [x] Step 3: refresh plan progress + canonical context pack state with completed evidence references.
- [x] Step 4: run required validators and record outcomes for closure gate.

**Verification:**
- [x] `pytest -q tests/test_ai_score.py tests/test_pipeline_agentic_late_stage.py tests/test_pipeline.py`
- [x] `python scripts/validate_planning_lifecycle.py --strict`
- [x] `python scripts/validate_checkpoint_packs.py`
- [x] `python scripts/validate_repo_contracts.py --fast`

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

## Execution Notes (2026-05-19)

- GitNexus refreshed in isolated worktree path and used for mandatory impact checks.
- Critical review outcomes:
  - `src/fitcv/ai_score.py:368-418` confirms `run_ai_scoring` remains sequential and reads ranking sleep via canonical-first + legacy fallback.
  - `src/fitcv/pipeline.py:4570-5261` confirms `cv_generation` loop remains sequential while event payload core already carries invariance fields (`configured_concurrency`, `worker_slot`, `started_at`, `finished_at`, `attempt_count`, `retry_count`).
  - `src/fitcv/config.py:load_config` has CRITICAL impact radius; Task 2 edits must stay narrow and compatibility-safe.
- Next execution order from gate:
  1. Task 2 canonical throughput read-path normalization.
  2. Task 3 ranking bounded parallelism.
  3. Task 4 cv_generation bounded parallelism.
- Task 4 kickoff slice completed:
  - introduced indexed generation-ready collection seam in `src/fitcv/pipeline.py` (`indexed_generation_ready_records`) as deterministic-order scaffolding for upcoming bounded worker migration.
  - verification: `pytest -q tests/test_pipeline.py -k "cv_generation or cv_analysis_concurrency or event_payload"` passed (`14 passed, 95 deselected`).
- Task 4 extraction slice completed:
  - added `_prepare_cv_generation_work_item(...)` in `src/fitcv/pipeline.py` to isolate per-item job/evidence/grounding payload preparation from loop control, preserving deterministic index context (`generation_total`, `generation_worker_slot`).
  - verification:
    - `pytest -q tests/test_pipeline.py -k "cv_generation or cv_analysis_concurrency or event_payload"` passed (`14 passed, 95 deselected`).
    - `pytest -q tests/test_pipeline_agentic_late_stage.py` passed (`13 passed`).
- Task 4 pre-dispatch seam completed:
  - added `generation_work_items` materialization list (`[(generation_index, analysis_record, prepared_work_item), ...]`) before execution loop in `src/fitcv/pipeline.py`.
  - this establishes deterministic, index-addressable work queue needed for bounded executor migration without changing result semantics yet.
  - verification:
    - `pytest -q tests/test_pipeline.py -k "cv_generation or cv_analysis_concurrency or event_payload"` passed (`14 passed, 95 deselected`).
- Task 4 bounded-dispatch prep completed:
  - `generation_work_items` preparation now uses bounded `ThreadPoolExecutor` when `configured_cv_generation_concurrency > 1` and multiple items exist.
  - prepared work items replay in deterministic index order via sorted `generation_index`.
  - this introduces executor dispatch seam while preserving sequential downstream execution semantics for safe migration.
  - verification:
    - `pytest -q tests/test_pipeline.py -k "cv_generation or cv_analysis_concurrency or event_payload"` passed (`14 passed, 95 deselected`).
    - `pytest -q tests/test_pipeline_agentic_late_stage.py` passed (`13 passed`).
- Task 4 deterministic replay-map seam completed:
  - replaced list-based work-item replay with explicit index-keyed map: `generation_work_items_by_index: dict[int, (analysis_record, prepared_work_item)]`.
  - execution loop now replays strictly via `for generation_index in sorted(generation_work_items_by_index)`.
  - this aligns structure with upcoming per-index worker outcome replay and keeps deterministic order invariant explicit.
  - verification:
    - `pytest -q tests/test_pipeline.py -k "cv_generation or cv_analysis_concurrency or event_payload"` passed (`14 passed, 95 deselected`).
    - `pytest -q tests/test_pipeline_agentic_late_stage.py` passed (`13 passed`).
- Task 4 runtime-state extraction step completed:
  - added `_initialize_cv_generation_runtime_state(work_item)` helper in `src/fitcv/pipeline.py`.
  - per-item runtime locals now hydrate from structured state payload (`job/evidence/fit/provenance/worker_slot/attempt counters`) instead of inline initialization block.
  - this is direct prerequisite for converting execution body to per-item worker outcome function while preserving current semantics.
  - verification:
    - `pytest -q tests/test_pipeline.py -k "cv_generation or cv_analysis_concurrency or event_payload"` passed (`14 passed, 95 deselected`).
    - `pytest -q tests/test_pipeline_agentic_late_stage.py` passed (`13 passed`).
- Task 4 started-event emission extraction step completed:
  - added `_emit_cv_generation_started_event(generation_index, generation_total, state)` helper in `src/fitcv/pipeline.py`.
  - replaced inline started-event reporter emission with helper call using `generation_state`.
  - this further decouples per-item execution-body logic into callable units needed for worker-outcome function migration.
  - verification:
    - `pytest -q tests/test_pipeline.py -k "cv_generation or cv_analysis_concurrency or event_payload"` passed (`14 passed, 95 deselected`).
    - `pytest -q tests/test_pipeline_agentic_late_stage.py` passed (`13 passed`).
- Task 4 result-event emission extraction step completed:
  - added outer-scope `_emit_cv_generation_result_event(state, status, ...)` helper in `src/fitcv/pipeline.py`.
  - removed loop-local nested result-event closure.
  - updated all in-loop result-event call sites to pass `generation_state`, preserving event payload shape and timing semantics.
  - verification:
    - `pytest -q tests/test_pipeline.py -k "cv_generation or cv_analysis_concurrency or event_payload"` passed (`14 passed, 95 deselected`).
    - `pytest -q tests/test_pipeline_agentic_late_stage.py` passed (`13 passed`).
- Task 4 invoked-event extraction step completed with regression fix:
  - added `_emit_cv_generation_invoked_event(state, cv_generation_model_value)` helper and replaced inline invoked-event emission.
  - fixed model provenance drift by passing current `job_cv_generation_model_value` (agentic path can mutate model after runtime initialization).
  - verification after fix:
    - `pytest -q tests/test_pipeline_agentic_late_stage.py` passed (`13 passed`).
    - `pytest -q tests/test_pipeline.py -k "cv_generation or cv_analysis_concurrency or event_payload"` passed (`14 passed, 95 deselected`).
- Task 4 validation-failure branch extraction step completed:
  - added `_handle_cv_generation_validation_failed(...)` helper to encapsulate validation-failed decision handling, debug-record emission, and reporter payloads.
  - replaced inline `if not validation["valid"]` block with helper call + continue path.
  - this is first concrete decision-branch extraction into callable per-item flow logic, directly advancing Task 4 Step 1 decomposition.
  - verification:
    - `pytest -q tests/test_pipeline_agentic_late_stage.py` passed (`13 passed`).
    - `pytest -q tests/test_pipeline.py -k "cv_generation or cv_analysis_concurrency or event_payload"` passed (`14 passed, 95 deselected`).
- Task 4 markdown-review branch extraction step completed:
  - added `_handle_cv_generation_markdown_review_required(...)` helper to encapsulate markdown-quality review-required decision handling.
  - replaced inline `markdown_review_reason` branch with helper call + continue path.
  - this continues decomposition of per-item decision flow into callable handlers required for final outcome-function extraction.
  - verification:
    - `pytest -q tests/test_pipeline_agentic_late_stage.py` passed (`13 passed`).
    - `pytest -q tests/test_pipeline.py -k "cv_generation or cv_analysis_concurrency or event_payload"` passed (`14 passed, 95 deselected`).
- Task 4 policy-acceptance branch extraction step completed:
  - added `_handle_cv_generation_policy_review_required(...)` helper to encapsulate policy acceptance review-required decision handling.
  - replaced inline `if not policy_pass` branch with helper call + continue path.
  - this further consolidates per-item decision logic into callable handlers and advances outcome-function readiness.
  - verification:
    - `pytest -q tests/test_pipeline_agentic_late_stage.py` passed (`13 passed`).
    - `pytest -q tests/test_pipeline.py -k "cv_generation or cv_analysis_concurrency or event_payload"` passed (`14 passed, 95 deselected`).
- Task 4 accepted-finalization extraction slice completed with regression fix:
  - added `_handle_cv_generation_accepted_debug_and_events(...)` helper to encapsulate accepted debug-record creation, observation emission, and accepted result-event emission.
  - replaced inline accepted debug/event block with helper call.
  - fixed model provenance drift in helper by passing current runtime values (`job_cv_generation_model_value`, `job_runtime_provenance`, `job_agentic_live_trace`) instead of relying on initial state snapshot.
  - verification after fix:
    - `pytest -q tests/test_pipeline_agentic_late_stage.py` passed (`13 passed`).
    - `pytest -q tests/test_pipeline.py -k "cv_generation or cv_analysis_concurrency or event_payload"` passed (`14 passed, 95 deselected`).
- Task 4 exception/failure branch extraction slice completed:
  - added `_handle_cv_generation_failure(...)` helper to encapsulate per-item exception finalization (`failure_status`, result event, failure debug record, error event).
  - replaced inline `except Exception` branch body with helper call + continue.
  - this closes major remaining branch decomposition for per-item outcome-function readiness.
  - verification:
    - `pytest -q tests/test_pipeline_agentic_late_stage.py` passed (`13 passed`).
    - `pytest -q tests/test_pipeline.py -k "cv_generation or cv_analysis_concurrency or event_payload"` passed (`14 passed, 95 deselected`).
- Task 4 per-item startup seam extraction slice completed:
  - added `_begin_cv_generation_item(...)` helper in `src/fitcv/pipeline.py` to centralize per-item startup span + runtime state hydration + started-event emission.
  - main execution loop now consumes returned runtime map, reducing inline state setup and preparing final `_execute_cv_generation_item(...)` consolidation.
  - behavior preserved (sequential execution-body unchanged).
  - verification:
    - `pytest -q tests/test_pipeline_agentic_late_stage.py` passed (`13 passed`).
    - `pytest -q tests/test_pipeline.py -k "cv_generation or cv_analysis_concurrency or event_payload"` passed (`14 passed, 95 deselected`).
- Task 4 per-item execution consolidation slice completed:
  - added `_execute_cv_generation_item(...)` helper in `src/fitcv/pipeline.py` to centralize invoked-event emission, validation/review gates, policy gate, persistence, and accepted debug/event finalization.
  - replaced corresponding inline post-generation decision/finalization block with helper call and explicit `should_continue` flow control.
  - behavior preserved (still sequential execution-body invocation).
  - verification:
    - `pytest -q tests/test_pipeline_agentic_late_stage.py` passed (`13 passed`).
    - `pytest -q tests/test_pipeline.py -k "cv_generation or cv_analysis_concurrency or event_payload"` passed (`14 passed, 95 deselected`).
- Task 4 non-agentic generation-body extraction slice completed:
  - added `_run_non_agentic_cv_generation(...)` helper in `src/fitcv/pipeline.py` to isolate non-agentic generate/validate/repair/retry compute path.
  - replaced inline non-agentic branch with helper call + tuple unpack, preserving per-item sequential semantics.
  - verification:
    - `pytest -q tests/test_pipeline_agentic_late_stage.py` passed (`13 passed`).
    - `pytest -q tests/test_pipeline.py -k "cv_generation or cv_analysis_concurrency or event_payload"` passed (`14 passed, 95 deselected`).
- Task 4 agentic generation-body extraction slice completed:
  - added `_run_agentic_cv_generation(...)` helper in `src/fitcv/pipeline.py` to isolate agentic generate/retry/review/debug outcome path.
  - replaced inline agentic branch with helper call + structured outcome hydration, preserving per-item sequential semantics and continue-path behavior.
  - verification:
    - `pytest -q tests/test_pipeline_agentic_late_stage.py` passed (`13 passed`).
    - `pytest -q tests/test_pipeline.py -k "cv_generation or cv_analysis_concurrency or event_payload"` passed (`14 passed, 95 deselected`).
- Task 4 bounded-submission safety prerequisite slice completed:
  - `_run_agentic_cv_generation(...)` no longer mutates shared debug list directly on early-continue paths; it returns deferred debug payload metadata.
  - main loop now applies deferred debug append/observation sequentially, preserving event order while unblocking thread-safe compute submission prep.
  - verification:
    - `pytest -q tests/test_pipeline_agentic_late_stage.py` passed (`13 passed`).
    - `pytest -q tests/test_pipeline.py -k "cv_generation or cv_analysis_concurrency or event_payload"` passed (`14 passed, 95 deselected`).
- Task 4 bounded-submission reporter-side-effect prerequisite slice completed:
  - `_run_agentic_cv_generation(...)` now returns deferred reporter payload metadata instead of emitting directly.
  - main loop now replays reporter emissions sequentially from returned payload, preserving deterministic side-effect ordering.
  - verification:
    - `pytest -q tests/test_pipeline_agentic_late_stage.py` passed (`13 passed`).
    - `pytest -q tests/test_pipeline.py -k "cv_generation or cv_analysis_concurrency or event_payload"` passed (`14 passed, 95 deselected`).
- Task 4 per-item compute seam unification slice completed:
  - added `_compute_cv_generation_outcome(...)` as single compute dispatcher for agentic and non-agentic per-item generation paths.
  - main loop now consumes normalized compute outcome payload for both branches, reducing switch-over surface for upcoming bounded executor submission.
  - verification:
    - `pytest -q tests/test_pipeline_agentic_late_stage.py` passed (`13 passed`).
    - `pytest -q tests/test_pipeline.py -k "cv_generation or cv_analysis_concurrency or event_payload"` passed (`14 passed, 95 deselected`).
- Task 4 bounded compute submission + deterministic replay slice completed:
  - added two-phase cv_generation execution in `src/fitcv/pipeline.py`:
    - phase A: `_begin_cv_generation_item(...)` runtime capture + bounded parallel `_compute_cv_generation_outcome(...)` submission/collection keyed by `generation_index`.
    - phase B: deterministic sorted replay by `generation_index` for all side effects (`reporter`, debug records, persistence, events) through existing handlers.
  - compute exceptions are captured per-index and replayed through existing `_handle_cv_generation_failure(...)` path.
  - verification:
    - `pytest -q tests/test_pipeline_agentic_late_stage.py` passed (`13 passed`).
    - `pytest -q tests/test_pipeline.py -k "cv_generation or cv_analysis_concurrency or event_payload"` passed (`14 passed, 95 deselected`).
- Task 4 verification hardening slice completed with regression fix:
  - executed expanded suite `pytest -q tests/test_pipeline.py`; found one regression in accepted debug-record state hydration after bounded replay refactor (`structured_cv_initial` was `None`).
  - fixed by synchronizing post-compute resolved values back into `generation_state` before `_execute_cv_generation_item(...)` and downstream accepted-debug emission.
  - verification after fix:
    - `pytest -q tests/test_pipeline.py` passed (`109 passed`).
    - `pytest -q tests/test_pipeline_agentic_late_stage.py` passed (`13 passed`).
- Task 5 canonical-throughput read-only compatibility slice completed:
  - updated `src/fitcv_cp/templates/settings.html` control rendering so rows marked `compatibility_alias_for` render as disabled/readonly and non-submitting.
  - this keeps canonical runtime throughput knobs as editable authority while preserving legacy alias visibility.
  - updated `docs/configuration.md` ownership notes to mark compatibility-readonly policy for throughput alias keys.
  - verification:
    - `rg -n "Runtime Throughput|Legacy Compatibility|readonly|disabled|stage_runtime" src/fitcv_cp/templates/settings.html docs/configuration.md`
    - `pytest -q tests/test_config.py` passed (`79 passed`).
    - `pytest -q tests/test_fitcv_cp/test_settings_schema.py` passed (`171 passed`).
- Task 5 collapsed compatibility mapping indicator slice completed:
  - updated `src/fitcv_cp/templates/settings.html` compatibility alias rows with explicit collapsed `<details>` block labeled `Legacy Compatibility`.
  - added migration indicator badge `Migration status: compatibility-readonly`.
  - compatibility alias mapping now explicitly surfaced as collapsed/read-only explanatory lane while canonical controls remain editable.
  - verification:
    - `rg -n "Runtime Throughput|Legacy Compatibility|readonly|disabled|stage_runtime|compatibility-readonly" src/fitcv_cp/templates/settings.html docs/configuration.md`
    - `pytest -q tests/test_fitcv_cp/test_settings_schema.py` passed (`171 passed`).
    - `pytest -q tests/test_config.py` passed (`79 passed`).
- Task 5 canonical-save-path narrowing evidence slice completed:
  - hardened settings save routes in `src/fitcv_cp/app.py` to drop throughput compatibility alias keys from persisted payloads (`_filter_canonical_settings_payload(...)`), keeping canonical runtime keys as single write path.
  - added regression test `test_post_settings_section_timing_drops_throughput_compatibility_aliases` in `tests/test_fitcv_cp/test_app.py`.
  - verification:
    - `pytest -q tests/test_fitcv_cp/test_app.py -k "timing_drops_throughput_compatibility_aliases or post_settings_section_valid_redirects"` passed (`2 passed`).
    - `pytest -q tests/test_fitcv_cp/test_settings_schema.py` passed (`171 passed`).
    - `pytest -q tests/test_config.py` passed (`79 passed`).
- Task 6 invariance ordering test slice completed with runtime fix:
  - added `test_run_pipeline_cv_generation_parallel_completion_preserves_deterministic_debug_order` in `tests/test_pipeline.py`.
  - test enforces deterministic `cv_generation_debug_records` ordering by canonical generation index even when parallel completion finishes out-of-order.
  - discovered and fixed runtime regression: missing `as_completed` import in `src/fitcv/pipeline.py` bounded compute replay path.
  - verification after fix:
    - `pytest -q tests/test_pipeline.py -k "cv_generation_parallel_completion_preserves_deterministic_debug_order or cv_generation or cv_analysis_concurrency or event_payload"` passed (`15 passed, 95 deselected`).
    - `pytest -q tests/test_pipeline_agentic_late_stage.py` passed (`13 passed`).
- Task 6 runtime matrix baseline slice completed:
  - executed baseline targeted runtime matrix command:
    - `pytest -q tests/test_ai_score.py tests/test_pipeline_agentic_late_stage.py tests/test_pipeline.py -k "ranking or cv_generation or concurrency or event_payload"`
  - result: `32 passed, 123 deselected`.
- Task 6 closure-gate validator slice completed:
  - `python scripts/validate_planning_lifecycle.py --strict` passed.
  - `python scripts/validate_checkpoint_packs.py` passed.
  - `python scripts/validate_repo_contracts.py --fast` passed.
  - closure note: validator gate is green; remaining open item is Task 6 Step 2 conservative/aggressive profile-specific matrix evidence.
- Task 6 profile-specific matrix evidence slice completed:
  - conservative-profile evidence:
    - `pytest -q tests/test_fitcv_cp/test_settings_schema.py -k "conservative_defaults_batch_size_10_concurrency_1 or enrichment_concurrency"` passed (`3 passed, 168 deselected`).
  - aggressive/bounded-parallel profile evidence:
    - `pytest -q tests/test_pipeline.py -k "cv_generation_parallel_completion_preserves_deterministic_debug_order or cv_analysis_concurrency_preserves_result_order"` passed (`2 passed, 108 deselected`).
  - together with prior baseline run and validator gate, Task 6 checklist steps are now fully evidenced.
