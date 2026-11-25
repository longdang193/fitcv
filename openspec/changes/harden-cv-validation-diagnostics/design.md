# Design

## Context

The current pipeline already has reusable policy and lifecycle primitives, but they are not one contract. `src/fitcv/section_policy.py` defines the myCVs order with Certifications before Skills, while `src/fitcv/validator.py` derives required headings by appending Skills before Certificates. `src/fitcv/cv_generator.py` serializes the structured model directly, so the mismatch is deterministic and independent of provider output.

Skill validation also has two authorities: structured skill items are preferred, but the validator can extract tokens from rendered Markdown when structured items are absent. Generation currently clears final structured and Markdown fields for `validation_failed`, and persistence accepts only a narrower set of review/PDF outcomes for retained artifacts. Reason normalization and generation-format classification inspect stage and message text, including warning text, which allows non-blocking length information to affect failure classification.

The existing Stage 6/7 change requires independent technical, review, PDF, persistence, and submission states and requires verified final PDF acceptance. This change preserves those contracts and adds the missing validation-draft and diagnostic behavior; it does not change the configured one-page/page-fit policy.

## Goals / Non-Goals

**Goals:**

- Make the current versioned myCVs policy the single source for section ordering across all projections.
- Preserve invalid but useful generated drafts in a visibly quarantined, non-submittable state.
- Make structured skill claims and provenance authoritative and make rendered Markdown a projection only.
- Introduce one typed diagnostic envelope that owns classification and stable reason propagation.
- Keep content, review, artifact/PDF, persistence, and submission outcomes independently inspectable.
- Retain legacy status/reason fields as deterministic compatibility projections during migration.

**Non-Goals:**

- Do not weaken factual validation, remove structural safeguards, or accept quarantined content.
- Do not change the existing one-page/page-fit acceptance policy or make a length warning a submission decision.
- Do not infer the reported run's Python cause, PDF page count, or persistence outcome without run artifacts.
- Do not redesign requirement-aware shortlisting, Stage 6 handoff admission, or the broader ranking model.
- Do not backfill or rewrite historical records merely to add new fields.

## Decisions

### 1. Reuse the existing section policy as the authority

Use the existing versioned myCVs section-order list and its key-to-display-name mapping for composition, serialization, required-heading derivation, and structural/PDF checks. The validator filters the same ordered list by meaningful content instead of constructing a separate order. This fixes the verified Certificates/Skills contradiction without removing order validation.

Alternative rejected: changing the serializer to match the validator only. That would leave other consumers free to drift and would preserve duplicate policy ownership.

### 2. Add a typed diagnostic envelope at the failure source

Each material outcome writes a versioned diagnostic record with at least `code`, `category`, `severity`, `blocking`, `retryable`, `source`, and structured `facts`. Known codes cover structural serialization, content/provenance, quality, renderer/PDF, provider, and persistence failures. Messages remain optional display text and are never used to select a code or state.

Downstream projections consume the code and state fields. Compatibility labels such as `post_validation_failed` and `manual_review_other` remain readable where required, but no new routing or persistence decision is made from their message text. Unknown failures use an explicit unclassified code rather than a guessed specific category.

Alternative rejected: a larger exception hierarchy. It would not solve persisted cross-process projections and would require every consumer to understand runtime types.

### 3. Store validation failures as quarantined drafts

When structured and rendered drafts exist after the bounded repair cycle, persist them in explicit quarantine payload fields alongside the validation snapshot, diagnostic list, input fingerprint, and trace reference. Mark the artifact state as `quarantined`, content validity as `invalid`, review as `not_approved`, and submission clearance as `blocked`. Do not populate accepted-output projections from the quarantine payload.

When no usable draft exists, persist only the failure scope and diagnostics. Existing `validation_failed` status remains the compatibility status; quarantine is an explicit artifact state, not a replacement status. Readers must distinguish a quarantined draft from an accepted or review-approved artifact.

Alternative rejected: retaining invalid data in `structured_cv_final`/`markdown_final`. Those fields already imply a final artifact to downstream readers and would make accidental submission or export more likely.

### 4. Remove rendered Markdown as a factual skill authority

The normalized structured skill set, canonical skill identity, and attached provenance/evidence references are the source of truth. Renderer checks may verify that Markdown faithfully represents the structured model, but a token found only in rendered text cannot create an unsupported skill claim. A projection mismatch is classified as a serialization/provenance diagnostic.

Legacy Markdown-only records remain readable but cannot authorize new factual reuse; they are marked provenance-unavailable and require recomputation or explicit review under the existing reuse rules.

Alternative rejected: keeping the Markdown fallback with more aliases. That would reduce some false negatives but leave projection formatting as a hidden factual authority.

### 5. Map independent states before legacy status

Persist and expose four decision dimensions: content validity, review state, artifact/PDF state, and submission clearance. Derive legacy status and reason fields from those dimensions plus the primary diagnostic code. The mapping must preserve existing behavior for accepted, review-required, PDF-failed, generation-failed, persistence-failed, and validation-failed readers while preventing one dimension from overwriting another.

A valid review-required artifact may retain Markdown/PDF; an invalid validation result may retain only a quarantine draft; a PDF failure does not turn valid content into invalid content. Final submission still requires the existing content, review, PDF, and page-fit gates.

### 6. Migrate by dual-read/dual-write, not by historical rewrite

New attempts write typed diagnostics and state dimensions together with existing projections. Readers first use the new fields and fall back to legacy status, validation snapshots, and error payloads for historical records. Legacy records are not silently reclassified or rewritten. After focused tests demonstrate parity, new consumers stop branching on message text.

## Risks / Trade-offs

- [Risk] Existing exports or UI code may assume `structured_cv_final` is the only draft field. -> Mitigation: add explicit quarantine projections, keep legacy fields readable, and test export/detail surfaces before switching consumers.
- [Risk] Removing rendered skill fallback may expose old records with incomplete provenance. -> Mitigation: mark them provenance-unavailable and require recomputation/review instead of accepting weaker evidence.
- [Risk] Diagnostic code coverage may be incomplete during migration. -> Mitigation: persist an explicit unclassified diagnostic with source/facts and flag the producer for follow-up; never guess from text.
- [Risk] Existing tests may encode the old Certificates/Skills order or non-persistable validation failure. -> Mitigation: update only tests that assert the corrected contract and retain compatibility assertions for historical status projections.
- [Risk] Quarantined artifacts increase storage and operator-visible records. -> Mitigation: reuse existing trace/fingerprint retention bounds and keep quarantine separate from accepted-result lists and submission exports.

## Migration Plan

1. Add the diagnostic and independent-state schema, keeping current status/reason projections available.
2. Make section-order derivation and serialization/validation round-trip from the existing section policy.
3. Change generation and persistence to write quarantine payloads for validation failures with usable drafts.
4. Switch skill validation to structured provenance and add projection-mismatch diagnostics for rendered output.
5. Replace downstream message/warning inference with diagnostic-code mapping and retain compatibility projections.
6. Run focused validator, renderer, generation-reason, persistence, pipeline-status, and Stage 6/7 tests, then the existing non-render suite. Run the existing targeted PDF acceptance unchanged.
7. Roll back consumers to legacy projections if required; the additive diagnostic/quarantine fields remain readable and do not authorize submission on their own.
