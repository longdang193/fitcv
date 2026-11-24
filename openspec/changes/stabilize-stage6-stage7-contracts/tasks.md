# Tasks

## 1. Contract definitions and normalization

- [x] 1.1 Define the additive Stage 6/7 handoff and technical-failure payload, including authoritative identity/provenance fields, `handoff_contract_failed`, terminality, retryability, checkpoint, worker projection, scope, and version rules; verify valid, missing, conflicting, and corrected-handoff fixtures round-trip through the existing contract serializers.
- [x] 1.2 Define versioned coverage fingerprint payloads and canonical serialization for requirement contract, assessment inputs, evidence compatibility, retrieval policy, and support policy; verify reordered equivalent inputs hash identically and material evidence revisions hash differently.
- [x] 1.3 Implement the single enriched-job experience-bound normalizer for missing, null, blank, zero, positive, negative, non-numeric, non-finite, and inverted inputs; verify the truth table and diagnostics in focused enrichment/data-contract tests.
- [x] 1.4 Route minimum and maximum experience consumers through the canonical nullable values without changing legacy deserialization; verify positive bounds remain supported and invalid/default-zero values create no synthetic requirements.
- [x] 1.5 Update the affected contract fixtures and operator-facing documentation with field ownership, schema versions, diagnostics, and precedence over historical planning changes; verify documented fields match serialized fixtures.

## 2. Stage 7 admission, status, and resume ownership

- [x] 2.1 Separate handoff validation from fit evaluation so a valid Final Top 15 handoff remains generation-eligible and an invalid or missing handoff becomes `handoff_contract_failed`; verify valid, missing, identity-conflict, rank-conflict, fingerprint-conflict, and corrected-upstream cases in `tests/test_agentic_cv_analysis.py` and contract tests.
- [x] 2.2 Stop emitting new `skipped_fit_gate` and `blocked_by_reranker_fit` decisions for valid Final Top 15 flows while retaining read compatibility for historical records; verify fresh-run, cached-record, and legacy-inspection behavior in the existing analysis, pipeline, and worker tests.
- [x] 2.3 Preserve independent technical, review, PDF, persistence, and submission states and project the new technical failure fields through worker, pipeline, checkpoint, and operator surfaces; verify terminality, retryability, scope, and failure-code parity in pipeline and worker tests.
- [x] 2.4 Implement the resume/invalidation matrix: compatible checkpoints resume, legacy fit-gate records recompute, changed upstream coverage/profile/evidence restarts at the first affected boundary, and conflicting worker/checkpoint state stops safely; verify replay and resume parity for each matrix row.
- [x] 2.5 Add focused documentation for status precedence, active-contract ownership, checkpoint scope, retry rules, and dependent invalidation; verify examples use emitted status names and payload fields.

## 3. Shortlist assessment and coverage integrity

- [x] 3.1 Replace run-global assessment completeness with per-job and per-occurrence completeness, failure origin, and retryability; verify one failed job and one failed occurrence do not downgrade unrelated jobs in `tests/test_pipeline_stage_runner.py` and `tests/test_shortlist_evaluation.py`.
- [x] 3.2 Persist and validate the complete compatibility fingerprint set; verify matching complete coverage reuses, missing/unknown/stale fingerprints recompute, and every rejection records a deterministic reason in shortlist and persistence tests.
- [x] 3.3 Preserve occurrence identity as the authoritative evidence key and allow wording fallback only for one unambiguous legacy occurrence; verify duplicate-wording, explicit-unrelated-identity, and legacy-evidence cases in `tests/test_shortlist_selection.py` and persistence tests.
- [x] 3.4 Propagate failure-derived uncertainty through AND/OR compounds and job-level aggregation while preserving complete policy-defined `U` separately; verify failed-job affected-set semantics, mixed OR outcomes, state, completeness, retryability, and branch diagnostics for each compound case.
- [x] 3.5 Implement deterministic OR tie handling using sorted union provenance/evidence and a stable display representative; verify input-order determinism, equal-branch provenance, contradiction handling, and compact evidence output.
- [x] 3.6 Persist bounded but integrity-complete evidence references with occurrence identity, evidence revision/content hash, projection version, deduplication, explicit manifest overflow handling, and missing-reference diagnostics; verify hydration rejects stale or contradictory references without silently dropping them.
- [x] 3.7 Keep assessment candidate breadth independent from bounded display evidence and record complete evidence identifiers for downstream handoff; verify a non-displayed candidate can establish coverage without expanding persisted display payloads.
- [x] 3.8 Update shortlist schemas, fixtures, and operator diagnostics for scoped completeness, fingerprint rejection, occurrence identity, OR provenance, evidence integrity, and dependency invalidation; verify fixtures round-trip through current serialization/hydration paths.

## 4. Cross-stage acceptance and release readiness

- [x] 4.1 Add production-shaped Stage 6-to-7 integration coverage proving valid handoffs with fit gaps reach grounded Markdown/PDF generation while technical handoff failures stop with structured diagnostics; verify downstream artifact and status projections.
- [x] 4.2 Add replay/resume coverage for legacy fit-gate records, pre-fingerprint coverage, incomplete failure-derived coverage, unavailable recomputation, changed profile/evidence revisions, and conflicting checkpoints; verify recomputation and invalidation begin at the specified boundary.
- [x] 4.3 Run the focused Stage 6/7 and shortlist test selection, then the full non-render suite; require no new failures against the recorded baseline, while documenting only demonstrably pre-existing or unrelated failures as follow-ups, and do not treat browser evidence as backend proof.
- [x] 4.4 Run mandatory targeted PDF acceptance for both optional-review and mandatory-review paths, including post-conversion integrity, renderability, schema/link/checksum, and configured page-fit checks; preserve the exact acceptance output as archive evidence.
- [x] 4.5 Run `openspec validate "stabilize-stage6-stage7-contracts" --type change --strict` and confirm the final status reports all artifacts coherent; archive only after implementation, focused verification, non-render verification, and targeted PDF acceptance are complete.

## Workflow follow-up

- Archive the change only after all tracked implementation and acceptance tasks pass.
- Sync the accepted delta into maintained `openspec/specs/` during the archive workflow.
- Preserve historical records and review artifacts; do not backfill legacy fit-gate or coverage payloads merely to satisfy the new schema.
