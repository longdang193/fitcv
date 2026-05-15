---
layer: change
artifact_type: spec
status: proposed
template_id: detailed-specification
name: fitcv-section-policy-algebra
parent_thread: workstream-bounded-agentic-cv-quality.cross-section-placeholder-guardrails
targets:
  - src/fitcv/cv_generator.py
  - src/fitcv/validator.py
  - src/fitcv/pipeline.py
  - tests/test_cv_generator.py
  - tests/test_validator.py
  - tests/test_pipeline_agentic_late_stage.py
  - docs/superpowers/plans/audit/20260515-1015-cert-grounding-drift/report.md
related_features:
  - cv_system
related_stages:
  - cv_generation
---

# FitCV Section Policy Algebra

## Goal

Define one shared section-policy contract for FitCV so generator, validator, and late-stage diagnostics apply same enablement, admissibility, and requiredness logic for structured CV sections.

This specification resolves current drift exposed by `Certifications` and establishes bounded design for extending same logic to similar sections without adding new asymmetric special cases.

## Key Deliverables

### Shared section-policy model

Define canonical section-policy inputs and decisions for structured CV sections, including section enablement, meaningful source-content evaluation, grounding admissibility, and validation requiredness.

### Certifications-first bounded integration

Apply shared policy model first to `Certifications`, replacing current split logic between `src/fitcv/cv_generator.py` and `src/fitcv/validator.py` while preserving current product behavior for unaffected sections.

### Audit-anchored validation proof

Tie specification outcomes to existing audit evidence so future implementation can demonstrate that structural rejection caused by section-policy drift is removed and that observability remains sufficient to diagnose any residual mismatch.

## Task/Wave Breakdown

### Wave 1: Source-first analysis

**Purpose:**
- define current behavior, boundaries, and design constraints before proposing decisions

**Steps:**
- [ ] inspect current `Certifications` handling in generator, validator, and late-stage telemetry
- [ ] identify all section-policy questions currently answered in more than one module
- [ ] record where profile truth, selected-evidence truth, and operator settings diverge
- [ ] define bounded initial target set for first shared-policy rollout

**Verification:**
- [ ] current-state drift map explicitly names each asymmetric decision edge affecting `Certifications`

**Exit Criteria:**
- no core design decision depends on unstated assumptions about section enablement or requiredness

### Wave 2: Decision closure

**Purpose:**
- resolve design choices and document why chosen shape is preferred

**Steps:**
- [ ] define canonical section-policy algebra and decision interfaces
- [ ] choose source of truth for each policy input
- [ ] define how generator and validator consume same decisions without duplicating policy logic
- [ ] define bounded migration strategy for `Certifications` first and later-section adoption

**Verification:**
- [ ] each major section-policy question has documented decision or explicit deferral

**Exit Criteria:**
- design is internally coherent and bounded

### Wave 3: Validation and approval readiness

**Purpose:**
- prepare spec for implementation handoff by making proof expectations explicit

**Steps:**
- [ ] define regression and runtime validation evidence for `Certifications`
- [ ] define invariant-preservation checks for unaffected sections
- [ ] identify post-implementation audit evidence updates needed for closure

**Verification:**
- [ ] validation plan proves symmetry, bounded rollout, and observability preservation

**Exit Criteria:**
- spec is ready for approval or implementation planning

## Design Decisions

### Decision: Use shared section-policy algebra instead of duplicated per-module section logic

- context: `Certifications` drift occurred because generator and validator each encoded section behavior with different source filters, different presence semantics, and different requiredness heuristics.
- choice: introduce one shared section-policy abstraction that computes policy decisions from common inputs and is consumed by both generator and validator.
- alternatives considered:
  - patch only `Certifications` in current call sites
  - keep section-specific helper logic duplicated in each module
  - move all policy into validator and let generator remain best-effort
- impact:
  - shared logic becomes single source of truth for section requiredness, admissibility, and section missingness semantics
  - future structured sections can adopt same algebra without repeating special cases
  - implementation must preserve existing public behavior while tightening internal symmetry

### Decision: Separate section inputs from section decisions

- context: current drift mixes raw facts with policy outcomes, such as list presence, profile meaningfulness, sanitized section rows, settings state, and evidence selection.
- choice: model policy as pure decisions derived from explicit inputs:
  - section identifier
  - operator enablement state
  - profile-backed canonical source rows
  - evidence-selected rows
  - placeholder/meaningfulness evaluation over canonical source rows
