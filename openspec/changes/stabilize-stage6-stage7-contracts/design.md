# Design

## Context

See `proposal.md` for the motivation and scope. The repository already has a versioned ranking-to-CV handoff, Stage 7 analysis fingerprints, requirement occurrence identifiers, shortlist assessment fingerprints, independent PDF/review state helpers, and persisted checkpoints. The review found that those primitives do not yet form one deterministic recovery contract:

- valid Final Top 15 fit gaps can still be confused with admission failure;
- persisted `U` results do not record whether uncertainty came from a completed assessment or a transient failure;
- resume behavior does not identify the owner of the current decision or the first boundary that must be recomputed;
- fingerprints do not state their complete semantic inputs, ownership, serialization, or evidence compatibility rules;
- technical handoff failure lacks a canonical status payload;
- compact evidence references and PDF acceptance are not fully bound to integrity and archive criteria.

The existing `align-ranking-cv-pipeline` and `requirement-aware-job-shortlisting` changes remain historical context. This change is additive and does not rewrite their artifacts.

## Goals / Non-Goals

**Goals:**

- Make Stage 6 provenance authoritative and make Stage 7 admission/recovery deterministic.
- Make coverage reuse safe under transient failures, policy changes, profile changes, evidence changes, and schema changes.
- Preserve occurrence identity, uncertainty origin, OR provenance, bounded evidence, and independent technical/review/PDF states across persistence and resume.
- Define the minimum lifecycle fields needed to checkpoint and retry the new technical outcomes.
- Provide focused tests and targeted PDF acceptance evidence that can be used before archive.

**Non-Goals:**

- Reworking the Pareto model, canonical ranking tuple, promotion/rollout gates, or broad infrastructure.
- Backfilling historical artifacts or renaming legacy status values in stored records.
- Treating a genuine source-asserted zero-years bound as a new requirement type; this change normalizes it to no bound and records a diagnostic.
- Making all lifecycle writes globally atomic; only direct gaps that prevent reliable representation/resume of the new states are in scope.
- Expanding assessment breadth, renderer behavior, or test-runner performance beyond the minimum needed to prove these contracts.

## Decisions

### 1. Stage 6 handoff is the authoritative Stage 7 admission boundary

The ranking stage is the producer of the existing versioned ranking-to-CV handoff. Stage 7 accepts only a handoff whose canonical payload and fingerprint validate, whose disposition is an admitted Final Top 15 row, and whose identity/provenance fields agree with the job and profile being processed.

The required authoritative inputs are the existing handoff schema version, canonical job identity, JD reference in source provenance, Final Top 15 rank, finite baseline score and score status, disposition, candidate-profile revision, ranking policy/order/contract versions, evidence identifiers, confirmed gaps/unknowns, source provenance, and handoff fingerprint. The validator owns canonical ordering and hash calculation; the producer owns populating the fields and the upstream source revisions.

A mismatch is a technical contract failure, not a fit decision. The failure payload uses one canonical Stage 7 analysis status, `handoff_contract_failed`, with `failure_code`, `terminal`, `retry_eligible`, `checkpoint`, `worker_status`, and `scope` fields. `scope` identifies the job identity and handoff fingerprint (or the missing-handoff attempt). The current attempt is terminal; retry is eligible only when an upstream producer can issue a corrected handoff or the missing predecessor becomes available. The worker and pipeline projections must preserve the same failure code and retryability rather than mapping it to a fit-gate status.

Alternative rejected: accepting a direct Stage 7 invocation without provenance. That would make stale or misidentified jobs indistinguishable from valid ranked jobs.

### 2. Valid fit gaps remain diagnostics; hard technical failures remain blocking

After handoff validation succeeds, fit classification, unresolved requirements, professional-experience gaps, `S/P/E/U` coverage, and review concerns are passed to grounded analysis. They do not emit new `skipped_fit_gate` or `blocked_by_reranker_fit` decisions for valid Final Top 15 flows. Historical values remain readable and visible to operators.

Technical validation, generation, persistence, and PDF failures remain blocking. Review-required artifacts may still be generated and persisted, but submission remains blocked until review approval and all technical/PDF/persistence checks pass.

Alternative rejected: replacing all failures with one generic status. That would lose the existing ability to distinguish technical recovery from human review.

### 3. Resume uses an explicit ownership and invalidation matrix

The active contract owns the resumed decision. A historical checkpoint is evidence of what happened, not authority to bypass current validation. Resume behavior is:

