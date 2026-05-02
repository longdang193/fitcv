---
layer: workstream
artifact_type: plan
status: proposed
parent_thread: workstream-operator-control-plane.operator-control-plane-phase-2-degraded-mode-and-portability-surface
parent_spec: docs/superpowers/specs/2026-05-02-phase-2-control-plane-degraded-mode-portability-spec.md
targets:
  - docs/observability.md
  - docs/architecture.md
  - docs/configuration.md
  - docs/api.md
  - docs/usage.md
related_features:
  - inspection_debugging
  - trigger_run_management
  - settings_system
related_stages:
  - enrich
  - rule_filter
  - cv_analysis
  - cv_generation
---

# Phase 2 Plan C Shared Surface Adoption

**Spec Set:**
- `docs/superpowers/specs/2026-05-02-observability-evidence-control-docs-alignment-spec.md`
- `docs/superpowers/specs/2026-05-02-phase-2-semantic-spine-flow-authority-spec.md`
- `docs/superpowers/specs/2026-05-02-phase-2-observability-otel-trace-context-spec.md`
- `docs/superpowers/specs/2026-05-02-phase-2-policy-versioned-stage-result-spec.md`
- `docs/superpowers/specs/2026-05-02-phase-2-control-plane-degraded-mode-portability-spec.md`

**Implementation Execution Map:** `docs/superpowers/execution_maps/2026-05-02-phase-2-observability-evidence-control-implementation-execution-map.md`

**Goal:** Apply the Phase 2 authority and contract model across shared cross-cutting docs without introducing conflicting claims or over-promising implementation status.

## Scope

- update shared surfaces:
  - observability
  - architecture
  - configuration
  - api
  - usage
- align all shared docs to:
  - one source of truth per concern
  - canonical StageResult contract
  - trace-vs-decision boundary
  - full/local/degraded mode narratives

## Non-Goals

- no workstream/thread restructuring in this plan
- no new spec creation in this plan
- no runtime code changes

## Execution-Pass Checkpoint Requirement

Each bounded-thread execution pass in this plan must publish one checkpoint result pack.

Required:

- create/update one pack per meaningful execution pass
- store pack at `docs/intent/workstreams/checkpoints/<workstream-id>/<thread-slug>/`
- follow `docs/operating_system/templates/checkpoint-result-pack.md`
- mark status as `pass`, `partial`, or `fail`
- include intent, actions, visible output, and next decision

## Key Invariants

- shared docs do not conflict with roadmap/workstream authority anchors
- observability docs describe traces as evidence surfaces, not gate authority
- configuration and usage docs describe portability direction clearly without claiming unimplemented backend parity
- StageResult contract is referenced consistently and not redefined inconsistently

## Parallel Lane Ownership

- Lane C1: `docs/observability.md`
- Lane C2: `docs/architecture.md`
- Lane C3: `docs/configuration.md`
- Lane C4: `docs/api.md`
- Lane C5: `docs/usage.md`

Coordination rule:

- one editor owner per file in a wave
- shared terminology checklist must be reconciled before final pass

## Task 1: Observability Surface Adoption

**Files:**
- Modify: `docs/observability.md`

- [ ] Step 1: Add or tighten architecture-contract section:
  - StageResult reference
  - trace context fields (`trace_id`, `span_id`, parent linkage)
  - trace vs decision interpretation
- [ ] Step 2: Add degraded/local/full mode observability expectations.
- [ ] Step 3: Ensure wording does not claim policy authority.

## Task 2: Architecture Surface Adoption

**Files:**
- Modify: `docs/architecture.md`

- [ ] Step 1: Add backend-agnostic ports/adapters direction.
- [ ] Step 2: Explicitly map “flow = orchestrator” and preserve stage semantics boundary.
- [ ] Step 3: Reference StageResult contract without redefining variants.

## Task 3: Configuration Surface Adoption

**Files:**
- Modify: `docs/configuration.md`

- [ ] Step 1: Add runtime mode and backend selection narratives:
  - full/local/degraded
  - backend/provider selection principles
- [ ] Step 2: Clarify these are architecture/operations contracts unless explicitly implemented.
- [ ] Step 3: Ensure no conflict with settings-used historical-truth semantics.

## Task 4: API And Usage Surface Adoption

**Files:**
- Modify:
  - `docs/api.md`
  - `docs/usage.md`

- [ ] Step 1: Align API/usage wording with recommendation-vs-acceptance authority.
- [ ] Step 2: Ensure artifact and trace narratives remain consistent with observability doc.
- [ ] Step 3: Ensure run-mode and degraded behavior wording is operator-safe and non-contradictory.

## Task 5: Cross-Surface Consistency Pass

**Files:**
- Modify if needed:
  - `docs/observability.md`
  - `docs/architecture.md`
  - `docs/configuration.md`
  - `docs/api.md`
  - `docs/usage.md`

- [ ] Step 1: Run terminology checklist:
  - flow/orchestrator
  - traces/OTel-compatible IDs
  - decisions/policy layer
  - evidence/stage artifacts
  - operations/control plane UI
- [ ] Step 2: Resolve any duplicate or conflicting StageResult definitions.
- [ ] Step 3: Confirm no doc implies completed backend migration unless explicit.

## Verification

- [ ] Step 1: Manual review across all `targets`.
- [ ] Step 2: Run:

```powershell
python scripts/validate_repo_contracts.py --fast
python scripts/validate_checkpoint_packs.py
```

- [ ] Step 3: Confirm no authority-boundary contradictions against:
  - `docs/intent/master-workstream-roadmap.md`
  - anchor workstreams

## Exit Criteria

1. All shared surfaces reflect the same Phase 2 authority model.
2. StageResult contract is consistently referenced across shared docs.
3. Portability/degraded-mode wording is clear and non-overpromising.
4. Validator passes and no cross-surface contradiction remains.
