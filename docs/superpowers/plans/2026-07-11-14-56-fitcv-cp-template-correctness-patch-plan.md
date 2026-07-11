---
layer: change
artifact_type: plan
status: proposed
template_id: implementation-plan
name: fitcv-cp-template-correctness-patch
parent_thread: workstream-operator-control-plane.operator-control-plane-run-detail-truth
parent_spec: docs/superpowers/specs/2026-07-11-14-42-fitcv-cp-template-correctness-patch-spec.md
targets:
  - src/fitcv_cp/templates/settings.html
  - src/fitcv_cp/templates/runs_list.html
  - src/fitcv_cp/templates/run_detail_tab_enriched.html
  - src/fitcv_cp/templates/synonym_promote_preview.html
  - src/fitcv_cp/app.py
  - src/fitcv_cp/bq_store.py
  - src/fitcv_cp/store.py
  - src/fitcv_cp/settings_schema.py
  - tests/test_fitcv_cp/test_app.py
  - tests/test_fitcv_cp/test_bq_store.py
  - tests/test_fitcv_cp/test_store.py
  - tests/test_fitcv_cp/test_synonym_promote_commit_field_aware.py
  - tests/test_fitcv_cp/test_synonym_promote_preview_field_aware.py
  - docs/api.md
  - docs/usage.md
  - docs/generated/planning_lineage.yaml
related_features: []
related_stages: []
---

## Goal

Implement bounded control-plane template correctness patch from
`docs/superpowers/specs/2026-07-11-14-42-fitcv-cp-template-correctness-patch-spec.md`
without expanding into control-plane redesign.

## Key Deliverables

### Deliverable 1: Settings rendering and validation truth is branch-invariant

`src/fitcv_cp/templates/settings.html`, `src/fitcv_cp/app.py`, and any small
schema-owned helpers implement one explicit settings rendering contract for
read-only state, composition layout, danger-zone visibility, and client/backend
validation ownership.

### Deliverable 2: Promotion and archived-delete request contracts have one owner

`src/fitcv_cp/templates/synonym_promote_preview.html`,
`src/fitcv_cp/templates/runs_list.html`, and `src/fitcv_cp/app.py` submit one
truthful selection or threshold contract per operator action, with tests proving
no competing input path remains in patched UI flow.

### Deliverable 3: Enriched tab markup, link safety, docs, and proof stay aligned

Patched enriched-tab HTML is structurally valid, `_blank` links in patched
surfaces include `rel="noopener"`, operator/API docs reflect changed request
contracts, and final verification distinguishes patch regressions from known
unrelated planning-lineage baseline drift.

## Task/Wave Breakdown

### Task 1: Normalize settings card shell and danger-zone summary behavior

**Purpose:**
- make settings editability and body layout independent from unrelated shell
  branching

**Files:**
- Inspect: `src/fitcv_cp/templates/settings.html`
- Inspect: `src/fitcv_cp/app.py`
- Modify: `src/fitcv_cp/templates/settings.html`
- Modify: `src/fitcv_cp/app.py`
- Verify: `tests/test_fitcv_cp/test_app.py`

**Preconditions:**
- parent spec remains `proposed|active`
- current shell split and danger-zone summary behavior are still present in live
  template source

**Steps:**
- [ ] Step 1: inventory current card shell branches, `read_only` gating, and
      `composition_matrix` entry points in `settings.html` and card projection in
      `app.py`.
- [ ] Step 2: normalize any `layout == "composition_matrix"` card to the
      standard non-collapsible shell in server-side card projection.
- [ ] Step 3: refactor template branches so `read_only` suppresses form and
      save/reset actions regardless of shell choice.
- [ ] Step 4: replace row-query-based danger-zone hide/show logic with explicit
      summary-section behavior driven by server-owned key metadata and axis
      filters only.

**Verification:**
- [ ] add or extend rendered settings tests for editable/read-only,
      collapsible/non-collapsible, and composition-card normalization behavior
- [ ] add or extend danger-zone tests proving load-time visibility and axis-only
      filtering behavior for summary section

**Exit Criteria:**
- settings shell choice no longer changes editability semantics
- composition cards have one supported shell in patched code
- danger-zone summary uses one explicit visibility contract

### Task 2: Remove duplicate client save blockers and project native attrs from current schema conventions

**Purpose:**
- keep backend validation authoritative while tightening native input behavior
  with smallest schema-owned projection

**Files:**
- Inspect: `src/fitcv_cp/templates/settings.html`
- Inspect: `src/fitcv_cp/app.py`
- Inspect: `src/fitcv_cp/settings_schema.py`
- Modify: `src/fitcv_cp/templates/settings.html`
- Modify: `src/fitcv_cp/app.py`
- Modify: `src/fitcv_cp/settings_schema.py`
- Verify: `tests/test_fitcv_cp/test_app.py`
- Verify: `tests/test_fitcv_cp/test_settings_schema.py`

