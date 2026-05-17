---
layer: change
artifact_type: plan
status: active
template_id: implementation-plan
name: ai-plane-unification-and-backend-symmetry-implementation
parent_thread: workstream-operator-control-plane.operator-control-plane-agentic-settings-surface
parent_spec: docs/superpowers/specs/2026-05-17-15-20-ai-plane-symmetry-invariance-equivalence-migration-spec.md
targets:
  - config/runtime/control_plane.yaml
  - config/runtime/pipeline.yaml
  - src/fitcv/config.py
  - src/fitcv/enrich.py
  - src/fitcv/ai_score.py
  - src/fitcv/cv_generator.py
  - src/fitcv/pipeline.py
  - src/fitcv_cp/worker_job.py
  - docs/configuration.md
  - docs/pipeline.md
  - tests/test_config.py
  - tests/test_enrich.py
  - tests/test_ai_score.py
  - tests/test_cv_generator.py
  - tests/test_pipeline.py
  - tests/test_pipeline_agentic_late_stage.py
related_features:
  - cv_system
  - settings_system
  - trigger_run_management
related_stages:
  - enrich
  - ranking
  - cv_analysis
  - cv_generation
---

## Goal

Implement AI-plane unification so model routing/auth are single-source and backend-agnostic, while preserving BigQuery and SQLite symmetry as persistence-only variants.

## Key Deliverables

### Deliverable 1

Unified AI routing and auth contract across `enrich`, `ranking_ai_score`, and `cv_generation` paths, with `control_plane.model_routing.parts.*` as runtime SSOT and API-key auth as canonical contract.

### Deliverable 2

Removal of legacy runtime ownership ambiguity (`gemini` fallback defaults, non-agentic decision branch ownership, flat compatibility model authority) while retaining compatibility telemetry and bounded deprecation windows.

### Deliverable 3

Backend equivalence verification suite proving same AI-stage decisions/provenance across sqlite and bigquery for identical inputs, with divergence allowed only in persistence substrate metadata.

## Task/Wave Breakdown

### Task 1: Freeze contracts and deprecation policy surface

**Purpose:**
- establish deterministic migration contract before code-path edits

**Files:**
- Inspect: `docs/superpowers/specs/2026-05-17-15-20-ai-plane-symmetry-invariance-equivalence-migration-spec.md`
- Modify: `docs/configuration.md`
- Modify: `docs/pipeline.md`
- Verify: `config/runtime/control_plane.yaml`

**Preconditions:**
- approved migration spec remains source of truth
- GitNexus freshness remains `fresh` for dependency lookup

**Steps:**
- [ ] Step 1: Document canonical AI auth contract (`FITCV_LLM_API_KEY` primary) and alias deprecation window.
- [ ] Step 2: Document strict plane boundary (`data_plane` vs `ai_plane`) and prohibited backend-to-AI coupling.
- [ ] Step 3: Add explicit runtime error contract text for missing routing/model/key.

**Verification:**
- [ ] `rg -n "FITCV_LLM_API_KEY|non-agentic|gemini_model|control_plane.model_routing" docs/configuration.md docs/pipeline.md -S`

**Exit Criteria:**
- docs define single runtime truth and deprecation semantics without contradictory ownership language

### Task 2: Remove legacy model fallback ownership in config resolution

**Purpose:**
- eliminate Gemini/default fallback authority and force routing-based model truth

**Files:**
- Inspect: `src/fitcv/config.py`
- Modify: `src/fitcv/config.py`
- Modify: `config/runtime/pipeline.yaml`
- Verify: `tests/test_config.py`

**Preconditions:**
- Task 1 complete
- GitNexus impact acknowledged for `get_cv_generation_model` (MEDIUM; direct callers in pipeline/cv_generator/worker_job path)

**Steps:**
- [ ] Step 1: Refactor `get_cv_generation_model` and related helpers to remove `gemini-2.5-flash` fallback authority.
- [ ] Step 2: Restrict compatibility projection fields to non-authoritative metadata only.
- [ ] Step 3: Update tests to require fail-fast behavior when model unresolved.

**Verification:**
- [ ] `pytest tests/test_config.py -q`
- [ ] `rg -n "gemini-2\.5-flash|gemini_model" src/fitcv/config.py config/runtime/pipeline.yaml tests/test_config.py -S`

**Exit Criteria:**
- no config runtime path can silently choose Gemini/default model when routing is unresolved

### Task 3: Unify AI auth and client construction across enrich/ranking/generation

