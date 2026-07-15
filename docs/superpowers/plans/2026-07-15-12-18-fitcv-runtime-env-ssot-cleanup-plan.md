---
layer: change
artifact_type: plan
status: completed
template_id: implementation-plan
name: fitcv-runtime-env-ssot-cleanup
parent_thread: workstream-operator-control-plane.fitcv-cp-app-ssot-symmetry-refactor
parent_spec: docs/superpowers/specs/2026-07-14-12-13-fitcv-llm-runtime-spine-master-spec.md
targets:
  - .env.example
  - src/fitcv/runtime_routing.py
  - src/fitcv/agentic_cv_generation.py
  - src/fitcv/config.py
  - src/fitcv_cp/app.py
  - docker-compose.yml
  - docker-compose.isolated.full.yml
  - docs/configuration.md
  - docs/pipeline.md
  - docs/fitcv-control-plane-setup.md
  - tests/test_runtime_routing.py
  - tests/test_pipeline_agentic_late_stage.py
  - tests/test_cv_generator.py
  - tests/test_fitcv_cp/test_app.py
  - tests/test_fitcv_cp/test_control_plane_config.py
  - docs/generated/planning_lineage.yaml
related_features:
  - settings_system
  - cv_system
  - inspection_debugging
related_stages:
  - enrich
  - ranking
  - cv_generation
---

# FitCV Runtime Environment SSOT Cleanup Implementation Plan

## Goal

Finish runtime-environment SSOT cleanup left after the LLM runtime-spine work:

- expose one repo-native LLM credential name, `FITCV_LLM_API_KEY`
- make enrichment, ranking, CV generation, LangGraph diagnostics, and auxiliary control-plane LLM calls use the same credential resolver
- use the same bounded `FITCV_LLM_*` vocabulary at the LangGraph adapter boundary; no credential alias projection
- remove deprecated LangGraph routing overrides and GCP/BigQuery residue from active runtime templates, Compose, and setup docs
- leave historical BigQuery migration scripts outside the supported runtime contract rather than creating another config layer

Planning triage:

- Layer: change
- Feature type: MODIFY
- Summary: collapse public runtime environment vocabulary onto config-owned routing and `FITCV_LLM_API_KEY`
- Affected stages: `enrich`, `ranking`, `cv_generation`
- Affected features: `settings_system`, `cv_system`, `inspection_debugging`
- Spec needed: no; completed runtime-spine master and Phase 3 specs already require shared credential resolution and adapter-only LangGraph
- Plan needed: yes

## Key Deliverables

### One public LLM environment namespace

`FITCV_LLM_API_KEY` is the only accepted repo-native LLM credential input. `OPENAI_API_KEY`, `OPENAI_COMPATIBLE_API_KEY`, and `FITCV_LANGGRAPH_OPENAI_API_KEY` no longer act as alternate authorities. Provider, model, base URL, wire API, and timeout remain owned by `config/runtime/control_plane.yaml`; no replacement environment override family is introduced.

### One credential resolution path

Shared runtime, CV generation, LangGraph readiness/diagnostics, and synonym triage resolve credential availability through the same repo-native function. Direct and LangGraph adapters receive the same resolved value. LangGraph receives that value as `FITCV_LLM_API_KEY` inside a bounded `FITCV_LLM_*` adapter mapping.

### No active GCP/BigQuery runtime contract

`.env.example`, supported Compose, and active control-plane setup docs contain no GCP project, BigQuery dataset, service-account key, or hardcoded workstation credential path. Historical BigQuery scripts may remain only as self-contained migration tools.

### Tests and docs prove symmetry

Tests lock canonical credential resolution, direct/LangGraph parity, missing-key failure, adapter projection, and absence of deprecated runtime variables. Docs and generated planning lineage state the same contract as code.

## Task/Wave Breakdown

### Task 1: Lock scope and invariants

**Purpose:**
- establish exact blast radius and a closed environment-key allowlist before shared code changes

