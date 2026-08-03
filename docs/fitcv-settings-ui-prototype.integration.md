# Candidate Profile Creation Integration

Operation: `getCandidateProfileFieldSchema`, `listCandidateProfiles`, `createCandidateProfileCreationAttempt`, `listCandidateProfileCreationAttempts`, `getCandidateProfileCreationAttempt`, `downloadCandidateProfileSource`, `getCandidateProfileSourceBlock`, `getCandidateProfileBaseline`, `patchCandidateProfileBaseline`, `regenerateCandidateProfileBaseline`, `approveCandidateProfileBaseline`, `getCandidateProfileDerived`, `patchCandidateProfileDerived`, `regenerateCandidateProfileDerived`, `approveCandidateProfileDerived`, `getCandidateProfileConfirmation`, `confirmCandidateProfileCreationAttempt`, `retryCandidateProfileCreationAttempt`, `getCandidateProfile`, `listCandidateProfileRuns`, `archiveCandidateProfile`, `restoreCandidateProfile`, `getLlmConfiguration`, `patchLlmConfiguration`
Contract owner: `docs/superpowers/specs/2026-08-01-23-49-canonical-candidate-uniform-evidence-projection-spec.md#api-contract`
Canonical field owner: `docs/superpowers/specs/2026-08-01-23-49-canonical-candidate-uniform-evidence-projection-spec.md#requirement-required-canonical-surface`
State and error owner: `docs/superpowers/specs/2026-08-01-23-49-canonical-candidate-uniform-evidence-projection-spec.md#state-transition-contract` and `#error-contract`
Status: mock-backed frontend approved August 3, 2026; backend Tasks 5-10 authorized against frozen frontend contract

## UI Intent

- prototype and shared components: `docs/fitcv-settings-ui-prototype.html`
- field labels, descriptions, controls, requirements, kinds, date grammar, and section order load from `getCandidateProfileFieldSchema`
- Upload, Baseline, Controlled Derivation, Confirmation, Candidate Details, and Candidate Profiles table use one Candidate Profile creation flow
- confirmation and Candidate Details render same server-owned `profile.canonical`; UI keeps no reconstructed baseline/derived copy
- server capabilities own action availability, retryability, stage progression, and disabled reasons

## Prototype Parity Contract

- approved visual and interaction SSOT is `docs/fitcv-settings-ui-prototype.html` blob `989af611bd7767c148022c79ac00c5069d8a3956`; implementation review must verify this blob before comparing mock UI
- prototype owns page headings, section names, section order, default expanded/collapsed state, component classes, visible metadata, and responsive layout; this note maps behavior and transport only and must not restate a competing presentation contract
- canonical field registry owns field inventory, labels, descriptions, requirement state, control shape, evidence kinds, section descriptions, and derived-claim metadata; templates do not copy these lists
- schema shape does not grant editability: stable IDs and provenance remain contextual display, while `origin`, `confidence`, and `support_status` render as derived metadata unless server contract explicitly enables editing
- one shared derived-claim component renders every skill, role family, domain tag, and responsibility theme with editable Name, checkbox evidence refs, metadata chips, server-owned Source/wand actions, Add, and Remove
- one shared baseline collection component hides internal `id` and `source_refs` controls, displays IDs in entry headings, and renders nested evidence through same evidence component
- regression checks assert required structures and forbidden fallbacks; text-presence assertions alone do not prove prototype parity
## State Ownership

- URL owns attempt ID and stage route: upload, baseline, derived, or confirmation
- server owns attempt status, revision, fingerprints, drafts, approvals, validation, failure, capabilities, confirmation payload, Candidate Profile revision, and lifecycle
- component-local state owns selected upload before submit, unsaved form batch, open Source dialog, pending request ID, and focus restoration
- Profile Name is submitted during Upload and read-only afterward; candidate Full name remains `profile.canonical.name`

## Upload

- form requires Profile Name and one `.md`, `.docx`, or `.yaml` file; one shared control and validation path handles every format
- submitting locks Profile Name, file control, and primary action; duplicate submit reuses same idempotency key
- `202` navigates to attempt baseline route and shows processing state while polling `getCandidateProfileCreationAttempt`
- unsupported, unsafe, corrupt, empty, mismatched, or oversized file errors remain on Upload with selected filename and Profile Name preserved where browser security permits
- Save and exit after attempt creation flushes pending review batch, then returns to Candidate Profiles without creating a profile revision

## Baseline Review

- loading keeps page heading, stepper, source action, and footer visible; field regions use skeletons
- processing preserves last valid draft read-only and shows server stage; no client-estimated completion percentage
- fields and repeatable collections render from canonical field metadata and draft `document`; annotations drive Source, warning, and regeneration affordances
- `i` opens field description; `Source` opens dialog backed by exact `source_block_id`; View Source uses original source operation
- user edits accumulate locally and persist as one ordered review batch on blur, collection action, stage navigation, Save and exit, or approval; never send one mutation per keystroke
- Add, edit, and remove use same ID-addressed operation grammar for experiences, education, projects, achievements, certifications, volunteering, and nested evidence
- Regenerate all sends `targets: ["*"]`; field wand sends one path. UI shows wand only when annotation says `regenerable: true`
- stale revision preserves unsaved operations, reloads server draft, highlights conflicts, and requires explicit reapply or discard
- Approve flushes pending edits first, then submits returned revision and fingerprint; success shows derivation processing

