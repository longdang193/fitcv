---
layer: change
artifact_type: spec
status: active
template_id: detailed-specification
name: fitcv-ssot-invariance-patch
parent_thread: workstream-fitcv-semantic-spine.semantic-spine-component-boundary-and-interface-contract
targets:
  - reviews/2026-06-25-14-25-48-fitcv/FITCV_SSOT_SYMMETRY_INVARIANCE_REVIEW.md
  - src/fitcv/pipeline_stage_context.py
  - src/fitcv/runtime_routing.py
  - src/fitcv/embeddings.py
  - src/fitcv/config.py
  - src/fitcv/ranking.py
  - src/fitcv/evidence.py
  - src/fitcv/persistence.py
  - src/fitcv/shortlist_runtime.py
  - src/fitcv/enrich.py
  - src/fitcv/tracker.py
  - src/fitcv/agentic_cv_analysis.py
  - src/fitcv/agentic_cv_generation.py
  - src/fitcv/pipeline.py
  - tests/
  - docs/api.md
  - docs/architecture.md
related_stages: []
---

## Goal

Define bounded patch scope for highest-confidence SSOT, symmetry, and invariance
bugs identified in
`reviews/2026-06-25-14-25-48-fitcv/FITCV_SSOT_SYMMETRY_INVARIANCE_REVIEW.md`.

This spec is for corrective patching, not full architecture migration.

## Implementation Status

Current evidence-backed status:
- Deliverable 1: met
- Deliverable 2: partially met
- Deliverable 3: met

What landed:
- checkpoint restore now validates future schema versions and persists explicit completed-stage metadata
- CV-generation env overrides now use one route owner
- evidence role-family neighbor scoring now honors runtime-configured taxonomy, including run-scoped overlay parity with ranking
- embedding reuse now distinguishes backend identity and blocks reuse for fallback-capable provider mode
- sqlite path wrappers now delegate to one owner
- pipeline/analysis late-stage status meanings now share one bounded contract helper
- tracker legacy BigQuery fallback is explicit and logged

What remains open:
- full BigQuery client consolidation across duplicate owners remains deferred because current shared builder has high blast radius
- `pipeline_stage_runner.py` and `reuse_law_engine.py` are now characterized as deferred, non-imported cleanup paths in active `src/` and `tests/`; delete/adopt decisions remain follow-up work

## Key Deliverables

### Deliverable 1: Correctness-critical runtime contracts are made single-owner enough to be trustworthy

Status: met

Checkpoint restore, CV-generation routing, evidence taxonomy scoring, degraded embedding reuse, and persistence fallback behavior each gain one authoritative live path for current runtime decisions.

### Deliverable 2: Patch scope stays bounded to live defects, not broad cleanup

Status: met

Dead code, partial extractions, and duplicate helpers are only removed or adopted when characterization tests prove that change is safe. This patch explicitly deferred broad cleanup, but did not yet add full parity proof for all deferred duplicate paths.

### Deliverable 3: Validation proof is executable

Status: met

Each adopted finding has targeted regression or characterization coverage that demonstrates both the current defect and the intended fixed contract. Focused regression proof landed for checkpoint, routing, taxonomy neighbor wiring including run-overlay parity, embeddings, persistence-path parity, tracker fallback, and deferred-cleanup import-graph characterization.

## Task/Wave Breakdown

### Wave 1: Source-first analysis

**Purpose:**
- confirm which review findings are current live defects versus cleanup-only debt

**Steps:**
- [ ] inspect current source for checkpoint, routing, taxonomy, embeddings, persistence, and status contracts
- [ ] classify findings into `fix now` and `defer with note`
- [ ] identify minimum shared owners already present in codebase to reuse instead of inventing new frameworks

**Verification:**
- [ ] current live-path ownership is explicit enough to patch without speculative rewrites

**Exit Criteria:**
- no fix-now item depends on unverified assumptions about dead or future paths

### Wave 2: Decision closure

**Purpose:**
- lock patch boundaries and contract rules before implementation planning

**Steps:**
- [ ] define authoritative restore metadata and schema handling rules for checkpoints
- [ ] define one route-owner rule for CV-generation routing surfaces
- [ ] define one effective runtime owner for role-family neighbor lookup
- [ ] define backend-aware embedding reuse contract
- [ ] define bounded persistence/status cleanup rules for current live paths

**Verification:**
- [ ] each fix-now area has one explicit chosen owner and one explicit non-goal boundary

**Exit Criteria:**
- implementation can consolidate live behavior without folding in unrelated architecture work

### Wave 3: Validation and approval readiness

**Purpose:**
- make patch acceptance measurable before implementation starts

**Steps:**
- [ ] define failing/regression tests required for each fix-now item
- [ ] define characterization tests required before deleting or adopting duplicate paths
- [ ] define docs and lineage refresh expectations if source contracts move

**Verification:**
- [ ] validation plan covers both correctness fixes and safe deferrals

**Exit Criteria:**
- spec is ready for implementation planning

## Design Decisions

### Decision: Patch correctness bugs before orchestrator rewrites