**Files:**
- Inspect: `src/fitcv/runtime_routing.py`
- Inspect: `src/fitcv/agentic_cv_generation.py`
- Inspect: `src/fitcv/config.py`
- Inspect: `src/fitcv_cp/app.py`
- Inspect: `.env.example`
- Inspect: `docker-compose.yml`
- Inspect: `docker-compose.isolated.full.yml`
- Verify: `tests/test_runtime_routing.py`

**Preconditions:**
- completed master spec remains authoritative
- GitNexus freshness is checked; stale output is advisory only
- source and tests remain final authority

**Steps:**
- [x] Step 1: run GitNexus upstream impact analysis before editing `resolve_openai_compatible_api_key`, `resolve_cv_generation_runtime_expectation`, and changed LangGraph attempt/adapter functions
- [x] Step 2: inventory tracked and local environment key names without printing secret values
- [x] Step 3: lock allowed vocabulary: public input `FITCV_LLM_API_KEY`; config-owned route facts; bounded `FITCV_LLM_*` adapter mapping; adapter location/mechanics variables only where still needed
- [x] Step 4: confirm `FITCV_LANGGRAPH_REPO_PATH` and `FITCV_LANGGRAPH_REPO_ROOT` remain distinct host-mount source and container destination concepts

**Verification:**
- [x] impact output names direct callers, affected processes, and risk level for each edited shared symbol
- [x] no command output contains credential values

**Exit Criteria:**
- edit scope and allowed environment vocabulary are explicit

### Task 2: Collapse credential input

**Purpose:**
- remove alternate credential authorities and make every repo-native caller use one resolver

**Files:**
- Modify: `src/fitcv/runtime_routing.py`
- Modify: `src/fitcv_cp/app.py`
- Modify: `tests/test_runtime_routing.py`
- Modify: `tests/test_fitcv_cp/test_app.py`
- Verify: `src/fitcv/llm_runtime.py`

**Preconditions:**
- Task 1 complete
- local `.env` value can be migrated without display or commit

**Steps:**
- [x] Step 1: make shared credential resolution read only `FITCV_LLM_API_KEY`
- [x] Step 2: delete the LangGraph credential-name tuple and `resolve_langgraph_openai_compatible_api_key()`
- [x] Step 3: replace control-plane readiness and synonym-triage checks with the canonical resolver
- [x] Step 4: update missing-credential messages to name only `FITCV_LLM_API_KEY`
- [x] Step 5: migrate ignored local `.env` key name while preserving its value; never stage or print `.env`
- [x] Step 6: test that deprecated aliases do not satisfy readiness and all paths report identical availability

**Verification:**
- [x] `rg -n "FITCV_LANGGRAPH_OPENAI_API_KEY|OPENAI_COMPATIBLE_API_KEY" src tests docs/configuration.md docs/pipeline.md .env.example` returns no active-contract matches
- [x] `rg -n "resolve_langgraph_openai_compatible_api_key" src tests` returns no matches
- [x] focused runtime-routing and control-plane credential tests pass

**Exit Criteria:**
- one repo-native credential name and resolver govern every LLM caller

### Task 3: Keep LangGraph vocabulary private

**Purpose:**
- preserve downstream protocol translation without allowing LangGraph to become a second routing or credential owner

**Files:**
- Modify: `src/fitcv/agentic_cv_generation.py`
- Modify: `src/fitcv/config.py`
- Modify: `src/fitcv/runtime_routing.py`
- Modify: `tests/test_pipeline_agentic_late_stage.py`
- Modify: `tests/test_cv_generator.py`
- Modify: `tests/test_fitcv_cp/test_control_plane_config.py`
- Verify: `src/fitcv/llm_runtime.py`

**Preconditions:**
- Task 2 complete
- canonical route continues to come from `config/runtime/control_plane.yaml`

