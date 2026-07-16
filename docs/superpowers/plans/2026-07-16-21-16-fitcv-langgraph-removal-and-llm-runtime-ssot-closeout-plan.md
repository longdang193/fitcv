---
layer: change
artifact_type: plan
status: completed
template_id: implementation-plan
name: fitcv-langgraph-removal-and-llm-runtime-ssot-closeout
parent_thread: workstream-operator-control-plane.fitcv-cp-app-ssot-symmetry-refactor
parent_spec: docs/superpowers/specs/2026-07-14-12-13-fitcv-llm-runtime-spine-master-spec.md
targets:
  - src/fitcv/agentic_cv_generation.py
  - src/fitcv/llm_runtime.py
  - src/fitcv/runtime_routing.py
  - src/fitcv_cp/app.py
  - config/runtime/control_plane.yaml
  - requirements.txt
  - docker-compose.yml
  - .env.example
  - README.md
  - docs/setup.md
  - docs/configuration.md
  - docs/pipeline.md
  - docs/architecture.md
  - docs/features/cv_system/feature.source.yaml
  - docs/stages/cv_generation.source.yaml
  - docs/superpowers/specs/2026-07-14-11-47-langgraph-runtime-adapter-only-spec.md
  - docs/generated/planning_lineage.yaml
  - docs/generated/architecture_dag.yaml
  - docs/generated/capability_lineage.yaml
  - tests/test_llm_runtime.py
  - tests/test_pipeline_agentic_late_stage.py
  - tests/test_deployment_config.py
  - tests/test_runtime_routing.py
  - tests/test_fitcv_cp/test_app.py
  - tests/test_fitcv_cp/test_control_plane_config.py
  - tests/test_fitcv_cp/test_main.py
related_features:
  - cv_system
  - settings_system
  - inspection_debugging
  - admin_control_plane_core
related_stages:
  - cv_generation
---

# Implementation Plan: Remove fitcv-langgraph and close LLM runtime SSOT gaps

## Goal

Remove FitCV's runtime, packaging, deployment, test, and active-documentation dependency on external `fitcv-langgraph` while retaining repo-native spine:

`LlmTaskRequest -> canonical current/frozen route -> adapter -> parse -> validate -> LlmRuntimeResult`

All generative OpenAI-compatible calls owned by this repo must use `execute_llm_task(...)`. Main pipeline routes remain `enrich_extraction`, `ranking_ai_score`, and `cv_generation_structured_write`. Provider-backed synonym triage gains one explicit route instead of borrowing CV-generation routing or issuing direct HTTP. Embeddings remain outside generative spine.

Non-goals:

- add LangGraph graphs, nodes, checkpoints, agents, or orchestration
- change stage-owned prompt, validation, repair, acceptance, reuse, persistence, or status semantics
- delete or modify sibling `fitcv-langgraph` repository
- move deterministic builtin synonym triage into generative runtime

## Key Deliverables

### One repo-native CV-generation runtime path

`src/fitcv/agentic_cv_generation.py` uses default adapter in `src/fitcv/llm_runtime.py`. Sibling discovery, dynamic import, `sys.path` mutation, and external `OpenAICompatibleJsonClient` transport disappear. Structured-write semantics, repair, provenance, observations, and traces remain stable.

### One generative transport authority

Provider-backed synonym triage creates `LlmTaskRequest`, calls `execute_llm_task(...)`, and owns only prompt/parser/validator semantics. Central runtime owns routing, credentials, transport, failures, and safe provenance. Builtin triage remains explicit degradation path.

### No external deployment contract

Dependencies, Compose, environment examples, tests, and active docs contain no required `langgraph` package, sibling mount, repo-path variable, or runtime import contract.

### Lifecycle alignment

Feature/stage sources describe one internal runtime. Deprecated adapter-only design becomes superseded. Generated architecture and planning outputs refresh from source. Negative guards keep legacy `FITCV_LANGGRAPH_*` variables non-authoritative.

## Task/Wave Breakdown

### Task 1: Lock invariants and baseline evidence

**Purpose:**
- establish behavior parity and blast-radius gates before shared runtime edits

**Files:**
- Inspect: `docs/superpowers/specs/2026-07-14-12-13-fitcv-llm-runtime-spine-master-spec.md`
- Inspect: `docs/superpowers/specs/2026-07-14-17-39-fitcv-llm-runtime-spine-phase-3-shared-runtime-contract-spec.md`
- Inspect: `src/fitcv/agentic_cv_generation.py`
- Inspect: `src/fitcv_cp/app.py`
- Verify: `tests/test_llm_runtime.py`
- Verify: `tests/test_pipeline_agentic_late_stage.py`
- Verify: `tests/test_fitcv_cp/test_app.py`