- alternatives considered:
  - infer all decisions ad hoc inside generator and validator call paths
  - rely only on selected evidence and ignore profile-level fallback
  - rely only on profile presence and ignore evidence selection shape
- impact:
  - policy reasoning becomes inspectable and testable
  - observability can emit stable diagnostic fields tied to policy decisions rather than only final validation failure
  - new sections can reuse same evaluation pattern with section-specific adapters only where truly needed
  - meaningfulness stops drifting between raw profile list length, generator sanitization, and validator-local content checks

### Decision: Requiredness must be symmetric with admissibility

- context: validator can only require a section when generator is allowed enough grounded input to produce it under same policy assumptions.
- choice: a section may be marked required only when all are true:
  - section enabled under operator settings
  - section has meaningful source content under canonical section-specific meaningfulness rules
  - section is admissible for generation under canonical grounding policy
- alternatives considered:
  - required if enabled alone
  - required if profile list exists, regardless of meaningfulness
  - required if validator can imagine content even when generator input path cannot
- impact:
  - closes structural rejection class where validator demands section generator cannot lawfully produce
  - makes requiredness rule explainable and testable

### Decision: Canonical section presence and missingness must be content-aware

- context: current generator-side structural checks can treat a section as present when key exists, while validator-side checks can treat same section as missing when content is empty.
- choice: shared policy must define canonical section presence and missingness for required structured sections using admissible meaningful content, not key presence alone and not raw list non-emptiness alone.
- alternatives considered:
  - preserve key-only presence semantics in generator
  - preserve raw non-empty-list semantics in validator
  - let each module keep separate missingness definitions
- impact:
  - eliminates generator-pass / validator-fail drift caused by incompatible structural proxies
  - makes structural rejection fingerprint reproducible and removable through one policy layer

### Decision: Certifications uses profile fallback when evidence-specific certification extraction is empty

- context: real profile certifications may exist even when selected evidence items do not explicitly mention certification names, while generator-side sanitization may collapse placeholder-only certification rows to empty.
- choice: for `Certifications`, shared policy must allow profile-backed certification rows as fallback admissible content when evidence-specific extraction is empty, provided rows remain meaningful after canonical placeholder filtering and section remains enabled.
- alternatives considered:
  - evidence-only certifications
  - unconditional profile fallback for all sections
  - make `Certifications` always optional
- impact:
  - fixes immediate starvation condition without weakening groundedness to unbounded free-form generation
  - keeps fallback scoped to canonical certification rows rather than arbitrary prose inference
  - prevents raw profile list existence from forcing requiredness when sanitized certification content is empty

### Decision: Roll out algebra with Certifications first, then generalize to other structured sections

- context: audit trigger came from `Certifications`, but architecture should support more than one section. Current source also shows `Education` already has a bespoke requiredness guard that should not be semantically expanded in this slice.
- choice: first implementation slice standardizes interfaces and migrates `Certifications`; other sections adopt same pattern later only after source-first review.
- alternatives considered:
  - all sections full migration in one patch
  - certifications-only hardcoded fix with no reusable abstraction
- impact:
  - reduces delivery risk
  - preserves bounded scope for current remediation
  - creates durable extension path for similar structures
  - leaves `Education` behavior unchanged in this slice except for safe mechanical reuse if needed without semantic expansion

## Invariants

- generator and validator must not compute conflicting requiredness for same section from same inputs
- generator and validator must not use different canonical definitions of section presence or missingness for required structured sections
- section requiredness must never depend on raw list presence alone when section meaningfulness rules exist
- placeholder-only or structurally empty rows must not make a section required
- sanitized-empty `certifications` rows must not be reinterpreted as required solely because raw profile list length is non-zero
- when a section is required, generator must receive admissible grounded content path for that section under same policy assumptions
- fallback from evidence-empty to profile rows must occur only after canonical placeholder filtering and meaningfulness evaluation
- section-policy decisions must be testable without executing full end-to-end pipeline
- policy rollout for `Certifications` must not weaken existing grounding, semantic, or skill validation contracts for unrelated sections
- telemetry for section-policy failures must remain sufficient to distinguish structural absence from grounding or markdown-quality failures

## Acceptance Criteria

