# Execution Context Pack

## 1) Objective

- **Workstream / Plan:** `docs/superpowers/plans/2026-05-15-15-43-cv-generation-selected-evidence-grounding-plan.md`
- **Goal:** Align CV generation with selected-evidence grounding so validator warnings drop without loosening validator.
- **Bounded Scope (in-scope only):** `src/fitcv/cv_generator.py`, `src/fitcv/prompts/templates/cv_generation_structured_write_v1.md`, small focused tests in `tests/test_validator.py`, live-run verification via `/admin/runs/<run_id>/*` exports.
- **Out of Scope (explicit):** Loosening validator strictness; broad ranking/enrichment changes; unrelated UI work.

## 2) Canonical Inputs (Source of Truth)

- **Primary plan:** `docs/superpowers/plans/2026-05-15-15-43-cv-generation-selected-evidence-grounding-plan.md`
- **Specs / maps / thread docs:** `docs/superpowers/specs/2026-05-15-15-26-cv-generation-selected-evidence-grounding-spec.md`, `docs/intent/workstreams/threads/workstream-bounded-agentic-cv-quality/02-agentic-cv-quality-generation-repair.md`
- **Governance / workflow rules used:** `docs/operating_system/prompt_templates/implementation-next-action-gate-prompt.md`, `docs/operating_system/governance/execution-context-pack-governance.md`

## 3) Current Task State

- **Completed:** Task 1, Task 2, Task 3, Task 4, Task 5
- **In Progress:** none
- **Deferred / Dropped:** none
- **Known divergence from plan (if any):**
  - Plan assumed Certifications could be omitted purely via prompt/required-sections. Live run showed validator still required Certifications based on profile fallback; fixed by making certification admissibility selected-evidence-only in `src/fitcv/section_policy.py`.

## 4) Files Changed This Session

- `docs/superpowers/plans/2026-05-15-15-43-cv-generation-selected-evidence-grounding-plan.md` — set `status: active` to begin execution
- `docs/superpowers/execution_context_packs/cv-generation-selected-evidence-grounding/latest.md` — initialize canonical execution handoff pack
- `artifacts/execution_context_pack.md` — mirror pointer to canonical context pack
- `src/fitcv/cv_generator.py` — compute `allowed_skills` from selected evidence, pass `allowed_*` into prompt context, constrain Skills to allow-list
- `src/fitcv/prompts/templates/cv_generation_structured_write_v1.md` — add allow-list blocks + hard rules
- `src/fitcv/section_policy.py` — make Certifications admissible only via selected evidence (no profile fallback)
- `tests/test_cv_generator.py` — update prompt expectations + add structured allow-list test
- `tests/test_validator.py` — update certification requirement test to selected-evidence-only behavior

## 5) Verification State

- **Last commands run:**
  - `python -m pytest tests/test_cv_generator.py -p no:langsmith -p no:anyio -vv -s`
  - `python -m pytest tests/test_validator.py -k "certification or grounding or soft_claim" -p no:langsmith -p no:anyio -vv -s`
  - `docker compose up -d --build web worker`
  - `python scripts/validate_planning_lifecycle.py --strict`
  - `python scripts/validate_checkpoint_packs.py`
  - `python scripts/validate_repo_contracts.py --fast`
  - `py scripts/validate_checkpoint_packs.py`
  - `py scripts/validate_template_required_sections.py`
  - `py scripts/validate_planning_lifecycle.py --strict`
- **Result summary:** unit tests passing; live run evidence captured (see below)
- **Failing checks (if any):**
  - `python scripts/validate_planning_lifecycle.py --strict` exits non-zero due to many `[WARN] planning_lifecycle_warning` findings about deprecated manual thread linkage sections across multiple `docs/intent/workstreams/threads/*` files.
- **Passing closeout checks (latest):**
  - `python scripts/validate_checkpoint_packs.py` passed
  - `python scripts/validate_repo_contracts.py --fast` passed
- **Gaps still unverified:** none

