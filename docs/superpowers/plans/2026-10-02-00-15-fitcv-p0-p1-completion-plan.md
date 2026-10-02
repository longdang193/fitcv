---
layer: change
artifact_type: plan
template_id: implementation-plan
contract_version: "1"
status: active
name: fitcv-p0-p1-completion
targets:
  - scripts/evaluate_p0b_source_job_relevance.py
  - scripts/validate_p0b_support_oracle.py
  - scripts/calibrate_p0b_recovery.py
  - scripts/benchmark_requirement_support.py
  - scripts/render_acceptance_state.py
  - src/fitcv/evidence.py
  - src/fitcv/pipeline.py
  - src/fitcv_cp/app.py
  - src/fitcv_cp/review_identity.py
  - config/acceptance_state.yaml
  - config/policy/cv_analysis.yaml
  - tests/fixtures/p0b/
  - tests/test_p0b_source_job_relevance_evaluator.py
  - tests/test_p0b_support_oracle.py
  - tests/test_calibrate_p0b_recovery.py
  - tests/test_p0b_holdout_review.py
  - tests/test_evidence.py
  - tests/test_acceptance_state.py
  - tests/test_fitcv_pipeline_prototype.py
  - tests/test_fitcv_cp/
  - .github/workflows/repo-hooks.yml
---

# FitCV P0/P1 Completion Implementation Plan

## Goal

Complete P0-B, P0-C, P1-A maintenance, and P1-B measurement without changing P0-A, P1-C, or P2 scope. Make runtime evidence acceptance truthful, preserve `top_k=2`, prevent unsupported proof, restore clean-checkout CI, and produce measured P1-B efficiency evidence.

## Review Decision

Adopt assessment sequence with these corrections:

- P0-B pair recall is not acceptance. `top_k=2` cannot recover all `211` valid pairs; acceptance must measure supportable-requirement coverage, assignment precision, and false support.
- Current `--oracle` public evaluation scores historical `selected_evidence_ids`; it does not exercise `retrieve_evidence_bundle()`. Keep historical output as `historical_review_selection_v1`; add runtime artifact `p0b.runtime_acceptance.v2`.
- Holdout files exist only in ignored `data/fitcv-p0-corpus/` paths. CI failure is reproducible in clean checkout. Test-owned sanitized fixtures are correct; restoring ignored corpus bundles is not.
- `src/fitcv/evidence.py` currently aliases `verification`/`qualification` and `selection`/`assignment` traces. Calibration cannot identify loss until owners emit separate outputs.
- P0-C is provisional. `_responsibility_rule_support()` allows broad discovery rules; strict proof must require essential entity/domain constraints in source-grounded evidence.
- P1-A needs no redesign. Keep render/page-fit and targeted repair behavior; only retain regression coverage.
- P1-B lifecycle exists, but efficiency evidence is insufficient at `n=1`. Measure ordinary accepted-CV runs before claiming completion.

## Preserved Invariants

- P0-A multilingual experiment remains rejected; no new retrieval path without new error evidence.
- P0-B keeps existing protected oracle and `top_k=2`; exhaustive pair labels remain truth data, not selected-output requirements.
- Candidate evidence projection remains canonical SSOT; no new vector DB, agent, service, or RAG layer.
- Evidence selection stays deterministic and source-grounded. Unsupported or contradicted evidence cannot become verified support or assigned CV evidence.
- P1-A keeps `cv_content_plan_v1`, targeted section repair, render/page-fit acceptance, and existing provider boundaries.
- P1-C and P2 remain deferred.

## Completion Gates

- **P0-B:** oracle validation fails closed; runtime artifact proves current retrieval; every supportable requirement reaches candidate pool and selected coverage where oracle cohort permits; unsupported selected/assigned pairs are zero; `top_k=2` remains unchanged; latency/cost metrics are recorded.
- **P0-C:** Claude Code and executive-search/domain counterexamples remain unverified unless essential constraints occur in same source-grounded fragment; regressions pass; acceptance state returns to `protected` only after fresh evidence.
- **P1-A:** existing render/page-fit and targeted-repair tests remain green.
- **P1-B:** telemetry captures provider calls, token counts when available, regeneration count, questions/resolutions, human actions, elapsed time, page fit, and accepted outcome across at least 10 accepted CVs from at least 3 jobs; report records denominator and missing-provider metrics.

