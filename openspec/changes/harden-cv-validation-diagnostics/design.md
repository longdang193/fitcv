# Design

## Context

See `proposal.md` for the motivation and scope. The repository already has a versioned section-policy module, a CV outcome envelope in `pipeline_contracts.py`, late-stage state/submission helpers, Stage 7 fingerprints and checkpoints, separate pipeline and control-plane persistence paths, and SQLite artifact-integrity checks. The review found that these primitives are not yet one coherent contract for validation failures, projection mismatches, quarantine, and reuse.

The existing Stage 6/7 behavior is accepted and remains authoritative: a valid handoff admits Stage 7, hard technical failures remain blocking, verified PDF acceptance is required for completion, persistence is a submission gate, and historical statuses remain readable. The lifecycle and diagnostic additions in this change are proposed behavior until implementation and acceptance tests land.

## Goals / Non-Goals

**Goals:**

- Extend the existing lifecycle and outcome contracts without creating a second authority.
- Make section order, section display/presence semantics, skill provenance, diagnostic classification, quarantine, and reuse compatibility deterministic.
- Preserve useful failed-attempt evidence without exposing it as accepted or review-approved output.
- Prove the combinations that cross validator, generator, renderer, pipeline, worker, SQLite, review, and reuse boundaries.

**Non-Goals:**

- Reworking the ranking model, Stage 6 handoff rules, provider selection, or the configured one-page/page-fit policy.
- Rewriting historical records or making quarantined content eligible for submission, download, review approval, or cache reuse.
- Replacing the existing outcome envelope or late-stage helpers with a parallel exception hierarchy.
- Making all lifecycle writes globally atomic; only the persistence boundaries needed to preserve terminality, identity, and original failure facts are in scope.

## Decisions

### 1. Extend the existing lifecycle authority

`late_stage_contract.py` and `pipeline_contracts.py` remain the canonical lifecycle/outcome owners. The proposed semantic state dimensions are:

| Dimension | Proposed values | Owner / rule |
| --- | --- | --- |
| Content validity | `valid`, `invalid`, `not_evaluated` | Validator and structured provenance checks |
| Technical/generation | `completed`, `failed`, `not_attempted` | Generation and handoff boundary |
| Draft disposition | `available`, `quarantined`, `unavailable` | Artifact persistence projection |
| Review | `not_required`, `pending`, `approved`, `rejected` | Review policy and review events |
| PDF/artifact | `not_attempted`, `verified`, `failed` | Renderer and post-conversion acceptance |
| Persistence | `pending`, `persisted`, `failed` | Pipeline, worker, and store write result |
| Submission | `blocked`, `eligible` | Derived only from authoritative dimensions and page-fit gates |

These names describe the proposed contract, not existing enum values. Each field gets an owner, allowed transitions, and a compatibility projection. Submission is never independently granted by a diagnostic or review event. A hard validation failure cannot become review-approved, and a PDF or persistence failure cannot erase valid content.

Alternative rejected: keeping only content, review, artifact/PDF, and submission. That would drop existing technical and persistence authorities and make valid-content/quarantine/persistence combinations ambiguous.

### 2. Make section policy complete, not merely shared

Extend the existing versioned myCVs policy with one explicit table containing canonical keys, display headings, order, source-driven/mandatory presence, meaningful-content predicate, and header handling. The canonical order is `summary -> education -> experience -> projects -> certificates -> skills`; the user-visible heading for the `certificates` key is `Certificates`. Generic config aliases and `cv_presets.py` ordering remain legacy or other-preset inputs unless they delegate to this policy.

Composition, Markdown serialization, structural validation, and PDF checks all consume the same table and presence predicate. The header is validated separately but uses the same policy version. Optional empty sections are omitted without disturbing relative order; mandatory or canonical-profile sections that are expected but absent produce a deterministic diagnostic. Duplicate, unexpected, malformed-empty, reversed, and Europass-specific headings remain covered by negative tests.

Alternative rejected: changing only the serializer or only the validator. Either leaves a second order authority.