**Preconditions:**
- Task 1 complete
- current server `validate_settings()` remains canonical save-path validator

**Steps:**
- [ ] Step 1: identify which native attrs can be derived from existing schema
      conventions without inventing a new constraint DSL.
- [ ] Step 2: add one small backend-owned projection helper for current
      conventions: integer minimum, `_secs` non-negative floats, other float
      `[0,1]` bounds, and existing `options` ownership.
- [ ] Step 3: remove hardcoded relational and weight-family submit blockers from
      `runPreflightGuardrails()` while keeping automation prerequisite prompts.
- [ ] Step 4: wire rendered settings controls to projected attrs and existing
      option owners only.

**Verification:**
- [ ] add or extend tests for rendered attrs on integer, float, select, and
      list-backed settings controls
- [ ] confirm save-path tests still fail only through backend validation, not
      duplicated JS rule ownership

**Exit Criteria:**
- backend remains sole blocking validator for settings saves
- rendered controls use current schema conventions instead of ad hoc template
  hardcoding

### Task 3: Make promotion commit checkbox-owned only

**Purpose:**
- remove competing submitted selection truth from synonym global promotion flow

**Files:**
- Inspect: `src/fitcv_cp/templates/synonym_promote_preview.html`
- Inspect: `src/fitcv_cp/app.py`
- Modify: `src/fitcv_cp/templates/synonym_promote_preview.html`
- Modify: `src/fitcv_cp/app.py`
- Verify: `tests/test_fitcv_cp/test_app.py`
- Verify: `tests/test_fitcv_cp/test_synonym_promote_commit_field_aware.py`
- Verify: `tests/test_fitcv_cp/test_synonym_promote_preview_field_aware.py`

**Preconditions:**
- current preview page remains sole UI source for promotion commit submission
- existing field-aware promotion tests still cover canonical promotion behavior

**Steps:**
- [ ] Step 1: remove `selected_ids_csv` from promotion preview form so checkbox
      collection `promote_proposal_id` is the only submitted selection owner.
- [ ] Step 2: remove CSV fallback parsing from promote-commit route and keep
      empty-checkbox submission as validation failure.
- [ ] Step 3: update preview and commit tests to prove checkbox-only path and
      reject old hidden-field-only submission.
- [ ] Step 4: keep actor/note and field-aware promotion behavior unchanged.

**Verification:**
- [ ] app tests cover checkbox success and empty-selection rejection
- [ ] field-aware promote preview/commit tests still pass after hidden CSV path
      removal

**Exit Criteria:**
- operator-visible checkbox state equals submitted promotion selection
- no hidden CSV fallback remains in patched UI flow

### Task 4: Make archived-delete template flow threshold-owned and truthful

**Purpose:**
- stop client-side DOM narrowing and stop count claims that backend may exceed

**Files:**
- Inspect: `src/fitcv_cp/templates/runs_list.html`
- Inspect: `src/fitcv_cp/app.py`
- Inspect: `src/fitcv_cp/store.py`
- Inspect: `src/fitcv_cp/bq_store.py`
- Modify: `src/fitcv_cp/templates/runs_list.html`
- Modify: `src/fitcv_cp/app.py`
- Verify: `tests/test_fitcv_cp/test_app.py`
- Verify: `tests/test_fitcv_cp/test_bq_store.py`
- Verify: `tests/test_fitcv_cp/test_store.py`

**Preconditions:**
- current delete route exists at `POST /admin/runs/bulk/delete-archived`
- compatibility support for optional `run_ids` outside patched template flow may
  remain unchanged in store/backend code

**Steps:**
- [ ] Step 1: remove matched DOM run-id collection and client-derived count from
      archived-delete UI flow.
- [ ] Step 2: update route payload handling so patched template flow submits only
      `older_than_days` and route calls delete backend without `run_ids`.
- [ ] Step 3: keep compatibility tests or add explicit inspection proof that any
      non-template caller support is unchanged unless a smaller simplification is
      proven safe.
- [ ] Step 4: rewrite confirm and success/no-match copy to describe
      threshold-wide destructive scope rather than visible-page count.

**Verification:**
- [ ] app tests cover threshold-only request payload, deleted summary, and
      invalid threshold rejection
- [ ] store/bq tests prove canonical dataset matching still owns delete result
      while patched UI flow does not rely on DOM narrowing

**Exit Criteria:**
- archived-delete UI flow has one threshold-owned contract
- template copy no longer overclaims client-side count accuracy

### Task 5: Repair enriched-tab markup and patched `_blank` link safety

