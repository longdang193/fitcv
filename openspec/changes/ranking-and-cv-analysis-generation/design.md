# Design

## Context

See `proposal.md` and the two capability specs for the behavioral contract. The current pipeline already has stage checkpoints, candidate evidence projections, ranking orchestration, CV analysis/generation modules, a native PDF path, and persisted artifacts. `src/fitcv/ranking.py` also exposes legacy personalized rank/residual fields; those fields must remain readable without remaining authoritative. `config/policy/cv.yaml` currently selects `europass`, while `src/fitcv/cv_presets.py` and `src/fitcv/cv_generator.py` own the current preset and PDF boundaries.

The FigJam flow places Ranking before the final Top 15 CV handoff. Ranking input is bounded by the existing 12,000-character contract. CV generation then performs evidence planning, fixed-template creation, initial ATS/achievement/impact optimization, unified validation, a bounded correction/revalidation loop, deterministic `mycvs_v1` Markdown rendering, mandatory PDF conversion, one-page render acceptance, and independent review/PDF outcomes.

## Goals / Non-Goals

**Goals:**

- Make new ranking decisions and their handoff versioned, reproducible, and evidence-backed.
- Reuse existing evidence, stage, checkpoint, and persistence boundaries.
- Add deterministic `mycvs_v1` rendering/validation without making converter details implicit.
- Preserve the existing one-page render acceptance and make submission clearance explicit.
- Preserve historical artifacts and a rollback-safe migration path.

**Non-Goals:**

- Rewriting profile ingestion, shortlist admission, or downstream fit truth.
- Adding a new model provider, search service, database, or general-purpose workflow engine.
- Deleting or backfilling historic personalized ranking or Europass artifacts.
- Allowing a weighted mega-score to replace the documented core/Pareto policy.

## Decisions

### 1. Keep ranking authority at one boundary

The ranking stage writes one versioned decision envelope. New consumers read the authoritative AI compatibility score and explicit score status from that envelope; historic personalized fields are compatibility data only.

**Alternative rejected:** removing legacy fields immediately, because historic operator views and persisted artifacts depend on them.

### 2. Use explicit result states instead of score coercion

Missing, invalid, and retryable evaluations remain typed outcomes. The ranking adapter must not convert them to `0.0`, because that conflates technical failure, uncertainty, and confirmed incompatibility.

**Alternative rejected:** zero-filling invalid scores for simpler sorting; it damages auditability and hides retryable failures.

### 3. Make the ranking-to-CV handoff immutable and provenance-rich

Persist a handoff object containing job qualifiers, baseline ranking data, evidence IDs, gaps, profile revision, contract versions, and a fingerprint. CV analysis consumes this object rather than reconstructing ranking context from mutable source tables.

**Alternative rejected:** passing only job ID and score; it cannot reproduce the exact decision or explain qualifier-sensitive CV changes.

### 4. Keep CV quality dimensions separate

Analysis, generation, review, PDF, and submission clearance are separate state transitions. Hard factual/provenance/schema/template checks and one-page render acceptance gate completion; ATS/recruiter quality is an optimization signal unless policy marks it material. Soft factual concerns may produce `review: required` and still permit conversion; hard validation failures prevent conversion.

**Alternative rejected:** one combined `cv_status`; it cannot represent a valid Markdown artifact with a failed converter or a review-required CV whose PDF was successfully generated.

### 5. Treat `myCVs` conversion as an external, pinned boundary

Render and validate exact `mycvs_v1` Markdown as defined by `schemas/mycvs_v1.md` before conversion. Record converter revision, stylesheet/template revision, input checksum, and conditional output checksum. Do not promote the path until those inputs are pinned and reproducible.

**Alternative rejected:** silently using the current external converter; it makes PDFs non-reproducible and prevents trustworthy release evidence.

### 6. Roll out additively

Read paths accept both historic and new artifact shapes. New writes use the versioned contract behind an explicit strategy/configuration gate. Resume uses the persisted strategy and contract versions rather than current defaults. Rollback changes the active strategy, not historic artifacts.

**Alternative rejected:** destructive migration or blanket rewrite of old artifacts.

## Risks / Trade-offs

- [Legacy readers depend on personalized fields] → Keep fields and label them historic; add compatibility tests before changing readers.
- [Non-deterministic model output] → Persist model/provider/settings, prompt/template revision, normalized inputs, timestamps, and final fingerprints; treat exact replay as an evaluation gate.
- [Converter drift or unavailable external tooling] → Pin revision/template/checksums and keep the existing safe PDF path until validated.
- [Review-required output may be mistaken for success] → Store independent review, PDF, and submission-clearance states; block submission until review is explicitly cleared.
- [One correction pass may leave quality gaps] → Preserve unresolved concerns and surface them for operator review rather than adding unbounded retries.

## Migration Plan

1. Add the two capability contracts and compatibility readers without changing the current production default.
2. Implement ranking decision envelopes and the immutable CV handoff behind a versioned strategy.
3. Add `mycvs_v1` rendering/validation and converter provenance while retaining the current safe preset/path.
4. Run shadow/replay and representative real-file probes; compare deterministic outputs and failure states.
5. Pin the converter commit/template/checksum policy and obtain release evidence.
6. Enable the new strategy only after all promotion gates pass; otherwise retain the legacy strategy and record the blocker.

## Open Questions

- Which exact external `myCVs` converter commit and stylesheet/template revision are release-approved?
- Which existing persistence table/artifact is the authoritative owner for the new handoff fingerprint?