**Steps:**
- [x] Step 1: remove credential harvesting from LangGraph env-file values and let shared runtime resolve `FITCV_LLM_API_KEY` once
- [x] Step 2: pass the resolved credential through as `FITCV_LLM_API_KEY`; do not translate it to a downstream alias
- [x] Step 3: remove `FITCV_CP_OPENAI_COMPATIBLE_BASE_URL` as alternate route authority instead of adding a renamed override
- [x] Step 4: stop advertising `FITCV_LANGGRAPH_PROVIDER`, `FITCV_LANGGRAPH_MODEL`, `FITCV_LANGGRAPH_OPENAI_BASE_URL`, and `FITCV_LANGGRAPH_WIRE_API` as operator inputs; private canonical route projection may still emit them when downstream protocol requires it
- [x] Step 5: remove or narrow drift logic that treats private adapter projection names as independent expected runtime config
- [x] Step 6: prove stale adapter-named environment values cannot override provider, model, base URL, wire API, timeout, or credential

**Verification:**
- [x] direct and LangGraph fixtures receive identical canonical route and credential inputs
- [x] adapter test proves direct and LangGraph paths use the same `FITCV_LLM_*` vocabulary
- [x] config tests prove environment cannot override canonical route ownership

**Exit Criteria:**
- LangGraph owns adapter mechanics only; repo-native LLM inputs use `FITCV_LLM_*` wording and config-owned route facts

### Task 4: Remove active GCP/BigQuery residue

**Purpose:**
- finish control-plane backend trim without deleting historical migration tools prematurely

**Files:**
- Modify: `.env.example`
- Modify: `docker-compose.yml`
- Delete: `docker-compose.isolated.full.yml`
- Modify: `docs/fitcv-control-plane-setup.md`
- Inspect: `scripts/bootstrap_bigquery.py`
- Inspect: `scripts/download_cvs.py`
- Inspect: `scripts/migrate_pipeline_runs_orchestration_columns.py`
- Inspect: `scripts/migrations/`
- Verify: `src/fitcv_cp/`

**Preconditions:**
- active control-plane code no longer reads GCP/BigQuery variables
- isolated Compose remains unreferenced and contains stale BigQuery/service-account deployment shape

**Steps:**
- [x] Step 1: remove `GCP_PROJECT`, `BIGQUERY_DATASET`, and `GCP_SA_KEY_PATH` from `.env.example`
- [x] Step 2: remove unused `GCP_PROJECT` injection from supported web and worker Compose services
- [x] Step 3: delete unreferenced isolated Compose instead of maintaining hardcoded workstation credential paths and retired backend config
- [x] Step 4: remove service-account setup and GCP troubleshooting from active control-plane setup docs
- [x] Step 5: retain BigQuery scripts only as historical self-contained tools; do not expose their variables through shared runtime templates or Compose
- [x] Step 6: verify remaining GCP/BigQuery matches are restricted to historical docs, evidence, and explicit migration scripts

**Verification:**
- [x] `rg -n "GCP_PROJECT|BIGQUERY_DATASET|GCP_SA_KEY_PATH|GOOGLE_APPLICATION_CREDENTIALS|sa_key.json" .env.example docker-compose.yml docs/fitcv-control-plane-setup.md src/fitcv_cp` returns no matches
- [x] `git grep -n "docker-compose.isolated.full.yml"` returns no live reference after deletion
- [x] supported Compose config renders successfully

**Exit Criteria:**
- active runtime and operator setup surfaces contain no GCP/BigQuery contract

### Task 5: Align docs, tests, and lineage

**Purpose:**
- make documentation and lifecycle evidence state the same contract as runtime

**Files:**
- Modify: `.env.example`
- Modify: `docs/configuration.md`
- Modify: `docs/pipeline.md`
- Modify: `docs/fitcv-control-plane-setup.md`
- Verify: `docs/features/settings_system/feature.source.yaml`
- Verify: `docs/features/cv_system/feature.source.yaml`
- Verify: `docs/features/inspection_debugging/feature.source.yaml`
- Refresh: `docs/generated/planning_lineage.yaml`
- Verify: `tests/test_runtime_routing.py`
- Verify: `tests/test_pipeline_agentic_late_stage.py`
- Verify: `tests/test_fitcv_cp/test_app.py`
- Verify: `tests/test_fitcv_cp/test_control_plane_config.py`