| Situation | Current owner | Action | Downstream invalidation |
|---|---|---|---|
| Same handoff fingerprint, same contract/policy/evidence revisions, valid checkpoint | Current stage | Resume from the checkpoint | None |
| Legacy fit-gate analysis record but valid current handoff | Stage 7 policy | Recompute Stage 7 admission/analysis | Do not reuse the fit-gate decision |
| Coverage fingerprint missing/mismatched or assessment incomplete | Shortlist assessment | Recompute affected job/occurrences | Invalidate Stage 5 admission, dependent Stage 6 handoff, and Stage 7 checkpoints for affected jobs |
| Coverage is stale/incomplete but recomputation cannot complete | Shortlist assessment | Persist affected occurrences as incomplete, failure-derived `U`, and retryable; emit no new authoritative Stage 5 admission | Invalidate any admission, Stage 6 handoff, and Stage 7 checkpoint that depended on the affected coverage; retry from the assessment boundary |
| Coverage recomputation proves the admitted set unchanged and only non-authoritative display metadata changed | Shortlist assessment | Preserve the admission decision but issue new provenance metadata | Invalidate only dependent evidence/checkpoints that reference changed metadata |
| Profile revision, JD reference, requirement contract, or upstream evidence revision changed | Upstream owner | Restart at the first affected assessment/ranking boundary | Invalidate all downstream decisions derived from the changed revision |
| Missing/invalid predecessor checkpoint or conflicting worker projection | Lifecycle owner | Stop with a technical resume failure and explicit reason | Do not guess or continue from a later stage |

The invalidation boundary is determined by dependency, not by run age: if a recomputed coverage can change admission or ranking inputs, Stage 5 and all dependent stages are invalid; if it cannot, only the affected evidence/checkpoint projection is replaced. A run must persist the checkpoint stage, input fingerprints, handoff fingerprint, contract versions, and invalidation reason.

Alternative rejected: always continuing the historical execution. That can preserve a decision that the active contract would no longer authorize.

### 4. Fingerprints are versioned, deterministic, and owned at the assessment boundary

The shortlist assessment boundary creates and validates these additive fingerprints:

- `coverage_contract_fingerprint`: requirement-contract schema/version plus the canonical occurrence graph, operators, normalized bounds, source references, and occurrence IDs.
- `assessment_input_fingerprint`: canonical job identity, candidate-profile revision, JD/source revision, evidence-projection version, retrieval-policy identifier/version, support-policy identifier/version, and `coverage_contract_fingerprint`.
- `evidence_compatibility_fingerprint`: the ordered evidence IDs together with each evidence record revision or content hash and the evidence projection version.
- `coverage_fingerprint_schema_version`: the schema identifier for the fingerprint payloads and serialization rules.

The assessment boundary owns the composition and hash algorithm; profile, evidence, retrieval, and support-policy producers own the revisions included in the payload. Each fingerprint is SHA-256 over UTF-8 canonical JSON with sorted object keys, explicitly represented nulls, stable sorted arrays by identity, no timestamps/run IDs/random values, and no duplicate identifiers. Missing required inputs or unknown fingerprint schema makes reuse ineligible rather than silently compatible.

Existing legacy fingerprint fields remain audit-only unless they can be mapped to these versioned payloads without loss; they SHALL NOT authorize reuse by themselves. Assessment completeness and `failure_derived` origin are eligibility gates alongside the fingerprints, not substitutes for them.

Coverage reuse requires all fingerprints, `assessment_completeness=complete`, and no occurrence marked `failure_derived=true`. A complete assessment may still contain policy-defined unresolved `U`; only uncertainty caused by retrieval/validation failure is retryable. The persisted record stores the non-reuse reason when recomputation occurs.

Alternative rejected: one global policy version or the presence of a coverage object. Those cannot prove that one job's profile, evidence, or semantic requirements still match.

### 4.1 Managed candidate profile provenance is a Stage 7 reuse input

The Stage 7 analysis fingerprint payload includes the managed `candidate_profile_id`, `candidate_profile_revision`, and canonical `candidate_profile_checksum` alongside the existing profile, job, contract, policy, and evidence inputs. The values come only from the control-plane provenance attachment; top-level legacy YAML fields, filenames, timestamps, and other profile content do not establish managed authority.

The payload uses the existing canonical JSON serialization and SHA-256 hashing conventions. The runtime marker used to identify the control-plane attachment is compatibility metadata and is excluded from the fingerprint payload. A revision-only change therefore changes the fingerprint even when the canonical checksum is unchanged.

Historical records remain readable. A record missing any required managed provenance field is ineligible for new reuse and is recomputed with the deterministic `managed_profile_provenance_missing` reason. Exact reuse remains available only when all three managed fields and the other fingerprint inputs match.

### 5. Normalize experience bounds at the enriched-job contract boundary

The enrichment/data-contract owner performs the only normalization before requirement construction. Downstream Stage 5/6/7 consumers read the canonical nullable values and do not reinterpret zero or invalid input.

The normalizer applies this truth table:

