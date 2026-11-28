# Tasks

## 1. Boundary investigation

- [ ] 1.1 Reproduce one representative non-persistable CV result with local or synthetic inputs and record the generation, validation, conversion, and persistence boundaries covered.
- [ ] 1.2 Identify the first authoritative rejecting boundary and map it to an existing typed diagnostic, verifying that later failures do not replace the primary outcome.

## 2. Narrow correction and evidence

- [ ] 2.1 Add only the smallest code or contract correction required by the demonstrated boundary, preserving existing acceptance and privacy gates; verify the representative path produces either a persisted valid artifact or an accurately typed rejection.
- [ ] 2.2 Add focused regression coverage for the demonstrated outcome and assert that persisted diagnostics are bounded and exclude prompts, profile/CV content, credentials, provider payloads, and unbounded exception text.
- [ ] 2.3 Run the focused tests and strict OpenSpec validation; record any inability to reproduce without starting a broad real-data rerun.

## Workflow follow-up

- Treat a broader real-data probe as a separate authorized operation after the representative evidence is accepted.
- Archive this change only after the investigation evidence and focused regression are reviewed.