- one shared section-policy surface exists for `Certifications` and is consumed by both generator and validator
- `Certifications` is required only when enabled and backed by meaningful admissible content under shared policy
- real certification rows in `data/candidate_profile.private.yaml` can no longer produce structural rejection solely because selected evidence omitted explicit certification mentions
- placeholder-only or empty certification rows do not force `Certifications` requiredness
- generator-side sanitized-empty `Certifications` content does not cause validator-side re-requiredness from raw profile list length alone
- canonical policy defines section presence and missingness consistently when `Certifications` key exists but content is empty
- regression coverage proves generator and validator stay symmetric for enabled/disabled, meaningful/placeholder, and evidence-present/evidence-empty certification scenarios
- validation-failure diagnostics remain able to show whether rejection came from structural section absence versus other validator families

## Non-Goals

- full multi-section algebra migration for every structured CV section in same implementation slice
- redesign of operator settings surface beyond clarifying how existing enablement participates in policy
- removal of section-specific meaningfulness adapters where real semantic differences still exist
- replacement of broader deterministic grounding, semantic grounding, skill, or markdown-quality validators
- prompt-only fix that leaves generator and validator policy duplicated

## Risks and Mitigations

- risk: abstraction introduced too early becomes generic shell with weak product fit
  - mitigation: bind first rollout to concrete `Certifications` failure class and require source-backed tests before wider adoption
- risk: policy refactor changes behavior for unaffected sections
  - mitigation: keep first migration bounded to `Certifications` and preserve current behavior elsewhere through explicit non-migrated defaults
- risk: profile fallback weakens grounding discipline
  - mitigation: restrict fallback to canonical certification rows, meaningfulness-filtered, only when section enabled and evidence extraction empty
- risk: observability stays too weak to prove future symmetry failures quickly
  - mitigation: preserve and extend validation payload tracing around policy decisions and missing-section outcomes

## Validation Plan

- proof target: `Certifications` requiredness is symmetric between generator and validator
  - method: test
  - evidence: focused unit coverage in `tests/test_cv_generator.py` and `tests/test_validator.py` for shared enabled/disabled, meaningful/placeholder, and evidence-present/evidence-empty scenarios
- proof target: real-profile certification fallback no longer causes structural rejection when evidence-specific certification extraction is empty
  - method: run
  - evidence: post-patch pipeline repro or focused integration evidence showing prior generator-pass / validator-fail `missing_sections=["Certifications"]` fingerprint no longer occurs for same class of run
- proof target: placeholder-only certification rows remain optional
  - method: test
  - evidence: regression test demonstrating section not required when certification rows are placeholder-only or structurally empty
- proof target: generator-side sanitized-empty certification rows do not trigger validator-side re-requiredness
  - method: test
  - evidence: regression test where raw profile certification list is non-empty, canonical placeholder filtering collapses it to empty, and shared policy marks `Certifications` not required
- proof target: canonical missingness semantics are consistent when section key exists but content is empty
  - method: test
  - evidence: regression test showing key presence alone does not satisfy required structured-section contract and empty content outcome is interpreted identically by generator and validator
- proof target: unrelated validator families remain authoritative and unchanged
  - method: comparison
  - evidence: focused late-stage tests showing grounding, semantic, skill, and markdown-quality failures still route independently of section-policy decision
- proof target: audit bundle remains source-grounded and closure-ready
  - method: inspection
  - evidence: updated `docs/superpowers/plans/audit/20260515-1015-cert-grounding-drift/report.md` with post-implementation verification evidence and maintained `AUDIT_CHECK_PASSED`

### Validation Matrix

- case: section enabled + meaningful profile certifications + no evidence-specific certification extraction
  - expected: `Certifications` required
  - expected admissibility path: meaningful profile fallback
- case: section enabled + placeholder-only profile certifications
  - expected: `Certifications` not required
  - expected admissibility path: none
- case: section enabled + raw profile certification list non-empty but canonical filtering collapses rows to empty
  - expected: `Certifications` not required
  - expected structural outcome: no generator-pass / validator-fail rejection
- case: section disabled + meaningful profile certifications
  - expected: `Certifications` not required
  - expected admissibility path: disabled-section suppression

## Completion Criteria

A specification item is considered complete when:

1. all Key Deliverables are satisfied
2. all downstream/child items are terminal
3. every child item is `completed` or `dropped`
4. shared section-policy design is approved or explicitly accepted as implementation handoff baseline
5. implementation planning can proceed without unresolved ambiguity about `Certifications` requiredness, admissibility, or fallback semantics