**Purpose:**
- make auth/routing invariant across all AI stages

**Files:**
- Inspect: `src/fitcv/enrich.py`
- Inspect: `src/fitcv/ai_score.py`
- Inspect: `src/fitcv/cv_generator.py`
- Modify: `src/fitcv/enrich.py`
- Modify: `src/fitcv/ai_score.py`
- Modify: `src/fitcv/cv_generator.py`
- Verify: `tests/test_enrich.py`
- Verify: `tests/test_ai_score.py`
- Verify: `tests/test_cv_generator.py`

**Preconditions:**
- Task 2 complete
- GitNexus impact reviewed for:
  - `Function:src/fitcv/enrich.py:_build_openai_compat_client` (LOW)
  - `Function:src/fitcv/ai_score.py:_make_genai_client` (LOW)
  - `Function:src/fitcv/cv_generator.py:_build_openai_compat_client` (LOW)

**Steps:**
- [ ] Step 1: Standardize key lookup order around canonical key + bounded alias fallback with warning.
- [ ] Step 2: Remove any AI client dependence on `service_account_key`.
- [ ] Step 3: Ensure routing source/provenance fields emitted consistently across stages.

**Verification:**
- [ ] `pytest tests/test_enrich.py tests/test_ai_score.py tests/test_cv_generator.py -q`
- [ ] `rg -n "service_account_key|OPENAI_API_KEY|OPENAI_COMPATIBLE_API_KEY|FITCV_LLM_API_KEY" src/fitcv/enrich.py src/fitcv/ai_score.py src/fitcv/cv_generator.py -S`

**Exit Criteria:**
- all AI stages share same auth/routing contract and reject account-key-only AI execution

### Task 4: Remove non-agentic runtime authority for AI decisions

**Purpose:**
- enforce single AI execution path independent of legacy mode split

**Files:**
- Inspect: `src/fitcv/pipeline.py`
- Inspect: `src/fitcv_cp/worker_job.py`
- Modify: `src/fitcv/pipeline.py`
- Modify: `src/fitcv_cp/worker_job.py`
- Verify: `tests/test_pipeline.py`
- Verify: `tests/test_pipeline_agentic_late_stage.py`

**Preconditions:**
- Task 3 complete
- GitNexus impact reviewed for `_build_settings_used_payload` (LOW) and `execute_pipeline_run` call chain

**Steps:**
- [x] Step 1: Remove decision-critical non-agentic branch ownership for AI stages.
- [x] Step 2: Keep trace/diagnostic fields compatible but ensure they report unified path.
- [x] Step 3: Update mode/status expectations in tests to reflect unified runtime path.

**Verification:**
- [ ] `pytest tests/test_pipeline.py tests/test_pipeline_agentic_late_stage.py -q`
- [ ] `rg -n "non_agentic|agentic_late_stage|late_stage_mode" src/fitcv/pipeline.py src/fitcv_cp/worker_job.py tests/test_pipeline.py tests/test_pipeline_agentic_late_stage.py -S`

**Exit Criteria:**
- backend or legacy mode toggles no longer alter AI decision path

### Task 5: Preserve backend symmetry as persistence-only difference

**Purpose:**
- guarantee equivalence across sqlite/bigquery for AI outcomes

**Files:**
- Inspect: `src/fitcv_cp/worker_job.py`
- Inspect: `tests/test_fitcv_cp/test_worker_job.py`
- Modify: `tests/test_fitcv_cp/test_worker_job.py`
- Modify: `tests/test_pipeline.py`
- Verify: `tests/test_fitcv_cp/test_worker_job.py`

**Preconditions:**
- Task 4 complete
- deterministic provider/test doubles available

**Steps:**
- [x] Step 1: Add paired sqlite/bigquery parity tests using identical fixture inputs.
- [x] Step 2: Assert equal AI stage decision/provenance payloads across backends.
- [x] Step 3: Restrict allowed diff set to persistence substrate metadata only.

**Verification:**
- [ ] `pytest tests/test_fitcv_cp/test_worker_job.py tests/test_pipeline.py -q`

**Exit Criteria:**
- parity tests fail on AI-plane drift and pass on allowed persistence-only differences

### Task 6: Final deprecation gates and repo validation closeout

**Purpose:**
- close migration with explicit removal gates and contract validation

**Files:**
- Inspect: `docs/configuration.md`
- Inspect: `docs/pipeline.md`
- Modify: `docs/configuration.md`
- Modify: `docs/pipeline.md`
- Verify: `docs/generated/planning_lineage.yaml`