| Input | Canonical value | Diagnostic | Requirement effect |
|---|---|---|---|
| missing, null, or blank | null | none | no bound |
| finite positive number | canonical positive value | none | bound may become a requirement |
| zero, including source-asserted zero | null | `zero_bound_ignored` | no synthetic requirement |
| negative, non-numeric, NaN, or infinite | null | `invalid_bound` | no bound from that side |
| valid positive min greater than valid positive max | both null | `inverted_range` | no synthetic range |

The normalizer preserves the raw input only in diagnostics/provenance. It does not invent a genuine zero-years requirement in this change.

Alternative rejected: independent `> 0` checks in each consumer. That leaves minimum and maximum semantics divergent and makes persisted fingerprints unstable.

### 6. Assessment state preserves occurrence-level uncertainty and deterministic OR provenance

Every occurrence stores its final state, assessment completeness, uncertainty origin, evidence identifiers, contradiction/qualifier diagnostics, and provenance. A job is complete only when every occurrence has been assessed without retrieval or validation failure.

Compound propagation is deterministic: a failure-derived child makes its parent and job incomplete/retryable unless an OR branch already establishes a supported result under the active policy; a complete no-support result remains a normal `E`/policy result, not a retrieval failure. For OR compounds, qualifying branches are ordered by the existing support policy. If multiple branches tie, selected branch IDs and evidence are the sorted union of all tied qualifying branches; a single display representative, when required, is the smallest stable branch ID. Unused weak branches do not downgrade a supported result.

For an OR compound with no qualifying supported branch, any failure-derived branch makes the result failure-derived `U`; when all branches were assessed without retrieval or validation failure, the existing support policy deterministically selects its policy-defined unresolved/contradictory outcome and preserves all material branch diagnostics. No branch state may be silently upgraded or discarded during aggregation.

Alternative rejected: deriving parent provenance from whichever child was last processed or from the compact display subset.

### 7. Evidence references are bounded but integrity-complete

Persisted coverage stores bounded selected evidence plus a bounded, complete reference manifest for the evidence identities required to substantiate each persisted occurrence state. Each reference binds `occurrence_id`, `evidence_id`, evidence revision or content hash, and evidence projection version. References are deduplicated by the full identity tuple and sorted deterministically. The manifest has an explicit configured upper bound; exceeding it is an integrity/reuse failure that triggers recomputation or retry rather than silent truncation. A missing, malformed, stale, or contradictory reference causes the affected occurrence to become unresolved and makes coverage reuse ineligible; it is not silently dropped. The store records the integrity/reuse reason while keeping historical payloads readable.

Alternative rejected: persisting only display text or only a bounded candidate list. Either loses reproducibility or makes assessment depend on presentation limits.

### 8. PDF acceptance is a completion gate for this change

The existing converter remains the implementation path. Archive readiness requires targeted acceptance proving both optional-review and mandatory-review paths produce a PDF whose post-conversion integrity, renderability, schema/link/checksum, and configured page-fit checks pass. A successful converter exit without those checks is not sufficient. Mandatory review still blocks submission, not PDF generation.

Alternative rejected: deferring targeted PDF acceptance to a later renderer effort, because this change explicitly preserves and relies on the PDF state contract.

## Risks / Trade-offs

- [Legacy consumers expect fit-gate statuses] -> Keep read compatibility, expose migration diagnostics, and update only new-run emission and reuse rules.
- [Coverage recomputation invalidates expensive downstream work] -> Persist dependency-based invalidation reasons and preserve only decisions proven independent of the changed input.
- [Strict fingerprints cause more recomputation] -> Include only material semantic revisions, keep serialization deterministic, and record the exact rejection reason.
- [A handoff failure hides a useful CV] -> Require minimum provenance, expose structured technical diagnostics, and permit retry only after a corrected upstream handoff.
- [Lifecycle storage cannot represent the new status fields] -> Bring the smallest additive checkpoint/worker projection migration into this change if focused tests prove the existing lifecycle cannot preserve terminality, retryability, or scope.
- [Targeted PDF acceptance is environment-sensitive] -> Run it against the existing converter and record the exact acceptance output separately from non-render tests.

## Migration Plan

1. Add additive status, checkpoint, fingerprint, completeness, normalization-diagnostic, and evidence-reference fields with backward-compatible readers.
2. Implement authoritative handoff validation and current-policy routing; keep legacy fit-gate records readable but non-authoritative.
3. Implement scoped assessment completeness, fingerprint compatibility, compound/OR propagation, and dependency-based invalidation.
4. Update worker/pipeline projections and operator diagnostics, then verify replay/resume behavior.
5. Run focused tests, the non-render suite, and targeted PDF acceptance for both review states.
6. Archive only after validation and acceptance evidence are complete; sync accepted deltas to maintained specs during archive.
7. Rollback preserves old readers and historical records; disable new reuse/routing fields only through a versioned compatibility switch if implementation discovery requires rollback.