**Preconditions:**
- internal LLM runtime approved as canonical
- unrelated working-tree edits identified and preserved
- stale GitNexus output remains advisory until refreshed

**Steps:**
- [x] Step 1: record CV-generation success, failure, repair, observation, and trace baselines
- [x] Step 2: record synonym success, invalid output, builtin degradation, fingerprint, reuse, and automation baselines
- [x] Step 3: run upstream impact before editing LangGraph helpers, `_generate_fresh_from_analysis`, `_call_synonym_triage_provider`, `_resolve_synonym_triage_runtime`, and `_synonym_triage_fingerprint`
- [x] Step 4: compare business results and canonical provenance, not deprecated adapter labels

**Verification:**
- [x] `powershell -ExecutionPolicy Bypass -File scripts/get_gitnexus_freshness.ps1`
- [x] focused baseline tests pass or pre-existing failures are recorded
- [x] no unreviewed HIGH or CRITICAL impact remains

**Exit Criteria:**
- implementation has explicit parity assertions and reviewed symbol impact

### Task 2: Collapse CV generation onto internal runtime

**Purpose:**
- delete external adapter selection and leave one structured-write runtime path

**Files:**
- Modify: `src/fitcv/agentic_cv_generation.py`
- Verify: `src/fitcv/llm_runtime.py`
- Verify: `src/fitcv/runtime_routing.py`
- Modify: `tests/test_pipeline_agentic_late_stage.py`
- Verify: `tests/test_llm_runtime.py`

**Preconditions:**
- Task 1 complete
- `execute_llm_task(...)` default adapter remains canonical transport
- `cv_generation_structured_write` remains canonical routing part

**Steps:**
- [x] Step 1: remove sibling discovery, external environment projection, dynamic import, and `sys.path` mutation helpers
- [x] Step 2: remove `_langgraph_runtime_adapter` and external client error translation; use internal normalized transport behavior
- [x] Step 3: collapse fresh generation to one provider generator calling `generate_cv(...)`; remove import-presence branching and stale `agentic_live_provider` naming
- [x] Step 4: preserve prompt rendering, schema, validation, repair, statuses, runtime evidence, invocation order, heartbeat behavior, and trace structure
- [x] Step 5: remove unused imports/constants and retain only `FITCV_LLM_*` debug controls
- [x] Step 6: replace external-adapter tests with internal-runtime success, failure, repair, observation, and trace tests

**Verification:**
- [x] import succeeds with no sibling repository on `sys.path`
- [x] provenance reports `adapter=openai_compatible` and `runtime_path=fitcv_llm_openai_compatible`
- [x] no test patches or imports `fitcv_langgraph.providers.live`
- [x] `python -m pytest tests/test_llm_runtime.py tests/test_pipeline_agentic_late_stage.py -q`

**Exit Criteria:**
- CV generation has one repo-native provider transport and unchanged business ownership

### Task 3: Route synonym triage through runtime spine

**Purpose:**
- remove remaining direct generative HTTP transport and borrowed CV-generation routing

**Files:**
- Modify: `src/fitcv_cp/app.py`
- Modify: `config/runtime/control_plane.yaml`
- Modify: `src/fitcv/llm_runtime.py`
- Verify: `src/fitcv/runtime_routing.py`
- Modify: `tests/test_llm_runtime.py`
- Modify: `tests/test_fitcv_cp/test_app.py`
- Modify: `tests/test_runtime_routing.py`
- Modify: `tests/test_fitcv_cp/test_control_plane_config.py`

**Preconditions:**
- Task 2 complete
- provider-backed synonym triage is auxiliary application LLM work, not pipeline stage
- `FITCV_LLM_API_KEY` remains sole generative credential input

**Steps:**
- [x] Step 1: add `synonym_triage_recommendation` under existing `llm.model_routing.parts`; reuse provider definitions and add no second config system
- [x] Step 2: extend `execute_llm_task(...)` with one optional pre-resolved `LlmRouting` input for immutable run snapshots; route validation, credential resolution, adapter selection, failures, and provenance remain on the same code path
- [x] Step 3: freeze the dedicated synonym route in run runtime inputs and make `_resolve_synonym_triage_runtime` stop borrowing `cv_generation_runtime_expectation`
- [x] Step 4: replace `_call_synonym_triage_provider` direct `httpx` construction with `LlmTaskRequest(response_mode="json_object")` and `execute_llm_task(...)` using that frozen route
- [x] Step 5: keep prompt, parser, and recommendation validator local; validator returns `LlmValidationResult`
- [x] Step 6: project canonical safe provenance into recommendation runtime evidence without keys or raw provider payloads; unsuccessful results use deterministic builtin degradation
- [x] Step 7: make fingerprints use dedicated frozen route identity, preserve sleep/concurrency and reuse invalidation, and delete duplicate shadowing `_synonym_triage_fingerprint`
- [x] Step 8: add runtime tests proving current-route and pre-resolved-route calls share validation, failure, adapter, and provenance semantics; replace direct-client tests with triage success, malformed output, fallback, reuse, and route-separation tests

