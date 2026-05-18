---
layer: change
artifact_type: spec
status: proposed
template_id: detailed-specification
name: evidence-module-ssot-refactor-spec

parent_thread: workstream-pipeline-efficiency-and-reuse.efficiency-reuse-exact-match-contract
targets:
  - src/fitcv/evidence.py
  - src/fitcv/pipeline.py
  - src/fitcv/agentic_cv_analysis.py
  - src/fitcv_cp/worker_job.py
related_features:
  - cv_system
related_stages: []
---

## Goal

Define bounded, behavior-preserving refactor for `src/fitcv/evidence.py` that enforces SSOT, structural symmetry, and testability while reducing branching/duplication and keeping external API stable.

## Key Deliverables

### Deliverable 1: Canonical design for evidence retrieval/refinement architecture

Produce target architecture that separates normalization, channel scoring, selection orchestration, and persistence concerns into explicit boundaries with single-source ownership per rule.

### Deliverable 2: Refactor safety contract and rollout sequencing

Define invariant set, compatibility boundaries, and phased execution order so refactor can land in small safe steps with measurable risk control.

### Deliverable 3: Verification and evidence plan

Define tests, static checks, and impact-verification evidence required to prove no behavior regression.

## Task/Wave Breakdown

### Wave 1: Source-first analysis

**Purpose:**
- capture current behavior, coupling, and high-risk entrypoints before changing structure

**Steps:**
- [ ] inspect `src/fitcv/evidence.py` functional partitions: normalization, scoring, selection, persistence
- [ ] capture high-complexity hotspots (long functions, branching concentration, dict-contract sprawl)
- [ ] capture GitNexus impact/context for public and integration-facing symbols

**Verification:**
- [ ] current-state architecture map includes callers and dependent processes

**Exit Criteria:**
- no design decision depends on unstated assumptions about callers or runtime contracts

### Wave 2: Decision closure

**Purpose:**
- close architecture and interface decisions with explicit SSOT ownership

**Steps:**
- [ ] define target module/class boundaries and canonical ownership of selection/scoring policy
- [ ] define typed contract model (`dataclass`/typed objects) replacing ad-hoc dict contracts internally
- [ ] define persistence adapter boundaries for sqlite vs bigquery paths

**Verification:**
- [ ] each major refactor decision has choice, alternative, and impact

**Exit Criteria:**
- design is internally coherent and implementation-plan ready

### Wave 3: Validation and approval readiness

**Purpose:**
- define proof obligations and rollout guardrails for behavior-preserving refactor

**Steps:**
- [ ] define acceptance criteria and non-goals
- [ ] define verification suite and expected evidence artifacts
- [ ] define rollback and containment strategy per wave

**Verification:**
- [ ] validation plan can prove contract parity and deterministic outputs

**Exit Criteria:**
- spec approved for implementation planning

## Design Decisions

### Decision: Introduce internal SSOT configuration objects

- context: multiple repeated `dict.get(..., default)` trees currently encode policy/semantic defaults in many places
- choice: add canonical internal typed objects (`SelectionPolicy`, `SemanticSettings`, `QuotaSettings`, `TrimSettings`) constructed once and passed through pipeline
- alternatives considered:
  - keep dict-based access and patch helper methods
  - central constants only without typed model
- impact:
  - removes duplicated default logic
  - improves mypy clarity
  - makes policy evolution isolated and testable

### Decision: Consolidate channel scoring with strategy-driven shared pipeline

- context: required-skill, role, domain, and responsibility scoring components share lexical/semantic/hybrid flow but duplicate implementation
- choice: implement shared scoring template with channel-specific strategy functions for lexical term extraction and rationale
- alternatives considered:
  - keep four bespoke component functions
  - merge partially with utility helpers only
- impact:
  - structural symmetry across channels
  - lower branching and lower bug surface for weight changes
  - easier addition/removal of retrieval channels

### Decision: Extract selection orchestration into dedicated engine

- context: `retrieve_evidence_bundle` currently mixes orchestration, diagnostics assembly, and policy application
- choice: create `EvidenceSelectionEngine` internal unit responsible for pool build, merge, final select, and debug candidate derivation
- alternatives considered:
  - keep functional style with additional helper functions only
