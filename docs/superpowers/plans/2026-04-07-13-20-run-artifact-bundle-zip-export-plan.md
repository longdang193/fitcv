---
feature_type: modify
feature_name: inspection_debugging
status: draft
summary: "Implement a run-level zip bundle export that packages all currently available artifacts using the existing artifact gating rules."
---

# Run Artifact Bundle Zip Export Plan

## Outcome

Add a `Download All Artifacts (.zip)` action on run detail that bundles all currently available artifacts for a run without introducing a second artifact contract.

## Tasks

1. Add shared bundle-selection helpers

- Reuse the existing run export availability and stage-gating rules.
- Produce one canonical list of bundle-eligible artifacts for a run.
- Keep `mapping-suggestions.json` enrich-gated.

2. Add a run-level zip export endpoint

- Create a control-plane route that returns a zip download for a run.
- Assemble the zip only from currently available persisted artifacts.
- Do not recompute pipeline outputs during export.

3. Add `manifest.json` generation

- Include bundle metadata such as run id, run status, included files, and missing files.
- Keep the manifest descriptive and lightweight.

4. Add the run-detail export action

- Add `Download All Artifacts (.zip)` to `Run Exports`.
- Place it ahead of the individual artifact links.
- Add compact helper copy clarifying that the zip includes currently available artifacts only.

5. Preserve existing individual downloads

- Keep all current artifact links and endpoints intact.
- Ensure the new bundle action does not change existing availability behavior.

6. Add focused regression coverage

- Test a partial staged run bundle.
- Test a succeeded run bundle.
- Test that enrich-gated artifacts are excluded before `enrich`.
- Test that the endpoint returns a user-facing error when no artifacts are available.

7. Sync docs

- Update `docs/features/inspection_debugging/inspection_debugging.yaml`
- Update `docs/features/inspection_debugging/history.md`
- Update `docs/features/trigger_run_management/trigger_run_management.yaml`
- Update `docs/features/trigger_run_management/history.md`

## Verification

- Run focused control-plane tests covering the new zip endpoint and run-detail export surface.
- Verify the zip contents and `manifest.json` structure in tests.
- Run `py_compile` for touched Python modules.

## Completion criteria

- Run detail exposes `Download All Artifacts (.zip)`.
- The zip contains all and only available artifacts for the run.
- Partial runs can download partial bundles.
- Individual artifact downloads still behave exactly as before.
