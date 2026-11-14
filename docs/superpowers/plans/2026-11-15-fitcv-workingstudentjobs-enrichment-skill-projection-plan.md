---
layer: change
artifact_type: plan
contract_version: "1"
status: proposed
template_id: implementation-plan
name: fitcv-workingstudentjobs-enrichment-skill-projection
targets:
  - scripts/fetch_workingstudentjobs.py
  - src/fitcv/enrich.py
  - tests/test_fetch_workingstudentjobs.py
  - tests/test_fetch_jobs.py
  - tests/test_enrich.py
  - docs/pipeline.md
---

# Goal

Preserve WorkingStudentJobs API skill metadata as enrichment input so valid
BI/automation signals are not lost on the full-description path, without
changing ranking thresholds, fit-gate policy, or the meaning of extracted
required skills.

# Outcomes

- Full-description WorkingStudentJobs records expose their existing source
  skill metadata at the canonical enrichment boundary.
- The enrichment request can use those source skills as supporting input while
  retaining the job description as the primary source and preserving the
  existing structured-output contract.
- Raw `sourceRecord` provenance remains intact and no source skill is silently
  promoted to a required skill without the existing extraction/normalization
  rules.
- Regression coverage proves the projection, the full-description requirement,
  the no-skills case, and unchanged behavior for non-WorkingStudentJobs inputs.
- Pipeline documentation distinguishes full description completeness from
  structured enrichment completeness.

# Constraints / decisions

- Keep `sourceRecord` as the untouched upstream payload; do not replace or
  duplicate the source-of-truth record.
- Reuse the existing enrichment request and prompt-building path. Do not add a
  new provider, adapter, storage table, feature flag, ranking signal, or
  orchestration layer.
- Source skills are evidence supplied to extraction, not an automatic final
  `required_skills` assignment. Existing provider parsing, canonicalization,
  description-repair, and semantic-completeness rules remain authoritative.
- Preserve the current WorkingStudentJobs fetch contract: records without a
  non-empty page description remain excluded and accepted page records remain
  marked full.
- Do not lower the `0.40` stretch threshold, bypass the reranker fit gate, or
  change the distinction between `blocked_by_reranker_fit` and later
  `skipped_fit_gate` outcomes.
- Keep the change read-only with respect to existing run artifacts; no replay,
  migration, or destructive data rewrite is in scope.
- Native Codex remains the implementation and acceptance controller. Orca or
  other delegated execution is optional and subordinate; no runtime IDs,
  worker assignments, or session state belong in this plan.

# Task graph

## Task A

**Objective:**

Define one canonical, optional enrichment-facing projection of the existing
WorkingStudentJobs API skills for records that already passed the full-page
description boundary.

**Scope:**

The WorkingStudentJobs ingestion-to-normalization boundary owned by
`scripts/fetch_workingstudentjobs.py`, including preservation of raw source
provenance and compatibility with the existing FitCV job record contract.

**Dependencies:**

None.

**Durable sequencing:**

The raw source payload and full-description admission behavior must remain
unchanged before the enrichment-facing projection is consumed.

**Constraints / decisions:**

- The projection must be absent or empty when the source provides no skills.
- It must not make the structured-summary fallback eligible for canonical
  output when the page description is missing.
- It must remain source-specific at the boundary rather than broadening the
  generic normalized job contract with speculative fields.

**Acceptance:**

- A full-page WorkingStudentJobs record retains `sourceRecord` and exposes the
  source skill values through the agreed enrichment-facing input.
- A record without source skills remains valid and does not gain invented
  values.
- Existing page-description filtering and `descriptionStatus="full"` behavior
  remain unchanged.

**Verification:**

- Focused unit tests cover populated and empty source skill arrays.
- Existing fetch tests continue to prove that missing page descriptions are
  excluded before canonical record creation.
- Inspect the resulting record shape for preserved raw provenance and no
  duplicated authoritative requirement fields.

**Stop / escalation conditions:**

Stop if the existing normalized job contract cannot carry the projection
without exposing source-specific data to unrelated consumers; return for a
boundary decision instead of adding a new shared abstraction.

## Task B

**Objective:**

