---
layer: change
artifact_type: plan
status: proposed
template_id: implementation-plan
name: fitcv-section-policy-algebra
parent_spec: docs/superpowers/specs/2026-05-15-10-32-fitcv-section-policy-algebra-spec.md
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

# FitCV Section Policy Algebra Implementation Plan

## Goal

Implement one shared section-policy path for FitCV so generator and validator make symmetric `Certifications` decisions from same inputs, preserve current behavior for non-migrated sections, and attach bounded verification evidence for audit closure.

## Key Deliverables

### Shared `Certifications` section-policy surface

Introduce reusable section-policy helpers or policy object(s) that centralize `Certifications` enablement, meaningfulness, admissibility, and requiredness decisions, and wire both generator and validator to consume same canonical outcomes.

### Regression-safe `Certifications` rollout

Replace current split `Certifications` logic in `src/fitcv/cv_generator.py` and `src/fitcv/validator.py` with shared policy behavior that preserves existing unrelated section behavior, supports profile fallback when evidence-specific certification extraction is empty, and blocks placeholder-only rows from forcing requiredness.

### Verification and audit evidence update

Add focused test coverage and runtime-proof updates so repository validation and audit artifacts demonstrate that structural `Certifications` drift is fixed without weakening other validator families or late-stage diagnostics.

## Task/Wave Breakdown

### Task 1: Baseline current `Certifications` policy and migration boundary

**Purpose:**
- lock down exact policy inputs, call sites, and non-migrated boundaries before refactor so shared logic stays bounded and behavior-preserving

**Files:**
- Inspect: `src/fitcv/cv_generator.py`
- Inspect: `src/fitcv/validator.py`
- Inspect: `src/fitcv/pipeline.py`
- Inspect: `tests/test_cv_generator.py`
- Inspect: `tests/test_validator.py`
- Inspect: `tests/test_pipeline_agentic_late_stage.py`
- Verify: `docs/superpowers/specs/2026-05-15-10-32-fitcv-section-policy-algebra-spec.md`

**Preconditions:**
- approved design baseline remains `docs/superpowers/specs/2026-05-15-10-32-fitcv-section-policy-algebra-spec.md`
- implementation stays bounded to shared `Certifications` policy plus supporting diagnostics and tests

**Steps:**
- [x] Step 1: inventory every `Certifications` decision point in generator, validator, and telemetry paths
- [x] Step 2: list canonical policy inputs required for shared logic, including setting state, profile rows, evidence-derived rows, and placeholder filtering
- [x] Step 3: mark non-migrated sections and preserve-current-behavior boundaries explicitly for implementation pass

**Verification:**
- [x] implementation notes or task-local checklist names each current `Certifications` decision edge and intended shared-policy destination
- Evidence note: inspected generator/validator/pipeline certification decision points, tightened spec semantic contract, and ran GitNexus CLI impact analysis (`--repo fitcv`) for `_find_missing_required_structured_sections`, `_structured_section_has_content`, `_format_certification_lines`, and `_is_synthetic_certifications_entry` to confirm blast radius before code edits.

**Exit Criteria:**
- migration scope is explicit enough to refactor without inventing broader multi-section behavior

### Task 2: Introduce shared section-policy helpers and migrate generator consumption

**Purpose:**
- create single reusable policy surface and move generator `Certifications` admissibility logic onto it first

**Files:**
- Inspect: `src/fitcv/cv_generator.py`
- Inspect: `src/fitcv/validator.py`
- Modify: `src/fitcv/cv_generator.py`
- Modify: `src/fitcv/validator.py`
- Verify: `tests/test_cv_generator.py`

**Preconditions:**
- Task 1 complete
- helper shape chosen remains local and bounded to current FitCV module design

**Steps:**
- [x] Step 1: add shared section-policy helper(s) in canonical FitCV module location that can evaluate `Certifications` meaningfulness, admissibility, and requiredness from explicit inputs
- [x] Step 2: route generator `Certifications` grounding-policy construction through shared helper(s), preserving profile fallback when evidence-specific certification extraction is empty
- [ ] Step 3: keep non-migrated sections on existing behavior unless refactor needs small mechanical alignment with no semantic expansion

**Verification:**
- [x] focused generator tests prove shared helper output drives allowed certification guidance for evidence-present and evidence-empty cases
- Evidence note: created `src/fitcv/section_policy.py`, rewired `src/fitcv/cv_generator.py` certifications section-evidence path through shared helper, then ran `python -m pytest tests/test_cv_generator.py -k "certification or grounding_policy or section"` => `12 passed`.

**Exit Criteria:**
- generator no longer owns separate `Certifications` policy semantics outside shared helper path

### Task 3: Migrate validator requiredness and structural checks onto shared policy

**Purpose:**
- make validator structural `Certifications` enforcement consume same canonical policy decisions as generator

**Files:**
- Inspect: `src/fitcv/validator.py`
- Inspect: `src/fitcv/cv_generator.py`
- Modify: `src/fitcv/validator.py`
- Verify: `tests/test_validator.py`

**Preconditions:**
- Task 2 complete
- shared helper surface already expresses inputs validator needs without hidden generator-only assumptions

**Steps:**
- [x] Step 1: replace validator-local `Certifications` requiredness branching with shared policy decision calls
- [x] Step 2: preserve placeholder filtering and meaningful-content semantics while removing duplicate or conflicting logic paths
- [x] Step 3: confirm missing-section and markdown-structure checks still report structural absence only when shared policy says section is truly required