- **Live-run evidence (docker mode):**
  - `dd51a1a2-521a-4bcf-a2e7-7cc94b55dd7d`:
    - `/admin/runs/<id>/cv-debug.json` shows `accepted=4` and no grounding-based validation failures.
    - `/admin/runs/<id>` Outputs card shows `available` with `generated=4, version_rows=4, downloadables=4`.
    - `/admin/cvs/<version_id>/download` returns `200`.
  - `c578ca78-86ce-4135-84fa-bc8195726979`:
    - `/admin/runs/<id>/cv-debug.json` shows `accepted=4` and `failed_rule_ids=[]`.
    - `/admin/runs/<id>/stage-artifacts/cv_generation.json` shows `validation_failed=0`.
    - `/admin/cvs/ae0caa4b-117e-41af-80a4-230ca5b0c11d/download` returns `200`.
  - `e7179a41-e83c-4272-8a4e-cd75809195cc`:
    - `/admin/runs/<id>/cv-debug.json` shows `debug_records=4`, `failed_rule_ids_count=0`.
    - `/admin/runs/<id>/stage-artifacts/cv_generation.json` shows `accepted=4`, `validation_failed=0`, `review_required=0`.
    - `/admin/cvs/83fdfc14-f30c-4b3c-bdfd-87184e6e629a/download` returns `200`.
  - `e415befa-0700-4cbd-9287-dd946a999297`:
    - `/admin/runs/<id>/cv-debug.json` shows `failed_rule_ids_count=0`.
    - `/admin/runs/<id>/stage-artifacts/cv_generation.json` shows `accepted=4`, `validation_failed=0`.
  - `58e1878f-fda2-42fc-8fc3-484b3427cd61`:
    - `/admin/runs/<id>/cv-debug.json` shows `failed_rule_ids_count=0`.
    - `/admin/runs/<id>/stage-artifacts/cv_generation.json` shows `accepted=4`, `validation_failed=0`.
  - `2c6dbacc-0c82-49b5-a4cd-372f7470f033`:
    - `/admin/runs/<id>/cv-debug.json` shows `debug_records=4`, `failed_rule_ids_count=0`.
    - `/admin/runs/<id>/stage-artifacts/cv_generation.json` shows `accepted=4`, `validation_failed=0`, `review_required=0`.
    - `/admin/cvs/5438dc3a-36ae-4e77-b841-6ca45fb00760/download` returns `200`.
  - `9d7440ef-2a55-4a02-8be6-4db2979a13cf`:
    - `/admin/runs/<id>/cv-debug.json` shows `failed_rule_ids_count=0`.
    - `/admin/runs/<id>/stage-artifacts/cv_generation.json` shows `accepted=4`, `validation_failed=0`, `review_required=0`.
  - `5a87a5a7-18cb-4597-9239-98575477247a`:
    - `/admin/runs/<id>/cv-debug.json` shows `failed_rule_ids_count=0`.
    - `/admin/runs/<id>/stage-artifacts/cv_generation.json` shows `accepted=4`, `validation_failed=0`, `review_required=0`.
  - Note: one transient failure run `5573f43b-1f87-4af9-9283-bc638ce0c8bd` returned `error_message="disk I/O error"`; rerun succeeded.
  - New transient failure run `db3b22e8-8672-4c92-b74c-2eb692402320` returned `error_message="disk I/O error"`; immediate rerun succeeded (`c578ca78-86ce-4135-84fa-bc8195726979`).

## 6) Open Blockers / Risks

- Transient sqlite/disk error observed once during rerun; treat as infra flake unless repeated.
- Audit opened for recurring live-run `disk I/O error`: `docs/superpowers/plans/audit/20260515-1633-live-run-disk-io-error/report.md`.
- Mitigation applied: sqlite WAL + busy timeout + retry in key persistence paths; post-fix verification: 3/3 live runs succeeded (`449820b5-0382-4dba-b8c8-a9f72ed75088`, `35cc209e-686c-4f86-861c-68dbcd75f0fe`, `7b5f3ce3-f1bf-4c90-a08f-628c9c04f388`).
- Closeout strict-gate exception approved by user: skip out-of-scope planning-lifecycle warnings for deprecated manual thread-linkage in `docs/intent/workstreams/threads/*` for this lane closure.
- Current checkout now contains mixed non-lane dirty changes (`config/env.yaml`, setup docs, separate config SSOT audit files, runtime data artifacts), so bounded-scope lane merge orchestration must not proceed from this workspace.

## 7) Next Exact Action

- **Action type:** unblock / isolation
- **Target:** lane-scoped closure orchestration safety boundary
- **Exact command or edit intent:** create/reuse clean lane-isolated worktree (or stash mixed dirty changes) and rerun closure orchestration there.
- **Why this is next:** lane evidence is complete, but current workspace violates bounded-scope closure gate due to mixed out-of-scope pending changes.

## 8) Resume Prompt (Copy/Paste)

```text
Read this execution context pack first. Verify its state against listed source files. Then execute the Next Exact Action immediately. Do not re-plan unless blocker is found.
```

## 9) Optional Deep Context (Consult Only)

- none

## Source-Truth Rule

If context pack, source files, and raw log disagree:
1. source files and current tests/checks win
2. then context pack
3. raw log is fallback evidence only
