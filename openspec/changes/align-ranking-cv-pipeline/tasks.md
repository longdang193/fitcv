# Tasks

## 1. Define contracts and compatibility boundaries

- [x] 1.1 Add versioned Stage 6 to Stage 7 handoff fields for job identity, JD reference, qualifiers, evidence IDs, gaps, score/status, profile revision, contract versions, fingerprints, and provenance; verify serialization and deserialization tests cover complete, missing, and legacy envelopes.
- [x] 1.2 Define separate ranking, review, PDF, persistence, and submission state dimensions in the existing late-stage contract; verify legacy status projections remain readable and technical PDF failure cannot map to review-required success.
- [x] 1.3 Preserve historical personalized fields as read-only compatibility data and define the new-run field emission policy; verify old artifacts load without being rewritten and new artifacts do not advertise personalized ordering.

## 2. Align Stage 6 ranking

- [x] 2.1 Remove new-run preference activation from the ranking orchestration and make valid finite `ai_score` the only ordering authority; verify a nonzero preference vector cannot change Final Top 15 order.
- [x] 2.2 Update ranking contracts and projections so `baseline_fit = ai_score`, `baseline_rank` is the canonical final order, and deterministic fingerprint/URL tie-breaking is preserved; verify valid score ordering, ties, and Top 15 capacity.
- [x] 2.3 Keep invalid, non-finite, out-of-range, and unscored AI results status-only without zero fallback; verify invalid rows are inspectable and never rank ahead of valid rows.
- [x] 2.4 Preserve validated shortlist evidence, qualifiers, gaps, S/P/E/U diagnostics, and provenance while building the bounded 12,000-character request; verify evidence outside the compact request remains available through canonical source references.
- [x] 2.5 Persist and expose auditable promotion overrides with operator identity, reason, strategy/version, evidence-gate state, timestamp, rollback target, and readable record; verify blocked gates remain blocked in the audit output.

## 3. Implement the unified Stage 7 workflow

- [x] 3.1 Change CV analysis for Final Top 15 jobs to produce evidence plans, truthful gaps, and generation-ready outcomes instead of applying an unintended secondary fit rejection; verify unresolved professional or qualification evidence yields omissions/gaps rather than skipped CV generation.
- [x] 3.2 Make the committed Stage 7 policy select the fixed myCVs template for new runs and keep legacy rendering only for historical compatibility; verify configuration, prompt/schema, and renderer tests agree on the canonical template.
- [x] 3.3 Add an explicit ADJUST step for ATS terminology, achievements, impact, clarity, and approximately 580 words; verify a factually valid but generic draft receives a targeted adjustment and re-enters all validation checks.
- [x] 3.4 Implement unified validation for factual provenance, exact myCVs Markdown schema, and ATS/recruiter quality with facts and schema as hard constraints; verify unsupported claims or schema violations prevent acceptance even when keyword quality improves.
- [x] 3.5 Add bounded targeted retries and a safe grounded fallback that preserves unresolved gaps; verify retry exhaustion still produces the safest content and records outstanding concerns.
- [x] 3.6 Separate optional review, mandatory review, validation failure, generation failure, and PDF failure while preserving a PDF path for review-required content; verify review-required content is not discarded before rendering.

## 4. Render, persist, and gate submission

- [x] 4.1 Validate exact myCVs Markdown schema, links, checksums, and page-fit inputs before conversion; verify invalid render proofs block PDF success and expose the owning validation error.
- [x] 4.2 Integrate the existing myCVs converter for both optional-review and mandatory-review branches; verify both branches persist a verified PDF and no replacement converter is introduced.
- [x] 4.3 Add bounded technical recovery for converter failure and persist an explicit technical failure state when recovery is exhausted; verify converter failure is not represented as review-required success.
- [x] 4.4 Persist PDF metadata, review metadata, checksums, and submission permission independently; verify a persisted mandatory-review PDF remains inspectable while submission is blocked until review completion.
- [x] 4.5 Update checkpoint/resume and operator projections to preserve the new state dimensions across fresh and reused runs; verify same-input reuse and legacy checkpoint reads do not silently change ranking or review meaning.

## 5. Documentation and integration verification

- [x] 5.1 Update pipeline/configuration/operator documentation with the Stage 6 AI-only order, handoff envelope, Stage 7 fixed order, review/PDF distinction, and submission gate; verify documented field names and statuses match the contract.
- [x] 5.2 Run focused ranking, evidence, analysis, generation, rendering, persistence, pipeline, and resume tests; verify the new contract scenarios pass without modifying unrelated working-tree paths.
- [x] 5.3 Run the repository validation suite relevant to the changed modules and record failures as implementation issues or explicit environment limitations; verify no release-readiness benchmark or rollout decision is inferred from these behavior tests.

## Workflow follow-up

- Apply this change only after review of the planning artifacts.
- Keep release-readiness risk assessment, latency/cost gates, rollout approval, benchmark closure, and calibration evidence as a separate follow-up change.
- Archive this change only after implementation, focused verification, and documentation are complete.
