---
layer: change
artifact_type: plan
status: proposed
template_id: implementation-plan
name: synonym-global-promotion-domain-role-family-symmetry
parent_thread: workstream-agentic-synonym-management.agentic-synonym-canonical-promotion-flow
parent_spec: docs/superpowers/specs/2026-05-25-12-26-synonym-global-promotion-domain-role-family-symmetry-spec.md
targets:
  - config/taxonomy/skill_synonyms.yaml
  - config/taxonomy/domain_synonyms.yaml
  - config/taxonomy/role_family_synonyms.yaml
  - src/fitcv_cp/app.py
  - src/fitcv_cp/worker_job.py
  - src/fitcv_cp/templates/synonym_review.html
  - src/fitcv_cp/templates/synonym_promote_preview.html
  - docs/api.md
related_features:
  - cv_system
related_stages:
  - enrich
  - rule_filter
  - cv_analysis
  - cv_generation
---

## Goal

Implement symmetric, SSOT-correct global promotion for synonym proposals across `skill`, `domain`, and `role_family` fields so promotion always writes to correct canonical policy map(s) and never cross-pollutes SSOT.

## Key Deliverables

### Deliverable 1: Field-aware promote preview + commit

Promote flow routes selected proposals by `proposal.field` and applies updates into:
- `skill` → `config/taxonomy/skill_synonyms.yaml` (`skill_synonyms`)
- `domain` → `config/taxonomy/domain_synonyms.yaml` (`domain_alias_map`)
- `role_family` → `config/taxonomy/role_family_synonyms.yaml` (`role_family_alias_map`)

### Deliverable 2: Symmetric global policy exports

Add global download endpoints for domain and role-family policy and document them in `docs/api.md`.

### Deliverable 3: Safety gates + tests

Add tests proving:
- no cross-field writes
- deterministic persistence
- idempotent promotion behavior

## Task/Wave Breakdown

### Task 1: Inventory current promotion + SSOT surfaces

**Purpose:**
- lock current-state boundaries and identify exact symbols/routes/files to modify

**Files:**
- Inspect: `src/fitcv_cp/app.py`
- Inspect: `src/fitcv_cp/worker_job.py`
- Inspect: `src/fitcv_cp/templates/synonym_review.html`
- Inspect: `src/fitcv_cp/templates/synonym_promote_preview.html`
- Inspect: `config/taxonomy/domain_synonyms.yaml`
- Inspect: `config/taxonomy/role_family_synonyms.yaml`
- Inspect: `src/fitcv/config.py`
- Inspect: `docs/api.md`

**Preconditions:**
- spec is approved for implementation planning scope (this plan)

**Steps:**
- [ ] confirm promote-preview/commit routes and which SSOT they load/persist today
- [ ] confirm proposal payload includes `field` values for domain and role-family
- [ ] confirm domain/role-family SSOT schema keys and intended ownership boundaries
- [ ] record current route list and filenames for existing skill global export

**Verification:**
- [ ] `rg -n "promote-preview|promote-commit|_load_global_skill_synonyms_map" src/fitcv_cp/app.py src/fitcv_cp/worker_job.py`
- [ ] `rg -n "domain_alias_map|role_family_alias_map" config/taxonomy/*.yaml src/fitcv/config.py`

**Exit Criteria:**
- exact edit points + current invariance violation documented in plan notes for later PR description

### Task 2: Add SSOT load/persist + YAML rendering helpers for domain/role-family alias maps

**Purpose:**
- provide first-class, deterministic IO for each global policy surface

**Files:**
- Modify: `src/fitcv_cp/app.py`
- Modify: `src/fitcv_cp/worker_job.py`
- Verify: `config/taxonomy/domain_synonyms.yaml`
- Verify: `config/taxonomy/role_family_synonyms.yaml`

**Preconditions:**
- Task 1 complete

**Steps:**
- [ ] add `_global_domain_synonyms_path()` + loader/persist for `domain_alias_map` only
- [ ] add `_global_role_family_synonyms_path()` + loader/persist for `role_family_alias_map` only
- [ ] implement deterministic YAML writer preserving existing header comments and non-mutated sections:
  - always keep `domain_neighbors` / `role_family_neighbors` untouched
  - only update alias-map mapping entries
