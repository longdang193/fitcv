# Stage 6/7 Contract Operations

This note records the current OpenSpec contract used by shortlist, CV analysis, and CV generation.

## Authority and status precedence

- Stage 5 owns admission and emits the versioned Stage 6-to-7 handoff.
- Stage 7 owns handoff validation and fit diagnostics. A valid Final Top 15 handoff is generation-eligible even when fit or experience evidence is unresolved.
- Missing, malformed, conflicting, or stale handoffs emit `handoff_contract_failed`; this is a terminal technical attempt with `retry_eligible=true` only when the upstream producer can issue a corrected handoff.
- Historical `skipped_fit_gate` and `blocked_by_reranker_fit` records remain readable but are not authoritative for new valid handoffs.
- Technical completion, review, PDF, persistence, and submission states remain separate. Review uncertainty can block submission without deleting a generated artifact.

## Checkpoint and reuse scope

Coverage reuse requires `fitcv.coverage_fingerprint.v1` with matching requirement, assessment, evidence, retrieval, and support components. Missing, invalid, stale, incomplete, or failure-derived coverage is recomputed and records a deterministic `coverage_reuse_rejections` reason. Recomputed coverage invalidates dependent shortlist, handoff, and downstream checkpoint decisions when admission or ranking inputs can change.

Evidence references are occurrence-scoped and must include an evidence revision or content hash plus projection version. The bounded manifest is integrity-complete: overflow, malformed, missing, stale, or contradictory references make reuse ineligible instead of silently dropping evidence.

## Experience bounds

`normalize_experience_bounds` is the canonical nullable projection. Blank, zero, negative, non-numeric, non-finite, and inverted values become `null` with diagnostics; finite positive values remain available to requirement construction and gap analysis.

## Retry and diagnostics

Assessment failures are tracked per job and per occurrence. A supported OR branch is authoritative over unused failed branches; when no OR branch qualifies, failure-derived uncertainty remains `U` and retryable. Deterministic OR ties preserve sorted branch, provenance, and evidence unions while choosing the smallest stable display representative.

## CV validation compatibility extension

Stage 7 generation/checkpoint inputs also carry `validation_policy_version`, `diagnostic_schema_version`, `section_policy_version`, and `skill_provenance_version`. A mismatch invalidates only the affected Stage 7 validation/generation boundary; compatible Stage 6 ranking and handoff work remains reusable. Historical rows without these inputs remain readable but cannot authorize factual reuse.

Validation diagnostics are typed and persisted as codes with structured facts. `submission_clearance` is derived from content validity, technical status, draft disposition, review, PDF/artifact, persistence, and page-fit gates. Quarantined drafts are retry context only and never accepted-output cache hits.