- impact:
  - smaller top-level orchestration API
  - deterministic unit-testable engine behavior
  - simpler future tuning of selection policy

### Decision: Separate persistence adapters from evidence-domain module

- context: `store_evidence_selection` combines domain transformation and backend-specific IO paths
- choice: extract persistence into adapter module boundaries (`sqlite` adapter and `bigquery` adapter) with stable call contract
- alternatives considered:
  - keep in-module branching by storage mode
- impact:
  - evidence-domain logic no longer coupled to backend write path
  - adapter tests can validate serialization independently

### Decision: Preserve external compatibility surface unchanged

- context: upstream callers rely on `retrieve_evidence_bundle`, `retrieve_evidence`, and evidence selection payload shape
- choice: keep public function names and output schema stable through refactor; perform internal-only restructuring first
- alternatives considered:
  - introduce new public API and deprecate old one during same change
- impact:
  - lower integration risk in `run_pipeline`, `analyze_ranked_job`, and worker process flow

## Invariants

- `retrieve_evidence_bundle` output keys and semantic meaning remain unchanged.
- `retrieve_evidence` compatibility path (legacy + context modes) remains behavior-compatible.
- Evidence ID generation remains deterministic for identical normalized input.
- Channel score range remains clamped to `[0.0, 1.0]`.
- Selection ranking remains deterministic for identical inputs and policy.
- Semantic alignment diagnostics (`semantic_methods`, reuse state, counts) remain present and schema-compatible.
- Persistence writes remain idempotent on `(job_url, evidence_id)` for sqlite mode.
- BigQuery payload fields remain schema-compatible with existing table contract.

## Acceptance Criteria

- all public callsites compile and pass tests without caller-side changes.
- golden-input snapshots for evidence selection match baseline output (or approved explicit deltas).
- duplicate scoring/default logic removed and replaced by one canonical internal path.
- long/high-branch functions in `evidence.py` reduced through extraction with no behavior drift.
- lint/type/test gates pass under repo standards.

## Non-Goals

- no ranking-policy retuning or business-threshold changes.
- no new retrieval channels.
- no schema migration for BigQuery table.
- no refactor of unrelated pipeline stages outside evidence boundaries except minimal call wiring.

## Risks and Mitigations

- Risk: hidden behavior drift from ordering/tie-break changes.
  - Mitigation: add regression fixtures for deterministic ordering, including edge cases with equal channel scores.
- Risk: semantic embedding cache behavior drift (fresh/reused counters).
  - Mitigation: dedicated tests for cache namespace paths and counter increments.
- Risk: integration regression in upstream pipeline process.
  - Mitigation: process-level tests covering `run_pipeline` path and worker execution path.
- Risk: stale docs/validator command references for architecture sync tooling.
  - Mitigation: include documentation-alignment task in follow-up plan and validate with `validate_repo_contracts.py --fast`.

## Validation Plan

- proof target: upstream blast radius is fully mapped before edits
  - method: GitNexus impact/context run
  - evidence: `gitnexus impact retrieve_evidence_bundle -d upstream --depth 4 --include-tests --repo "C:\Users\HOANG PHI LONG DANG\repos\JOB-PROJECT"` output (risk LOW, direct callers enumerated)

- proof target: public API/output contract preserved
  - method: regression tests + snapshot comparison on representative profiles/job-contexts
  - evidence: passing test report with fixture comparisons for `retrieve_evidence_bundle` and `retrieve_evidence`

- proof target: scoring symmetry and SSOT defaults enforced
  - method: unit tests for each channel through shared scoring pipeline
  - evidence: tests proving identical results vs baseline and single default source usage

- proof target: persistence behavior parity
  - method: adapter-level tests for sqlite upsert and BigQuery row payload shape
  - evidence: passing adapter tests and unchanged expected serialized fields

- proof target: repo contract gates remain green after spec/planned refactor
  - method: validator runs
  - evidence: `python scripts/hooks/run_validator.py --fast`, `python scripts/validate_repo_contracts.py --fast`

## Completion Criteria

1. all Key Deliverables are satisfied
2. all downstream/child items are terminal
3. every child item is `completed` or `dropped`

Canonical source-of-truth:

<LINK>
- `docs/operating_system/governance/repo-governance.md`
- `scripts/validate_planning_lifecycle.py`
</LINK>
