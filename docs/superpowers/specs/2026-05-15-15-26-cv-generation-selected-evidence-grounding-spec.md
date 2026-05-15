---
layer: change
artifact_type: spec
status: proposed
template_id: detailed-specification
name: cv-generation-selected-evidence-grounding
parent_thread: workstream-bounded-agentic-cv-quality.agentic-cv-quality-generation-repair
targets:
  - src/fitcv/cv_generator.py
  - src/fitcv/prompts/templates/cv_generation_structured_write_v1.md
  - src/fitcv/validator.py
related_features:
  - cv_system
related_stages:
  - cv_generation
---

# CV Generation: Selected-Evidence Grounding Alignment

## Goal

Reduce `cv_generation` live-run warnings caused by validator grounding failures by aligning generator instructions and per-job constraints with the validator’s selected-evidence grounding rules, without loosening validator strictness.

## Key Deliverables

### Generator-facing grounding contract

Define explicit prompt-level and runtime-level contract that Skills/Certifications (and other claim-heavy sections) must be sourced from selected evidence, not from the full candidate profile.

### Deterministic constraints surface for the model

Define a minimal, deterministic allow-list payload derived from selected evidence and passed to the CV generation prompt so the model can comply without guessing.

### Validation-ready proof plan

Define concrete proof steps and evidence artifacts (live-run + debug JSON) that demonstrate grounding warnings drop and accepted CVs remain downloadable.

## Task/Wave Breakdown

### Wave 1: Source-first analysis

**Purpose:**
- confirm current failure modes and where grounding rules are enforced

**Steps:**
- [ ] Inspect validator grounding checks in `src/fitcv/validator.py` for:
  - selected-skill grounding violations
  - soft-claim grounding violations
- [ ] Inspect CV generation prompt surface in:
  - `src/fitcv/prompts/templates/cv_generation_structured_write_v1.md`
  - evidence usage guidance builder in `src/fitcv/cv_generator.py`
- [ ] Capture baseline evidence from an existing run where warnings appear:
  - `/admin/runs/<run_id>/cv-debug.json` `failed_rule_ids`
  - `/admin/runs/<run_id>/settings-used.json` evidence budget + prompt ids

**Verification:**
- [ ] Root cause documented with direct evidence links and rule IDs.

**Exit Criteria:**
- no proposed change depends on unknown validator behavior.

### Wave 2: Decision closure

**Purpose:**
- pick smallest change that makes generator comply with existing validator rules

**Steps:**
- [ ] Specify new prompt constraints:
  - “Skills section must list only skills present in selected evidence”
  - “Certifications section must include only certifications present in selected evidence; omit otherwise”
  - “Do not invent certifications or skills from the broader candidate profile”
- [ ] Specify runtime inputs added to prompt:
  - `allowed_skills` (canonicalized)
  - `allowed_certifications` (exact strings)
  - optional: `allowed_employers`, `allowed_projects` (future-safe; may be deferred)
- [ ] Decide certification handling when allow-list empty:
  - option A (preferred): remove Certifications from required sections for that job
  - option B: allow empty Certifications section (rejected; violates current constraints)

**Verification:**
- [ ] Contract aligns with validator behavior without changing validator rules.

**Exit Criteria:**
- chosen contract has clear acceptance criteria + bounded implementation targets.

### Wave 3: Validation and approval readiness

**Purpose:**
- make proof expectations explicit for implementation handoff

**Steps:**
- [ ] Define targeted live-run verification:
  - trigger run
  - confirm `cv_generation` outcomes + warnings in timeline
  - confirm accepted CV still yields `cv_versions` row and download works
- [ ] Define regression checks:
  - existing validator tests remain valid
  - no loosening of validator strictness required for success

**Verification:**
- [ ] Validation plan includes exact commands/URLs and evidence locations.

**Exit Criteria:**
- spec ready for implementation planning (`skill-writing-plans`).

## Design Decisions

### Decision: Keep validator strict; constrain generator inputs

- context: Live runs show `validation_failed` warnings caused by “present in candidate profile but not in selected evidence” and “Soft claim is not supported by selected evidence” failures in `/admin/runs/<run_id>/cv-debug.json`.
- choice: Preserve selected-evidence grounding checks; add deterministic allow-list derived from selected evidence and enforce prompt constraints to keep Skills/soft claims inside selected-evidence support surface. For Certifications, remove profile-only fallback so the section is required only when selected evidence explicitly supports certifications.
- alternatives considered:
  - loosen validator rules (rejected: increases ungrounded/hallucinated claims risk)
  - increase `pipeline.evidence_top_k` (rejected: cost/latency and still allows ungrounded claims)
  - allow “profile skills” as valid support (rejected: defeats selected-evidence contract)
- impact:
  - `src/fitcv/cv_generator.py` will need to emit allow-lists + stricter evidence usage guidance
  - `src/fitcv/prompts/templates/cv_generation_structured_write_v1.md` must include hard constraints
  - `src/fitcv/section_policy.py` certification admissibility becomes selected-evidence-only (no profile fallback)

### Decision: Omit Certifications section when no supported certifications

- context: Certifications are high-risk for hallucination and currently trigger soft-claim grounding failures.
- choice: Make Certifications conditional per job: include only when selected evidence explicitly supports at least one certification; profile-only certifications are treated as unsupported for this validator contract.
- alternatives considered:
  - keep Certifications always required (rejected: pushes model toward unsupported claims or empty sections)
- impact:
  - required sections list in constraints must be per-job, not global-only, or Certifications must be allowed to be absent when unsupported.

## Invariants

- Validator grounding checks remain strict; do not downgrade to warnings.
- CV markdown output standard stays unchanged (headings, bullets, no placeholders).
- Existing download mechanics remain unchanged:
  - accepted CV produces a `cv_versions.version_id`
  - download path `/admin/cvs/<version_id>/download` continues to work.
- Evidence budget and selection policy remain unchanged by default (no required `evidence_top_k` increase).
- Certifications are never accepted solely because they exist in the candidate profile; admissibility requires selected-evidence support.

## Validation Plan

- proof target: grounding warnings reduced for selected-evidence violations
  - method: live run + inspection
  - evidence:
    - `/admin/runs/<run_id>/cv-debug.json` shows fewer/zero `failed_rule_ids` matching:
      - `Skill '*' ... present in candidate profile but not in selected evidence`
      - `Soft claim is not supported by selected evidence:`
- proof target: accepted CV still persisted and downloadable
  - method: live run + HTTP check
  - evidence:
    - `/admin/runs/<run_id>` Outputs card shows `state=available` with `downloadables>0`
    - `/admin/cvs/<version_id>/download` returns `200`
- proof target: no validator loosening required
  - method: code inspection + test run
  - evidence:
    - `src/fitcv/validator.py` grounding rules unchanged
    - existing unit tests pass (include any newly added tests for the allow-list contract)

## Completion Criteria

- Spec deliverables above satisfied with explicit acceptance criteria and validation plan.
- Downstream plan (implementation plan) created and approved, or spec explicitly marked completed/superseded.
