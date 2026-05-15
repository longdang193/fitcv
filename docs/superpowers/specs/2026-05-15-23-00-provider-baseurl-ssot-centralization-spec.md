---
layer: change
artifact_type: spec
status: proposed
template_id: detailed-specification
name: provider-baseurl-ssot-centralization
parent_thread: workstream-operator-control-plane.operator-control-plane-phase-2-degraded-mode-and-portability-surface
targets:
  - config/runtime/control_plane.yaml
  - .env
  - src/fitcv/config.py
  - src/fitcv_cp/app.py
related_features:
  - admin_control_plane_core
related_stages: []
---

## Goal

Centralize provider routing ownership so `base_url`, `wire_api`, `provider`, and `model` default contract has one canonical owner with explicit override semantics.

## Key Deliverables

### Deliverable 1: Canonical ownership contract

- Declare `config/runtime/control_plane.yaml` as canonical owner for provider routing defaults:
  - `control_plane.providers.*.base_url`
  - `control_plane.providers.*.wire_api`
  - `control_plane.model_routing.parts.*.provider`
  - `control_plane.model_routing.parts.*.model`

### Deliverable 2: Override semantics contract

- Keep `.env` for secrets and optional runtime-local overrides only.
- Define deterministic precedence with source attribution in diagnostics.

## Task/Wave Breakdown

### Wave 1: Source-first analysis

**Purpose:**
- Confirm current consumers and split ownership surfaces.

**Steps:**
- [x] identify canonical routing contract in `control_plane.yaml`
- [x] identify env-based runtime vars in `.env` and compose
- [x] identify ambiguity: duplicate-looking endpoint fields without explicit owner text

**Verification:**
- [x] current-state ambiguity documented with concrete fields and paths

**Exit Criteria:**
- ownership confusion reproducible and scoped

### Wave 2: Decision closure

**Purpose:**
- Select simplest stable contract by razor principle.

**Steps:**
- [x] compare three models:
  - control-plane owner + env override
  - env-only owner
  - control-plane-only strict (no env override)
- [x] select model minimizing concepts while preserving operational flexibility
- [x] define exact ownership and precedence semantics

**Verification:**
- [x] each major design question resolved or explicitly deferred

**Exit Criteria:**
- selected design has one owner and one constrained override path

### Wave 3: Validation and approval readiness

**Purpose:**
- Define proof expectations before implementation planning.

**Steps:**
- [x] define acceptance criteria for ownership and precedence behavior
- [x] define validation proofs and evidence artifacts
- [x] define non-goals and residual risks

**Verification:**
- [x] validation plan can prove contract without broad refactor

**Exit Criteria:**
- spec ready for implementation plan handoff

## Design Decisions

### Decision: Canonical owner is control-plane config

- context: routing contract currently appears in both YAML and env views
- choice: canonical defaults live in `config/runtime/control_plane.yaml`
- alternatives considered:
  - env-only ownership
  - strict control-plane-only no override
- impact:
  - clearer code review and governance ownership
  - repo defaults remain declarative and versioned

### Decision: `.env` is secrets plus optional override channel only

- context: deployment/local flows need safe temporary runtime override
- choice: keep env vars allowed only as optional override path, not default owner
- alternatives considered:
  - remove env routing vars immediately
  - keep current ambiguous split
- impact:
  - preserves operational flexibility
  - removes ownership ambiguity when docs/diagnostics mark override source

### Decision: Deterministic precedence plus fail-fast

- context: ambiguous runtime behavior increases incident/debug cost
- choice: precedence = env override (if set) -> control-plane default -> fail fast
- alternatives considered:
  - silent fallback to other provider/defaults
- impact:
  - explicit behavior and easier debugging
  - prevents hidden cross-provider drift

## Invariants

- `config/runtime/control_plane.yaml` remains single canonical owner for routing defaults.
- `.env` must not be treated as default owner for routing contract fields.
- missing required routing fields after precedence resolution must fail fast.
- diagnostics must include resolved source (`env_override` or `control_plane`).

## Validation Plan

- proof target: canonical owner behavior
  - method: unit tests for resolution path
  - evidence: tests proving env-unset uses control-plane values
- proof target: override semantics
  - method: unit tests with env override set
  - evidence: tests proving env values take precedence and source label reflects override
- proof target: fail-fast behavior
  - method: negative tests with missing required routing fields
  - evidence: explicit error/assertions, no silent fallback
- proof target: operator clarity
  - method: diagnostics payload inspection
  - evidence: runtime event includes resolved endpoint and source label

## Acceptance Criteria

1. One canonical owner for routing defaults is documented and enforced.
2. Env routing variables are explicitly override-only semantics.
3. Runtime precedence is deterministic and test-covered.
4. Missing resolved routing configuration fails fast.
5. Diagnostics show resolved source attribution.

## Non-Goals

- redesign broader config architecture outside provider routing contract
- removal of all backward-compatible env names in same change
- unrelated pipeline/ranking/runtime feature edits

## Risks and Mitigations

- risk: existing local scripts rely on implicit env ownership
  - mitigation: phased compatibility window plus explicit deprecation notice
- risk: diagnostics update incomplete across code paths
  - mitigation: add centralized routing-resolution helper and single diagnostics contract test
- risk: strict fail-fast may surface hidden misconfig in current environments
  - mitigation: rollout with preflight check command and clear remediation output

## Completion Criteria

1. all Key Deliverables are satisfied
2. all downstream/child items are terminal
3. every child item is `completed` or `dropped`

