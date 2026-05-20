# Execution Context Pack

## 1) Objective

- **Workstream / Plan:** `ranking-concurrency-ssot-symmetry-invariance-fix` / `docs/superpowers/plans/2026-05-20-01-09-ranking-concurrency-ssot-symmetry-invariance-fix-plan.md`
- **Goal:** Restore ranking-stage concurrency SSOT/symmetry/invariance by adding canonical control surface, enforcing canonical precedence, and validating runtime behavior semantics.
- **Bounded Scope (in-scope only):** ranking throughput control surfaces, ranking runtime read path, ranking settings snapshots, targeted ranking tests/docs.
- **Out of Scope (explicit):** enrich/cv_analysis/cv_generation throughput changes unrelated to ranking lane.

## 2) Canonical Inputs (Source of Truth)

- **Primary plan:** `docs/superpowers/plans/2026-05-20-01-09-ranking-concurrency-ssot-symmetry-invariance-fix-plan.md`
- **Specs / maps / thread docs:** `docs/superpowers/specs/2026-05-19-16-45-runtime-throughput-ssot-symmetry-invariance-optimization-spec.md`
- **Governance / workflow rules used:** `docs/operating_system/governance/repo-governance.md`; `docs/operating_system/governance/execution-context-pack-governance.md`; `docs/operating_system/prompt_templates/implementation-next-action-gate-prompt.md`

## 3) Current Task State

- **Completed:**
  - GitNexus index refreshed.
  - Task 1 completed: root-cause evidence captured (`ranking` runtime can read concurrency, settings surface lacks canonical `stage_runtime.ranking.concurrency` key).
  - Baseline targeted test run (`pytest tests/test_ai_score.py -k "ranking or concurrency or stage_runtime"`).
  - Task 2 completed: canonical `stage_runtime.ranking.concurrency` added to settings schema, timing section registry, and stage mapping.
  - Task 2 tests passed for timing canonical payload save and throughput IA contract coverage.
  - Task 3 completed: settings-used snapshot ranking stage now uses shared canonical runtime resolvers for `sleep_secs` and `concurrency`.
  - Task 3 tests passed for canonical precedence + compatibility fallback resolver behavior and ranking snapshot materialization.
  - Task 4 completed: ranking pacing semantics validated (`sleep_secs=0` overlap path, `sleep_secs>0` submission pacing path) and documented.
- **In Progress:**
  - none
- **Deferred / Dropped:**
  - none
- **Known divergence from plan (if any):**
  - Existing unrelated baseline local modifications are preserved by user instruction.

## 4) Files Changed This Session

- `docs/superpowers/plans/2026-05-20-01-09-ranking-concurrency-ssot-symmetry-invariance-fix-plan.md` — Task 1 steps marked completed.
- `docs/superpowers/execution_context_packs/ranking-concurrency-ssot-symmetry-invariance-fix/latest.md` — initialized canonical lane context pack.
- `src/fitcv_cp/settings_schema.py` — added canonical ranking concurrency key + timing section inclusion + ranking stage map entry.
- `tests/test_fitcv_cp/test_settings_schema.py` — IA contract canonical timing coverage includes ranking concurrency key.
- `tests/test_fitcv_cp/test_app.py` — timing section payload tests include canonical ranking concurrency save path.
- `src/fitcv_cp/worker_job.py` — ranking stage-runtime snapshot fill now uses shared runtime resolver helpers.
- `tests/test_config.py` — added canonical-precedence and compatibility-fallback tests for stage runtime concurrency.
- `tests/test_fitcv_cp/test_worker_job.py` — added ranking concurrency settings-used snapshot materialization test.
- `tests/test_ai_score.py` — added explicit overlap/pacing behavior tests for ranking concurrency path.
- `docs/configuration.md` — added ranking pacing contract note clarifying sequential-looking provider timestamps when `sleep_secs` > 0.

## 5) Verification State

