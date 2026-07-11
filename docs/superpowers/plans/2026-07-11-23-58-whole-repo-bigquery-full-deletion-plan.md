---
layer: change
artifact_type: plan
status: active
template_id: implementation-plan
name: whole-repo-bigquery-full-deletion
parent_thread: workstream-operator-control-plane.operator-control-plane-phase-2-degraded-mode-and-portability-surface
parent_spec: docs/superpowers/specs/2026-07-11-23-55-whole-repo-bigquery-full-deletion-spec.md
targets:
  - src/fitcv/config.py
  - src/fitcv/config_compat.py
  - src/fitcv/embeddings.py
  - src/fitcv/evidence.py
  - src/fitcv/gap_analysis.py
  - src/fitcv/ranking.py
  - config/env.yaml
  - config/env.forced_fresh_probe.yaml
  - pyproject.toml
  - uv.lock
  - docs/configuration.md
  - docs/pipeline.md
  - tests/test_config.py
  - tests/test_embeddings.py
  - tests/test_enrich.py
  - tests/test_evidence.py
  - tests/test_gap_analysis.py
  - tests/test_rule_filter.py
  - tests/test_tracker.py
  - tests/test_vector_search.py
  - tests/test_persistence_contract.py
related_features: []
related_stages: []
---

## Goal

Land whole-repo SQLite-only cleanup so runtime, config, docs, dependencies, and
tests all match shipped product truth.

## Key Deliverables

### Deliverable 1: Runtime and config surfaces are SQLite-only

Config loading strips retired BigQuery-era keys, dead BigQuery naming is gone
from active runtime modules, and startup/config files no longer advertise
BigQuery settings.

### Deliverable 2: Dependency and test surfaces match current behavior

Dead Vertex/BigQuery dependency chain is removed from manifest/lock, and tests
prove SQLite/local behavior instead of backend parity.

### Deliverable 3: Product docs and planning artifacts reflect final scope

Docs describe SQLite-only operation and bounded change artifacts state the whole-
repo removal scope truthfully.

## Task/Wave Breakdown

### Task 1: Remove runtime residue

**Purpose:**
- delete dead BigQuery-era helpers, names, and comments from active source

**Files:**
- Modify: `src/fitcv/config.py`
- Modify: `src/fitcv/config_compat.py`
- Modify: `src/fitcv/evidence.py`
- Modify: `src/fitcv/gap_analysis.py`
- Modify: `src/fitcv/ranking.py`
- Modify: `src/fitcv/embeddings.py`

**Preconditions:**
- SQLite-only runtime path already exists

**Steps:**
- [x] Step 1: rename/remove stale BigQuery-era helper names in active source.
- [x] Step 2: keep only SQLite/local embedding and persistence behavior.
- [x] Step 3: preserve explicit retired-key stripping in config loading.

**Verification:**
- [x] `py -3 -m py_compile src/fitcv/config.py src/fitcv/config_compat.py src/fitcv/evidence.py src/fitcv/gap_analysis.py src/fitcv/ranking.py src/fitcv/embeddings.py`

**Exit Criteria:**
- no live runtime code depends on BigQuery client or backend switching

### Task 2: Remove config and dependency residue

**Purpose:**
- remove BigQuery-era operator config and direct/transitive dependency ownership

**Files:**
- Modify: `config/env.yaml`
- Modify: `config/env.forced_fresh_probe.yaml`
- Modify: `pyproject.toml`
- Modify: `uv.lock`
- Modify: `docker-compose.yml`

**Preconditions:**
- Task 1 complete

**Steps:**
- [x] Step 1: delete BigQuery keys from shipped config files and compose env.
- [x] Step 2: remove dead `google-cloud-aiplatform` dependency.
- [x] Step 3: refresh `uv.lock` so transitive `google-cloud-bigquery` disappears.

**Verification:**
- [x] `uv lock`
- [x] `rg -n -i "google-cloud-bigquery|FITCV_CP_DATA_BACKEND|bigquery_dataset|service_account_key" pyproject.toml uv.lock config docker-compose.yml`