**Purpose:**
- remove browser-repair dependency and missing `noopener` from patched enriched
  tab surface

**Files:**
- Inspect: `src/fitcv_cp/templates/run_detail_tab_enriched.html`
- Modify: `src/fitcv_cp/templates/run_detail_tab_enriched.html`
- Verify: `tests/test_fitcv_cp/test_app.py`
- Verify: `tests/test_fitcv_cp/test_run_detail_output_availability.py`

**Preconditions:**
- enriched-tab toolbar wrapper and `_blank` link defects are still present in
  current template source

**Steps:**
- [ ] Step 1: repair select-shell wrapper markup without changing toolbar class
      ownership or custom multiselect behavior.
- [ ] Step 2: add missing `rel="noopener"` on patched `_blank` links in enriched
      tab output.
- [ ] Step 3: keep all unrelated tab-loading and CSS-system behavior unchanged.

**Verification:**
- [ ] add or extend rendered HTML assertions for valid wrapper structure
- [ ] add or extend assertions that patched `_blank` links include
      `rel="noopener"`

**Exit Criteria:**
- enriched-tab markup is structurally valid
- patched `_blank` links are safety-complete

### Task 6: Align docs, planning lineage, and final verification baseline

**Purpose:**
- keep contract docs current and make final proof explicit about known unrelated
  validator debt

**Files:**
- Inspect: `docs/api.md`
- Inspect: `docs/usage.md`
- Modify: `docs/api.md`
- Modify: `docs/usage.md`
- Modify: `docs/generated/planning_lineage.yaml`
- Verify: `docs/superpowers/specs/2026-07-11-14-42-fitcv-cp-template-correctness-patch-spec.md`
- Verify: `docs/superpowers/plans/2026-07-11-14-56-fitcv-cp-template-correctness-patch-plan.md`

**Preconditions:**
- Tasks 1-5 complete
- known unrelated validator blockers remain:
  - `docs/superpowers/specs/2026-06-26-00-49-indeed-job-input-adapter-spec.md`
  - `docs/superpowers/plans/2026-06-26-00-50-indeed-job-input-adapter-plan.md`
  - `docs/generated/planning_lineage.yaml` drift until refreshed

**Steps:**
- [ ] Step 1: update `docs/api.md` for archived-delete threshold-only request
      shape and checkbox-only promote-commit contract.
- [ ] Step 2: update `docs/usage.md` only where operator-facing delete or
      promotion behavior text would otherwise be stale.
- [ ] Step 3: regenerate `docs/generated/planning_lineage.yaml` after plan/spec
      changes.
- [ ] Step 4: run focused tests for patched settings, promotion, archived-delete,
      and enriched-tab surfaces.
- [ ] Step 5: run fast validator hook and confirm any remaining failure set is
      limited to the known unrelated Indeed adapter planning debt unless that
      debt is fixed in the same branch.

**Verification:**
- [ ] `python -m pytest tests/test_fitcv_cp/test_app.py -k "settings or promote or archived or enriched"`
- [ ] `python -m pytest tests/test_fitcv_cp/test_bq_store.py -k "delete_archived_runs"`
- [ ] `python -m pytest tests/test_fitcv_cp/test_store.py -k "delete_archived_runs"`
- [ ] `python -m pytest tests/test_fitcv_cp/test_synonym_promote_commit_field_aware.py`
- [ ] `python -m pytest tests/test_fitcv_cp/test_synonym_promote_preview_field_aware.py`
- [ ] `python scripts/generate_planning_lineage.py`
- [ ] `python scripts/hooks/run_validator.py --fast`

**Exit Criteria:**
- docs mention patched request contracts truthfully
- planning lineage is refreshed
- final proof distinguishes patch regressions from known unrelated validator debt

## Verification

- `python -m pytest tests/test_fitcv_cp/test_app.py -k "settings or promote or archived or enriched"`
- `python -m pytest tests/test_fitcv_cp/test_bq_store.py -k "delete_archived_runs"`
- `python -m pytest tests/test_fitcv_cp/test_store.py -k "delete_archived_runs"`
- `python -m pytest tests/test_fitcv_cp/test_synonym_promote_commit_field_aware.py`
- `python -m pytest tests/test_fitcv_cp/test_synonym_promote_preview_field_aware.py`
- `python scripts/generate_planning_lineage.py`
- `python scripts/hooks/run_validator.py --fast`

## Completion Criteria

A plan item is considered complete when:

1. all Key Deliverables are satisfied
2. all downstream/child items are terminal
3. every child item is `completed` or `dropped`

Canonical source-of-truth:

<LINK>
- `docs/operating_system/governance/repo-governance.md`
- `scripts/validate_planning_lifecycle.py`
</LINK>