- **Last commands run:**
  - `npx gitnexus analyze`
  - `git rev-parse --abbrev-ref HEAD` (`main`)
  - `git status --short` (dirty worktree)
  - `python scripts/validate_planning_lifecycle.py --strict`
  - `python scripts/validate_checkpoint_packs.py`
  - `python scripts/validate_repo_contracts.py --fast`
  - `rg -n "^- \[ \]" docs/superpowers/plans/2026-05-20-01-09-ranking-concurrency-ssot-symmetry-invariance-fix-plan.md docs/superpowers/execution_context_packs/ranking-concurrency-ssot-symmetry-invariance-fix/latest.md` (no matches)
  - `python scripts/validate_template_required_sections.py`
  - `npx gitnexus analyze`
  - `pytest -q tests/test_ai_score.py -k "ranking or concurrency or stage_runtime"`
  - `rg -n "stage_runtime.ranking.sleep_secs|get_stage_runtime_concurrency|ranking_concurrency|ThreadPoolExecutor(max_workers=ranking_concurrency)|stage_runtime.ranking.concurrency" src/fitcv/ai_score.py src/fitcv_cp/settings_schema.py src/fitcv_cp/app.py -S`
  - `pytest -q tests/test_fitcv_cp/test_settings_schema.py::test_settings_ia_contract_canonical_timing_keys_are_throughput_runtime_used`
  - `pytest -q tests/test_fitcv_cp/test_app.py::test_post_settings_section_timing_drops_throughput_compatibility_aliases tests/test_fitcv_cp/test_app.py::test_post_settings_section_timing_accepts_canonical_only_payload`
  - `pytest -q tests/test_config.py::test_get_stage_runtime_concurrency_clamps_and_defaults tests/test_config.py::test_get_stage_runtime_concurrency_prefers_canonical_stage_runtime tests/test_config.py::test_get_stage_runtime_concurrency_falls_back_to_compatibility_key tests/test_config.py::test_get_stage_runtime_sleep_secs_prefers_canonical_stage_runtime tests/test_config.py::test_get_stage_runtime_sleep_secs_falls_back_to_compatibility_key`
  - `pytest -q tests/test_fitcv_cp/test_worker_job.py -k "settings_used and ranking and concurrency"`
  - `pytest -q tests/test_ai_score.py -k "parallel_path_overlaps_workers_when_sleep_zero or parallel_path_still_paces_submission_when_sleep_positive or parallel_path_preserves_input_order or parallel_path_isolates_runtime_exceptions"`
  - `rg -n "ranking|concurrency|sleep_secs|runtime throughput" docs/configuration.md src/fitcv_cp/templates/settings.html`
- **Result summary:**
  - GitNexus index refreshed again for current worktree (`24,138 nodes | 47,352 edges | 291 clusters | 300 flows`).
  - Closure precondition reconciliation scan for this lane artifacts reports zero unresolved checklist items (`- [ ]` count = 0).
  - Template required-sections validator passes.
  - Index refresh success.
  - Baseline ranking test pass (`1 passed` selected).
  - Evidence confirms symmetry gap and default-to-1 runtime fallback boundary.
  - Task 2 patch evidence: canonical ranking concurrency now writable via timing section and preserved in canonical-only timing payload save path.
  - Task 3 patch evidence: settings-used snapshot no longer hardcodes ranking concurrency fallback; canonical resolver behavior proven by tests.
  - Task 4 evidence: ranking concurrency can overlap at `sleep_secs=0`, and positive `sleep_secs` intentionally paces submission causing sequential-like provider timestamps.
  - Task 5 lane-scoped verification pass under approved exclusion policy for unrelated baseline failures: `14 passed`.
  - Planning/checkpoint/repo-contract validators pass after lineage regeneration.
  - Closure-gate validation commands pass on current state.
  - Operational merge precondition not satisfied yet because lane changes are still uncommitted on `main` (no dedicated lane branch to fast-forward merge).
- **Failing checks (if any):**
  - historical full-suite snapshot remains: `pytest -q tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_settings_schema.py tests/test_ai_score.py tests/test_config.py` -> `24 failed, 694 passed, 1 skipped` (failures concentrated in `tests/test_fitcv_cp/test_app.py`, baseline UI/synonym/review queue behaviors outside ranking lane).
  - stale lineage gate fixed via `python scripts/generate_planning_lineage.py`
  - `python scripts/validate_repo_contracts.py --fast` now passes after lineage regeneration.
- **Gaps still unverified:**
  - none for ranking-concurrency lane scope.

## 6) Open Blockers / Risks

- Baseline worktree contains unrelated modified files; must avoid reverting per user instruction and keep ranking-lane scope bounded.
- Closure action blocker: current lane state is not isolated on a lane branch; merge sequence requiring `git merge --ff-only <lane-branch>` cannot execute from dirty `main`.

## 7) Next Exact Action

- **Action type:** edit
- **Target:** git lane isolation for closure
- **Exact command or edit intent:** create and switch to dedicated lane branch from current `main` state, then stage lane-scoped files for first commit boundary.
- **Why this is next:** artifact/verification gates pass, but closure merge flow is blocked until lane branch exists.

## 8) Resume Prompt (Copy/Paste)

```text
Read this execution context pack first. Verify its state against listed source files. Then execute the Next Exact Action immediately. Do not re-plan unless blocker is found.
```

## 9) Optional Deep Context (Consult Only)

- **conversation_id:** not captured in-repo
- **overview_log:** not referenced
- **consult_if:** ambiguity remains after source/test review
- **notes_from_log (optional, concise):** none

## Source-Truth Rule

If context pack, source files, and raw log disagree:
1. source files and current tests/checks win
2. then context pack
3. raw log is fallback evidence only