### 3. Extend the existing diagnostic registry

The proposed diagnostic envelope extends the existing outcome contract. The registry is the single source for code meaning, producer ownership, allowed facts, severity, blocking, retryability, terminality, and legacy projection. The initial registry must cover at least:

| Category | Proposed code | Decision effect |
| --- | --- | --- |
| Structural | `invalid_section_order` | Block artifact acceptance |
| Provenance | `unsupported_skill_claim` | Block content acceptance |
| Projection | `skill_projection_mismatch` | Block artifact acceptance |
| Quality | `estimated_length_exceeded` | Warning only |
| Review | `unsupported_requirement_gap` | Block submission pending review |
| Artifact | `page_fit_failed` | Block final acceptance |
| Renderer | `pdf_render_failed` | Technical failure |
| Provider | `provider_timeout` | Retry under policy |
| Persistence | `quarantine_persistence_failed` | Preserve original failure and block submission |
| Unknown | `unclassified_failure` | Fail conservatively |

These are proposed stable contract names to be confirmed at implementation against existing emitted codes. Existing `classify_cv_outcome()` and reason projections consume the registry; they are not duplicated. Multiple diagnostics are deduplicated by stable identity and ordered by explicit precedence, then code/source/facts. Primary diagnostic selection is deterministic. Unknown codes are retained with source/facts and project conservatively; no message substring can select or refine a code. The worker stores the typed code rather than only a stage label.

Alternative rejected: an exception hierarchy or independent worker/UI classifiers. Those do not survive persistence boundaries and would repeat the current drift.

### 4. Define structured skill identity and projection safety

A structured skill claim must carry a canonical skill identity, display label, provenance/evidence references, and provenance version. The validator distinguishes missing structured claims, explicitly empty claims, supported canonical claims, and unsupported claims. Canonical profile skills remain authoritative; selected evidence is not silently made mandatory where current policy does not require it.

Rendered Markdown is checked as a projection. A rendered skill label that canonicalizes to the structured claim is acceptable. An extra, omitted, or unreconcilable material rendered skill is a blocking `skill_projection_mismatch` for final artifact acceptance, while the structured content result remains separately classified. Legacy Markdown-only records remain readable but are provenance-unavailable and cannot authorize new factual reuse.

Alternative rejected: deleting all rendered checks. That would remove the factual-safety guard without making Markdown the authority.

### 5. Isolate quarantine from ordinary artifact persistence

Quarantine uses additive storage fields or a dedicated quarantine payload associated with the same job, candidate, CV attempt/version, input identity, and validation payload revision. It stores any available structured draft and/or rendered draft, an availability map, validation snapshot, diagnostic list, input and policy fingerprints, trace reference, payload checksum, and idempotency key. Accepted fields such as `structured_cv_final` and `markdown_final` are never populated from quarantine.

Draft semantics are explicit:

- Complete: structured and rendered payloads are both available and bound to the final validation snapshot.
- Partial: one payload or one inspectable representation is available; missing payloads are not fabricated and the availability map is persisted.
- Unavailable: no usable payload exists; persist failure scope and diagnostics only.

The current attempt is terminal when validation fails, but the record may be retry-eligible. A retry creates a new attempt/version with a parent link and recomputes the active validation/provenance boundary; it never mutates the historical quarantine. Quarantine is operator-preview-only: it is excluded from accepted lists, ordinary downloads, review approval, submission exports, and reuse cache hits. A failed quarantine write preserves the original validation failure and adds a typed persistence failure; it does not replace the original diagnostic with a generic generation failure.

Both the normal pipeline and the control-plane worker must implement the same read/write semantics. SQLite migrations are additive, preserve historical rows, enforce checksums and identity, and are idempotent for repeated writes.

Alternative rejected: broadening ordinary final-artifact persistence to accept `validation_failed`. That risks exposing invalid content through existing readers.

### 6. Reconcile finalization transitions