**Preconditions:**
- Tasks 1-5 complete

**Steps:**
- [x] Step 1: Document sunset criteria and enforcement timing for auth aliases and legacy fields.
- [x] Step 2: Run planning/doc lineage refresh if metadata graph changed.
- [x] Step 3: Run full fast repo contract validation.

**Verification:**
- [ ] `python scripts/generate_planning_lineage.py`
- [ ] `python scripts/hooks/run_validator.py --fast`

**Exit Criteria:**
- migration plan artifacts, docs, and validation gates are aligned and green

## Verification

- `pytest tests/test_config.py tests/test_enrich.py tests/test_ai_score.py tests/test_cv_generator.py -q`
- `pytest tests/test_pipeline.py tests/test_pipeline_agentic_late_stage.py tests/test_fitcv_cp/test_worker_job.py -q`
- `python scripts/hooks/run_validator.py --fast`

## Completion Criteria

A plan item is considered complete when:

1. all Key Deliverables are satisfied
2. all downstream/child items are terminal
3. every child item is `completed` or `dropped`

Canonical source-of-truth:

<LINK>
- `docs/operating_system/governance/repo-governance.md`
- `scripts/validate_planning_lifecycle.py`
</LINK>

## Execution Progress Log

- 2026-05-17: Task 4 Step 1 remains in progress. Migrated additional `tests/test_pipeline.py` harness coverage from legacy `generate_cv`/`run_all_validations` mocks to agentic contracts via `run_agentic_cv_analysis` + `run_agentic_cv_generation` helpers.
- 2026-05-17: Updated contract-aligned expectations in `tests/test_pipeline.py` and `tests/test_pipeline_agentic_late_stage.py` to match current acceptance-policy and validation semantics.
- 2026-05-17: Verification passed: `pytest tests/test_pipeline.py tests/test_pipeline_agentic_late_stage.py tests/test_fitcv_cp/test_worker_job.py -q` (`167 passed`).
- 2026-05-17: Migrated `test_run_pipeline_returns_correct_schema` to agentic harness path; guard suite remains green (`167 passed`).
- 2026-05-17: Migrated `test_run_pipeline_returns_export_results_sorted_and_statused` to agentic harness (analysis ready + reranker-blocked branches), preserving export/debug contract assertions; guard suite still green (`167 passed`).
- 2026-05-17: Migrated pre-bigquery raw-row prep cluster (`test_run_pipeline_prepares_raw_rows_before_bigquery_insert`) to agentic harness; preserved raw-ingest assertions; guard suite green (`167 passed`).
- 2026-05-17: Migrated `test_run_pipeline_layer4_uses_enriched_job_fields_for_gap_and_debug` to agentic harness and aligned resumed `cv_generation` test with explicit agentic generation mock; guard suite green (`167 passed`).
- 2026-05-17: Hardened candidate-embedding and dedup export cluster under agentic runtime config (`test_run_pipeline_shortlist_does_not_write_candidate_chunk_embeddings`, `test_run_pipeline_export_marks_deduplicated_rows_explicitly`); guard suite green (`167 passed`).
- 2026-05-17: Determined remaining legacy-coupled test inventory from existing artifacts; executed smallest safe step by enabling agentic runtime path in `test_run_pipeline_passes_job_dicts_to_embeddings_and_urls_to_vector_search`; guard suite green (`167 passed`).
- 2026-05-17: Migrated `test_run_pipeline_skips_invalid_cv` to agentic generation validation-failed contract; preserved rejection behavior; guard suite green (`167 passed`).
- 2026-05-17: Executed next Task 4 Step 1 micro-slice by enabling agentic runtime path in `test_run_pipeline_skips_reranker_skip_fit_jobs`; guard suite green (`167 passed`).
- 2026-05-17: Executed next Task 4 Step 1 micro-slice by enabling agentic runtime path in `test_run_pipeline_per_job_failure_skips_not_crashes`; failure-resilience behavior preserved; guard suite green (`167 passed`).
- 2026-05-17: Executed next Task 4 Step 1 micro-slice by enabling agentic runtime path in `test_run_pipeline_uses_reranker_fit_as_sole_post_filter_cv_gate`; reranker-fit gating behavior preserved; guard suite green (`167 passed`).
- 2026-05-17: Hard-flip gate attempt executed by forcing `_agentic_late_stage_enabled` true in `src/fitcv/pipeline.py`; guard suite failed (14 tests), then flip reverted to restore green baseline. Failed clusters: validation-repair legacy tests, CV generation observation payload tests, bounded generation event payload, analysis-grounding forwarding, and default non-agentic expectation in `tests/test_pipeline_agentic_late_stage.py::test_run_pipeline_keeps_original_late_stage_path_by_default`.
- 2026-05-17: Migrated `test_run_pipeline_logs_full_validation_reasons` to agentic validation-failed contract; hard-flip re-attempt reduced failures from 14 to 13, then reverted to keep baseline green (`167 passed`). Remaining hard-flip blockers: retries/placeholder-repair, CV generation observation payload suite, ranked-fit-floor payload, pipeline-complete payload, analysis-grounding forwarding/provenance, and default non-agentic expectation test.
- 2026-05-17: Migrated `test_run_pipeline_retries_once_for_missing_sections_only` to agentic retry contract (first generation_failed recoverable -> second accepted). Hard-flip re-attempt reduced failures from 13 to 12, then reverted to restore green baseline (`167 passed`).
- 2026-05-17: Migrated `test_run_pipeline_emits_cv_generation_item_observation_for_accepted_generation` to explicit agentic contracts (`run_agentic_cv_analysis`/`run_agentic_cv_generation`) with preserved observation assertions; guard suite green (`167 passed`).
- 2026-05-17: Migrated `test_run_pipeline_emits_cv_generation_item_observation_for_validation_failed` to explicit agentic contracts; corrected accidental cross-test patch contamination and restored suite stability; guard suite green (`167 passed`).
- 2026-05-17: Continued hard-flip blocker observation cluster: review-required observation test moved toward agentic contract; fixed/removed misplaced cross-test patch blocks to preserve suite stability; guard suite green (`167 passed`).
- 2026-05-17: Migrated grounding-forwarding blocker (`test_run_pipeline_forwards_analysis_grounding_payload_to_validation`) to agentic-era contract by asserting evidence/provenance forwarding through `analysis_record` passed to `run_agentic_cv_generation`. Hard-flip re-attempt reduced failures from 12 to 8; reverted flip to restore green baseline (`167 passed`). Remaining hard-flip blockers: placeholder-repair, persistence_failed observation, generation_failed observation, ranked-fit-floor payload, pipeline-complete payload omission, bounded generation validation-failed event, CV-analysis evidence-selection provenance test, and default non-agentic expectation test.
- 2026-05-17: Completed remaining hard-flip blocker migration batch for Task 4 Step 1 (`tests/test_pipeline.py`, `tests/test_pipeline_agentic_late_stage.py`) covering placeholder-repair, observation payloads, ranked-fit-floor payload, pipeline-complete payload, validation-failed event payload, analysis provenance assertion path, and default mode expectation update.
- 2026-05-17: Hard-flip gate passed with forced unified path (`_agentic_late_stage_enabled` returning `True`); verification green: `pytest tests/test_pipeline.py tests/test_pipeline_agentic_late_stage.py tests/test_fitcv_cp/test_worker_job.py -q` (`167 passed`).
- 2026-05-17: Task 4 Step 1 marked complete; next eligible Task 4 action is Step 2 cleanup/alignment of trace fields and non-agentic compatibility surfaces under unified runtime reporting.
- 2026-05-17: Completed Task 4 Step 2 telemetry cleanup in `src/fitcv/pipeline.py` and `src/fitcv_cp/worker_job.py` by normalizing late-stage payloads to unified `agentic` reporting with compatibility fields retained; updated worker-job expectations in `tests/test_fitcv_cp/test_worker_job.py`.
- 2026-05-17: Verification passed after Step 2 alignment: `pytest tests/test_pipeline.py tests/test_pipeline_agentic_late_stage.py tests/test_fitcv_cp/test_worker_job.py -q` (`167 passed`).
- 2026-05-17: Task 4 fully complete. Next eligible action: Task 5 Step 1 paired sqlite/bigquery parity tests for AI-stage equivalence.
- 2026-05-17: Task 5 Step 1 started and completed first concrete slice by adding `test_worker_results_export_keeps_ai_plane_payload_equivalent_across_backends` in `tests/test_fitcv_cp/test_worker_job.py` (paired backend runtime execution with identical AI-plane result fixture).
- 2026-05-17: Verification passed for Task 5 Step 1 slice:
  - `pytest tests/test_fitcv_cp/test_worker_job.py -q -k "results_export_keeps_ai_plane_payload_equivalent_across_backends"` (`1 passed`)
  - `pytest tests/test_fitcv_cp/test_worker_job.py tests/test_pipeline.py -q` (`156 passed`)