- [ ] ensure writer sorts aliases and writes trailing newline

**Verification:**
- [ ] unit tests for YAML render/parse round-trip for each file type

**Exit Criteria:**
- dedicated helpers exist for each SSOT surface; no promotion logic yet

### Task 3: Refactor promote preview builder to be field-aware

**Purpose:**
- preview must show what will change per field and compute conflicts per field

**Files:**
- Modify: `src/fitcv_cp/app.py`
- Modify: `src/fitcv_cp/templates/synonym_promote_preview.html`

**Preconditions:**
- Task 2 complete

**Steps:**
- [ ] extend preview builder to:
  - read proposal `field`
  - group rows by field
  - use correct global map for each field to classify add/update/skip
  - compute conflicts per field (duplicate alias with multiple canonicals within same field)
- [ ] update template to render grouped sections (Skills / Domain / Role Family) with per-field counts and blocked reasons
- [ ] keep behavior for “already present” vs “blocked” rows consistent with existing skill preview semantics

**Verification:**
- [ ] test preview builder with mixed-field selected ids; assert per-field groupings and counts

**Exit Criteria:**
- preview page explicitly shows which SSOT maps will be written

### Task 4: Refactor promote commit to apply per-field and persist correct SSOT files

**Purpose:**
- commit must update correct SSOT map(s), and must never write a non-skill proposal into skill SSOT

**Files:**
- Modify: `src/fitcv_cp/app.py`
- Modify: `src/fitcv_cp/worker_job.py` (guardrails for auto-promote)

**Preconditions:**
- Task 3 complete

**Steps:**
- [ ] implement commit path that:
  - reuses preview output as decision envelope
  - applies promotions per field to correct map
  - persists only fields without conflicts
  - records per-field applied/skipped/failed counts in redirect query params and event payload(s)
- [ ] enforce worker auto-promote skill-only:
  - skip proposals where `field != "skill"` with explicit reason
  - never write domain/role-family from auto-promote in this change

**Verification:**
- [ ] tests: commit updates correct SSOT file(s) for mixed-field selection
- [ ] tests: auto-promote skips non-skill proposals and does not mutate domain/role SSOT

**Exit Criteria:**
- promotion invariants proven by tests (“no cross-field writes”, “correct SSOT updated”)

### Task 5: Add symmetric global policy download endpoints + docs update

**Purpose:**
- make SSOT policy visible and exportable for domain and role-family, matching skill

**Files:**
- Modify: `src/fitcv_cp/app.py`
- Modify: `docs/api.md`

**Preconditions:**
- Task 4 complete

**Steps:**
- [ ] add `GET /admin/synonyms/global-domain.yaml` exporting `domain_alias_map` YAML
- [ ] add `GET /admin/synonyms/global-role-family.yaml` exporting `role_family_alias_map` YAML
- [ ] decide and implement back-compat for existing `GET /admin/synonyms/global.yaml` (keep as skill export or add redirect to `/admin/synonyms/global-skill.yaml`)
- [ ] update `docs/api.md` to reflect per-field SSOT and new endpoints

**Verification:**
- [ ] route tests for 200 + expected YAML top keys per endpoint

**Exit Criteria:**
- operators can download canonical global policy for all three fields

### Task 6: Regression tests + validation and generated planning outputs refresh

**Purpose:**
- ensure repo contract validators pass and planning lineage stays current

**Files:**
- Verify: `tests/*` (new/updated tests)
- Verify: `docs/generated/planning_lineage.yaml`

**Preconditions:**
- Tasks 1–5 complete

**Steps:**
- [ ] run targeted tests for promotion preview/commit + worker auto-promote guardrails
- [ ] run `python scripts/hooks/run_validator.py --fast`
- [ ] run `python scripts/generate_planning_lineage.py` if validator reports stale planning lineage

**Verification:**
- [ ] test output shows new tests passing
- [ ] validator passes with no planning lineage drift

**Exit Criteria:**
- repo passes hook subset validators and promotion behavior is covered by tests

## Verification

- `python -m pytest -q`
- `python scripts/hooks/run_validator.py --fast`

## Completion Criteria

1. all Key Deliverables are satisfied
2. all downstream/child items are terminal
3. every child item is `completed` or `dropped`