**Verification:**
- [x] provider-backed triage reaches `execute_llm_task(...)` once per fresh attempt
- [x] `src/fitcv_cp/app.py` no longer builds `/responses` or `/chat/completions` calls for triage
- [x] CV-generation route changes do not redefine synonym route, and later config changes do not alter a run's frozen synonym route
- [x] malformed output becomes normalized parse/validation failure before builtin degradation
- [x] `python -m pytest tests/test_runtime_routing.py tests/test_fitcv_cp/test_control_plane_config.py tests/test_fitcv_cp/test_app.py -q`

**Exit Criteria:**
- every generative provider call uses internal runtime spine; application semantics stay outside transport

### Task 4: Remove dependency and deployment bridge

**Purpose:**
- make FitCV install and start without external package or sibling checkout

**Files:**
- Modify: `requirements.txt`
- Modify: `docker-compose.yml`
- Modify: `.env.example`
- Modify: `tests/test_deployment_config.py`

**Preconditions:**
- Tasks 2 and 3 complete
- source contains no runtime `fitcv_langgraph` import

**Steps:**
- [x] Step 1: remove direct `langgraph>=1.0,<2.0` requirement after proving no source import needs it
- [x] Step 2: remove `FITCV_LANGGRAPH_REPO_ROOT` and sibling mounts from web and worker
- [x] Step 3: remove `FITCV_LANGGRAPH_REPO_PATH` example and comments
- [x] Step 4: make deployment tests assert repo-owned shared mounts only
- [x] Step 5: add negative assertions against sibling mounts and repo-root variables

**Verification:**
- [x] `docker compose config --quiet`
- [x] `python -m pytest tests/test_deployment_config.py -q`
- [x] `python -m pip check`
- [x] clean import smoke test succeeds without direct `langgraph` requirement

**Exit Criteria:**
- deployment contract is self-contained

### Task 5: Align active docs, lifecycle sources, and guards

**Purpose:**
- make human and generated sources state one runtime ownership model

**Files:**
- Modify: `README.md`
- Modify: `docs/setup.md`
- Modify: `docs/configuration.md`
- Modify: `docs/pipeline.md`
- Modify: `docs/architecture.md`
- Modify: `docs/features/cv_system/feature.source.yaml`
- Modify: `docs/stages/cv_generation.source.yaml`
- Modify: `docs/superpowers/specs/2026-07-14-11-47-langgraph-runtime-adapter-only-spec.md`
- Verify: `tests/test_runtime_routing.py`
- Verify: `tests/test_fitcv_cp/test_control_plane_config.py`
- Verify: `tests/test_fitcv_cp/test_main.py`
- Refresh: `docs/generated/planning_lineage.yaml`
- Refresh: generated outputs owned by `tools/docs/generate_architecture_metadata.py`

**Preconditions:**
- Tasks 2 through 4 complete
- source and tests identify final routes and provenance

**Steps:**
- [x] Step 1: replace active LangGraph language with one internal spine and explicit route inventory
- [x] Step 2: document synonym routing as auxiliary generative work; keep embeddings and builtin triage outside spine
- [x] Step 3: update `cv_system.config-owned-generation-contract` and `cv_generation` stage source to remove dual-adapter wording
- [x] Step 4: remove adapter-only spec from active stage refs and mark spec `superseded`; retain historical evidence
- [x] Step 5: retain negative tests proving deprecated `FITCV_LANGGRAPH_*` routing variables are ignored; keep unrelated generic validator fixtures
- [x] Step 6: refresh generated planning and architecture surfaces through canonical generators only

**Verification:**
- [x] active code/config/deploy/docs/feature/stage surfaces contain no live external LangGraph contract
- [x] deprecated-env guards remain green
- [x] `python tools/docs/generate_architecture_metadata.py --check`
- [x] `python scripts/validate_planning_lifecycle.py`

**Exit Criteria:**
- docs, lifecycle sources, generated outputs, and tests agree on internal ownership

### Task 6: Run residue audit and final verification

**Purpose:**
- prove removal completeness across code, config, deployment, tests, docs, and lifecycle

**Files:**
- Verify: `src/`
- Verify: `tests/`
- Verify: `config/`
- Verify: `docker-compose.yml`
- Verify: `.env.example`
- Verify: `README.md`
- Verify: `docs/`

**Preconditions:**
- Tasks 1 through 5 complete
- generated outputs refreshed from source

