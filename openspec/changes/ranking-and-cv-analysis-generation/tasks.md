# Tasks

## 1. Version the ranking contract and persistence

- [x] 1.1 Add the ranking-order, score-contract, and decision-envelope versions in `src/fitcv/ranking_contract.py`; implement the `ranking_cv_handoff_v1` canonical JSON/SHA-256 fingerprint with explicit `null` values and deterministic array ordering, and verify exact digest fixtures plus changed-input rejection in `tests/test_ranking_contract.py`.
- [x] 1.2 Extend `src/fitcv/ranking.py::rank_jobs` to select the persisted authoritative order for new versus resumed runs without silently mixing personalization; verify valid, invalid, unscored, retryable, equal-score, and canonical-identity tie cases in `tests/test_ranking.py` and `tests/test_ranking_evaluation.py`.
- [x] 1.3 Extend `src/fitcv/pipeline_stage_artifacts.py::build_ranking_stage_block` and the existing run/checkpoint persistence seams in `src/fitcv_cp/models.py`, `src/fitcv_cp/sqlite_store.py`, and `src/fitcv_cp/worker_job.py` to persist order/policy/contract versions and resume them deterministically; verify checkpoint and replay parity in `tests/test_pipeline_checkpoint_contract.py` and `tests/test_pipeline_stage_resume_parity.py`.
- [x] 1.4 Preserve the existing three-state `score_status` contract and retry fields while exposing diagnostics instead of coercing failures to zero; verify historic score rows and retryable worker outcomes remain readable in `tests/test_ranking_contract.py` and `tests/test_fitcv_cp/test_worker_job.py`.

## 2. Build the immutable ranking-to-CV handoff

- [x] 2.1 Build the handoff from admitted shortlist rows, canonical evidence, qualifiers, gaps/unknowns, profile revision, ranking provenance, and score state; persist it under `stage_transition_artifacts_json.stages.ranking` with per-job references and fail closed on missing required fields, verified by focused pipeline artifact tests.
- [x] 2.2 Keep Pareto admission and `pipeline.shortlist_strategy` ownership in the shortlist capability; verify ranking consumes admitted rows without promoting, overriding, or duplicating shortlist decisions in `tests/test_shortlist_evaluation.py`, `tests/test_shortlist_selection.py`, and `tests/test_pipeline.py`.
- [x] 2.3 Wire CV analysis to consume the persisted handoff rather than reconstructing mutable ranking context; verify evidence IDs, job qualifiers, baseline rank/score, and handoff fingerprint survive the worker boundary in `tests/test_agentic_cv_analysis.py` and `tests/test_fitcv_cp/test_worker_job.py`.
- [x] 2.4 Document the ranking-to-CV handoff fields, ownership, and failure semantics in `docs/pipeline.md` and `docs/observability.md`; verify every documented field and artifact path matches the serialized stage block.

## 3. Add the gated deterministic CV renderer

- [x] 3.1 Add an additive renderer-strategy setting owned by `config/policy/cv.yaml`, keeping `cv.preset: europass` as the default and making `mycvs_v1` explicit opt-in; verify configuration parsing, validation, default behavior, and resume precedence in `tests/test_config.py` and `tests/test_pipeline_config_access.py`.
- [x] 3.2 Implement deterministic `mycvs_v1` Markdown serialization and validation at the existing CV-generation boundary, including the maintained contact/Iconify header, visible `Summary → Education → Experience → Projects → Certificates → Skills` order, grounded content, deterministic audit metadata, source references, LF/UTF-8 normalization, handoff identity, and checksum scope; add valid/invalid fixtures and verify them in `tests/test_cv_generator.py`.
- [ ] 3.3 Add the external converter adapter at the existing render-proof boundary, recording converter revision, stylesheet/template revision, input checksum, optional output checksum, and `mycvs_external_render_v1`; verify unpinned, incomplete, wrong-contract, multi-page, and successful render-proof cases in `tests/test_cv_render_acceptance.py` and `tests/test_fitcv_cp/test_run_artifact_contracts.py`.
- [x] 3.4 Preserve the existing Europass/native path while making the new renderer strategy consume the canonical intermediate CV model; verify existing Europass composition and render-proof tests remain green in `tests/test_cv_generator.py` and `tests/test_config.py`.

## 4. Preserve independent CV lifecycle outcomes

- [x] 4.1 Extend the existing worker and persistence boundaries to store generation, review, PDF, and submission-clearance outcomes independently, including review-required Markdown with attempted PDF conversion and converter failure without overwriting valid Markdown; verify transitions in `tests/test_fitcv_cp/test_worker_job.py`, `tests/test_fitcv_cp/test_sqlite_store.py`, and `tests/test_agentic_cv_generation.py`.
- [x] 4.2 Require one-page render acceptance and recognized renderer identity before PDF status becomes generated; verify checksum mismatch, missing proof, review blocking, explicit approval, rejection, and historic status compatibility in `tests/test_cv_render_acceptance.py`, `tests/test_fitcv_cp/test_run_artifact_contracts.py`, and `tests/test_fitcv_cp/test_app.py`.
- [x] 4.3 Verify historic personalized ranking and Europass artifacts remain readable and are not rewritten during migration; add compatibility fixtures or assertions at the existing read paths and run the focused persistence/read tests.
- [x] 4.4 Update `docs/configuration.md`, `docs/pipeline.md`, and `docs/observability.md` with renderer strategy, lifecycle fields, rollback behavior, converter provenance, and the disabled-until-pinned release gate; verify documented defaults and field names against configuration and artifact tests.

## 5. Prove readiness before enablement

- [ ] 5.1 Run deterministic shadow/replay probes over representative ranked jobs and the project’s real jobs/profile inputs, recording ranking order, handoff fingerprints, Markdown checksums, lifecycle outcomes, and any blocked converter gate; verify repeated identical inputs produce identical envelopes and outputs.
- [ ] 5.2 Pin the release-approved external converter commit and stylesheet/template revision only after reproducibility evidence exists; verify the release record satisfies the `mycvs_external_render_v1` gate and that the safe existing path remains selected when it does not.
- [x] 5.3 Run focused validation for ranking, pipeline/checkpoint, CV generation/render acceptance, worker, persistence, and configuration changes, then run `openspec validate ranking-and-cv-analysis-generation --strict` and `git diff --check`; record failures without changing unrelated worktree files.

## Workflow follow-up

- Archive the change only after implementation, review, release-gate evidence, and acceptance are complete.
- Verify the archived change remains valid and that historic artifacts remain readable after activation or rollback.