## Execution Approach

- **Mode:** inline sequential. Tasks share `src/fitcv/evidence.py`, evaluator contracts, and acceptance SSOT; serialize changes.
- **Coordination:** none. Current workspace only; no worktree or subagent required.
- **Commit policy:** no commits in plan execution unless user explicitly requests one.
- **Shared-owner rule:** change canonical code/config first, then tests, generated evidence, and acceptance state.
- **Fallback:** execute Tasks 1–8 sequentially when parallel delegation is unavailable.
## Execution Order

Wave 1: Tasks 1–3. No retrieval optimization before these gates pass.

Wave 2: Tasks 4–5. Calibration determines whether code changes are needed.

Wave 3: Tasks 6–7. Optimize only measured residuals; then measure P1-B.

Wave 4: Task 8. Update SSOT, evidence, and run final verification.

### Task 1: Establish `p0b.runtime_acceptance.v2`

**Purpose:** Evaluate current runtime predictions, not historical review selections.

**Task Function:** backend contract and evaluator implementation.

**Template Profile:** unresolved.

**Specification Coverage:** P0-B acceptance contract v2; historical/runtime prediction separation.

**Required Skills:** `skill-backend-verification`, `skill-code-standards`.

**Files And Symbols:**
- `scripts/evaluate_p0b_source_job_relevance.py`: `validate_public_inputs()`, `evaluate_public_corpus()`, `evaluate_actual_fitcv()`, `main()`.
- `scripts/benchmark_requirement_support.py`: existing `retrieve_evidence_bundle()` benchmark output and stage metrics.
- `scripts/validate_p0b_support_oracle.py`: manifest/hash validation.
- `tests/test_p0b_source_job_relevance_evaluator.py`, `tests/test_p0b_support_oracle.py`.

**Dependencies:** none.

**Authority:** Change evaluator/schema/tests only. Do not alter canonical oracle labels or corpus bytes. Stop if oracle manifest, projection fingerprint, or expected requirement IDs disagree.

**Steps:**
1. Define runtime artifact schema `p0b.runtime_acceptance.v2` with `code_sha`, policy fingerprint, projection fingerprint, oracle manifest/hash, `top_k`, source-job IDs, candidate-pool supporters, verified supporters, selected evidence, requirement coverage, assignments, timings, and provider/embedding counters.
2. Generate artifact by calling `retrieve_evidence_bundle()` for each oracle source job. Do not populate runtime predictions from review CSV selections.
3. Preserve current review-based result under explicit `historical_review_selection_v1` naming.
4. Validate exact oracle requirement/evidence sets, expected Cartesian pair count `549`, label counts, zero `unjudged`, provenance, projection hash, and accepted manifest before scoring.
5. Replace pair-recall acceptance with candidate requirement recall, verified requirement coverage, selected requirement coverage at `top_k`, assignment precision, unsupported/contradicted assignment count, and efficiency metrics. Keep exhaustive pair metrics diagnostic-only.
6. Return non-zero on every public-input validation failure, including calibration input failure.

**Verification:**
- `python -m pytest -q tests/test_p0b_support_oracle.py tests/test_p0b_source_job_relevance_evaluator.py tests/test_calibrate_p0b_recovery.py`
- Add tests for truncated 18-row oracle, manifest hash mismatch, runtime-vs-historical source, `top_k=2`, zero unsupported assignments, and non-zero invalid-input CLI exit.

**Exit Criteria:** Runtime artifact generated from current retrieval; historical path cannot satisfy runtime gate; invalid oracle cannot produce metrics.

### Task 2: Repair clean-checkout CI fixtures

**Purpose:** Remove tests' dependency on ignored historical corpus bundles.

**Task Function:** test fixture migration.

**Template Profile:** unresolved.

**Specification Coverage:** Full Suite green; canonical 25-file public corpus unchanged.

**Required Skills:** `skill-code-standards`.

