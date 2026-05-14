---
layer: change
artifact_type: plan
status: completed
template_id: implementation-plan
name: hardcoded-synonym-triage-prompt-centralization
parent_thread: workstream-agentic-synonym-management.hardcoded-synonym-triage-prompt-centralization
parent_spec: docs/superpowers/specs/2026-05-14-hardcoded-synonym-triage-prompt-centralization-spec.md
targets:
  - src/fitcv/prompts/templates/synonym_triage_recommendation_v1.md
  - src/fitcv/prompts/registry.py
  - src/fitcv/prompts/renderer.py
  - src/fitcv_cp/app.py
  - tests/test_prompts.py
  - tests/test_fitcv_cp/test_app.py
  - docs/superpowers/plans/audit/20260514-hardcoded-prompts/report.md
related_features: []
related_stages: []
---

# Hardcoded Synonym Triage Prompt Centralization Plan

## Goal

Remove hardcoded synonym-triage prompt from `src/fitcv_cp/app.py` and migrate it into FitCV centralized prompt template and registry system without changing downstream response-shape expectations or breaking current control-plane behavior.

## Key Deliverables

### Centralized prompt definition for synonym triage

Create source-owned prompt template and registry entry for synonym-triage recommendation generation so prompt discovery, versioning, and rendering follow existing `fitcv.prompts` contracts.

### Control-plane caller migration with behavior parity

Replace inline prompt assembly in `src/fitcv_cp/app.py` with `render_prompt(...)` using explicit context variables while preserving provider request behavior and JSON-output expectations consumed by synonym-triage parsing.

### Verification and audit closeout evidence

Keep red/green coverage focused on prompt registration and render behavior, confirm control-plane tests remain green, and update audit verification evidence for `20260514-hardcoded-prompts`.

## Task/Wave Breakdown

### Task 1: Confirm prompt contract and extract canonical template content

**Purpose:**
- Capture exact hardcoded synonym-triage prompt behavior and map dynamic values into template variables before implementation edits.

**Files:**
- Inspect: `src/fitcv_cp/app.py`
- Inspect: `src/fitcv/prompts/registry.py`
- Inspect: `src/fitcv/prompts/renderer.py`
- Inspect: `tests/test_prompts.py`
- Modify: `src/fitcv/prompts/templates/synonym_triage_recommendation_v1.md`

**Preconditions:**
- Existing red tests in `tests/test_prompts.py` document required registry ID and render variables.
- Hardcoded prompt text remains source of truth for behavior parity until extraction completes.

**Steps:**
- [x] Step 1: Re-read hardcoded prompt block in `src/fitcv_cp/app.py` and identify exact static instructions plus interpolated values.
- [x] Step 2: Create `src/fitcv/prompts/templates/synonym_triage_recommendation_v1.md` using canonical prompt wording with `$proposal_json` and `$now_iso` placeholders matching red-test expectations.
- [x] Step 3: Confirm template preserves strict JSON-output requirements and does not weaken downstream parsing contract.

**Verification:**
- [x] `pytest -q tests/test_prompts.py -k synonym_triage`

**Exit Criteria:**
- Template file exists.
- Template variables align with tests and renderer contract.
- Prompt wording preserves current output-shape instructions.

### Task 2: Register prompt and migrate caller to render_prompt

**Purpose:**
- Connect new template to centralized registry and remove inline prompt string from control-plane code with minimal scope change.

**Files:**
- Inspect: `src/fitcv/prompts/registry.py`
- Inspect: `src/fitcv/prompts/renderer.py`
- Modify: `src/fitcv/prompts/registry.py`
- Modify: `src/fitcv_cp/app.py`
- Verify: `tests/test_prompts.py`
- Verify: `tests/test_fitcv_cp/test_app.py`

**Preconditions:**
- Task 1 complete.
- No unrelated prompt migrations bundled into same patch.

**Steps:**
- [x] Step 1: Add `synonym_triage.recommendation.v1` definition to `src/fitcv/prompts/registry.py` following existing metadata and template-path conventions.
- [x] Step 2: Import and call `render_prompt` from `src/fitcv_cp/app.py`, passing serialized proposal JSON and ISO timestamp through explicit context keys.
- [x] Step 3: Remove hardcoded inline prompt string only after rendered output covers same semantic instructions and provider call flow remains unchanged.

**Verification:**
- [x] `pytest -q tests/test_prompts.py -k synonym_triage`
- [x] `pytest -q tests/test_fitcv_cp/test_app.py -k "synonym_triage"`

**Exit Criteria:**
- Registry entry resolves successfully.
- Control-plane path renders centralized prompt instead of inline string.
- Focused prompt and app tests pass.

### Task 3: Run bounded pattern detection and audit closeout verification

**Purpose:**
- Check for adjacent hardcoded prompt drift, classify findings, and capture audit-close evidence without expanding patch scope unless same failure mode is confirmed and cheap to fix safely.

**Files:**
- Inspect: `src/fitcv_cp/app.py`
- Inspect: `src/fitcv/prompts/templates/`
- Inspect: `src/fitcv/prompts/registry.py`
- Modify: `docs/superpowers/plans/audit/20260514-hardcoded-prompts/report.md`

**Preconditions:**
- Task 2 complete.
- Focused tests pass locally.

**Steps:**
- [x] Step 1: Search related prompt-calling surfaces for similar inline prompt construction and classify each finding as `confirmed`, `likely`, or `risk`.
- [x] Step 2: Decide `fix now` versus `defer` using current failure boundary, touching only same contract family if remediation is trivial and safe.
- [x] Step 3: Run audit verification command and update audit report with fix summary, verification evidence links, and final disposition.

**Verification:**
- [x] `pytest -q tests/test_prompts.py -k synonym_triage`
- [x] `pytest -q tests/test_fitcv_cp/test_app.py -k "synonym_triage"`
- [x] `python scripts/audit_check.py docs/superpowers/plans/audit/20260514-hardcoded-prompts`

**Exit Criteria:**
- Pattern findings logged with explicit classification.
- Audit verifier passes for current audit bundle.
- Audit report reflects final status and evidence.

## Verification

- `pytest -q tests/test_prompts.py -k synonym_triage`
- `pytest -q tests/test_fitcv_cp/test_app.py -k "synonym_triage"`
- `python scripts/audit_check.py docs/superpowers/plans/audit/20260514-hardcoded-prompts`

## Completion Criteria

1. `src/fitcv/prompts/templates/synonym_triage_recommendation_v1.md` exists and renders with required context variables.
2. `src/fitcv/prompts/registry.py` registers `synonym_triage.recommendation.v1` under existing prompt-definition conventions.
3. `src/fitcv_cp/app.py` no longer contains hardcoded synonym-triage prompt text and uses centralized rendering.
4. Focused prompt and control-plane tests pass.
5. Audit bundle `20260514-hardcoded-prompts` records passing verification evidence and closure-ready disposition.