- 2026-05-17: Next eligible action is Task 5 Step 2/Step 3 tightening: expand parity assertions to explicit AI-stage decision/provenance fields and enumerate allowed backend-only diff set.
- 2026-05-17: Completed Task 5 Step 2/3 by tightening `test_worker_results_export_keeps_ai_plane_payload_equivalent_across_backends` to assert full results-export payload equivalence after normalizing explicit allowed backend-only diffs (`data_plane.state_backend`, `data_plane.artifact_backend`, `finished_at`).
- 2026-05-17: Verification passed for Task 5 completion:
  - `pytest tests/test_fitcv_cp/test_worker_job.py -q -k "results_export_keeps_ai_plane_payload_equivalent_across_backends"` (`1 passed`)
  - `pytest tests/test_fitcv_cp/test_worker_job.py tests/test_pipeline.py -q` (`156 passed`)
- 2026-05-17: Task 5 complete. Next eligible action: Task 6 Step 1 deprecation-gate doc finalization (`docs/configuration.md`, `docs/pipeline.md`), then Task 6 verification gates.
- 2026-05-17: Executed Task 6 Step 2 lineage refresh gate; command passed:
  - `python scripts/generate_planning_lineage.py` (`Generated docs/generated/planning_lineage.yaml`)
- 2026-05-17: Next eligible action is Task 6 Step 3 full fast validator gate (`python scripts/hooks/run_validator.py --fast`).
- 2026-05-17: Executed Task 6 Step 3 validator gate; command passed:
  - `python scripts/hooks/run_validator.py --fast`
  - Result: repo contract validation passed (hook subset), including planning/checkpoint/context-pack validators.
