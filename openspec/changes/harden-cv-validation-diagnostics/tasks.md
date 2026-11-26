# Tasks

## 1. Freeze cross-stage contracts

- [x] 1.1 Extend the existing late-stage and outcome contracts with canonical lifecycle dimensions, owners, allowed transitions, derived submission rules, and legacy projections; verify contract tests cover proposed state combinations without changing existing Stage 6 handoff admission.
- [x] 1.2 Define the versioned diagnostic registry, producer ownership, stable codes, fact schemas, retryability/terminality, deduplication, primary-diagnostic precedence, unknown-code behavior, and legacy projections; verify multiple diagnostics produce the same persisted primary code regardless of producer order.
- [x] 1.3 Add validation-policy, diagnostic-schema, section-policy, and skill-provenance versions to the Stage 7 fingerprint/checkpoint compatibility contract; verify a policy-only change invalidates affected Stage 7 reuse while compatible Stage 6 work remains reusable.

## 2. Canonical rendering and validation policy

- [x] 2.1 Extend the versioned myCVs section policy with canonical keys, `Certificates` display mapping, presence rules, meaningful-content semantics, and header handling; verify no second myCVs order remains authoritative in presets or generic heading maps.
- [x] 2.2 Route composition, Markdown serialization, structural validation, and PDF acceptance through the same section policy, preserving Certificates-before-Skills and Europass behavior; verify valid structured CVs round-trip and optional omissions preserve relative order.
- [x] 2.3 Add negative order/presence coverage for duplicates, unexpected headings, malformed empty groups, reversed sections, mandatory omissions, and header handling; verify structural safeguards still reject invalid artifacts.

## 3. Structured factual authority

- [x] 3.1 Define the structured skill claim identity and provenance projection, distinguishing missing, explicitly empty, supported, and unsupported claims while preserving canonical-profile authority; verify supported, canonicalized, and unsupported structured-claim cases.
- [x] 3.2 Remove rendered Markdown as an independent skill authority while retaining projection checks; verify canonical label differences pass, unexpected rendered skill claims block final artifact acceptance, and structured content is not falsely reclassified as unsupported.
- [x] 3.3 Mark legacy Markdown-only records provenance-unavailable for new factual reuse while keeping them readable; verify recomputation and historical-reader compatibility for records with missing provenance.

## 4. Typed diagnostics and finalization

- [x] 4.1 Replace warning/message substring branches in generation-format, review-reason, worker, and persistence mapping with registry codes and structured facts; verify message mutation does not change classification and workers persist typed codes rather than only stage labels.
- [x] 4.2 Implement the finalization transition matrix for fresh generation, repair, exact reuse, optional review, mandatory review, page-fit failure, conversion failure, corrupt/mismatched PDF, accepted persistence failure, quarantine persistence failure, and retry; verify hard validation cannot become review-approved and PDF/persistence failure cannot erase valid content.
- [x] 4.3 Update pipeline, worker, review-event, export, and operator projections to derive submission clearance from lifecycle dimensions; verify accepted, review-required, validation-failed, PDF-failed, and persistence-failed combinations retain independent facts.
- [x] 4.4 Document the diagnostic registry, lifecycle fields, precedence, compatibility projections, and verification boundary in `docs/pipeline.md`, `docs/observability.md`, and maintained API/configuration contracts; verify examples use emitted codes and fields rather than message parsing.

## 5. Quarantined validation drafts

- [x] 5.1 Add additive quarantine storage distinct from accepted artifact fields, including complete/partial/unavailable availability, attempt/version identity, validation snapshot, diagnostics, fingerprints, trace reference, checksums, and idempotency; verify quarantine cannot populate accepted `structured_cv_final` or `markdown_final` projections.
- [x] 5.2 Implement matching pipeline and control-plane worker write/read projections and idempotent SQLite migration behavior; verify fresh and pre-change databases reload complete and partial quarantines without rewriting historical records.
- [x] 5.3 Preserve the original validation failure when a quarantine write fails and add a typed persistence failure; verify the failure is not rewritten as generic generation failure and submission remains blocked.
- [x] 5.4 Isolate quarantine from review approval, accepted downloads, submission exports, accepted lists, and reuse cache hits; verify a retry creates a new linked attempt/version and leaves the original quarantine immutable.

## 6. Cross-stage verification

- [x] 6.1 Add the minimum acceptance matrix covering valid/no-review, valid/mandatory-review, review approval, invalid complete/partial/unavailable drafts, estimated length warning, actual page-fit failure, conversion failure, corrupt PDF, quarantine persistence failure, accepted persistence failure, provider failure, and historical insufficient provenance; verify all dimensions and submission outcomes match the proposed contract.
- [x] 6.2 Run focused validator, generator, renderer, reason-mapping, pipeline, worker, SQLite migration, reuse/checkpoint, review-event, and Stage 6/7 tests; verify quarantine round-trips through both persistence paths and multiple-diagnostic precedence is deterministic.
- [x] 6.3 Run the existing non-render suite and targeted PDF acceptance for optional and mandatory review paths, recording unrelated baseline failures separately; verify browser evidence is not used as backend proof.
- [x] 6.4 Run `openspec validate "harden-cv-validation-diagnostics" --type change --strict` before implementation and after implementation, and confirm artifact completeness is reported separately from runtime acceptance evidence.

## Workflow follow-up

- Archive the change only after implementation, migration, focused/non-render, and targeted PDF acceptance evidence are complete.
- Sync the accepted capability delta into maintained `openspec/specs/` during archive.