**Preconditions:**
- Tasks 2 through 4 complete

**Steps:**
- [x] Step 1: make `.env.example` show only `FITCV_LLM_API_KEY` as required LLM secret plus genuinely supported non-routing mechanics
- [x] Step 2: remove temporary alias wording and state that adapter protocol projection is not an accepted input
- [x] Step 3: verify feature-source wording still states central route ownership; modify source only if current statements become false
- [x] Step 4: refresh `docs/generated/planning_lineage.yaml` through `scripts/generate_planning_lineage.py`; no architecture generator exists in this checkout and no feature source changed
- [x] Step 5: run focused tests, Compose validation, repo validators, and GitNexus detect-changes before commit

**Verification:**
- [x] tracked docs and `.env.example` contain one public LLM credential name: `FITCV_LLM_API_KEY`
- [x] no generated file is manually patched
- [x] all focused tests and validators pass

**Exit Criteria:**
- code, tests, templates, docs, and generated lineage agree on one runtime environment contract

## Verification

- `.\.venv\Scripts\python.exe -m pytest tests/test_runtime_routing.py tests/test_pipeline_agentic_late_stage.py tests/test_cv_generator.py tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_control_plane_config.py -q`
- `docker compose config --quiet`
- `rg -n "FITCV_LANGGRAPH_OPENAI_API_KEY|OPENAI_COMPATIBLE_API_KEY" src tests .env.example docs/configuration.md docs/pipeline.md`
- `rg -n "GCP_PROJECT|BIGQUERY_DATASET|GCP_SA_KEY_PATH|GOOGLE_APPLICATION_CREDENTIALS|sa_key.json" .env.example docker-compose.yml docs/fitcv-control-plane-setup.md src/fitcv_cp`
- `.\.venv\Scripts\python.exe scripts/generate_planning_lineage.py`
- `.\.venv\Scripts\python.exe scripts/validate_adoption_shape.py`
- `.\.venv\Scripts\python.exe scripts/validate_repo_contracts.py --fast`
- `.\.venv\Scripts\python.exe scripts/validate_repo_contracts.py`
- GitNexus `detect_changes(scope="all")` reports only expected routing, adapter, control-plane, test, Compose, docs, and generated-lineage impact
- `git status --short` confirms ignored `.env` is not staged

Rollback policy:

- use `git revert` for tracked changes if deployment validation fails
- never restore multiple credential authorities or adapter aliases as rollback; keep `FITCV_LLM_API_KEY` canonical end-to-end
- restore a replacement isolated Compose only through a separate supported deployment spec without hardcoded host paths or GCP/BigQuery assumptions

## Completion Criteria

A plan item is considered complete when:

1. all Key Deliverables are satisfied
2. every task checklist and verification line is marked `- [x]`
3. every child item is `completed` or `dropped`
4. `FITCV_LLM_API_KEY` is the sole accepted repo-native LLM credential input
5. direct, LangGraph, control-plane diagnostics, and auxiliary LLM calls share one resolver and availability semantics
6. active runtime and adapter mappings contain no `OPENAI_API_KEY` projection
7. active runtime templates, Compose, setup docs, and control-plane source contain no GCP/BigQuery config
8. local `.env` is migrated but remains ignored, unprinted, and uncommitted
9. focused tests, Compose validation, validators, generated-output checks, and GitNexus change detection pass

Canonical source-of-truth:

<LINK>
- `docs/superpowers/specs/2026-07-14-12-13-fitcv-llm-runtime-spine-master-spec.md`
- `docs/superpowers/specs/2026-07-14-17-39-fitcv-llm-runtime-spine-phase-3-shared-runtime-contract-spec.md`
- `docs/operating_system/governance/repo-governance.md`
- `scripts/validate_planning_lifecycle.py`
</LINK>