- 2026-05-17: Next eligible action is closeout-gate validation set from execution prompt (`validate_planning_lifecycle --strict`, `validate_checkpoint_packs`, `validate_repo_contracts --fast`) then close-now decision.
- 2026-05-17: Executed closeout-gate validation trio; all passed:
  - `python scripts/validate_planning_lifecycle.py --strict`
  - `python scripts/validate_checkpoint_packs.py`
  - `python scripts/validate_repo_contracts.py --fast`
- 2026-05-17: Task 6 Step 1 confirmed satisfied by existing deprecation docs in `docs/configuration.md` and `docs/pipeline.md` (sunset boundaries, alias windows, removal gates, fail-fast contract).
- 2026-05-17: Workflow-live-run-debugging evidence run #1: `run_id=bc813187-3a87-463b-852f-1bd25870e876` reached terminal `succeeded`, but `agentic-live-trace.json` was `trace_status=degraded` with repeated `cv_generation` `error_code=401` (`invalid_api_key`) from OpenAI Responses API; `cvs_generated=0`.
- 2026-05-17: Workflow-live-run-debugging evidence run #2: `run_id=edb1ea11-3c16-4481-942a-edc48050fc30` reproduced same boundary (`trace_status=degraded`, `error_code=401`, `cvs_generated=0`).
- 2026-05-17: Failure boundary identified: live provider credential validity, component=`fitcv_langgraph_live` in `cv_generation` step. No code patch applied in this pass; issue is environment/runtime credential state rather than migration logic regression.
- 2026-05-17: Workflow-live-run-debugging evidence run #3: `run_id=f7e10bff-84d8-47a3-8c27-2658f688f847` again reached terminal `succeeded` with degraded trace; all 3 attempted generation records failed at `agentic_live_provider` with OpenAI `401 invalid_api_key`, confirming external credential blocker persists.
- 2026-05-17: Runtime routing override applied in `.env` for openai-compatible provider (`FITCV_LANGGRAPH_PROVIDER=9router`, `FITCV_LANGGRAPH_OPENAI_BASE_URL=http://host.docker.internal:20128/v1`, `FITCV_LANGGRAPH_WIRE_API=responses`, `FITCV_LANGGRAPH_MODEL=cx/gpt-5.2`) and `web/worker` restarted.
- 2026-05-17: Live run `run_id=f8549230-ac38-4035-8ce3-c1545d2f1ce5` no longer shows provider auth errors; embedded `agentic_live_trace` in `cv-debug.json` reports `trace_status=completed` with statuses `validation_failed, review_required, review_required` and empty error codes.
- 2026-05-17: Remaining live-run boundary is policy checkpoint pause (`status=awaiting_continue`, `checkpoint_status=awaiting_review`) with review-required queue items, not provider/runtime credential failure.
