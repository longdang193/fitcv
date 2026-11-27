# Tasks

## 1. Continuation classification and handoff integrity

- [x] 1.1 Evaluate ranking `decision_summary` failure codes before the recoverable partial-ranking exception, and verify partial-plus-valid-handoff-plus-technical-failure remains terminal in focused worker tests.
- [x] 1.2 Apply the existing ranking-to-CV handoff validator at the single continuation boundary, compare canonical handoff identities with authoritative selected ranking identities, and verify missing, duplicate, fingerprint-invalid, and mismatched handoffs fail closed.
- [x] 1.3 Distinguish required checkpoint/handoff persistence from optional telemetry/debug persistence, and verify required persistence failure cannot publish `AWAITING_CONTINUE` while optional projection failure remains secondary.

## 2. Lifecycle and diagnostic persistence

- [x] 2.1 Preserve the primary owning failure and retry boundary through late finalization, and verify a secondary artifact/projection failure does not overwrite the original technical failure.
- [x] 2.2 Replace raw or shallow failure/debug persistence with the existing bounded typed/allowlisted diagnostic projection, and verify nested sensitive fields, raw exception text, prompts, profile/CV content, and provider payloads are excluded.
- [x] 2.3 Map supported legacy failure outcomes to registered typed diagnostics, bound collection size and safe facts, and verify blocking diagnostics win over nonblocking warnings while valid scores survive malformed explanatory metadata.
- [x] 2.4 Pass the resolved lifecycle outcome to job, stage, debug, Markdown, and PDF projections, and verify generation/PDF failures are not projected as success or not-reached while valid Markdown remains independently reviewable.

## 3. Verification and release gate

- [x] 3.1 Run focused worker, ranking, diagnostic, artifact-contract, and persistence tests plus strict OpenSpec validation and `git diff --check`; record any failures without modifying private/run artifacts.
- [x] 3.2 Run a deterministic synthetic/local continuation probe covering required persistence, handoff correspondence, terminalization, and sanitized diagnostics; require clean persisted evidence before authorizing any real-data probe.

## Workflow follow-up

- Archive this change only after implementation, review, verification, and acceptance evidence are complete.
- Treat a real-data probe as a separate authorized operation; do not start one as part of this planning change.
