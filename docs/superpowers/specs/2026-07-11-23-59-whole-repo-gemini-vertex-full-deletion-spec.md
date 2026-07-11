---
layer: change
artifact_type: spec
status: active
template_id: detailed-specification
name: whole-repo-gemini-vertex-full-deletion
parent_thread: workstream-operator-control-plane.operator-control-plane-phase-2-degraded-mode-and-portability-surface
targets:
  - src/fitcv/config.py
  - src/fitcv/ai_score.py
  - src/fitcv/enrich.py
  - src/fitcv/cv_generator.py
  - src/fitcv/runtime_routing.py
  - src/fitcv/agentic_cv_generation.py
  - src/fitcv/pipeline.py
  - src/fitcv/pipeline_stage_artifacts.py
  - src/fitcv_cp/worker_job.py
  - config/policy/cv.yaml
  - config/runtime/pipeline.yaml
  - config/runtime/control_plane.yaml
  - pyproject.toml
  - uv.lock
  - docs/configuration.md
  - docs/pipeline.md
  - docs/api.md
  - tests/test_config.py
  - tests/test_ai_score.py
  - tests/test_enrich.py
  - tests/test_cv_generator.py
  - tests/test_pipeline.py
  - tests/test_fitcv_cp/test_control_plane_config.py
  - tests/test_fitcv_cp/test_main.py
  - tests/test_fitcv_cp/test_worker_job.py
related_features: []
related_stages: []
---

# Detailed Spec: Whole-repo Gemini / Vertex AI removal

## Goal

Remove Gemini and Vertex AI as supported runtime providers across whole repo.
Keep generic OpenAI-compatible provider routing and SQLite/local data paths.
Delete native Google client code, Google-specific config/env surfaces, Google
dependency ownership, and tests/docs that still describe Gemini or Vertex AI as
shipped behavior.

## Key Deliverables

### Deliverable 1: Runtime provider path is Google-free

Active runtime code no longer imports `google.genai`, `google.auth`, or
Google-specific client error/types modules, and no stage falls back to a
Gemini-native or Vertex-native client path.

### Deliverable 2: Config and dependency surfaces are provider-neutral

Active config and dependency manifests no longer expose `gemini_model`,
`vertex_location`, `GEMINI_API_KEY`, or `GOOGLE_APPLICATION_CREDENTIALS` as
supported product setup.

### Deliverable 3: Tests and docs match final provider truth

Tests, operator docs, and runtime provenance text describe only supported
non-Google provider paths.

## Authoritative Ownership

### Runtime provider and model ownership

- `control_plane.model_routing.parts.enrich_extraction` is the SSOT owner for
  enrich provider + model routing.
- `control_plane.model_routing.parts.ranking_ai_score` is the SSOT owner for
  ranking provider + model routing.
- `control_plane.model_routing.parts.cv_generation_structured_write` is the
  SSOT owner for CV generation provider + model routing.
- `config/runtime/control_plane.yaml` is the canonical config surface for active
  provider ids, wire API, base URL, and stage model routing.

### Retired ownership

- `config/runtime/pipeline.yaml` no longer owns `gemini_model` after this change.
- `config/policy/cv.yaml` no longer owns a provider-branded model default after
  this change.
- `get_gemini_model(...)` and `get_vertex_location(...)` do not survive as active
  runtime ownership helpers.

### Env override policy

- Keep existing generic LangGraph env overrides only when provider-neutral:
  `FITCV_LANGGRAPH_PROVIDER`, `FITCV_LANGGRAPH_MODEL`,
  `FITCV_LANGGRAPH_OPENAI_BASE_URL`, and `FITCV_LANGGRAPH_WIRE_API`.
- Retire Google-specific auth envs from supported runtime contract:
  `GEMINI_API_KEY` and `GOOGLE_APPLICATION_CREDENTIALS`.

### Surviving provider contract

- Allowed active provider ids: `openai`, `openai_compatible`, `9router`.
- Allowed wire APIs: existing OpenAI-compatible HTTP paths already supported by
  runtime code.
- Google-branded provider ids or Google-native fallback branches are invalid
  after this change.

## Task/Wave Breakdown

### Wave 1: Source-first analysis

**Purpose:**
- bound every live Gemini / Vertex AI runtime seam before deletion

**Steps:**
- [x] inspect provider-routing, scoring, enrichment, and CV-generation call paths
- [x] inspect config helpers and stage provenance helpers for Gemini / Vertex naming
- [x] inspect tests, manifests, and supported docs for Google-provider assumptions

**Verification:**
- [x] high-risk symbols and low-risk leaf clients are explicitly identified

