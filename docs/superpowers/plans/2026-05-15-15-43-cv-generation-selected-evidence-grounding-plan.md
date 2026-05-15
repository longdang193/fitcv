---
layer: change
artifact_type: plan
status: completed
template_id: implementation-plan
name: cv-generation-selected-evidence-grounding
parent_thread: workstream-bounded-agentic-cv-quality.agentic-cv-quality-generation-repair
parent_spec: docs/superpowers/specs/2026-05-15-15-26-cv-generation-selected-evidence-grounding-spec.md
targets:
  - src/fitcv/cv_generator.py
  - src/fitcv/prompts/templates/cv_generation_structured_write_v1.md
  - src/fitcv/validator.py
  - tests/test_validator.py
related_features:
  - cv_system
related_stages:
  - cv_generation
---

# CV Generation: Selected-Evidence Grounding Alignment (Implementation Plan)

## Goal

Align CV generation outputs with existing selected-evidence grounding validator rules so live runs no longer emit `cv_generation` warnings driven by unsupported Skills/Certifications/soft claims.

## Key Deliverables

### Deterministic allow-list payload for CV generation

Runtime computes per-job allow-lists (skills and certifications) derived from selected evidence and passes them into the CV generation prompt so the model can comply deterministically.

**Example (per-job prompt payload):**

Selected evidence (input) contains only these skill/cert mentions:
- evidence item A: “Built SQL + Power BI dashboards…”
- evidence item B: “Implemented dbt models…”
- evidence item C: (no cert references)

Derived allow-lists (output) passed into prompt variables:

```json
{
  "allowed_skills": ["SQL", "Power BI", "dbt"],
  "allowed_certifications": []
}
```

Implication:
- model may list `SQL`, `Power BI`, `dbt` in Skills
- model must not list profile-only skills like `Observability`, `Workflow Automation`, etc unless they appear in selected evidence
- model must not invent certifications if allow-list empty

### Prompt constraints enforce allow-lists

`cv_generation_structured_write_v1` prompt explicitly instructs that Skills/Certifications must be a subset of provided allow-lists; omit unsupported items.

**Example (prompt instruction text):**

```text
Allowed Skills (selected-evidence only): SQL, Power BI, dbt
Allowed Certifications (selected-evidence only): (none)

Hard rules:
- Skills section MUST contain only skills from Allowed Skills. Do not add any other skills from the broader candidate profile.
- Certifications section MUST be omitted when Allowed Certifications is empty.
- Never invent certifications or training.
```

### Verification evidence: warnings drop without loosening validator

Unit tests cover allow-list behavior and live-run evidence shows fewer/zero grounding-based `validation_failed` outcomes (no validator changes required).

**Example (what “good” evidence looks like):**

- Unit test asserts:
  - when `allowed_certifications=[]`, rendered CV has no `## Certifications` section
  - when `allowed_skills=["SQL"]`, rendered CV Skills contains `SQL` but not `Observability`
- Live run (post-change) shows:
  - `/admin/runs/<run_id>/cv-debug.json` has `validation_failed` count reduced, and `failed_rule_ids` no longer include strings like:
    - `Skill 'X' in CV Skills section is present in candidate profile but not in selected evidence`
    - `Soft claim is not supported by selected evidence:`
  - accepted CV still persists to `cv_versions` and `/admin/cvs/<version_id>/download` returns `200`

## Task/Wave Breakdown

### Task 1: Map current data flow + pick insertion seam

**Purpose:**
- Identify where selected evidence is assembled and where CV generation prompt variables are built so allow-lists can be added with minimal surface area.

**Files:**
- Inspect: `src/fitcv/cv_generator.py`
- Inspect: `src/fitcv/prompts/templates/cv_generation_structured_write_v1.md`
- Inspect: `src/fitcv/validator.py`

**Preconditions:**
- Spec available: `docs/superpowers/specs/2026-05-15-15-26-cv-generation-selected-evidence-grounding-spec.md`
- Baseline evidence: `http://localhost:8000/admin/runs/f1097cd9-8632-47e9-832a-5cf9935a1996/cv-debug.json`

**Steps:**
- [x] Locate function building CV generation prompt vars (selected evidence + constraints + section evidence).
- [x] Identify selected evidence structure available at that seam (e.g., evidence ids + skill mentions + cert mentions).
- [x] Confirm validator expectations for:
  - selected skill grounding violations
  - soft claim grounding violations

**Verification:**
- [x] Document chosen seam in implementation notes within this plan task (no new spec needed).

**Exit Criteria:**
- Clear plan for where to compute allow-lists and how to pass them to prompt variables.

### Task 2: Compute allow-lists from selected evidence

**Purpose:**
- Add deterministic computation of allow-lists that match validator extraction rules as closely as practical.