**Exit Criteria:**
- shipped config/manifests no longer advertise BigQuery support

### Task 3: Rewrite tests to SQLite-only truth

**Purpose:**
- delete obsolete parity coverage and keep only active behavior checks

**Files:**
- Modify: `tests/test_config.py`
- Modify: `tests/test_embeddings.py`
- Modify: `tests/test_enrich.py`
- Modify: `tests/test_evidence.py`
- Modify: `tests/test_gap_analysis.py`
- Modify: `tests/test_rule_filter.py`
- Modify: `tests/test_tracker.py`
- Modify: `tests/test_vector_search.py`
- Modify: `tests/test_persistence_contract.py`
- Modify: `tests/test_fitcv_cp/test_control_plane_config.py`

**Preconditions:**
- Tasks 1-2 complete

**Steps:**
- [x] Step 1: remove tests that only prove BigQuery or dual-backend behavior.
- [x] Step 2: update config fixtures to current repo defaults.
- [x] Step 3: harden remaining SQLite assertions against suite-order noise.

**Verification:**
- [x] `py -3 -m pytest tests/test_ingest.py tests/test_candidate.py tests/test_vector_search.py tests/test_config.py tests/test_fitcv_cp/test_control_plane_config.py tests/test_fitcv_cp/test_main.py tests/test_fitcv_cp/test_worker_job.py tests/test_ai_score.py tests/test_embeddings.py tests/test_enrich.py tests/test_evidence.py tests/test_gap_analysis.py tests/test_rule_filter.py tests/test_tracker.py tests/test_persistence_contract.py -q`

**Exit Criteria:**
- touched regression suites pass without BigQuery-era assumptions

### Task 4: Update docs and planning artifacts

**Purpose:**
- capture whole-repo scope truthfully in docs/spec/plan surfaces

**Files:**
- Modify: `docs/configuration.md`
- Modify: `docs/pipeline.md`
- Modify: `docs/superpowers/specs/2026-07-11-23-55-whole-repo-bigquery-full-deletion-spec.md`
- Modify: `docs/superpowers/plans/2026-07-11-23-58-whole-repo-bigquery-full-deletion-plan.md`

**Preconditions:**
- Tasks 1-3 complete

**Steps:**
- [x] Step 1: remove stale BigQuery setup wording from supported docs.
- [x] Step 2: write truthful whole-repo spec and plan artifacts.
- [ ] Step 3: refresh generated planning/discovery surfaces if needed.

**Verification:**
- [ ] `py -3 scripts/generate_planning_lineage.py`
- [ ] `py -3 tools/docs/generate_architecture_metadata.py`

**Exit Criteria:**
- docs and planning artifacts describe final SQLite-only repo truth

## Verification

- `py -3 -m pytest tests/test_ingest.py tests/test_candidate.py tests/test_vector_search.py tests/test_config.py tests/test_fitcv_cp/test_control_plane_config.py tests/test_fitcv_cp/test_main.py tests/test_fitcv_cp/test_worker_job.py tests/test_ai_score.py tests/test_embeddings.py tests/test_enrich.py tests/test_evidence.py tests/test_gap_analysis.py tests/test_rule_filter.py tests/test_tracker.py tests/test_persistence_contract.py -q`
- `uv lock`
- `rg -n -i "google-cloud-bigquery|google\.cloud\.bigquery|bigquery_client|build_bigquery_client|FITCV_CP_DATA_BACKEND|load_to_bigquery|load_candidate_to_bigquery|bq_store" src tests config docs pyproject.toml uv.lock start_web.ps1 start_worker.ps1 docker-compose.yml -g '!docs/superpowers/**' -g '!docs/intent/**' -g '!docs/operating_system/**'`

## Completion Criteria

1. all Key Deliverables are satisfied
2. all downstream/child items are terminal
3. every child item is `completed` or `dropped`