**Exit Criteria:**
- no deletion step depends on unstated provider fallback behavior

### Wave 2: Decision closure

**Purpose:**
- lock exact replacement shape before code deletion

**Steps:**
- [x] keep generic `resolve_model_routing_part(...)` routing surface
- [x] delete Gemini-native / Vertex-native client implementations instead of wrapping them
- [x] replace Gemini-named config ownership with provider-neutral stage ownership
- [x] define exact retired-key and invalid-provider behavior at config boundary

**Verification:**
- [x] chosen shape preserves non-Google provider routing while removing Google-only runtime branches

**Exit Criteria:**
- implementation scope is exact enough to execute without re-deciding provider policy mid-patch

### Wave 3: Validation and approval readiness

**Purpose:**
- make deletion proof explicit for high-risk runtime surfaces

**Steps:**
- [x] define runtime grep proof for Google import/env/config deletion
- [x] define focused regression suites for scoring, enrichment, CV generation, routing, and worker execution
- [x] define generated-surface and repo-validator refresh requirements

**Verification:**
- [x] validation plan can prove whole-repo Gemini / Vertex removal without relying on manual interpretation

**Exit Criteria:**
- spec is ready for implementation planning

## Triage

Layer: change
Feature type: REPLACE
Summary: replace Gemini / Vertex-native runtime with provider-neutral OpenAI-compatible-only runtime
Reasoning: Gemini / Vertex retention is no longer product direction and now adds provider drift, config noise, dead branches, and misleading operator setup
Invariants:
  - SQLite/local data path stays unchanged
  - generic routing surface may stay if it still serves non-Google providers
  - structured scoring, enrichment, and CV generation remain available through supported non-Google provider paths
  - docs and tests reflect shipped provider truth, not historical Google compatibility
  - generated/lock surfaces refresh from current sources after edits
Dependencies:
  - whole-repo BigQuery removal already landed or is landing in same branch
Risk anchors:
  - `src/fitcv/config.py:253` `resolve_model_routing_part` has CRITICAL upstream blast radius
  - `src/fitcv/config.py:1142` `get_vertex_location` has CRITICAL upstream blast radius
  - `src/fitcv/config.py:1210` `get_gemini_model` has HIGH upstream blast radius
  - `src/fitcv/ai_score.py:221` `_make_genai_client` is low-risk leaf deletion candidate
  - `src/fitcv/enrich.py:1606` `_make_genai_client` is low-risk leaf deletion candidate
Affected stages:
  - enrich_extraction
  - ranking_ai_score
  - cv_generation
Affected features:
  - none
Primary lens: cross-cutting
Affected docs:
  feature_source: none
  feature_yaml: none
  feature_lineage: none
  feature_history: none
  stage_source: none
  stage_contract: none
  feature_docs: none
  cross_cutting_docs:
    - docs/configuration.md
    - docs/pipeline.md
    - docs/api.md
  readme: none
  generated:
    - uv.lock
Generated refresh required: yes
Capability IDs:
  - none
Invariant IDs:
  - none
Spec needed: yes
Plan needed: yes

## Acceptance Criteria

1. No active source module imports `google.genai`, `google.auth`,
   `google.api_core`, or Google-provider client error/types helpers.
2. No active runtime path reads `GEMINI_API_KEY` or
   `GOOGLE_APPLICATION_CREDENTIALS` as supported provider auth.
3. No active config surface owns `gemini_model` or `vertex_location`.
4. `pyproject.toml` and `uv.lock` no longer retain `google-genai` through direct
   dependency ownership.
5. `ai_score`, `enrich`, and `cv_generator` run only through supported
   non-Google provider clients.
6. Worker/runtime provenance and operator-facing status text no longer describe
   Gemini or Vertex AI as supported provider paths.
7. Google-branded provider ids in active routing config fail deterministically at
   config/runtime boundary with one documented error path.
8. Retired Google config keys do not survive into loaded runtime config,
   effective-settings snapshots, or stage provenance payloads.
9. Focused regression suites include one positive surviving-provider routing case
   and one negative Google-provider rejection case.
10. Focused regression suites pass for config, scoring, enrichment, CV
    generation, pipeline routing, and worker execution.
11. Repo fast validator passes after doc/generated refresh.

## Non-Goals

- remove Gemini or Vertex AI from business data, scraped job text, candidate text,
  or skill taxonomy where those words are domain content
- erase archived audit artifacts or historical docs under excluded archive /
  intent / operating-system trees
- redesign generic provider-routing architecture beyond what is required to
  remove Google-native runtime paths

## Design Decisions

### Decision: keep routing abstraction, delete Google-native branches

