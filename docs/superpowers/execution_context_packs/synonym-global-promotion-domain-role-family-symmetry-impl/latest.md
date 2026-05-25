---
lane_id: synonym-global-promotion-domain-role-family-symmetry-impl
artifact_type: execution_context_pack
status: active
created_at: 2026-05-25
---

# Execution Context Pack

## 1) Objective

- **Workstream / Plan:** `workstream-agentic-synonym-management.agentic-synonym-canonical-promotion-flow` / `docs/superpowers/plans/2026-05-25-12-26-synonym-global-promotion-domain-role-family-symmetry-plan.md`
- **Goal:** Implement symmetric, SSOT-correct global promotion for synonym proposals across `skill`, `domain`, `role_family`.
- **Bounded Scope (in-scope only):** promote preview/commit per-field routing + SSOT persistence + exports + tests + docs sync.
- **Out of Scope (explicit):** neighbor maps mutation (`domain_neighbors`, `role_family_neighbors`), expanding auto-promote to non-skill fields, unrelated config/test baseline regressions.

## 2) Canonical Inputs (Source of Truth)

- **Primary plan:** `docs/superpowers/plans/2026-05-25-12-26-synonym-global-promotion-domain-role-family-symmetry-plan.md`
- **Specs / maps / thread docs:**
  - `docs/superpowers/specs/2026-05-25-12-26-synonym-global-promotion-domain-role-family-symmetry-spec.md`
  - `docs/intent/workstreams/threads/workstream-agentic-synonym-management/04-agentic-synonym-canonical-promotion-flow.md`
- **Governance / workflow rules used:**
  - `docs/operating_system/templates/execution-context-pack-template.md`
  - `docs/operating_system/governance/execution-context-pack-governance.md`
  - `docs/operating_system/prompt_templates/implementation-next-action-gate-prompt.md`

## 3) Current Task State

- **Completed:**
  - worktree created: `.worktrees/synonym-global-promotion-domain-role-family-symmetry-impl` on branch `codex/synonym-global-promotion-domain-role-family-symmetry-impl` based on `main@a76c4ee3`
  - GitNexus indexed via CLI: `npx gitnexus analyze` (2026-05-25)
  - Task 1 inventory complete
  - Task 2 SSOT helpers + unit tests complete
  - Task 3 promote preview is field-aware (UI grouped by field)
  - Task 4 promote commit is field-aware (app-side), conflict fields skipped
  - Task 4 worker auto-promote is skill-only (guardrails + test)
  - Task 5 global policy exports added + docs/api.md updated
  - Task 6 targeted tests + fast validators run
- **In Progress:**
  - none
- **Deferred / Dropped:**
  - none
- **Known divergence from plan (if any):**
  - baseline targeted test failure observed before changes: `python -m pytest -q tests/test_config.py` fails `test_load_config_defaults_to_repo_config_shape` due to candidate_profile path expectation mismatch; treat as pre-existing baseline issue, not part of this lane.

## 4) Files Changed This Session

- `docs/superpowers/execution_context_packs/synonym-global-promotion-domain-role-family-symmetry-impl/latest.md` — initialize canonical context pack.
- `src/fitcv_cp/app.py` — add domain/role-family SSOT IO helpers + YAML block replacement helper.
- `src/fitcv_cp/worker_job.py` — add domain/role-family SSOT IO helpers + YAML block replacement helper.
- `tests/test_fitcv_cp/test_synonym_global_policy_io.py` — unit tests for YAML block replacement helper.
- `tests/test_fitcv_cp/test_synonym_promote_preview_field_aware.py` — preview builder mixed-field test.
- `tests/test_fitcv_cp/test_synonym_promote_commit_field_aware.py` — commit routes by field, skips conflict fields.
- `src/fitcv_cp/templates/synonym_promote_preview.html` — field-grouped promote preview UI.
- `docs/superpowers/plans/2026-05-25-12-26-synonym-global-promotion-domain-role-family-symmetry-plan.md` — tick Task 1–2 checkboxes.

## 5) Verification State

- **Last commands run:**
  - `python scripts/hooks/run_validator.py --fast` (pass in worktree)
  - `python -m pytest -q tests/test_config.py` (FAIL: `tests/test_config.py::test_load_config_defaults_to_repo_config_shape`)
  - `python -m pytest -q tests/test_fitcv_cp/test_synonym_global_policy_io.py` (pass)
  - `python -m pytest -q tests/test_fitcv_cp/test_synonym_promote_preview_field_aware.py` (pass)
  - `python -m pytest -q tests/test_fitcv_cp/test_synonym_promote_commit_field_aware.py` (pass)
  - `python -m pytest -q tests/test_fitcv_cp/test_worker_job_auto_promote_skill_only.py` (pass)
  - `python -m pytest -q tests/test_fitcv_cp/test_app.py -k "download_global_domain_synonyms_yaml or download_global_role_family_synonyms_yaml or download_global_synonyms_yaml"` (pass)
  - `python scripts/hooks/run_validator.py --fast` (pass)
- **Result summary:**
  - validators pass; added unit tests pass; targeted pytest has 1 pre-existing failure unrelated to synonym promotion surfaces.
- **Failing checks (if any):**
  - `tests/test_config.py::test_load_config_defaults_to_repo_config_shape` expects `data/candidate_profile.yaml` but config returns `data/candidate_profile.private.yaml`.
- **Gaps still unverified:**
  - promotion behavior tests do not exist yet; will be added during Tasks 2–5.

## 6) Open Blockers / Risks

- GitNexus impact analysis is required before editing high-blast-radius symbols; use `npx gitnexus impact` with `-r <repoPath>` to disambiguate.
- Promotion currently ignores proposal `field`; risk of SSOT corruption (domain/role-family proposals written into skill SSOT). Must fix early.

## 7) Next Exact Action

- **Action type:** edit
- **Action type:** command
- **Target:** repo state
- **Exact command or edit intent:** review `git diff` in worktree, then commit changes on branch `codex/synonym-global-promotion-domain-role-family-symmetry-impl`.
- **Why this is next:** implementation work landed; next step is to checkpoint via commit before any broader testing or PR orchestration.

## 8) Resume Prompt (Copy/Paste)

```text
Read this execution context pack first. Verify its state against listed source files. Then execute the Next Exact Action immediately. Do not re-plan unless blocker is found.
```

## 9) Optional Deep Context (Consult Only)

- **conversation_id:** none
- **consult_if:** none

## Source-Truth Rule

If context pack, source files, and raw log disagree:
1. source files and current tests/checks win
2. then context pack
3. raw log is fallback evidence only