**Files And Symbols:**
- `tests/test_p0b_holdout_review.py`.
- `tests/fixtures/p0b/`.
- `scripts/validate_p0b_holdout_review.py`.
- `.github/workflows/repo-hooks.yml` only if focused command needs adjustment.

**Dependencies:** none; can run with Task 1.

**Authority:** Add sanitized test-owned data only. Do not add ignored historical packets to `data/fitcv-p0-corpus` or change `.git/info/exclude`.

**Steps:**
1. Replace `P0B / ...` references in `tests/test_p0b_holdout_review.py` with minimal fixtures under `tests/fixtures/p0b/` or a test factory in that directory.
2. Preserve validator behavior covered by v1/v2/v3/v5 tests: schema rejection, requirement drift, invalid support, exact supported row, distinct reviewer IDs, exclusion counts, modality policy, and reviewer-pair validation.
3. Keep only fields required by `validate_review_file()`, `validate_review_payload()`, and `validate_review_pair()`; do not copy private source packets.
4. Confirm no test imports ignored `data/fitcv-p0-corpus` holdout files.

**Verification:**
- `python -m pytest -q tests/test_p0b_holdout_review.py tests/test_p0_public_corpus.py`
- `git ls-files data/fitcv-p0-corpus | Measure-Object` remains `25`.
- Fresh clean-checkout Full Suite no longer raises `FileNotFoundError` from `tests/test_p0b_holdout_review.py`.

**Exit Criteria:** Holdout tests pass with tracked test fixtures; public corpus remains unchanged.

### Task 3: Harden P0-C essential proof

**Purpose:** Separate broad candidate discovery from verified source proof.

**Task Function:** backend correctness fix.

**Template Profile:** unresolved.

**Specification Coverage:** P0-C qualifier/entity/domain truthfulness.

**Required Skills:** `skill-backend-verification`, `skill-test-driven-development`.

**Files And Symbols:**
- `src/fitcv/evidence.py`: `_responsibility_constraints()`, `_responsibility_rule_support()`, `_assess_responsibility_support()`, `_annotate_responsibility_support()`.
- `tests/test_evidence.py` and responsibility-related fixtures.
- `tests/test_agentic_cv_analysis.py` only if shared requirement-resolution behavior is affected.

**Dependencies:** Task 2 green; Task 1 oracle contract available.

**Authority:** Preserve discovery aliases. Change only verified-support semantics. Stop on any existing supported skill/domain regression unrelated to essential-constraint proof.

**Steps:**
1. Parse required tool/entity, occupational/domain, degree field, duration, and level from existing responsibility descriptors.
2. Keep generic aliases available for candidate admission, but never let generic `tool`, `research`, `market`, or equivalent satisfy an essential entity/domain constraint.
3. Require all essential constraints plus action/object/qualifier/duration checks in one source-grounded evidence fragment before `verified_support=True`.
4. Keep contradiction and negation fail-closed.
5. Add Claude Code and executive-search/domain counterexamples; assert candidate discovery may occur while verified support stays false.

**Verification:**
- `python -m pytest -q tests/test_evidence.py tests/test_agentic_cv_analysis.py`
- Direct assertions cover generic distractor, exact entity/domain, missing qualifier, contradiction, and valid support.

**Exit Criteria:** P0-C regressions pass; no broad alias can create false verified support.

### Task 4: Emit truthful runtime stage boundaries

**Purpose:** Make calibration identify first loss without production payload explosion.

**Task Function:** backend diagnostics and calibration.

**Template Profile:** unresolved.

**Specification Coverage:** P0-B stage accounting; latency/operational overhead.

**Required Skills:** `skill-backend-verification`.

**Files And Symbols:**
- `src/fitcv/evidence.py`: `_build_retrieve_evidence_bundle_payload()`, `_EvidenceSelectionEngine.run()`, `retrieve_evidence_bundle()`.
- `config/policy/cv_analysis.yaml` only for an explicit diagnostic/calibration switch if existing config has no suitable switch.
- `scripts/calibrate_p0b_recovery.py`, `tests/test_calibrate_p0b_recovery.py`, `tests/test_evidence.py`.

