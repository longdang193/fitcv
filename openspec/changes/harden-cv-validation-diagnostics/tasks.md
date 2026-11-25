# Tasks

## 1. Canonical rendering and validation order

- [ ] 1.1 Route myCVs required-section derivation and structural order checks through the existing versioned section policy, preserving the Certificates-before-Skills order and verifying the generated Markdown round-trip in `tests/test_cv_generator.py` and `tests/test_validator.py`.
- [ ] 1.2 Update renderer/PDF acceptance fixtures that encode heading order and verify `tests/test_cv_render_acceptance.py` still passes without removing order validation.

## 2. Structured factual authority

- [ ] 2.1 Define the structured skill claim/provenance projection used by validation and remove rendered Markdown as an independent skill authority; verify supported, canonicalized, and projection-mismatch cases in `tests/test_validator.py` and `tests/test_agentic_cv_generation.py`.
- [ ] 2.2 Mark legacy Markdown-only skill records as provenance-unavailable for new reuse while keeping them readable; verify legacy compatibility and recomputation behavior in validator, reuse, and pipeline tests.

## 3. Typed diagnostics and independent states

- [ ] 3.1 Add the versioned typed diagnostic envelope and stable codes for structural, content/provenance, quality, renderer/PDF, provider, persistence, and unclassified outcomes; verify code-driven classification in `tests/test_cv_generation_reason_mapping.py` and contract tests.
- [ ] 3.2 Replace warning/message substring branches in generation-format and review-reason mapping with diagnostic-code and structured-fact branches, including a non-blocking length/page-fit warning case; verify no message mutation changes the classification.
- [ ] 3.3 Persist and project independent content-validity, review, artifact/PDF, and submission-clearance fields while retaining legacy statuses; verify accepted, review-required, validation-failed, PDF-failed, and persistence-failed projections in `tests/test_pipeline.py`, `tests/test_pipeline_outcome_fact.py`, and `tests/test_stage6_stage7_contracts.py`.
- [ ] 3.4 Document the new diagnostic and state contract in `docs/pipeline.md`, `docs/observability.md`, and any maintained API/configuration contract that exposes CV statuses; verify examples use emitted codes and fields.

## 4. Quarantined validation drafts

- [ ] 4.1 Preserve usable structured and rendered drafts, validation snapshots, fingerprints, and diagnostics in explicit quarantine fields after `validation_failed`; verify drafts are readable but excluded from accepted-output and submission projections.
- [ ] 4.2 Persist validation failures without usable drafts as diagnostic-only failures and verify retryability, terminality, and scope remain distinct from quarantined artifacts.
- [ ] 4.3 Add persistence, export, reload, and operator-detail coverage for quarantined drafts without rewriting historical records; verify `tests/test_persistence_contract.py`, `tests/test_pipeline.py`, and relevant `tests/test_fitcv_cp/` contract tests.

## 5. Cross-stage verification

- [ ] 5.1 Run focused validator, generator, renderer, reason-mapping, persistence, pipeline-status, and Stage 6/7 tests and verify the corrected order, preserved quarantine, structured skill authority, and typed diagnostics together.
- [ ] 5.2 Run the existing non-render suite and targeted PDF acceptance, recording any unrelated baseline failures without treating browser evidence as backend proof.
- [ ] 5.3 Run `openspec validate "harden-cv-validation-diagnostics" --type change --strict` and confirm the final change status reports every required artifact complete.

## Workflow follow-up

- Archive the change only after implementation and focused/non-render/PDF acceptance evidence are complete.
- Sync the accepted capability delta into maintained `openspec/specs/` during archive.
