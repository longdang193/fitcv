---
layer: change
artifact_type: plan
status: completed
template_id: implementation-plan
name: env-config-single-source-of-truth-plan
parent_thread: workstream-operator-control-plane.operator-control-plane-settings-surface-alignment
parent_spec: docs/superpowers/specs/2026-04-28-operator-control-plane-settings-surface-alignment-spec.md
targets:
  - src/fitcv_cp/app.py
  - docs/setup.md
  - docs/fitcv-control-plane-setup.md
  - docker-compose.isolated.full.yml
  - tests/test_fitcv_cp/test_app.py
  - docs/superpowers/plans/audit/20260512-2058-env-config-sot-drift/report.md
  - docs/superpowers/plans/audit/20260512-2058-env-config-sot-drift/manifest.yaml
related_features:
  - admin_control_plane_core
  - trigger_run_management
related_stages:
  - cv_generation
---

## Goal

Remove runtime config ambiguity by enforcing one canonical config file (`config/env.yaml`), while preserving backward-compatible explicit path overrides and updating docs + audit evidence accordingly.

## Key Deliverables

### Canonical default config path alignment

Control plane default request/runtime config path uses `config/env.yaml` instead of `.env.yaml` in defaulted entry points, while still accepting explicit `config_path` values passed by users/tests.

### Public onboarding and runbook alignment

Setup and control-plane docs clearly define:
- canonical config source: `config/env.yaml`
- `.env` purpose: secrets/environment variables
- `.env.yaml` status: optional local override only (or deprecated usage note if retained)

### Audit traceability completion

Audit bundle `20260512-2058-env-config-sot-drift` records fix outcome, verification evidence, and disposition update with valid checksum-linked artifacts.

## Task/Wave Breakdown

### Task 1: Lock canonical default config path in runtime surface

**Purpose:**
- Make runtime default deterministic and single-source aligned.

**Files:**
- Inspect: `src/fitcv_cp/app.py`
- Modify: `src/fitcv_cp/app.py`
- Verify: `tests/test_fitcv_cp/test_app.py`

**Preconditions:**
- Audit finding F-001 confirmed.
- Mixed `.env.yaml`/`config/env.yaml` references mapped.

**Steps:**
- [x] Step 1: Locate defaulted `config_path` values (e.g., `Form(".env.yaml")`, function defaults).
- [x] Step 2: Change only default values to `config/env.yaml`.
- [x] Step 3: Preserve explicit path passthrough behavior; no schema or loading logic broad refactor in this task.

**Verification:**
- [x] `rg -n "Form\(\"\.env\.yaml\"\)|config_path: str = \"\.env\.yaml\"" src/fitcv_cp/app.py`
- [x] `py -m pytest tests/test_fitcv_cp/test_app.py -q`

**Exit Criteria:**
- No remaining default `.env.yaml` in targeted control-plane defaults.
- App tests covering request/config path behavior pass.

### Task 2: Align setup and runbook docs to canonical config contract

**Purpose:**
- Eliminate contributor confusion and drift from onboarding docs.

**Files:**
- Inspect: `docs/setup.md`, `docs/fitcv-control-plane-setup.md`, `docker-compose.isolated.full.yml`
- Modify: `docs/setup.md`, `docs/fitcv-control-plane-setup.md` (and compose doc references only if needed)
- Verify: same docs plus config references via grep

**Preconditions:**
- Task 1 defaults finalized.

**Steps:**
- [x] Step 1: Replace quick-start flow references that assume `.env.yaml.example` when file may be absent.
- [x] Step 2: State canonical source and precedence explicitly (`config/env.yaml` baseline, explicit override path optional).
- [x] Step 3: Ensure compose/runbook wording does not imply equal-authority dual config files.

**Verification:**
- [x] `rg -n "\.env\.yaml\.example|Copy-Item .*\.env\.yaml\.example" docs/setup.md docs/fitcv-control-plane-setup.md`
- [x] `rg -n "config/env\.yaml|\.env\.yaml" docs/setup.md docs/fitcv-control-plane-setup.md`

**Exit Criteria:**
- Docs present one clear canonical config contract.
- No broken startup instruction due missing `.env.yaml.example` dependency.

### Task 3: Pattern detection and bounded remediation decision

**Purpose:**
- Detect adjacent drift patterns and decide immediate fix vs defer with audit rationale.

**Files:**
- Inspect: `tests/test_pipeline.py`, `tests/**`, docs/config references
- Modify: optional minimal targeted files only if low risk
- Verify: grep outputs + rationale in audit report

**Preconditions:**
- Task 1 and Task 2 complete.

**Steps:**
- [x] Step 1: Scan for `.env.yaml` vs `config/env.yaml` usage across tests/docs/runtime scripts.
- [x] Step 2: Classify each cluster as `confirmed | likely | risk`.
- [x] Step 3: Apply only low-risk immediate fixes; defer broad fixture migration with explicit notes.

**Verification:**
- [x] `rg -n "config_path=\"\.env\.yaml\"|config_path=\"config/env\.yaml\"|\.env\.yaml" tests docs src`

**Exit Criteria:**
- Pattern findings documented with explicit fix-now/defer decisions.

### Task 4: Close audit loop with evidence and gate

**Purpose:**
- Preserve audit-evidence mandate compliance after patch.

**Files:**
- Inspect: `docs/superpowers/plans/audit/20260512-2058-env-config-sot-drift/report.md`, `manifest.yaml`
- Modify: same + new evidence files under `evidence/results/`
- Verify: `scripts/audit_check.py`

**Preconditions:**
- Tasks 1-3 complete with concrete outputs.

**Steps:**
- [x] Step 1: Add post-fix evidence artifact(s) with command outputs/checksums.
- [x] Step 2: Update report findings, fix path, verification results, residual risk, disposition.
- [x] Step 3: Update manifest evidence index and verification status.

**Verification:**
- [x] `py scripts/audit_check.py docs/superpowers/plans/audit/20260512-2058-env-config-sot-drift`

**Exit Criteria:**
- Audit gate passes.
- Report has no unresolved required decision checkboxes.

## Verification

- `py -m pytest tests/test_fitcv_cp/test_app.py -q`
- `rg -n "Form\(\"\.env\.yaml\"\)|config_path: str = \"\.env\.yaml\"" src/fitcv_cp/app.py`
- `rg -n "\.env\.yaml\.example|Copy-Item .*\.env\.yaml\.example" docs/setup.md docs/fitcv-control-plane-setup.md`
- `py scripts/audit_check.py docs/superpowers/plans/audit/20260512-2058-env-config-sot-drift`

## Completion Criteria

1. canonical default config path updated in runtime entry points without breaking explicit override behavior
2. setup/runbook docs consistently communicate single source of truth and startup success path
3. pattern scan performed with fix-now/defer decisions recorded
4. audit bundle updated with post-fix evidence and `audit_check` pass evidence
5. no unrelated files changed outside declared target scope