**Dependencies:** Tasks 1–3.

**Authority:** Compact production counts/timings always allowed. Full requirement/evidence pair lists only under explicit calibration flag. No new tracing service.

**Steps:**
1. Emit canonical item count, admitted candidate count, verified supporter count, qualified supporter count, selected count, assigned count, uncovered requirement count, latency, embedding, and provider counters.
2. Produce verification and qualification from distinct owner outputs; produce selection and assignment from distinct outputs. Do not duplicate one mapping under two stage names.
3. Gate full pair lists behind explicit calibration mode.
4. Update `calibrate_p0b_recovery.py` to classify each supportable requirement once: `not_in_canonical_pool`, `retrieval_loss`, `verification_failure`, `qualification_failure`, `selection_loss`, `assignment_loss`, or `covered`; record unsupported/contradicted separately.

**Verification:**
- `python -m pytest -q tests/test_calibrate_p0b_recovery.py tests/test_evidence.py`
- Calibration output proves disjoint/exhaustive requirement classification and compact default payload.

**Exit Criteria:** `194 retrieval losses` no longer used as root cause until requirement-level calibration proves it.

### Task 5: Fix measured residual coverage only

**Purpose:** Improve P0-B accuracy without speculative architecture.

**Task Function:** bounded retrieval/selection correction.

**Template Profile:** unresolved.

**Specification Coverage:** P0-B requirement coverage under `top_k=2`.

**Required Skills:** `skill-backend-verification`, `skill-performance-optimization` only if Task 4 shows latency work is required.

**Files And Symbols:**
- `src/fitcv/evidence.py`: `_select_channel_candidates()`, `_select_final_evidence()`, `_recover_verified_supporters()`, `_coverage_gain()`, `_EvidenceSelectionEngine.run()`.
- `config/policy/cv_analysis.yaml` only for existing selection weights/quotas.
- `tests/test_evidence.py`, `tests/test_p0b_source_job_relevance_evaluator.py`.

**Dependencies:** Task 4 calibration identifies a real requirement-level retrieval or selection loss.

**Authority:** Do not increase `top_k` above `2`. Do not add vector DB, agent, graph, reranker, or LLM verifier. If calibration shows no residual retrieval/selection loss, skip implementation and record evidence.

**Steps:**
1. If candidate-pool loss exists, reserve bounded candidate slots for uncovered requirements using already-computed direct-support facts, then fill remaining capacity with existing lexical/semantic ranking.
2. If selection loss exists, make verified new-requirement coverage primary objective; use existing channel/base score as tie-breaker; prefer one item covering multiple requirements.
3. Preserve deterministic ordering and current evidence type quotas.
4. Re-run runtime acceptance before any latency optimization.

**Verification:**
- `python -m pytest -q tests/test_evidence.py tests/test_p0b_source_job_relevance_evaluator.py`
- Runtime artifact shows non-decreasing candidate and selected requirement coverage, zero unsupported assignments, unchanged `top_k=2`, and no p50/p95 regression beyond recorded baseline.

**Exit Criteria:** Only measured residual receives code changes; impossible pair-recall target remains removed.

### Task 6: Optimize hot path after accuracy gate

**Purpose:** Reduce latency/provider/embedding work without coverage regression.

**Task Function:** backend performance optimization.

**Template Profile:** unresolved.

**Specification Coverage:** P0-B efficiency; no operationally unnecessary RAG complexity.

**Required Skills:** `skill-performance-optimization`, `skill-backend-verification`.

**Files And Symbols:**
- `src/fitcv/evidence.py`: existing projection and embedding cache helpers, `_embed_text_cached()`, `retrieve_evidence_bundle()`.
- `scripts/benchmark_requirement_support.py`.
- `tests/test_benchmark_requirement_support.py`, `tests/test_evidence.py`.

**Dependencies:** Tasks 4–5; accuracy gate green.

**Authority:** Reuse process-local or existing SQLite-backed cache. No new service or dependency. Stop if coverage/precision drops.