## Controlled Derivation

- Skills, role families, domain tags, and responsibility themes use same repeatable claim component
- each claim has stable ID, value, origin, confidence, and editable `evidence_refs`; Source opens evidence-resolution dialog without side inspector
- Add, edit, remove, regenerate all, regenerate one, stale recovery, and approval follow same baseline interaction contract
- unsupported user claims stay visible with clear unsupported state; backend capability decides whether claim can affect pipeline
- navigating back and editing baseline accepts full derived invalidation; UI does not retain a hidden client copy

## Confirmation

- request `getCandidateProfileConfirmation`; do not assemble confirmation from local baseline and derived state
- render restored prototype structure in order: Confirmation Overview, Source Input, Approval Status, Baseline Facts, and Derived Claims
- reuse shared section-card, baseline-preview, and derived-preview renderers used by Candidate Details; checksums, source-document IDs, parser provenance, and LLM provenance remain non-visual
- primary action stays disabled while request is pending, fingerprints are stale, validation blocks readiness, or capability denies confirmation
- confirmation uses one idempotency key; duplicate clicks remain locked until stored result returns
- success navigates to returned Candidate Profile details; details render returned `profile.canonical` unchanged
- persistence failure keeps confirmation visible, shows retry action, and never adds table row optimistically

## Candidate Profiles and Details

- table lists only confirmed Candidate Profiles as pipeline resources; resumable attempts use creation-attempt query and are visually distinct from profiles
- list rows, status, lifecycle, and capabilities come from server summaries; UI does not infer `use_for_run`
- details load `getCandidateProfile`; every confirmed field comes from `profile.canonical`, while Profile Name, Candidate Profile ID, source input, lifecycle, capabilities, and Related Runs come from resource metadata
- render restored prototype structure in order: Profile Overview, Source Input, Baseline Facts, Derived Claims, collapsed Traceability, and collapsed Related Runs; integrity checksums and parser/LLM provenance remain transport/persistence fields only
- archive and restore reconcile returned resource and preserve immutable `profile.canonical`
- failed attempts link back to owning stage or retry action; they never appear selectable in Run creation

## Errors and Recovery

- validation: map `field_errors[].field` to canonical ID-addressed controls; keep page-level summary and first-error focus
- stale revision or fingerprint: preserve local changes, fetch current stage, and require explicit reconciliation
- invalid transition: replace local attempt metadata with response `data`, navigate only when server `next_action` changes
- retryable processing or LLM error: retain last valid draft and expose server retry capability
- non-retryable source error: retain attempt diagnostics and offer new Upload; do not fake retry
- already confirmed: open returned/existing Candidate Profile rather than creating another row

## Accessibility and Responsive Behavior

- use native file input, buttons, links, labels, selects, dialogs, and fieldsets; repeatable entries expose clear group names and remove confirmations
- processing and save status use polite live regions; errors use assertive summary without repeatedly announcing unchanged polling state
- Source and `i` controls have distinct accessible names; dialog returns focus to invoking control
- stepper exposes current step, completed steps, and blocked navigation without color-only meaning
- footer actions wrap in source order without overlap; content remains visible at 200% zoom and narrow width
- long field names, values, evidence refs, filenames, and localized copy wrap without truncation
- preserve visible focus, keyboard order, supported themes, reduced motion, and existing contrast tokens

## Required Evidence

Prior mock approval evidence from August 2, 2026 is invalidated. Required parity work:

- [x] field-schema regression covers canonical evidence kinds, optional title, complete help descriptions, `support_status`, section descriptions, and shared derived shape
- [x] exact markup regression covers prototype DOM hierarchy, classes, action order, button variants, and hidden internal controls
- [x] one deterministic fixture supplies prototype and runtime mock values, IDs, selected refs, and capabilities
- [x] browser flow covers Candidate Profiles, Upload, Baseline, Controlled Derivation, Confirmation, Candidate Details, and LLM Configuration
- [x] desktop, 375px, effective 200% width, dark theme, Source dialog focus return, long evidence labels, computed high-risk styles, screenshots, and zero console warnings pass
- [x] independent verifier reports `Spec compliance: PASS` and `UI parity quality: APPROVED` against prototype blob `989af611bd7767c148022c79ac00c5069d8a3956`
- [x] exact presentation projections cover Source excerpt/locator values, validated-model copy, evidence-kind labels, derived origin labels, and confirmation date labels without changing canonical raw values
- [x] user approved corrected mock UI on August 3, 2026 before backend Tasks 5-10

- backend contract tests cover upload safety, all three formats, ID-addressed mutations, regeneration targets, approvals, invalidation, errors, idempotency, and exact confirmation/detail canonical equality
- store tests cover migration idempotency, immutable source/snapshots/revisions, review batches, concurrency, transaction rollback, one revision per confirmation, archive symmetry, and Run eligibility
- frontend state tests cover processing, field and collection edits, Source dialogs, regenerable capabilities, stale reconciliation, upstream invalidation, confirmation retry, and exact Candidate Details rendering
- Playwright flow covers MD, DOCX, and YAML creation; multiple entries; per-field and all regeneration; evidence-ref editing; Save and exit/resume; stale conflict; confirmation; details; archive/restore; keyboard and narrow layout
- Chrome DevTools evidence confirms operation payloads, status codes, no duplicate submissions, no console errors, and no layout shift across processing and error states
