---
layer: change
artifact_type: spec
status: proposed
template_id: detailed-specification
name: config-razor-ssot-simplification
parent_thread: workstream-fitcv-semantic-spine.semantic-spine-component-boundary-and-interface-contract
targets:
  - config/env.yaml
  - config/runtime/control_plane.yaml
  - config/runtime/pipeline.yaml
  - config/live_smoke.yaml
  - src/fitcv/config.py
  - docs/configuration.md
  - tests/test_config.py
related_features:
  - settings_system
  - cv_system
related_stages:
  - enrich
  - ranking
  - cv_generation
---

## Goal

Apply Razor principle and single-source-of-truth rules to `config/` so users can predict exactly where to edit backend, model routing, and pipeline behavior without duplicate or conflicting keys.

## Key Deliverables

### Deliverable 1: Canonical ownership map is strict and minimal

Config ownership is reduced to one canonical file per concern:

- backend/provider/model routing -> `config/runtime/control_plane.yaml`
- pipeline numeric/runtime knobs -> `config/runtime/pipeline.yaml`
- infra bridge keys -> `config/env.yaml`

### Deliverable 2: `config/live_smoke.yaml` is removed

`config/live_smoke.yaml` is deleted as a canonical surface to eliminate duplicate model/runtime declarations and reduce user confusion.

### Deliverable 3: Model key semantics are provider-agnostic and non-duplicated

No brand-specific model-owner ambiguity remains across config files (`gemini_model` style ownership ambiguity removed or downgraded to non-owner compatibility path).

### Deliverable 4: Loader and docs enforce SSOT behavior

Loader rules, docs, and tests explicitly enforce one-owner-per-key-family behavior and fail/warn on duplicate ownership regressions.

## Task/Wave Breakdown

### Wave 1: Source-first analysis

**Purpose:**
- baseline current config duplication and ownership drift before edits

**Steps:**
- [ ] inventory all model/backend/runtime keys across `config/`
- [ ] classify keys by canonical owner vs duplicate vs legacy-compat
- [ ] map active runtime consumers in `src/fitcv/config.py` and related loaders

**Verification:**
- [ ] each ownership claim has source file/line evidence

**Exit Criteria:**
- no design decision depends on ambiguous ownership assumptions

### Wave 2: Razor ownership closure

**Purpose:**
- remove non-essential config surfaces and enforce one obvious edit path

**Steps:**
- [ ] delete `config/live_smoke.yaml`
- [ ] remove or relocate duplicated model/runtime declarations so canonical ownership remains only in runtime files
- [ ] keep `config/env.yaml` restricted to infra bridge intent and approved compatibility keys only
- [ ] tighten loader merge/compat rules to reject silent re-expansion of duplicate ownership

**Verification:**
- [ ] repo scan shows no deleted surface references requiring runtime behavior
- [ ] no duplicate owner keys remain across canonical config surfaces

**Exit Criteria:**
- one config location per concern is enforceable and documented

### Wave 3: Validation and handoff readiness

**Purpose:**
- prove non-regressive behavior and operator clarity after simplification

**Steps:**
- [ ] update `docs/configuration.md` with single-owner edit guide
- [ ] add/adjust tests for ownership invariants and deleted-surface contract
- [ ] run targeted runtime/config validation and one bounded live run evidence check

**Verification:**
- [ ] all acceptance criteria have explicit proof artifacts

**Exit Criteria:**
- spec is implementation-plan ready with no unresolved ownership ambiguity

## Design Decisions

### Decision: Remove `config/live_smoke.yaml` instead of preserving profile overlays

- context: duplicate profile-like files create hidden precedence and user confusion
- choice: delete `config/live_smoke.yaml` in this bounded change
- alternatives considered:
  - keep as optional profile overlay with strict allowlist
  - keep unchanged and rely on docs-only clarification
- impact:
  - lowers cognitive load for app users
  - removes one drift vector across model/runtime keys

### Decision: Model ownership lives in routing config, not mixed runtime/env surfaces

- context: users conflate provider route, model id, and backend infra when keys appear in multiple places
- choice: treat `control_plane.model_routing.parts.*.model` as model-routing owner; pipeline keeps only non-routing runtime knobs
- alternatives considered:
  - keep model keys duplicated in pipeline/env for convenience
- impact:
  - provider-agnostic semantics become explicit
  - fewer contradictory edits and clearer run-time provenance

### Decision: Keep infra bridge keys in `env.yaml` only

- context: backend mode and credentials are operational concerns separate from stage tuning
- choice: constrain `env.yaml` to infra bridge contract (`gcp_project`, `bigquery_dataset`, `service_account_key`, location keys)
- alternatives considered:
  - move infra keys into pipeline or control-plane routing surfaces
- impact:
  - clean separation between infra identity and model/stage behavior
  - easier onboarding for users selecting BigQuery vs sqlite

### Decision: Enforce SSOT with validator + tests, not docs alone

- context: docs-only guidance drifts over time
- choice: add validator/test checks for duplicate ownership and deleted-surface regression
- alternatives considered:
  - warning-only logs
- impact:
  - prevents regression back to multi-owner config contract

## Invariants

- one key family has one canonical config owner
- deleted `config/live_smoke.yaml` does not remain as hidden runtime dependency
- runtime behavior remains deterministic under documented load order
- backend infra keys stay separated from stage/pipeline behavior keys
- config semantics remain provider-agnostic (no brand-name ownership confusion)

## Acceptance Criteria

- `config/live_smoke.yaml` is absent from repository and runtime references
- model routing keys are not duplicated across env/pipeline/canonical routing surfaces
- `docs/configuration.md` includes a concise “edit-here” ownership table for backend, model routing, and pipeline knobs
- targeted tests assert deleted-surface and one-owner invariants
- bounded live run evidence confirms settings resolution and stage flow are non-regressive

## Non-Goals

- redesigning ranking or CV policy logic
- changing model quality thresholds or business scoring semantics
- broad control-plane UI redesign in this spec
- repo-wide cleanup of unrelated planning metadata drift

## Risks and Mitigations

- risk: deleting `live_smoke.yaml` breaks hidden local workflows
  - mitigation: run reference scan + targeted smoke run before closure
- risk: removing duplicate model keys changes expected fallback behavior
  - mitigation: codify explicit fallback/owner rule in loader tests
- risk: users still confuse backend infra vs model routing
  - mitigation: add explicit owner matrix and “if you want X, edit Y” guide in `docs/configuration.md`

## Validation Plan

- proof target: `live_smoke.yaml` is fully retired
  - method: static path/reference scan
  - evidence: `rg` output showing no active runtime references

- proof target: canonical owner map has no duplicate model/runtime key families
  - method: config diff + ownership scan
  - evidence: key-family ownership report attached to plan/checkpoint artifacts

- proof target: loader enforces SSOT boundaries
  - method: targeted `tests/test_config.py` invariants
  - evidence: passing test output for SSOT/deleted-surface cases

- proof target: runtime behavior non-regressive
  - method: one bounded live run with settings/artifact inspection
  - evidence: run status + `settings-used.json` + `cv_analysis.json`

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