**Steps:**
1. Reuse candidate preprocessing by projection fingerprint, support-policy version, and embedding contract fingerprint.
2. Batch unique semantic texts; reuse candidate embeddings across jobs.
3. Run exact verified support and cheap lexical signals before semantic fallback; embed only unresolved, ambiguous, or near-tie cases.
4. Measure identical workload before/after with retrieval latency, p50/p95, evidence examined, embedding calls, prompt bytes, and provider calls.

**Verification:**
- `python -m pytest -q tests/test_benchmark_requirement_support.py tests/test_evidence.py`
- Benchmark report shows non-decreasing coverage/precision and improved or neutral p50/p95.

**Exit Criteria:** Accuracy gate remains green; cost/latency improvement is evidenced or optimization is skipped.

### Task 7: Complete P1-B efficiency measurement

**Purpose:** Turn working uncertainty lifecycle into measured acceptance evidence.

**Task Function:** backend telemetry and bounded lifecycle optimization.

**Template Profile:** unresolved.

**Specification Coverage:** P1-B actionable uncertainty efficiency.

**Required Skills:** `skill-backend-verification`, `skill-test-driven-development`.

**Files And Symbols:**
- `src/fitcv/pipeline_contracts.py`: `build_requirement_uncertainty()` and existing resolution contracts.
- `src/fitcv_cp/app.py`: `_build_hitl_review_queue()`, `_build_hitl_closure_summary()`, review action/regeneration handlers.
- `src/fitcv/pipeline.py`: CV analysis/generation summaries and trace records.
- Existing `src/fitcv_cp/store.py` or run-artifact owner selected by current persistence path; do not create a second event store.
- Tests covering HITL resolution, regeneration, closure, and CV acceptance.

**Dependencies:** P0 gates green; P1-A tests green.

**Authority:** Preserve current lifecycle and accepted artifact identity. No full regeneration per answer. No new provider or queue.

**Steps:**
1. Persist per accepted CV: provider calls, input/output tokens when available, regeneration count, questions shown, answers, reused resolutions, human actions, elapsed time, final page-fit result, and accepted/not-accepted outcome.
2. Batch multiple answers for one job and trigger one bounded re-analysis/regeneration after submission.
3. Reuse existing resolution fingerprints and artifacts; keep unresolved/failed states explicit.
4. Produce measurement report over at least 10 accepted CVs across at least 3 jobs. Report missing provider metrics instead of fabricating values.

**Verification:**
- `python -m pytest -q tests/test_fitcv_pipeline_prototype.py tests/test_fitcv_cp -q`
- Direct lifecycle tests cover no-answer, multi-answer, approve-as-is, regenerate-once, rejection, retry, and final artifact state.
- Measurement report includes denominator, action counts, elapsed time, token/provider availability, page fit, and acceptance rate.

**Exit Criteria:** P1-B status changes only from `measurement_only` after representative evidence exists; lifecycle behavior remains green.

### Task 8: Reconcile acceptance SSOT and closeout

**Purpose:** Make status, acceptance, and measurement unambiguous.

**Task Function:** acceptance state and final verification.

**Template Profile:** unresolved.

**Specification Coverage:** P0/P1 status closure; P1-C/P2 deferral.

**Required Skills:** `skill-verification-before-completion`.

**Files And Symbols:**
- `config/acceptance_state.yaml`.
- `scripts/render_acceptance_state.py` and `tests/test_acceptance_state.py`.
- `docs/superpowers/evidence/` fresh P0-B, P0-C, P1-A, and P1-B evidence files.
- `.github/workflows/repo-hooks.yml`.

**Dependencies:** Tasks 1–7.

**Authority:** Update status only from fresh verification outputs. Preserve historical evidence paths. Do not claim P1-C or P2 completion.

**Steps:**
1. Version acceptance contract for runtime v2. Rename `source_commit` to `evaluation_freeze_commit` only if migration keeps the frozen-commit meaning; otherwise retain field and document that meaning in schema/tests. Do not silently point it at current `HEAD`.
2. Separate status fields into `implementation_status`, `acceptance_status`, and `measurement_status` only if existing renderer/tests can migrate without duplicate SSOT; otherwise keep current schema and add contract version plus explicit evidence semantics.
3. Set P0-B/P0-C/P1-B values only from fresh reports. Keep P0-A rejected, P1-A maintenance-only, P1-C deferred, P2 deferred.
4. Run public corpus integrity, oracle validation, focused suites, Full Suite, and Render Acceptance in clean checkout.
5. Record exact commit, commands, outputs, artifact hashes, and residual non-blocking limitations.