- context: provider routing is shared across scoring, enrichment, and CV generation,
  but Gemini / Vertex-native clients are only one provider family behind that shared seam.
- choice: keep `resolve_model_routing_part(...)` and related generic routing helpers,
  but delete Google-native client creation and Google-specific fallback logic.
- alternatives considered:
  - delete whole routing layer and hard-wire one provider path
  - keep Google-native branches behind deprecated compatibility flags
- impact:
  - smallest safe root-cause change for broad provider drift
  - preserves non-Google runtime portability
  - avoids legacy-only Google fallback branches

### Decision: delete Gemini-specific config names, not alias them forever

- context: `gemini_model` and `vertex_location` encode dead provider ownership
  into active config and tests.
- choice: remove active ownership of `gemini_model` and `vertex_location`; use
  provider-neutral stage config and routed model ownership instead.
- alternatives considered:
  - keep Gemini-named keys as permanent aliases
  - keep Google keys but ignore them at runtime
- impact:
  - supported config matches final product direction
  - docs and tests stop teaching dead Google setup
  - migration is explicit instead of silent legacy retention

### Decision: fail fast on Google provider ids at config boundary

- context: deletion is not complete if active routing config can still resolve a
  Google provider name and fail later at execution time.
- choice: reject Google-branded provider ids during routing/config resolution with
  one deterministic error path.
- alternatives considered:
  - allow Google provider ids but fail later when client creation runs
  - silently remap Google provider ids to a surviving provider
- impact:
  - one SSOT rejection path
  - clearer operator error than deferred runtime failure
  - no hidden compatibility aliasing

### Decision: strip retired Google keys at config-load boundary

- context: old env/config files and tests may still carry `gemini_model` or
  `vertex_location`, and Google auth envs may still be present in operator shells.
- choice: remove retired Google config keys from loaded config and keep Google auth
  env vars out of supported runtime behavior.
- alternatives considered:
  - preserve keys as ignored legacy noise forever
  - preserve keys in effective-settings snapshots for audit history
- impact:
  - runtime snapshots reflect active product contract only
  - one boundary owns migration cleanup
  - test fixtures move to surviving routing keys instead of dead aliases

### Decision: remove `google-genai` dependency instead of adapter shim

- context: once Google-native clients are deleted, direct dependency ownership
  remains only as drift.
- choice: remove `google-genai` from manifest and lock.
- alternatives considered:
  - keep package installed for hypothetical future reuse
  - hide package behind wrapper abstraction
- impact:
  - fewer transitive dependencies
  - no false signal that Google runtime remains supported

## Invariants

- SQLite/local data path remains unchanged
- supported scoring, enrichment, and CV generation behavior remains available
  through non-Google provider paths
- generic provider-routing helpers remain only if they still serve active providers
- no active runtime surface advertises Google-specific auth or model ownership
- Google provider ids fail at config/routing boundary, not later in stage execution
- retired Google config keys do not survive load/merge/snapshot boundaries
- generated surfaces refresh from current sources after edits

## Validation Plan

- proof target: live runtime is Google-free
  - method: grep active source for `google.genai`, `google.auth`, `google.api_core`,
    `GEMINI_API_KEY`, `GOOGLE_APPLICATION_CREDENTIALS`, `gemini_model`, and `vertex_location`
  - evidence: no active runtime hits remain outside allowed historical/doc exclusions
- proof target: supported provider behavior still works
  - method: run focused tests for config, scoring, enrichment, CV generation,
    pipeline routing, and worker execution
  - evidence: targeted suites pass without Google-specific fixtures or branches
- proof target: Google provider paths are rejected uniformly
  - method: add one negative routing/config test for Google provider ids and one
    negative load/snapshot test for retired Google keys
  - evidence: failure happens at config/runtime boundary with one documented error
    and retired keys do not appear in effective runtime config
- proof target: supported docs/manifests match product truth
  - method: inspect `pyproject.toml`, `uv.lock`, `config/policy/cv.yaml`,
    `config/runtime/pipeline.yaml`, `config/runtime/control_plane.yaml`, and supported docs
  - evidence: no supported manifest/doc surface teaches Gemini or Vertex AI setup
- proof target: planning/discovery surfaces stay valid
  - method: regenerate lineage/metadata surfaces and run fast validator
  - evidence: generated outputs refresh cleanly and repo validator passes

## Completion Criteria

A specification item is considered complete when:

1. all Key Deliverables are satisfied
2. all downstream/child items are terminal
3. every child item is `completed` or `dropped`

Canonical source-of-truth:

<LINK>
- `docs/operating_system/governance/repo-governance.md`
- `scripts/validate_planning_lifecycle.py`
</LINK>
