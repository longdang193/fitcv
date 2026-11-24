# Tasks

## 1. Canonical Experience-Bound Contract

- [ ] 1.1 Define one nullable experience-bound normalization path in `src/fitcv/agentic_cv_analysis.py` and its owning contract surface, covering missing, enrichment-default zero, positive, and invalid values; verify focused unit tests distinguish `None` from a genuine positive bound.
- [ ] 1.2 Route both minimum and maximum experience consumers through the canonical normalized values without changing legacy deserialization; verify `tests/test_agentic_cv_analysis.py` and related requirement-support tests pass for zero, null, and bounded inputs.
- [ ] 1.3 Update the affected contract comments, fixtures, and planning-facing documentation to describe nullable bounds and the deferred genuine-zero source representation; verify documented fields match serialized test fixtures.

## 2. Stage 7 Admission and Legacy Routing

- [ ] 2.1 Separate Stage 7 handoff validation from fit evaluation in `src/fitcv/agentic_cv_analysis.py`, so a valid Final Top 15 handoff remains generation-eligible while invalid or missing handoffs become technical contract failures with structured diagnostics; verify success, invalid-handoff, and missing-handoff cases in `tests/test_agentic_cv_analysis.py`.
- [ ] 2.2 Stop emitting new `skipped_fit_gate` and `blocked_by_reranker_fit` terminal routing decisions while retaining read compatibility for historical records; verify fresh-run and cached-record expectations in `tests/test_agentic_cv_analysis.py`, `tests/test_pipeline.py`, and `tests/test_fitcv_cp/test_worker_job.py`.
- [ ] 2.3 Ensure technical completion, review state, PDF state, and submission clearance remain independently represented across the CV generation path; verify material-uncertainty and technical-failure scenarios in the existing pipeline and acceptance tests.
- [ ] 2.4 Update operator-facing status and migration documentation for the new routing semantics, including how legacy fit-gate records are inspected but excluded from current decisions; verify examples agree with emitted payloads and status assertions.

## 3. Shortlist Assessment and Coverage Integrity

- [ ] 3.1 Replace run-global assessment completeness in `src/fitcv/pipeline_stage_runner.py` and related evaluation contracts with per-job and per-occurrence completeness states; verify one failed job and one failed occurrence do not downgrade unrelated jobs in `tests/test_pipeline_stage_runner.py` and `tests/test_shortlist_evaluation.py`.
- [ ] 3.2 Add and persist the required compatibility fingerprints for requirement coverage in `src/fitcv/shortlist_selection.py` and its owning persistence contract; verify matching fingerprints reuse coverage and missing or stale fingerprints force recomputation with a recorded reason.
- [ ] 3.3 Preserve occurrence identity as the authoritative evidence key, allowing legacy wording fallback only for an unambiguous match; verify duplicate-wording and legacy-evidence cases in `tests/test_shortlist_selection.py` and relevant persistence tests.
- [ ] 3.4 Make OR coverage state and provenance follow the satisfying alternative, and keep assessment candidate breadth independent from bounded display evidence; verify branch provenance, contradiction, compact evidence, and complete-reference cases in `tests/test_shortlist_selection.py` and `tests/test_pipeline_stage_runner.py`.
- [ ] 3.5 Update shortlist coverage schemas, fixtures, and operator diagnostics to document scoped completeness, fingerprint rejection, occurrence identity, OR provenance, and bounded evidence references; verify fixtures round-trip through the current serialization and hydration paths.

## 4. Cross-Stage Verification and Resume Safety

- [ ] 4.1 Add production-shaped Stage 6-to-7 integration coverage proving that valid handoffs with fit gaps still produce the expected downstream artifact path, while technical handoff failures stop safely with diagnostics; verify `tests/test_pipeline_agentic_late_stage.py` and resume-parity coverage.
- [ ] 4.2 Add replay/resume coverage for legacy fit-gate records and pre-fingerprint shortlist coverage, proving records remain readable but are recomputed or re-routed under the active contract; verify `tests/test_pipeline_stage_resume_parity.py` and relevant SQLite/store tests.
- [ ] 4.3 Run the focused Stage 6/7 and shortlist test selection, then the full non-render suite; record any failures as contract or implementation follow-ups and keep render acceptance separate from this change.
- [ ] 4.4 Reconcile the implementation-facing documentation and test expectations with both new capability specs before archive; verify `openspec validate "stabilize-stage6-stage7-contracts" --type change --strict` and the final status report show a coherent, complete change.

## Workflow follow-up

- Archive the change only after implementation, focused verification, full non-render verification, and review requirements are complete.
- Sync the accepted delta into `openspec/specs/` during the archive workflow; do not treat proposal-time specs as maintained main specs.