**Verification:**
- `python -m pytest -q tests/test_acceptance_state.py tests/test_p0_public_corpus.py tests/test_p0b_support_oracle.py tests/test_p0b_source_job_relevance_evaluator.py tests/test_calibrate_p0b_recovery.py tests/test_evidence.py`
- `python -m pytest -q -m "not render_acceptance"`
- `python -m pytest -q tests/test_cv_render_acceptance.py -m render_acceptance`
- Render acceptance state and confirm all referenced evidence paths exist.

**Exit Criteria:** Fresh clean-checkout evidence supports every claimed closure; P1-C remains explicitly deferred.

## Deferred Scope

- **P0-A:** no work unless new retrieval evidence contradicts rejected multilingual experiment.
- **P1-A:** maintenance only; no compiler redesign.
- **P1-C:** deferred; later offline aggregation over imported jobs and verified gaps.
- **P2:** deferred until measured residual P0-B errors exist.

## Final Review Checklist

- Every acceptance metric scores current runtime, not historical selected IDs.
- Oracle validation fails before metrics on any hash, set, count, provenance, or unjudged-row failure.
- No ignored corpus file is required by tests.
- Essential entities/domains cannot be satisfied by generic aliases.
- Stage names map to distinct owner outputs.
- `top_k=2` remains fixed.
- Retrieval/selection optimization is conditional on requirement-level calibration.
- P1-B denominator is greater than one and explicitly reported.
- P1-C and P2 remain deferred.







## Execution Record — October 1, 2026

- Tasks 1–6: implemented and verified. P0-B runtime acceptance passes with `top_k=2`; P0-C strict proof remains fail-closed; P1-A render/page-fit checks remain green. Task 6 optimization skipped because no before/after optimization benchmark was required by measured residuals.
- Task 7: lifecycle telemetry and projection changes verified, but representative P1-B measurement is not complete. No source-backed sample of at least 10 accepted CVs across 3 jobs exists in this workspace. Keep `p1_b: measurement_only`.
- Task 8: acceptance SSOT and evidence updated; P1-C and P2 remain deferred.
- Verification: focused acceptance/evaluator/evidence suite `104 passed, 4 skipped`; pipeline/agentic/run-artifact suite `185 passed`; full non-render suite `2986 passed, 8 skipped, 3 deselected`; render acceptance `3 passed`; `git diff --check` clean.
- Plan remains `active` until P1-B representative measurement exists. No commit or push.

- Additional P1-B evidence: historical event extraction found `89` accepted CV records across `16` jobs, but those records predate `accepted_cv_effort_v1` and lack required provider/token/review-action/page-fit fields. Added `docs/superpowers/evidence/2026-10-01-fitcv-p1b-historical-measurement.md`; status remains `measurement_only`.

- Task 7 live measurement: captured `11` accepted CVs across `4` runs and `11` jobs with provider calls, available token usage, regeneration counts, review-question counts, elapsed time, and render results. Template spacing and margins were tightened; all `11` generated PDFs now render to `1` page. Auto-accepted artifacts correctly report human actions as `not_applicable`. Added `docs/superpowers/evidence/2026-10-02-fitcv-p1b-live-measurement.md`; P1-B promoted to `passed`.

## Execution Record — October 2, 2026

- Fixed production CV overflow in `templates/cv_template.md` with Pandoc margin, list-spacing, and paragraph-spacing metadata. Added dense-skill render regression coverage.
- Re-rendered all `11` live accepted CV artifacts: `11 / 11` fit one page.
- Acceptance state: P0-B `passed`, P1-B `passed`, P1-C `deferred`, P2 `deferred`.
- Verification: focused acceptance `101 passed`; full non-render `2986 passed, 8 skipped, 4 deselected`; render acceptance `4 passed`; `git diff --check` clean.
- Plan complete. No commit or push.
