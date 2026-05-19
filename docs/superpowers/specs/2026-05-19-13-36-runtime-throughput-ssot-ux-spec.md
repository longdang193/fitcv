---
layer: change
artifact_type: spec
status: proposed
template_id: detailed-specification
name: runtime-throughput-ssot-ux
parent_thread: workstream-operator-control-plane.operator-control-plane-agentic-settings-surface
targets:
  - src/fitcv_cp/app.py
  - src/fitcv_cp/templates/settings.html
  - tests/test_fitcv_cp/test_app.py
related_features:
  - settings_system
related_stages:
  - enrich
  - ranking
  - cv_analysis
  - cv_generation
---

## Goal

Define SSOT-compliant settings UX for runtime throughput so operators have one canonical tuning surface, while legacy alias behavior remains compatibility-only and non-duplicative.

## Key Deliverables

### Single canonical runtime-throughput surface

Settings page exposes one throughput control card for canonical `stage_runtime.*` keys only, eliminating split ownership perception across Agentic and Advanced sections.

### Compatibility-surface demotion

Legacy throughput alias keys remain visible only as read-only compatibility metadata/projection, not as peer editable runtime knobs.

### Verified UI contract symmetry

Tests prove stage/control-surface/runtime-used truthfulness remains intact after registry/layout consolidation.

## Task/Wave Breakdown

### Wave 1: Source-first analysis

**Purpose:**
- confirm exact duplication boundary and impacted execution paths

**Steps:**
- [x] inspect `settings_page_sections` construction in `src/fitcv_cp/app.py`
- [x] inspect row/badge render logic in `src/fitcv_cp/templates/settings.html`
- [x] inspect current settings-page contract tests in `tests/test_fitcv_cp/test_app.py`
- [x] run GitNexus impact for `_build_settings_context` upstream callers

**Verification:**
- [x] impacted callers and risk are explicit (`LOW`, direct admin settings flows)

**Exit Criteria:**
- runtime-throughput duplication boundary is explicit and bounded to settings UI assembly/render/test layer

### Wave 2: Decision closure

**Purpose:**
- lock SSOT-preserving structure and file-level edits

**Steps:**
- [x] select one canonical throughput card model
- [x] define exact card-key composition and compatibility projection behavior
- [x] define exact tests to add/update/remove

**Verification:**
- [x] all decisions map to exact files and unchanged runtime behavior

**Exit Criteria:**
- design has one ownership path per throughput fact

### Wave 3: Validation and approval readiness

**Purpose:**
- define proof that UI contract remains truthful while removing split UX ownership

**Steps:**
- [x] define targeted pytest selectors
- [x] define acceptance criteria and non-goals
- [x] define migration-risk controls for legacy aliases

**Verification:**
- [x] validation plan includes proof targets + expected evidence lines

**Exit Criteria:**
- spec ready for implementation planning handoff

## Design Decisions

### Decision: Single canonical throughput registry surface

- context: current UX shows `Agentic Runtime Throughput` and `Advanced Runtime Tuning`, causing perceived dual ownership of runtime throughput intent.
- choice: keep one canonical throughput card with all editable canonical `stage_runtime.*` throughput keys.
- alternatives considered:
  - keep dual cards with wording tweaks (rejected: still dual ownership)
  - keep dual cards by stage partition only (rejected: still split operator navigation)
- impact:
  - `src/fitcv_cp/app.py`: collapse runtime-throughput key assembly into one card source
  - `src/fitcv_cp/templates/settings.html`: render one canonical card, compatibility data separated
  - tests updated to assert one ownership surface

### Decision: Compatibility aliases become metadata-only surface

- context: legacy alias rows currently appear as editable peers and dilute SSOT.
- choice: keep alias mapping visible as compatibility metadata, but remove alias editable rows from primary throughput section.
- alternatives considered:
  - remove alias visibility entirely (rejected: loses migration observability)
  - keep alias rows editable with warning label (rejected: preserves split-write ambiguity)
- impact:
  - settings UI still communicates alias linkage via badges/help
  - runtime normalization path remains unchanged

### Decision: Structural symmetry via classifier helper

- context: key grouping logic risks drift if hand-curated in multiple card blocks.
- choice: define one local classifier/helper in `app.py` for throughput key partitions:
  - canonical editable throughput keys
  - compatibility alias-only keys
- alternatives considered:
  - inline list duplication in multiple cards (rejected: anti-symmetry)
- impact:
  - reduces future drift and keeps grouping invariant testable

## Invariants

- There is exactly one primary editable settings surface for runtime throughput intent.
- Editable throughput rows use canonical `stage_runtime.*` keys only.
- Legacy alias keys do not act as parallel write surface.
- Existing runtime consumption behavior and alias normalization semantics are unchanged.
- Stage/control-surface/runtime-used badges remain truthful for canonical rows.

# Acceptance Criteria

- Settings page contains one canonical throughput card (no dual ownership split).
- Canonical throughput keys for `enrich`, `ranking`, `cv_analysis`, `cv_generation` are editable in that card.
- Legacy alias keys are not presented as primary editable peers.
- Existing IA badge truth (`stage`, `control surface`, `runtime-used`) remains valid for late-stage rows.
- Existing settings save endpoints keep behavior compatible (no contract-breaking route changes).

# Non-Goals

- No runtime config schema change for key names or defaults.
- No removal of alias normalization logic in `settings_schema.py`.
- No provider/model routing redesign.
- No broad settings-page visual redesign beyond throughput ownership consolidation.

# Risks and Mitigations

- risk: hidden dependency in tests expecting old dual-card copy.
  - mitigation: update only affected assertions; keep behavioral tests for row metadata and save actions.
- risk: accidental removal of enrich/ranking canonical knobs while collapsing cards.
  - mitigation: explicit canonical key list in spec + targeted render assertions by key label/id.
- risk: migration ambiguity if alias visibility removed too aggressively.
  - mitigation: keep compatibility alias badge/help text visible in metadata surface.

## Validation Plan

- proof target: one canonical throughput ownership surface in registry assembly
  - method: inspection of `settings_page_sections` structure in `src/fitcv_cp/app.py`
  - evidence: single runtime-throughput card definition with complete canonical key set

- proof target: template still renders truthful metadata for canonical throughput rows
  - method: pytest + HTML assertions
  - evidence: passing tests for stage/control-surface/runtime-used badges on canonical rows

- proof target: compatibility aliases remain visible but non-primary
  - method: pytest + HTML assertions for alias badge/help presence and no alias-primary card duplication
  - evidence: dedicated test assertions in `tests/test_fitcv_cp/test_app.py`

- proof target: settings UX regressions avoided for advanced disclosure semantics
  - method: existing advanced disclosure test update/retain
  - evidence: passing `test_settings_page_uses_advanced_disclosure_for_expert_controls`

## Targeted Verification Commands

- `pytest tests/test_fitcv_cp/test_app.py -k "settings_page_surfaces_late_stage_stage_runtime_controls_in_agentic_section or settings_page_uses_advanced_disclosure_for_expert_controls or admin_settings_late_stage_runtime_rows_have_truthful_stage_and_runtime_badges" -q`
- `pytest tests/test_fitcv_cp/test_settings_schema.py -k "ia_contract or runtime_used" -q`

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


