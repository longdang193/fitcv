# Inspection & Debugging — History

## Changelog

### 2.0.0 — active

- Inspection surfaces now expose manual staged-run checkpoint state, including execution mode, checkpoint status, completed stages, and next stage
- Paused manual runs can inspect stage artifacts before continuation, and stage-artifact downloads remain available while a run is `awaiting_continue`
- Run detail and runs list now expose `Run Next Stage` actions for paused manual runs without introducing a separate debug viewer

### 1.9.2 — active

- Run-scoped enriched-job reads now deserialize canonical skill entity JSON companions and mapping suggestions for inspection/debug surfaces
- Enriched exports can carry raw-plus-canonical enrich context without forcing downstream readers to reinterpret those JSON blobs manually

### 1.9.1 — active

- Newly generated stage-transition artifacts now report `schema_version: "stage_transition_artifacts_v3"` so the six-feature ranking artifact shape is version-detectable
- Shortlist stage artifacts now separate raw vector row counts from unique-job raw-hit counts
- Shortlist debug payloads now describe observed raw-hit status using `not_returned_in_raw_hits` wording instead of implying stronger retrieval causes
- Raw retrieval anomalies that fail to rejoin `passed_jobs` are exposed diagnostically instead of silently entering the scoring shortlist

### 1.9.0 — active

- Shortlist stage artifacts now separate raw vector row counts from unique-job raw-hit counts
- Shortlist debug payloads now describe observed raw-hit status using `not_returned_in_raw_hits` wording instead of implying stronger retrieval causes
- Raw retrieval anomalies that fail to rejoin `passed_jobs` are exposed diagnostically instead of silently entering the scoring shortlist

### 1.8.1 — active

- Newly generated stage-transition artifacts now report `schema_version: "stage_transition_artifacts_v3"` so the six-feature ranking artifact shape is version-detectable
- Specs/plans: see `refs` in the feature contract

### 1.8.0 — active

- Ranking-stage artifacts now expose the full six-feature ranking contract used by a run, including configured weights, missing-value defaults, zero-weight features, and contributing features
- Ranking `inputs_sample`, `outputs_sample`, and scored-not-ranked samples now carry all six ranking feature values plus `final_score`

### 1.7.0 — active

- Stage-transition artifacts now carry bounded input, output, and changed-state samples for each stage instead of summary-only handoff counts
- The richer artifact contract makes stage downloads more useful for debugging failed retrieval, ranking, filtering, and CV-generation transitions
- This rollout keeps `settings-used.json` separate and does not introduce `run-bundle.json`

### 1.6.0 — active

- Added a dedicated run-scoped `settings-used.json` download so effective run settings can be inspected without opening stage artifacts or internal snapshots
- Event timeline rows for recognized stage-boundary events can now download the corresponding stage-slice JSON directly
- This rollout stays download-only and does not add an in-page artifact viewer

### 1.5.0 — active

- Added a run-scoped stage-transition artifact download so major pipeline handoffs can be inspected without reconstructing them from later exports
- Inspection surfaces now explicitly distinguish stage-transition artifacts from the heavier CV-generation debug snapshot
- This rollout keeps the stage-transition artifact bounded and summary-first rather than duplicating full downstream payloads

### 1.4.1 — active

- Adopted the stage-aware doc system by mapping `inspection_debugging` to `primary_stage: cv_generation`
- Declared bounded stage participation across `enrich`, `rule_filter`, `shortlist`, `ranking`, and `cv_generation`
- This was a documentation-structure adoption only; no inspection runtime behavior changed by itself

### 1.4.0 — active

- Run detail can now show explicit decision-chain detail from run-results export instead of only a generic outcome badge
- CV-generation debug snapshots now separate authoritative ranking fit from secondary gap explanation so the decision path is easier to inspect

### 1.3.0 — active

- Run detail now exposes an admin-only `Download CV Debug JSON` action when a run-scoped CV-generation debug snapshot exists
- Completed runs can persist a bounded run-scoped CV-generation debug snapshot with live Layer 4 artifacts and failure-path details

### 1.2.0 — active

- Run detail results tab and large table usability improvements
- Specs/plans: see `refs` in the feature contract

### 1.1.0 — active

- Run input snapshot consistency
- Specs/plans: see `refs` in the feature contract

### 1.0.0 — active

- Initial feature: 3-tab inspection interface on run detail page
- Specs/plans: see `refs` in the feature contract

## Post-Execution Review

> Fill after status transitions to `active`.