- context: review found several true runtime defects plus several broad duplication concerns
- choice: implement narrow fixes for live contract splits first; defer large pipeline/orchestrator consolidation until parity tests exist
- alternatives considered:
  - immediate full pipeline-stage-runner adoption
  - large SSOT migration across all duplicate modules in one patch
- impact:
  - lowers risk
  - keeps diff reviewable
  - avoids mixing bugfixes with speculative architecture work

### Decision: Treat checkpoint metadata as authoritative and payload-shape inference as compatibility fallback

- context: current resume logic infers completion from non-empty payloads
- choice: prefer explicit completed-stage metadata and schema validation for modern checkpoints
- alternatives considered:
  - keep data-shape inference as primary owner
- impact:
  - removes zero-output ambiguity
  - makes future checkpoint evolution safer

### Decision: Use one resolved route object for CV-generation surfaces

- context: env override generation currently mixes fields from separate routing parts
- choice: preflight, provenance, env overrides, and execution must read one route contract
- alternatives considered:
  - keep stage-specific ad hoc routing reads
- impact:
  - removes branch-dependent provider/model disagreement

### Decision: Make degraded embeddings non-equivalent to provider embeddings

- context: deterministic fallback vectors can currently satisfy normal reuse identity
- choice: backend/dimension/fallback provenance must participate in reuse identity or reuse eligibility
- alternatives considered:
  - keep current model-only fingerprint
- impact:
  - prevents silent cache poisoning across vector spaces

### Decision: Canonicalize role-family neighbor access before wider taxonomy cleanup

- context: runtime overlay and consumer lookup use conflicting paths
- choice: choose one canonical effective runtime path and give ranking/evidence a shared public accessor
- alternatives considered:
  - patch only evidence call sites
- impact:
  - fixes current scoring drift while shrinking future private-helper coupling

## Invariants

- same effective config must produce same routing, taxonomy, and reuse decisions across equivalent runtime paths
- checkpoint resume must not depend solely on whether output collections are empty or non-empty for modern checkpoints
- degraded local embeddings must never be reused as if they were provider embeddings under same contract fingerprint
- evidence and ranking must read same effective role-family neighbor relationships
- SQLite and BigQuery branches may degrade compatibly, but degradation must be explicit and testable
- cleanup-only refactors must not ship without characterization proof when they touch live shared behavior

## Acceptance Criteria

- checkpoint restore rejects unsupported schema versions and resumes correctly for zero-output completed-stage cases
- CV-generation routing surfaces no longer combine provider/base URL from one route with model from another
- evidence role-family scoring honors configured neighbors and ranking/evidence parity holds for both base config and run-scoped overlay config
- degraded embedding fallback cannot be silently reused under normal provider embedding identity
- persistence helper/path behavior is centralized enough that equivalent callers resolve same sqlite path rules now; broader BigQuery client-owner consolidation remains follow-up
- status/error shared meanings are sourced from one live contract surface or one tightly bounded compatibility layer
- large duplicate-path cleanup items are explicitly deferred unless parity tests justify change; current active-code characterization proves these two paths are not imported by live `src/` or `tests/` surfaces

## Non-Goals

- no full rewrite of `pipeline.py` into pure orchestration in this patch
- no complete reuse-engine redesign unless needed for one confirmed live defect
- no broad placeholder-policy or section-policy cleanup unless a current correctness bug is demonstrated
- no repo-wide feature metadata migration beyond touched source-of-truth surfaces

## Risks and Mitigations

- risk: patch set grows into architecture rewrite
  - mitigation: require failing tests and explicit live-owner proof before each fix-now change
- risk: duplicate dead-path cleanup breaks undocumented consumers
  - mitigation: characterize imports/callers first; defer deletion when proof is weak
- risk: changing embedding or checkpoint contracts breaks compatibility with stored historical artifacts
  - mitigation: support explicit compatibility fallback with tests and clear provenance
- risk: persistence hardening exposes latent schema drift in BigQuery
  - mitigation: keep downgrade path explicit, logged, and regression-tested

## Validation Plan

- proof target: checkpoint resume contract is schema-aware and not empty-payload-driven for modern checkpoints
  - method: test
  - evidence: targeted checkpoint restore tests covering explicit completion metadata, unsupported schema, and zero-output completion

- proof target: CV-generation routing surfaces agree on one resolved route
  - method: test
  - evidence: tests for env overrides, preflight, provenance, and execution-facing routing resolution from same config

- proof target: evidence and ranking consume same role-family neighbor config
  - method: test
  - evidence: ranking/evidence parity tests with base config and runtime overlay config

- proof target: degraded embeddings are not reused as provider embeddings
  - method: test
  - evidence: embedding reuse tests covering fallback provenance, backend mismatch, and dimension mismatch

- proof target: persistence fallback is explicit and bounded
  - method: test
  - evidence: tracker/persistence tests for SQLite path/client resolution and BigQuery structured-field downgrade behavior

- proof target: cleanup-only duplicate paths are not rewritten blindly
  - method: inspection + characterization test
  - evidence: import/caller characterization plus explicit deferral notes for non-runtime-critical duplicates

## Completion Criteria

A specification item is considered complete when:

1. all Key Deliverables are satisfied
2. all downstream/child items are terminal
3. every child item is `completed` or `dropped`




