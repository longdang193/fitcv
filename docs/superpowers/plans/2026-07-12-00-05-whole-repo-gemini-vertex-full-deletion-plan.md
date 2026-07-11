---
layer: change
artifact_type: plan
status: active
template_id: implementation-plan
name: whole-repo-gemini-vertex-full-deletion
parent_thread: workstream-operator-control-plane.operator-control-plane-phase-2-degraded-mode-and-portability-surface
parent_spec: docs/superpowers/specs/2026-07-11-23-59-whole-repo-gemini-vertex-full-deletion-spec.md
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

## Goal

Delete Gemini / Vertex-native runtime support across whole repo while keeping
active non-Google provider routing, stage execution, docs, and tests aligned to
one provider-neutral contract.

## Key Deliverables

### Deliverable 1: Runtime routing is Google-free and deterministic

Active runtime code no longer imports or builds Google-native clients, and
Google provider ids fail at config/routing boundary instead of during stage
execution.

### Deliverable 2: Config and manifests match final provider SSOT

Active config removes Google-branded model ownership, keeps provider/model SSOT
in control-plane routing, and manifest/lock files drop `google-genai`.

### Deliverable 3: Regression proof matches shipped provider truth

Focused tests prove surviving provider routing still works, retired Google keys
do not survive config load/snapshot boundaries, and supported docs no longer
teach Gemini / Vertex setup.

## Task/Wave Breakdown

### Task 1: Normalize provider ownership and retirement policy

**Purpose:**
- move active model/provider ownership to one SSOT and define one boundary for retired Google keys and provider ids

**Files:**
- Inspect: `src/fitcv/config.py`
- Inspect: `src/fitcv/runtime_routing.py`
- Modify: `src/fitcv/config.py`
- Modify: `src/fitcv/runtime_routing.py`
- Modify: `config/runtime/pipeline.yaml`
- Modify: `config/runtime/control_plane.yaml`
- Modify: `config/policy/cv.yaml`
- Verify: `tests/test_config.py`
- Verify: `tests/test_fitcv_cp/test_control_plane_config.py`

**Preconditions:**
- approved spec defines surviving provider ids and retired-key policy

**Steps:**
- [ ] Step 1: remove active `gemini_model` / `vertex_location` ownership from config surfaces.
- [ ] Step 2: keep stage model/provider SSOT in `control_plane.model_routing.parts.*`.
- [ ] Step 3: reject Google provider ids during routing/config resolution with one deterministic error path.
- [ ] Step 4: strip retired Google keys from loaded runtime config and snapshots.

**Verification:**
- [ ] `py -3 -m pytest tests/test_config.py tests/test_fitcv_cp/test_control_plane_config.py -q`

**Exit Criteria:**
- one active provider/model SSOT exists and no loaded config keeps Google-branded ownership

### Task 2: Delete Google-native runtime clients and fallbacks

**Purpose:**
- remove Google-native execution branches while keeping surviving provider execution intact

**Files:**
- Inspect: `src/fitcv/ai_score.py`
- Inspect: `src/fitcv/enrich.py`
- Inspect: `src/fitcv/cv_generator.py`
- Inspect: `src/fitcv/agentic_cv_generation.py`
- Inspect: `src/fitcv/pipeline.py`
- Inspect: `src/fitcv/pipeline_stage_artifacts.py`
- Inspect: `src/fitcv_cp/worker_job.py`
- Modify: `src/fitcv/ai_score.py`
- Modify: `src/fitcv/enrich.py`
- Modify: `src/fitcv/cv_generator.py`
- Modify: `src/fitcv/agentic_cv_generation.py`
- Modify: `src/fitcv/pipeline.py`
- Modify: `src/fitcv/pipeline_stage_artifacts.py`
- Modify: `src/fitcv_cp/worker_job.py`
- Verify: `tests/test_ai_score.py`
- Verify: `tests/test_enrich.py`
- Verify: `tests/test_cv_generator.py`
- Verify: `tests/test_pipeline.py`
- Verify: `tests/test_fitcv_cp/test_main.py`
- Verify: `tests/test_fitcv_cp/test_worker_job.py`

**Preconditions:**
- Task 1 complete

**Steps:**
- [ ] Step 1: delete `_make_genai_client` Google-native logic and related imports from scoring and enrich paths.
- [ ] Step 2: delete Gemini-native fallback branches from enrich and CV-generation code.
- [ ] Step 3: keep only surviving OpenAI-compatible client paths and provider-neutral provenance text.
- [ ] Step 4: remove dead helper calls to `get_gemini_model(...)` and `get_vertex_location(...)` after callers are migrated.