Add a transition matrix for fresh generation, bounded repair, exact-match reuse, optional review, mandatory review, page-fit failure, conversion exception, corrupt/mismatched PDF, accepted-artifact persistence failure, quarantine persistence failure, and retry. The matrix must preserve these invariants:

- hard validation failure remains invalid/quarantined or unavailable and cannot become review-approved;
- valid content remains valid when PDF or persistence fails;
- estimated length warnings remain non-blocking quality diagnostics;
- actual page-fit or PDF integrity failure blocks completion through the PDF/artifact dimension;
- mandatory review blocks submission but does not prevent verified PDF persistence;
- reused `pdf_failed` remains a PDF/artifact failure rather than being rewritten as a generic generation failure.

Alternative rejected: one finalizer branch that overwrites earlier facts with a single status.

### 7. Version reuse and checkpoint compatibility

Add validation-policy, diagnostic-schema, section-policy, and skill-provenance versions to the Stage 7 generation fingerprint and checkpoint compatibility inputs. A change to these versions invalidates affected Stage 7 validation/generation reuse and checkpoints at the first affected boundary; compatible Stage 6 ranking and handoff work remains reusable. Historical records remain readable but records missing required provenance or compatibility inputs cannot authorize new reuse. Quarantined records are retry context only and never accepted-output cache hits.

Alternative rejected: relying only on revalidation at reuse time. Revalidation cannot establish checkpoint ownership or prove that historical provenance satisfies the new contract.

### 8. Preserve compatibility through explicit projections

New attempts dual-write the proposed fields and current legacy status/reason values. Readers prefer the new fields when present and fall back to legacy status, snapshots, and error payloads for historical rows. The fallback never rewrites history or invents provenance. Legacy projections are deterministic and documented per primary diagnostic/state combination.

## Risks / Trade-offs

- [Risk] Existing readers expose ordinary CV fields without quarantine awareness. -> Mitigation: keep quarantine in distinct fields and add explicit exclusion tests for lists, downloads, exports, review events, and reuse.
- [Risk] Two persistence paths drift. -> Mitigation: share the semantic projection contract, test pipeline and worker round-trips, and make SQLite migration checksums/idempotency explicit.
- [Risk] A more complete diagnostic registry changes legacy reason output. -> Mitigation: preserve deterministic compatibility projections and compare historical reader behavior in migration tests.
- [Risk] Structured provenance is missing from older records. -> Mitigation: mark them provenance-unavailable and require recomputation or explicit policy-approved review; never infer authority from Markdown.
- [Risk] Strict policy versions cause extra Stage 7 recomputation. -> Mitigation: invalidate only the affected validation/generation boundary and retain compatible Stage 6 work.
- [Risk] Renderer or environment defects remain difficult to reproduce. -> Mitigation: keep renderer/PDF diagnostics separate, capture tool/reference versions, and retain grounded drafts where persistence permits.

## Migration Plan

1. Freeze the lifecycle fields, diagnostic registry, section-policy table, provenance identity, primary-diagnostic precedence, and compatibility mappings.
2. Add additive diagnostic, lifecycle, quarantine, fingerprint, and SQLite schema fields with backward-compatible readers and idempotent migration.
3. Route section presence/order and display names through the explicit versioned myCVs policy.
4. Replace rendered Markdown as a factual authority with structured provenance plus blocking projection checks.
5. Update generation, pipeline, worker, review-event, export, and reuse projections to respect independent dimensions and quarantine exclusions.
6. Add versioned Stage 7 invalidation and retry semantics; preserve compatible Stage 6 handoffs and ranking work.
7. Run the cross-stage acceptance matrix, focused tests, migration tests, non-render suite, and targeted PDF acceptance for optional and mandatory review paths.
8. If rollback is required, restore consumers to legacy projections through a versioned switch; retain additive fields and historical quarantine records, which never authorize submission on their own.

## Verification Boundary

Strict OpenSpec validation proves artifact consistency only. It does not prove implementation correctness, runtime lifecycle settlement, database migration safety, or PDF acceptance; those require the implementation and acceptance evidence listed in `tasks.md`.
