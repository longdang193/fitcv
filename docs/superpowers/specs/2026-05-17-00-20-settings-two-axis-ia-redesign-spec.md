---
layer: change
artifact_type: spec
status: proposed
template_id: detailed-specification
name: settings-two-axis-ia-redesign
parent_thread: workstream-fitcv-semantic-spine.semantic-spine-component-boundary-and-interface-contract
targets:
  - src/fitcv_cp/templates/settings.html
  - src/fitcv_cp/app.py
  - src/fitcv_cp/settings_schema.py
  - docs/superpowers/plans/brainstorming/2026-05-17-settings-page-ia-redesign/report.md
related_features:
  - settings_system
  - cv_system
related_stages:
  - cv_generation
---

## Goal

Define two-axis Settings information architecture that separates decision intent layers from workflow-stage applicability, reducing ambiguity and error-prone interpretation while preserving existing settings contracts.

## Key Deliverables

### Deliverable 1: Two-axis IA contract

Canonical UI contract for intent-layer navigation plus stage/state filtering, including setting-card semantics and badges.

### Deliverable 2: Edit-policy and guardrail contract

Clear edit behavior by layer (inline save vs guarded save) and explicit pre-save invariant checks aligned with existing backend constraints.

### Deliverable 3: Runtime truth and applicability contract

Explicit "applies when" and effective-state presentation so users can distinguish visibility intent, data eligibility, and stage gating.

## Task/Wave Breakdown

### Wave 1: Source-first analysis

**Purpose:**
- confirm current settings behavior, ambiguity points, and existing contract boundaries

**Steps:**
- [ ] map current settings keys to runtime consumer surfaces
- [ ] classify current keys into intent-layer categories
- [ ] classify stage/state applicability for each setting group
- [ ] identify settings that are metadata-only vs runtime-effective

**Verification:**
- [ ] each key has explicit intent category and applicability mapping

**Exit Criteria:**
- no IA decision depends on unstated assumptions about setting usage

### Wave 2: Decision closure

**Purpose:**
- finalize two-axis IA shape and behavior-level contracts

**Steps:**
- [ ] define primary nav layers: General, Workflow Controls, Advanced Tuning, Governance/Metadata
- [ ] define secondary stage filters: All, Retrieve, Rule Filter, Rerank, Evidence, CV Compose, Validate, Run Lifecycle
- [ ] define setting-card contract fields: What, Effect, Applies when, Dependencies, Default source, Observed in
- [ ] define badges: Layer, Stage(s), Runtime-used, Metadata-only, Risk
- [ ] define edit policy per layer and guardrail trigger points

**Verification:**
- [ ] each ambiguity case in thread context maps to explicit UI contract element

**Exit Criteria:**
- IA decisions form coherent, non-overlapping model

### Wave 3: Validation and approval readiness

**Purpose:**
- make proof expectations explicit before implementation planning

**Steps:**
- [ ] define acceptance checks for clarity, correctness, and contract preservation
- [ ] define invariant-preservation verification against current backend rules
- [ ] list open decisions that require explicit approval before plan drafting

**Verification:**
- [ ] validation plan can prove no behavioral contract regression

**Exit Criteria:**
- spec is ready for implementation plan handoff

## Design Decisions

### Decision: Use two-axis IA instead of single-axis grouping

- context: current Settings mixes runtime, policy, and metadata concerns, creating ambiguous user expectations
- choice: combine intent-layer primary navigation with stage/state secondary filtering
- alternatives considered:
  - helper-text-only patch in current IA
  - stage-first IA without intent layers
- impact:
  - improves discoverability of "what this controls" and "when this applies"
  - supports clearer invariance/equivalence communication

### Decision: Keep existing settings keys and backend contracts unchanged in IA phase

- context: thread requested clearer architecture, not behavior rewrite
- choice: IA redesign remains presentation/interaction layer; existing key schema and runtime semantics stay source of truth
- alternatives considered:
  - simultaneous key/schema refactor
- impact:
  - lowers rollout risk
  - isolates UX clarity change from backend behavior change

### Decision: Introduce explicit setting-card contract

- context: users cannot infer effective behavior from labels alone
- choice: each setting card exposes meaning, effect, applicability, dependency, default source, and consumer reference
- alternatives considered:
  - badges only
- impact:
  - reduces false bug reports from hidden applicability conditions

### Decision: Layered edit policy with pre-save guardrails

- context: high-risk tuning keys and low-risk visibility toggles currently feel similar
- choice: inline-save for low-risk layers; guarded save + preflight checks for advanced/high-risk layers
- alternatives considered:
  - uniform save behavior for all keys
- impact:
  - improves safety without blocking normal configuration flow

## Invariants

- Existing setting keys and persisted config paths remain unchanged during IA redesign phase.
- Existing backend validation rules remain source of truth; UI guardrails mirror but do not replace backend enforcement.
- Metadata-only keys remain distinguishable from runtime-effective keys.
- Stage/state applicability must be explicit for settings that are not globally active.
- Visibility intent toggles must not imply guaranteed section rendering when data eligibility gates apply.

## Acceptance Criteria

- Users can locate any setting by either intent layer or stage filter without ambiguous category overlap.
- For each displayed setting, UI shows whether key is runtime-used or metadata-only.
- For each stage-sensitive setting, UI shows explicit applies-when stage/state context.
- Pre-save guardrails block known invariant violations with actionable messages.
- Existing settings payload format and backend validation behavior are unchanged.

## Non-Goals

- No renaming or removal of existing settings keys in this spec.
- No redesign of unrelated admin pages.
- No change to CV generation policy semantics beyond clarity presentation.
- No migration of storage backend or runtime orchestration in this spec.

## Risks and Mitigations

- Risk: IA categories drift from real runtime usage.
  - Mitigation: derive category/applicability mapping from source consumers before UI finalization.
- Risk: badge/contract fields become stale.
  - Mitigation: anchor card fields to schema + consumer mapping contract, then verify during regression checks.
- Risk: perceived behavior changes from wording changes.
  - Mitigation: preserve existing defaults and contracts; add explicit wording for intent vs eligibility vs stage gating.

## Validation Plan

- proof target: two-axis IA covers all existing setting keys without orphaned or duplicated placement
  - method: inspection + mapping comparison
  - evidence: key-to-layer and key-to-stage mapping table with full key coverage
- proof target: UI preserves backend contract behavior
  - method: run existing settings save/validation flows with representative valid/invalid inputs
  - evidence: unchanged backend outcomes and expected validation errors
- proof target: ambiguity cases are resolved
  - method: scenario inspection using known thread cases (for example Certifications visibility intent)
  - evidence: setting card clearly separates visibility intent, eligibility dependency, and stage applicability
- proof target: metadata-only vs runtime-used distinction is visible and correct
  - method: inspection against schema/ui_surface and runtime consumer map
  - evidence: sampled keys show correct badges and details

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