**Verification:**
- [ ] `py -3 -m pytest tests/test_ai_score.py tests/test_enrich.py tests/test_cv_generator.py tests/test_pipeline.py tests/test_fitcv_cp/test_main.py tests/test_fitcv_cp/test_worker_job.py -q`

**Exit Criteria:**
- no active stage execution path imports or branches into Google-native clients

### Task 3: Rewrite tests to provider-neutral truth

**Purpose:**
- replace Google-specific fixtures with surviving-provider and negative-boundary proof

**Files:**
- Modify: `tests/test_config.py`
- Modify: `tests/test_ai_score.py`
- Modify: `tests/test_enrich.py`
- Modify: `tests/test_cv_generator.py`
- Modify: `tests/test_pipeline.py`
- Modify: `tests/test_fitcv_cp/test_control_plane_config.py`
- Modify: `tests/test_fitcv_cp/test_main.py`
- Modify: `tests/test_fitcv_cp/test_worker_job.py`

**Preconditions:**
- Tasks 1-2 complete

**Steps:**
- [ ] Step 1: delete tests that only prove Gemini API key, Vertex credentials, or `google.genai` client behavior.
- [ ] Step 2: add one positive routing test for surviving provider ids.
- [ ] Step 3: add one negative routing/config test for Google provider ids.
- [ ] Step 4: add one negative config-load/snapshot test proving retired Google keys do not survive.

**Verification:**
- [ ] `py -3 -m pytest tests/test_config.py tests/test_ai_score.py tests/test_enrich.py tests/test_cv_generator.py tests/test_pipeline.py tests/test_fitcv_cp/test_control_plane_config.py tests/test_fitcv_cp/test_main.py tests/test_fitcv_cp/test_worker_job.py -q`

**Exit Criteria:**
- tests lock external provider contract, not historical Google implementation details

### Task 4: Remove dependency/docs residue and refresh generated surfaces

**Purpose:**
- finish manifest, doc, and generated-surface cleanup so repo contract is truthful end-to-end

**Files:**
- Modify: `pyproject.toml`
- Modify: `uv.lock`
- Modify: `docs/configuration.md`
- Modify: `docs/pipeline.md`
- Modify: `docs/api.md`
- Modify: `docs/superpowers/specs/2026-07-11-23-59-whole-repo-gemini-vertex-full-deletion-spec.md`
- Modify: `docs/superpowers/plans/2026-07-12-00-05-whole-repo-gemini-vertex-full-deletion-plan.md`

**Preconditions:**
- Tasks 1-3 complete

**Steps:**
- [ ] Step 1: remove `google-genai` from manifest and refresh lock.
- [ ] Step 2: remove Gemini / Vertex setup wording from supported docs only.
- [ ] Step 3: regenerate planning lineage and any required generated metadata surfaces.

**Verification:**
- [ ] `uv lock`
- [ ] `py -3 scripts/generate_planning_lineage.py`
- [ ] `py -3 scripts/hooks/run_validator.py --fast`

**Exit Criteria:**
- docs, manifests, and generated surfaces all describe final provider truth

## Verification

- `py -3 -m pytest tests/test_config.py tests/test_ai_score.py tests/test_enrich.py tests/test_cv_generator.py tests/test_pipeline.py tests/test_fitcv_cp/test_control_plane_config.py tests/test_fitcv_cp/test_main.py tests/test_fitcv_cp/test_worker_job.py -q`
- `uv lock`
- `rg -n -i "google-genai|google\.genai|google\.auth|google\.api_core|GEMINI_API_KEY|GOOGLE_APPLICATION_CREDENTIALS|gemini_model|vertex_location|vertexai=True" src tests config docs pyproject.toml uv.lock -g '!docs/superpowers/**' -g '!docs/intent/**' -g '!docs/operating_system/**'`
- `py -3 scripts/generate_planning_lineage.py`
- `py -3 scripts/hooks/run_validator.py --fast`

## Completion Criteria

1. all Key Deliverables are satisfied
2. all downstream/child items are terminal
3. every child item is `completed` or `dropped`

Canonical source-of-truth:

<LINK>
- `docs/operating_system/governance/repo-governance.md`
- `scripts/validate_planning_lifecycle.py`
</LINK>
