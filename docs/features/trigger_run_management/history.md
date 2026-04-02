# Trigger & Run Management — History

## Changelog

### 2.2.0 — active

- Admin settings now expose `rule_filter.selected_filters` so deterministic post-enrichment checks can be configured as blocking versus mark-only
- The default blocking set remains seniority, location type, contract type, and experience level; `must_have_skill_missing` and `domain_not_preferred` now default to mark-only
- This rollout keeps rule ownership in `rule_filter` and does not move those checks into ranking

### 2.1.0 — active

- Manual staged runs paused after `enrich` can now upload a run-scoped synonym-overlay YAML before continuing into `rule_filter`
- Uploaded overlays are persisted on the run's effective settings snapshot and apply only to that run's downstream stages
- This rollout keeps the trusted base `config/skill_synonyms.yaml` unchanged and does not add a full synonym editor

### 2.0.0 — active

- Added a staged/manual run mode that pauses after each major stage and persists checkpoint metadata plus a serialized checkpoint payload for continuation
- Manual runs can now resume from `next_stage` via explicit `Run Next Stage` actions instead of restarting the full pipeline by default
- Run detail and runs-list surfaces now distinguish automatic vs manual execution while preserving the existing one-click `run_all` flow

### 1.9.0 — active

- Run detail stage-artifact downloads now carry richer per-stage input, output, and changed-state samples instead of summary-only stage blocks
- Timeline-linked stage-slice JSON downloads remain download-first while becoming more useful for debugging stage transitions
- This rollout preserves the existing artifact surfaces and does not add a unified run-bundle export

### 1.8.0 — active

- Run detail can now download a dedicated `settings-used.json` snapshot for succeeded runs when available
- Timeline rows for recognized stage-boundary events now expose per-stage JSON downloads derived from the persisted run-scoped stage-artifacts snapshot
- This rollout keeps the run detail strictly download-first and does not add an artifact viewer

### 1.7.0 — active

- Run detail can now download a run-scoped `stage-artifacts.json` snapshot for succeeded runs when available
- Stage-transition artifacts now expose bounded per-stage handoff summaries alongside the existing results export and CV debug download surfaces
- This rollout keeps stage-transition artifacts as an inspection/debug surface, not a replacement for the results export

### 1.6.1 — active

- Adopted the stage-aware doc system by mapping `trigger_run_management` to `primary_stage: normalize`
- Declared bounded stage participation across `normalize`, `enrich`, `rule_filter`, and `shortlist`
- This was a documentation-structure adoption only; no run-trigger runtime behavior changed by itself

### 1.6.0 — active

- Run-results export now includes an explicit decision chain per job so shortlist path, primary fit authority, CV attempt/skip, and validation outcome are visible without inference
- Ranked jobs now use reranker fit as the sole post-filter authority for CV eligibility instead of reconciling against a competing gap-fit decision
- Run detail pipeline outcomes now surface decision-chain detail alongside the existing status badge

### 1.5.3 — active
- Top-level run-results `shortlist_debug` now distinguishes raw vector-search hits from the later scoring shortlist, including explicit backfill counts and backfilled job URLs when retrieval misses passed jobs
- Layer 3 shortlist event messaging now reports raw vector hits separately from scoring-shortlist size when backfill occurs
- Legacy note: this release predated the later decision-consistency cleanup that made reranker fit the sole post-filter authority

### 1.5.2 — active

- Run-results export now includes shortlist debug context, including a per-row `shortlist_debug` block for passed jobs and a top-level shortlist summary with the candidate query text and shortlist counts
- `not_shortlisted` rows now explain that the job URL was not returned by vector search instead of only showing null scores
- Layer 4 gap matching now handles long requirement phrases more usefully and excludes obviously non-skill requirements from the fit-ratio denominator

### 1.5.1 — active

- Ranked jobs skipped by the Layer 4 fit gate now surface as `ranked_skipped_fit_gate` instead of being folded into the generic `ranked_no_cv` bucket
- Layer 4 fit-gated ranked jobs now emit CV-generation debug records, so run-scoped CV debug snapshots stay complete instead of dropping those jobs entirely
- Run detail pipeline outcome labels now show `Ranked, skipped by fit gate` for that status

### 1.5.0 — active

- Run-results export now distinguishes passed non-CV jobs as `not_shortlisted`, `shortlisted_not_scored`, or `scored_not_ranked` instead of collapsing them into one vague status
- Run detail now shows a compact `Pipeline Outcome` label for enriched jobs so “passed filter” is no longer confused with “CV should have been generated”
- Layer 4 CV generation now rebuilds ranked jobs from enriched context before gap analysis, so debug snapshots and gap summaries retain JD fields like title and required skills

### 1.4.0 — active

- Run detail now exposes a separate `Download CV Debug JSON` action for succeeded runs when a run-scoped CV-generation debug snapshot is available

### 1.3.0 — active

- Run-results export now carries structured CV data and CV generation metadata when present
- Control-plane CV read paths can fetch structured CV fields from `cv_versions` while keeping markdown downloads unchanged

### 1.2.0 — active

- Run detail page exposes `Download Results JSON` for succeeded runs with an export snapshot
- Run-complete worker persists an immutable run-results export snapshot on `pipeline_runs`
- Export payload includes ordered jobs, enrichments, statuses, scores, and inline CV markdown when present

### 1.1.0 — active

- CV results banner on run detail page
- CV downloads for generated CVs
- Specs/plans: see `refs` in the feature contract

### 1.0.0 — active

- Initial feature: runs list page with status badges and three trigger modes
- Specs/plans: see `refs` in the feature contract

## Post-Execution Review

> Fill after status transitions to `active`.