**Steps:**
- [x] Step 1: run focused runtime, generation, triage, deployment, routing, and control-plane tests
- [x] Step 2: run import, Compose, dependency, lifecycle, architecture, and repo-contract checks
- [x] Step 3: search active surfaces for imports, discovery, `sys.path` mutation, mounts, repo-path variables, stale labels, and direct provider HTTP
- [x] Step 4: classify remaining matches only as archive/audit history, deprecated-env guards, or unrelated generic fixtures
- [x] Step 5: run GitNexus change detection and confirm expected flows only
- [x] Step 6: inspect `git diff --check` and `git status --short`; exclude secrets, sibling files, and unrelated changes

**Verification:**
- [x] every pass/fail command below passes; residue-search output is manually classified
- [x] no active production code imports or discovers `fitcv_langgraph`
- [x] no generative transport exists outside `src/fitcv/llm_runtime.py`
- [x] no key or raw provider payload enters persisted evidence, logs, snapshots, or generated docs

**Exit Criteria:**
- removal and SSOT closeout have executable proof at every changed boundary

## Verification

- `python -m pytest tests/test_llm_runtime.py tests/test_pipeline_agentic_late_stage.py tests/test_deployment_config.py tests/test_runtime_routing.py tests/test_fitcv_cp/test_control_plane_config.py tests/test_fitcv_cp/test_main.py tests/test_fitcv_cp/test_app.py -q`
- `python -c "import fitcv.agentic_cv_generation; import fitcv_cp.app"`
- `docker compose config --quiet`
- `python -m pip check`
- `powershell -NoProfile -Command '$m = rg -n "fitcv_langgraph|fitcv-langgraph|FITCV_LANGGRAPH_REPO_ROOT|FITCV_LANGGRAPH_REPO_PATH|fitcv_llm_langgraph|adapter=.langgraph" src config docker-compose.yml requirements.txt .env.example README.md docs/setup.md docs/configuration.md docs/pipeline.md docs/architecture.md docs/features docs/stages; if ($LASTEXITCODE -eq 0) { $m; exit 1 }; exit 0'`
- `powershell -NoProfile -Command '$m = rg -n "/responses|/chat/completions" src/fitcv_cp/app.py; if ($LASTEXITCODE -eq 0) { $m; exit 1 }; exit 0'`
- `python scripts/generate_planning_lineage.py` (must produce no diff after refresh)
- `python tools/docs/generate_architecture_metadata.py --check`
- `python scripts/validate_planning_lifecycle.py`
- `python scripts/validate_adoption_shape.py`
- `python scripts/validate_repo_contracts.py --fast`
- `python scripts/validate_repo_contracts.py`
- GitNexus `detect_changes(scope="all")` reports only expected runtime, generation, triage, deployment, test, docs, and lineage impact
- `git diff --check`
- `git status --short`

Residue policy:

- zero matches required in active production/runtime/deployment/operator/lifecycle surfaces
- allowed matches require manual classification: archives, audit evidence, deprecated-env guards, generic validator fixtures
- `src/fitcv/llm_runtime.py` remains sole OpenAI-compatible generative transport owner

Rollback policy:

- use `git revert` if behavior or deployment verification fails
- never restore sibling discovery, `sys.path` mutation, external transport, duplicate credentials, or deprecated route authority
- restore functionality through internal spine and canonical routes only

## Completion Criteria

A plan item is considered complete when:

1. all Key Deliverables are satisfied
2. every task checklist and verification line is marked `- [x]`
3. every child item is `completed` or `dropped`
4. CV generation uses only `execute_llm_task(...)` and repo-native adapter
5. provider-backed synonym triage uses `LlmTaskRequest` and `execute_llm_task(...)`; builtin triage remains explicit fallback
6. dependencies, Compose, environment examples, source, tests, and active docs have no external runtime contract
7. `FITCV_LLM_API_KEY` remains sole generative credential input
8. pipeline routes remain three canonical parts; `synonym_triage_recommendation` is auxiliary route
9. embeddings remain outside generative spine
10. feature/stage sources and generated outputs state one internal authority
11. focused tests, selected control-plane tests, Compose, dependency, residue, lifecycle, repo, and GitNexus checks pass

Canonical source-of-truth:

<LINK>
- `docs/superpowers/specs/2026-07-14-12-13-fitcv-llm-runtime-spine-master-spec.md`
- `docs/superpowers/specs/2026-07-14-17-39-fitcv-llm-runtime-spine-phase-3-shared-runtime-contract-spec.md`
- `src/fitcv/llm_runtime.py`
- `config/runtime/control_plane.yaml`
- `docs/operating_system/governance/repo-governance.md`
- `scripts/validate_planning_lifecycle.py`
</LINK>
## Closeout Evidence

- Test-fixture drift audit: `docs/superpowers/plans/audit/20260716-llm-runtime-closeout-test-fixture-drift/report.md`
- Focused verification: `572 passed`
- Repo-contract verification: `101 passed`
- GitNexus change detection: `low` risk, zero affected execution flows
