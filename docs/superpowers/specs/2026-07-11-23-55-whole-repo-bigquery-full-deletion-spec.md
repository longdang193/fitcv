---
layer: change
artifact_type: spec
status: active
template_id: detailed-specification
name: whole-repo-bigquery-full-deletion
parent_thread: workstream-operator-control-plane.operator-control-plane-phase-2-degraded-mode-and-portability-surface
targets:
  - src/fitcv/config.py
  - src/fitcv/config_compat.py
  - src/fitcv/persistence.py
  - src/fitcv/shortlist_runtime.py
  - src/fitcv/ai_score.py
  - src/fitcv/gap_analysis.py
  - src/fitcv/ranking.py
  - src/fitcv/rule_filter.py
  - src/fitcv/tracker.py
  - src/fitcv/ingest.py
  - src/fitcv/candidate.py
  - src/fitcv/evidence.py
  - src/fitcv/enrich.py
  - src/fitcv/embeddings.py
  - src/fitcv/vector_search.py
  - src/fitcv/pipeline.py
  - src/fitcv_cp/worker_job.py
  - config/env.yaml
  - config/env.forced_fresh_probe.yaml
  - pyproject.toml
  - uv.lock
  - docker-compose.yml
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

# Detailed Spec: Whole-repo BigQuery removal

## Goal

Remove BigQuery as supported repo concept, not only as control-plane backend.
Keep product direction SQLite-only. Remove live BigQuery runtime code, dependency
ownership, startup/config surfaces, and tests that still describe dual-backend
behavior.

## Key Deliverables

### Deliverable 1: Runtime surfaces are SQLite-only

Active source modules no longer construct, import, or branch into BigQuery-backed runtime behavior.

### Deliverable 2: Config and dependencies stop advertising BigQuery

Shipped config, manifests, and lock data no longer present BigQuery as supported setup.

### Deliverable 3: Tests and docs match shipped product truth

Regression coverage and supported docs describe SQLite-only behavior instead of historical backend parity.

## Task/Wave Breakdown

### Wave 1: Source-first analysis

**Purpose:**
- confirm remaining live BigQuery/runtime residue across source, config, tests, and docs

**Steps:**
- [x] inspect active runtime modules for BigQuery helpers and backend branching
- [x] inspect shipped config and dependency surfaces for BigQuery-era keys
- [x] inspect tests/docs for backend-parity assumptions

**Verification:**
- [x] remaining live BigQuery scope is explicit and bounded

**Exit Criteria:**
- no deletion decision depends on hidden backend paths

### Wave 2: Decision closure

**Purpose:**
- lock SQLite-only replacement shape and delete dead compatibility residue

**Steps:**
- [x] define runtime surfaces to delete versus keep
- [x] define config compatibility policy for retired keys
- [x] define test/doc rewrites needed for SQLite-only truth

**Verification:**
- [x] decisions preserve shipped SQLite behavior while removing dead BigQuery support

**Exit Criteria:**
- implementation scope is concrete and deletion-safe

### Wave 3: Validation and approval readiness

**Purpose:**
- make proof expectations explicit before and during execution

**Steps:**
- [x] define focused regression suite
- [x] define manifest/config grep proof for BigQuery deletion
- [x] define generated-surface refresh expectations

**Verification:**
- [x] validation plan can prove whole-repo BigQuery removal without relying on manual interpretation

**Exit Criteria:**
- spec is ready for implementation and closeout validation

## Triage

Layer: change
Feature type: REPLACE
Summary: replace remaining BigQuery-era runtime and test surfaces with SQLite-only truth
Reasoning: BigQuery is not product direction; retention only adds dead code, stale tests, config drift, and false operator expectations
Invariants:
  - supported persistence path stays SQLite-only
  - startup surfaces do not require BigQuery config
  - pipeline behavior stays unchanged for SQLite/local execution
  - docs and tests reflect shipped behavior, not historical backend parity
  - generated/lock surfaces refresh from current sources after edits
Dependencies:
  - prior SQLite-only runtime cut already landed
Affected stages:
  - none
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

1. No live source module imports or builds a BigQuery client.
2. No live runtime path branches on `FITCV_CP_DATA_BACKEND`.
3. Pipeline persistence helpers use SQLite-only naming and behavior.
4. `config/env.yaml` and `config/env.forced_fresh_probe.yaml` no longer advertise BigQuery keys.
5. `pyproject.toml` and `uv.lock` no longer retain BigQuery through direct or transitive dependency ownership.
6. Supported docs stop describing BigQuery-era operator setup.
7. Obsolete dual-backend and BigQuery-client tests are removed or rewritten to SQLite-only truth.
8. Focused touched regression suites pass.

## Non-Goals

- remove domain vocabulary like BigQuery as job skill text
- rewrite business fixtures that mention candidate experience with BigQuery
- erase archive or historical audit artifacts under excluded doc trees

## Design Decisions

### Decision: delete dead dependency chain

- choice: remove unused `google-cloud-aiplatform` dependency so `uv.lock` also drops transitive `google-cloud-bigquery`
- reason: embeddings path is already deterministic local and no longer needs Vertex embedding client

### Decision: keep explicit obsolete-key stripping

- choice: keep config loader dropping retired `bigquery_dataset` and `service_account_key` keys
- reason: old local env files should not silently leak removed backend keys back into runtime snapshots

### Decision: delete parity tests, keep SQLite contract tests

- choice: remove tests whose only value was BigQuery or backend-parity behavior
- reason: repo should prove shipped behavior only


## Invariants

- supported persistence path stays SQLite-only
- startup and config surfaces do not require BigQuery settings
- active runtime behavior stays unchanged for SQLite/local execution
- docs and tests reflect shipped behavior, not historical backend parity
- generated surfaces refresh from current sources after edits


## Validation Plan

- proof target: live runtime no longer depends on BigQuery
  - method: source inspection plus focused regression tests
  - evidence: no active module imports/builds BigQuery client and touched suites pass
- proof target: shipped setup no longer advertises BigQuery
  - method: grep config/manifests/docs plus lock refresh
  - evidence: no supported config or dependency surface retains BigQuery support keys or packages
- proof target: planning/discovery surfaces stay consistent
  - method: regenerate lineage/docs validators
  - evidence: generated files refresh cleanly and validators pass


## Completion Criteria

A specification item is considered complete when:

1. all Key Deliverables are satisfied
2. all downstream/child items are terminal
3. every child item is completed or dropped

Canonical source-of-truth:

<LINK>
- docs/operating_system/governance/repo-governance.md
- scripts/validate_planning_lifecycle.py
</LINK>
