---
layer: workstream
artifact_type: plan
status: proposed
parent_thread: workstream-agentic-observability.agentic-observability-shared-trace-standard
parent_spec: docs/superpowers/specs/2026-05-02-observability-evidence-control-docs-alignment-spec.md
targets:
  - docs/intent/master-workstream-roadmap.md
  - docs/intent/workstreams/workstream-fitcv-semantic-spine.md
  - docs/intent/workstreams/workstream-agentic-observability.md
  - docs/intent/workstreams/workstream-deterministic-acceptance-and-artifact-truth.md
  - docs/intent/workstreams/workstream-operator-control-plane.md
related_features:
  - trigger_run_management
  - inspection_debugging
related_stages:
  - normalize
  - enrich
  - rule_filter
  - shortlist
  - ranking
  - cv_analysis
  - cv_generation
---

# Phase 2 Plan A Authority Anchors

**Spec Set:**
- `docs/superpowers/specs/2026-05-02-observability-evidence-control-docs-alignment-spec.md`
- `docs/superpowers/specs/2026-05-02-phase-2-semantic-spine-flow-authority-spec.md`
- `docs/superpowers/specs/2026-05-02-phase-2-observability-otel-trace-context-spec.md`
- `docs/superpowers/specs/2026-05-02-phase-2-policy-versioned-stage-result-spec.md`
- `docs/superpowers/specs/2026-05-02-phase-2-control-plane-degraded-mode-portability-spec.md`

**Implementation Execution Map:** `docs/superpowers/execution_maps/2026-05-02-phase-2-observability-evidence-control-implementation-execution-map.md`

**Goal:** Lock the top-level Phase 2 ownership model so downstream doc updates cannot drift authority boundaries.

**Authority anchors to enforce:**
- flow = orchestrator
- traces = OTel-compatible IDs
- decisions = policy layer
- evidence = stage artifacts
- operations = control plane UI

## Scope

- finalize Phase 2 section language in the master roadmap
- align core ownership wording in four anchor workstreams:
  - fitcv semantic spine
  - agentic observability
  - deterministic acceptance and artifact truth
  - operator control plane

## Non-Goals

- no shared-surface cross-cutting doc updates yet (`docs/observability.md`, `docs/architecture.md`, `docs/configuration.md`, `docs/api.md`, `docs/usage.md`)
- no execution-map or plan-set regeneration in this plan

## Execution-Pass Checkpoint Requirement

Each bounded-thread execution pass in this plan must publish one checkpoint result pack.

Required:

- create/update one pack per meaningful execution pass
- store pack at `docs/intent/workstreams/checkpoints/<workstream-id>/<thread-slug>/`
- follow `docs/operating_system/templates/checkpoint-result-pack.md`
- mark status as `pass`, `partial`, or `fail`
- include intent, actions, visible output, and next decision

## Key Invariants

- no two workstreams claim the same authority concern as primary ownership
- observability wording does not claim decision authority
- control-plane wording does not claim policy ownership
- semantic-spine wording does not imply UI or policy owns stage flow

## Task 1: Roadmap Anchor Finalization

**Files:**
- Modify: `docs/intent/master-workstream-roadmap.md`

- [ ] Step 1: Ensure Phase 2 section exists and uses the exact five concern anchors.
- [ ] Step 2: Keep sequencing guardrail present and ordered:
  - roadmap
  - workstreams
  - threads
  - complete spec set
  - spec-authoring map
  - detailed specs
  - implementation execution map
  - implementation plans
- [ ] Step 3: Confirm completion language references stage-result contract, policy versioning, trace context continuity, and portability framing.

## Task 2: Core Workstream Ownership Alignment

**Files:**
- Modify:
  - `docs/intent/workstreams/workstream-fitcv-semantic-spine.md`
  - `docs/intent/workstreams/workstream-agentic-observability.md`
  - `docs/intent/workstreams/workstream-deterministic-acceptance-and-artifact-truth.md`
  - `docs/intent/workstreams/workstream-operator-control-plane.md`

- [ ] Step 1: Verify each file has Phase 2 alignment language.
- [ ] Step 2: Verify each file claims only its bounded ownership concern(s).
- [ ] Step 3: Remove or adjust any language that implies overlapping ownership.

## Task 3: Consistency Sweep

**Files:**
- Modify if needed:
  - `docs/intent/workstreams/workstream-bounded-agentic-cv-quality.md`
  - `docs/intent/workstreams/workstream-agentic-synonym-management.md`
  - `docs/intent/workstreams/workstream-pipeline-efficiency-and-reuse.md`

- [ ] Step 1: Confirm supporting workstreams reference Phase 2 boundaries without overriding anchor ownership.
- [ ] Step 2: Normalize terminology for “recommendation vs acceptance authority.”

## Verification

- [ ] Step 1: Manual diff pass on all `targets` in this plan.
- [ ] Step 2: Run:

```powershell
python scripts/validate_repo_contracts.py --fast
python scripts/validate_checkpoint_packs.py
```

- [ ] Step 3: Confirm no contradiction across roadmap and anchor workstreams on the five authority concerns.

## Exit Criteria

1. Master roadmap and anchor workstreams are authority-consistent.
2. The five concern anchors are explicit and non-overlapping.
3. Validator passes with no new contract errors.
4. Downstream plans can proceed without re-opening ownership semantics.