Pass the optional source-skill projection through the existing enrichment
request so the extraction provider can recover relevant BI/automation signals
that are present in the source API record but absent from page prose.

**Scope:**

The canonical request builder and extraction prompt path owned by
`src/fitcv/enrich.py`; non-WorkingStudentJobs callers remain compatible.

**Dependencies:**

Task A.

**Durable sequencing:**

The request must continue to use the full job description as primary input and
must preserve existing metadata, routing, fingerprints, response parsing, and
fallback behavior.

**Constraints / decisions:**

- Add the source skills as bounded supporting metadata through the existing
  prompt input structure; do not create a second provider call.
- Keep the projection deterministic and bounded by the same request-budget
  discipline already used by enrichment.
- Do not inject source skills directly into `required_skills`, `tech_stack`, or
  other extracted fields after provider response parsing.
- Include the source-skill input in the existing request fingerprint so stale
  enrichment requests cannot be reused as if the new input had been present;
  do not add a migration or replay mechanism.
- Preserve route provenance semantics for reuse and auditability.

**Acceptance:**

- A request built from a full-description WorkingStudentJobs record contains
  its source skills in the provider-visible input.
- A request from a record without source skills is unchanged apart from the
  absence of that optional input.
- Existing extraction parsing and merge behavior remain authoritative for the
  final structured fields.

**Verification:**

- Unit-test the request payload/prompt for representative skills including
  `Power BI`, `Datenmodellierung`, and `Prozessautomatisierung`.
- Assert that source skills are not post-hoc promoted into required skills by
  the merge path.
- Run the focused enrichment test suite and inspect request fingerprint or
  provenance assertions where existing tests cover them.

**Stop / escalation conditions:**

Stop if adding source skills requires changing the provider response schema,
ranking contract, or cross-source semantics; defer that broader policy change
instead of expanding this correction.

## Task C

**Objective:**

Reconcile tests and documentation with the new enrichment input boundary and
prove that the correction does not alter ranking or CV-analysis gating.

**Scope:**

The focused fetch/enrichment tests and the cross-cutting pipeline ownership
documentation. Ranking, CV-analysis, and run-artifact code are verification
boundaries only and are not implementation targets.

**Dependencies:**

Tasks A and B.

**Acceptance:**

- Focused tests pass for WorkingStudentJobs fetch, enrichment request
  construction, parsing/merge behavior, and existing full-description
  rejection.
- Diff and source inspection confirm that ranking policy remains
  `holistic_ai_only` with `structured_fit=0.0` and the `stretch=0.40` threshold;
  the change does not alter the direct reranker gate.
- Documentation states that a full description can still have sparse
  structured enrichment and identifies the enrichment request as the owner of
  source-skill recovery.
- No unrelated source, generated surface, or run artifact is modified.

**Verification:**

- Run focused pytest for `tests/test_fetch_workingstudentjobs.py`,
  `tests/test_fetch_jobs.py`, and `tests/test_enrich.py`.
- Run the applicable broader enrichment/pipeline tests if the focused change
  affects shared request or merge helpers.
- Run `git diff --check` and inspect the final diff against the approved target
  set.
- Confirm no ranking threshold, fit-gate status, or stage-transition behavior
  changed in the diff.

**Stop / escalation conditions:**

Stop before implementation completion if tests require provider/network access,
if source skills would be treated as verified requirements without provenance,
or if the change alters ranking or stage-gate semantics. Escalate those as
separate decisions rather than silently widening this plan.

# Final verification

- Confirm the implementation is limited to the approved ingestion/enrichment
  projection, focused tests, and pipeline documentation.
- Prove with fresh automated output that full-description WorkingStudentJobs
  records expose source skills to enrichment and that missing descriptions are
  still rejected.
- Prove that source skills remain supporting input rather than an automatic
  `required_skills` assignment.
- Prove that non-WorkingStudentJobs enrichment requests and existing parser,
  merge, fingerprint, fallback, and provenance behavior remain compatible.
- Prove that ranking configuration and CV-analysis gate behavior are unchanged;
  no claim should be made that the fix raises any particular model score until
  a later controlled rerun supplies ranking input/output evidence.
- Record fresh test and diff evidence before any commit, push, merge, or
  release action. Those actions remain outside this plan's authority.
