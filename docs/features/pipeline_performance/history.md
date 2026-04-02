# Pipeline Performance — History

## Changelog

### 1.4.0 — active

- Enrich now computes a stable raw-job fingerprint from normalized pre-enrichment inputs and can reuse shared `structured_jobs` rows when the fingerprint matches
- Reuse is additionally gated by an enrich-contract fingerprint so prompt, model, schema, or post-processing drift invalidates cached enrich output automatically
- Enrich-stage artifacts and run-scoped enriched exports now expose fresh-vs-reused provenance plus raw-job and enrich-contract fingerprint fields for debugging

### 1.3.0 — active

- Enrich extraction prompt text is now loaded from a centralized prompt registry instead of a large inline builder string
- Runtime config validates the effective enrich prompt ID and exposes prompt runtime metadata for downstream inspection
- Enrich-stage inspection can report prompt provenance without changing stage business logic or response-schema ownership

### 1.2.0 — active

- Enrich now emits raw-plus-canonical companions for repeatedly interpreted semantic fields
- Required/preferred skills now include canonical companion lists plus entity payloads
- Run-scoped enriched rows can carry reviewable mapping suggestions without mutating the trusted synonym map

### 1.1.0 — active

- Gemini structured output with Pydantic fallback
- Specs/plans: see `refs` in the feature contract

### 1.0.0 — active

- Initial feature: pre-enrichment global job filters
- Specs/plans: see `refs` in the feature contract

## Post-Execution Review

> Fill after status transitions to `active`.
