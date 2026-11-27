# Design

## Context

See `proposal.md` for the motivation. The previous hardening change already introduced partial-ranking handoff validation, typed diagnostics, stage-aligned checkpoint intent, and generation-failure records. The follow-up review shows that those mechanisms are not yet applied as one authoritative lifecycle contract: failure-code precedence, identity correspondence, required persistence, diagnostic projection, and finalization ownership can disagree.

The implementation must preserve the existing pipeline and avoid turning optional observability into a new admission gate.

## Goals / Non-Goals

**Goals:** Make continuation fail closed when required ranking-to-CV state is invalid or not durable; preserve the real failure owner and retry boundary; make persisted diagnostics bounded and privacy-safe; keep lifecycle projections consistent without losing valid Markdown.

**Non-Goals:** Change ranking policy, score validity, enrichment policy, shortlist policy, provider retry policy, PDF acceptance policy, scheduling, or storage architecture. Do not add a diagnostic service, a second handoff schema, or blanket failure rules for all partial results.

## Decisions

- **Order classification before recovery.** Evaluate explicit stage failure counters and decision-level failure codes before the partial-ranking exception. This prevents a usable subset from masking a stage-level persistence or contract failure while preserving mixed valid/invalid scoring behavior when no independent failure exists.
- **Reuse one handoff validator.** Use the existing handoff validator at the ranking-to-CV boundary, then compare canonical identities with the authoritative selected ranking output. Do not create a parallel schema or fingerprint algorithm.
- **Separate required from optional persistence.** The checkpoint, continuation handoff, and owning stage outcome are required state. Debug, telemetry, and secondary projections are best effort and cannot authorize continuation. If required persistence fails, terminalize the owning stage instead of publishing `AWAITING_CONTINUE`.
- **Use an allowlist projection.** Build persisted diagnostic records from stable codes, stage, status, bounded summaries/references, and bounded safe facts. Normalize compatibility fields from the same safe object so raw exception/provider data cannot bypass sanitization.
- **Resolve lifecycle status once.** Pass the resolved outcome into job, stage, debug, Markdown, and PDF projections. Preserve Markdown independently when valid, while recording PDF failure separately.
- **Preserve primary failure ownership.** Finalization errors append secondary diagnostics and do not rewrite the first authoritative technical failure or its checkpoint boundary.
- **Keep diagnostic severity explicit.** Select blocking diagnostics before applying precedence; retain nonblocking warnings as secondary context. Map legacy failure codes to registered typed codes at the existing normalization boundary.

## Risks / Trade-offs

- [A stricter handoff correspondence check could reject stale or malformed continuation state] ? Fail closed only for required handoff defects and add focused compatibility fixtures for valid existing handoffs.
- [Allowlisting reduces forensic detail] ? Retain stable codes, owning stage, bounded references, fingerprints, and counts; keep detailed provider data in existing access-controlled operational systems rather than pipeline artifacts.
- [Optional projection failures may be less visible] ? Record bounded secondary diagnostics and expose persistence status without blocking a valid required checkpoint.
- [Legacy outcome readers may expect old fields] ? Preserve existing stable fields and add only normalized bounded values; verify historic reads with compatibility tests.

## Migration Plan

No data migration or new dependency is required. Implement the contract behind existing persistence boundaries, keep legacy fields readable, run focused synthetic/local tests, then perform a separate real-data probe only after the implementation and verification evidence is accepted. Rollback is a code revision rollback; persisted records remain readable because existing stable fields are retained.

## Open Questions

None that change the contract or task breakdown. The enrichment and shortlist uncertainty findings remain deferred and require separate focused reproduction before specification.