**Files:**
- Modify: `src/fitcv/cv_generator.py`
- Verify: `src/fitcv/validator.py`

**Preconditions:**
- Task 1 complete (chosen seam identified).

**Steps:**
- [x] Add `allowed_skills` computation:
  - derive from selected evidence items only
  - canonicalize using existing skill canonicalization logic (same as validator path where possible)
- [x] Add `allowed_certifications` computation:
  - include only cert rows explicitly present in selected evidence items
  - keep exact text stable (avoid model-invented variants)
- [x] Ensure allow-list is per-job (based on that job’s selected evidence), not run-global.

**Verification:**
- [x] Add/extend unit tests to prove allow-lists are computed and passed into prompt vars.

**Exit Criteria:**
- Generator provides allow-lists in prompt context for at least one test fixture.

### Task 3: Tighten CV generation prompt with allow-list constraints

**Purpose:**
- Ensure model respects selected-evidence grounding contract for Skills and Certifications.

**Files:**
- Modify: `src/fitcv/prompts/templates/cv_generation_structured_write_v1.md`

**Preconditions:**
- Task 2 complete (variables available).

**Steps:**
- [x] Add new prompt blocks:
  - `## Allowed Skills (selected-evidence only)` + list payload
  - `## Allowed Certifications (selected-evidence only)` + list payload
- [x] Add hard constraint text:
  - Skills section must be subset of Allowed Skills
  - Certifications section must include only Allowed Certifications
  - If Allowed Certifications empty, omit Certifications section (and do not invent)
- [x] Keep markdown output standard constraints unchanged.

**Verification:**
- [x] Add snapshot-style test or unit test that prompt rendering includes allow-list blocks.

**Exit Criteria:**
- Prompt includes enforceable, unambiguous grounding instructions.

### Task 4: Make Certifications conditional (no empty required section)

**Purpose:**
- Avoid forcing the model to hallucinate certifications when none supported, while keeping required-section ordering rules coherent.

**Files:**
- Modify: `src/fitcv/cv_generator.py`
- Verify: `src/fitcv/validator.py`
- Verify: `tests/test_validator.py`

**Preconditions:**
- Task 2 complete.

**Steps:**
- [x] Change per-job required sections list so Certifications is included only when allow-list non-empty.
- [x] Keep validator acceptance criteria satisfied (no empty required sections; no placeholders).

**Verification:**
- [x] Extend validator tests to cover:
  - Certifications omitted when unsupported
  - No grounding violations introduced by omission

**Exit Criteria:**
- Validation failures for unsupported certifications no longer appear when allow-list empty.

### Task 5: Live-run verification (docker mode)

**Purpose:**
- Produce evidence that grounding-based warnings drop under real runtime.

**Files:**
- Verify: live endpoints

**Preconditions:**
- Tasks 1–4 complete.
- Control plane running (`docker compose ps` shows `web` and `worker` up).

**Steps:**
- [x] Trigger run:
  - `Invoke-RestMethod -Method Post -Uri "http://localhost:8000/runs" -ContentType "application/json" -Body '{"jobs_path":"data/sample_jobs.json","config_path":"config/env.yaml","triggered_by":"admin","run_mode":"run_all"}'`
- [x] For completed run, inspect:
  - `/admin/runs/<run_id>/cv-debug.json`
  - `/admin/runs/<run_id>/stage-artifacts/cv_generation.json`
- [x] Confirm downloadability still works for accepted CV:
  - `/admin/runs/<run_id>` Outputs card shows `available`
  - `/admin/cvs/<version_id>/download` returns `200`

**Verification:**
- [x] Evidence recorded in result pack or follow-up audit bundle if a qualifying failure occurs.

**Exit Criteria:**
- Live run produces fewer/zero grounding-based validation failures without changing validator strictness.

## Verification

- `python -m pytest tests/test_validator.py -k \"certification or grounding or soft_claim\" -p no:langsmith -p no:anyio -vv -s`
- `python -m pytest tests/test_fitcv_cp/test_run_detail_output_availability.py -p no:langsmith -p no:anyio -vv`
- Live run proof (docker mode):
  - `POST http://localhost:8000/runs`
  - Inspect `/admin/runs/<run_id>/cv-debug.json` and confirm selected-evidence grounding rule strings absent/reduced.
  - Evidence run: `dd51a1a2-521a-4bcf-a2e7-7cc94b55dd7d` (`accepted=4`, no grounding failures in `cv-debug.json`, outputs downloadable)

## Completion Criteria

- All Key Deliverables met with direct evidence:
  - tests passing
  - live-run `cv-debug.json` shows grounding warnings removed/reduced
  - accepted CV still yields downloadable `cv_versions.version_id`
- Plan status can be set to `completed` and `python scripts/validate_planning_lifecycle.py --strict` passes.