**Verification:**
- [x] validator tests cover enabled vs disabled, meaningful vs placeholder-only, and evidence-empty vs admissible-fallback scenarios
- Evidence note: GitNexus impact executed for `_find_missing_required_structured_sections`, `_structured_section_has_content`, and `run_all_validations` prior to edits; validator now gates Certifications requiredness + structured content + markdown missing checks via shared policy semantics; added regressions for meaningful/non-meaningful profile certification cases; `python -m pytest tests/test_validator.py` => `47 passed`.

**Exit Criteria:**
- validator and generator derive same `Certifications` requiredness outcome from same inputs

### Task 4: Preserve diagnostics and add focused regression coverage

**Purpose:**
- keep observability useful and prove unaffected validator families remain authoritative

**Files:**
- Inspect: `src/fitcv/pipeline.py`
- Modify: `src/fitcv/pipeline.py`
- Modify: `tests/test_cv_generator.py`
- Modify: `tests/test_validator.py`
- Modify: `tests/test_pipeline_agentic_late_stage.py`

**Preconditions:**
- Task 3 complete
- section-policy outputs and failure modes are stable enough to expose in assertions or telemetry

**Steps:**
- [x] Step 1: keep or refine `layer4_cv_validation_failed` diagnostics so section-policy-related structural failures remain inspectable
- [x] Step 2: add regression tests for real failure class where profile certifications are meaningful but evidence-specific extraction is empty
- [x] Step 3: add comparison tests showing semantic grounding, skill, and markdown-quality validators still route independently of shared `Certifications` policy
- Evidence note:
  - `src/fitcv/pipeline.py` retains `layer4_cv_validation_failed` emission with `missing_sections`, grounding, semantic, skill, and markdown-quality outputs in failure payload.
  - focused verification commands passed:
    - `python -m pytest tests/test_cv_generator.py -k "certification or grounding_policy or section"` => `12 passed`
    - `python -m pytest tests/test_validator.py -k "certification or required_structured_sections or meaningful"` => `2 passed`
    - `python -m pytest tests/test_pipeline_agentic_late_stage.py -k "certification or validation_failed or review_required"` => `2 passed`

**Verification:**
- [x] focused late-stage tests prove structural-failure fingerprint changes only for resolved `Certifications` drift class and not for unrelated validator families

**Exit Criteria:**
- observability and regression surfaces can distinguish fixed symmetry drift from unrelated validation failures

### Task 5: Run bounded verification and update audit closure evidence

**Purpose:**
- produce final proof that implementation satisfies spec and audit expectations

**Files:**
- Inspect: `docs/superpowers/plans/audit/20260515-1015-cert-grounding-drift/report.md`
- Modify: `docs/superpowers/plans/audit/20260515-1015-cert-grounding-drift/report.md`
- Verify: `tests/test_cv_generator.py`
- Verify: `tests/test_validator.py`
- Verify: `tests/test_pipeline_agentic_late_stage.py`
- Verify: `docs/superpowers/plans/audit/20260515-1015-cert-grounding-drift/manifest.yaml`

**Preconditions:**
- Tasks 1 through 4 complete
- runtime or integration repro path available for same class of `Certifications` structural rejection previously captured by audit bundle

**Steps:**
- [x] Step 1: run focused unit and integration verification for shared `Certifications` policy behavior
- [x] Step 2: capture post-patch evidence showing prior `missing_sections=["Certifications"]` failure class is resolved for meaningful certification data
- [x] Step 3: update audit report with verification evidence and any remaining bounded follow-up notes
- Evidence note (Step 1):
  - `python -m pytest tests/test_cv_generator.py -k "certification or grounding_policy or section"` => `12 passed`
  - `python -m pytest tests/test_validator.py -k "certification or required_structured_sections or meaningful"` => `2 passed`
  - `python -m pytest tests/test_pipeline_agentic_late_stage.py -k "certification or validation_failed or review_required"` => `2 passed`
  - `python scripts/validate_repo_contracts.py --fast` => passed
- Evidence note (Step 2/3):
  - updated `docs/superpowers/plans/audit/20260515-1015-cert-grounding-drift/report.md` with post-patch proof mapping and verification outcomes
  - `python scripts/audit_check.py docs/superpowers/plans/audit/20260515-1015-cert-grounding-drift` => `AUDIT_CHECK_PASSED`

**Verification:**
- [x] audit bundle references concrete post-patch proof and remains structurally valid

**Exit Criteria:**
- implementation has runnable proof, audit evidence is refreshed, and work is ready for execution handoff or closeout verification

## Verification

- `python -m pytest tests/test_cv_generator.py -k "certification or grounding_policy or section"`
- `python -m pytest tests/test_validator.py -k "certification or required_structured_sections or meaningful"`
- `python -m pytest tests/test_pipeline_agentic_late_stage.py -k "certification or validation_failed or review_required"`
- `python scripts/validate_repo_contracts.py --fast`

## Completion Criteria

A plan item is considered complete when:

1. all Key Deliverables are satisfied
2. all downstream/child items are terminal
3. every child item is `completed` or `dropped`
4. generator and validator consume one shared `Certifications` policy path for enablement, admissibility, and requiredness decisions
5. focused verification and audit evidence show structural `Certifications` drift is resolved without regressing unrelated validator families

Canonical source-of-truth:

<LINK>
- `docs/operating_system/governance/repo-governance.md`
- `scripts/validate_planning_lifecycle.py`
</LINK>
