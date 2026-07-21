# Synonym Management Integration

Operation: central synonym editing, review, promotion, clearing, and backup workflows
Contract owner: global mappings in `config/taxonomy/skill_synonyms.yaml`, `config/taxonomy/domain_synonyms.yaml`, and `config/taxonomy/role_family_synonyms.yaml`; proposal lifecycle in `src/fitcv_cp/synonym_proposals.py`
Status: pending backend aggregation and draft-validation contract

## UI Behavior

- `#synonyms` owns shared Skills, Domain, and Role Family configuration; Pipeline Automation & Reuse links to this workspace.
- Editor is read-only until Edit list. Save validates flat `alias: canonical` syntax, empty values, conflicting targets, and canonical cycles.
- Invalid drafts remain visible but inactive. Pipeline keeps last valid compiled configuration; issue counts navigate to affected lines.
- Review entries use Pending, Approved, and Declined tabs. Legacy Deferred values normalize to Pending.
- When Auto-accept is off, every generated suggestion enters review as Pending.
- Approve adds the mapping to the shared synonym database. No separate Promote action or setting exists.
- Apply Approved Synonyms is the single pipeline-use gate for approved mappings in current and future runs.
- Reuse may cache equivalent synonym proposal analysis, but never copies review decisions between runs.
- Pending allows Approve, Decline, and Clear. Approved allows Clear only. Declined allows Approve and Clear.
- Approve adds a candidate mapping and refreshes configuration validation; Decline changes review status; Clear removes queue rows without reversing active mappings.
- Review filters and selection controls reuse shared panel spacing and table behavior. Conflict validation stays in the editor and suggestion details, not the review table.
- Suggestion Overview owns source-run metadata, and available Source Run IDs open Run Details. Evidence contains only signals supporting the proposed canonical.
- Synonym changes apply to future runs. Completed run outcomes retain their captured synonym revision.
- Processing Summary Log shows processed time, total, approved, declined, pending, and successfully added counts. Clear hides loaded entries locally without deleting canonical backend history.
- Backup files remain opaque backend artifacts. Production frontend uploads/downloads them without parsing or rewriting taxonomy files.

## Required Evidence

- Backend tests prove authorization, cross-run aggregation, Pending behavior, status transitions, queue clearing, and atomic promotion.
- Validation tests prove malformed syntax, empty canonicals, alias conflicts, and cycles cannot replace last valid compiled mappings.
- Backup tests prove server-side validation and no partial taxonomy replacement on failure.
- Frontend tests cover editor modes, search navigation, issue navigation, unsaved-change protection, batch actions, clearing, logs, empty/error states, and duplicate-submit prevention.
- Browser evidence confirms keyboard operation and supported light, dark, narrow, and zoomed layouts.

## Known Gaps

- Existing review approval is run-scoped (`approve_for_run_overlay`). Central Approve needs a backend operation combining review decision, candidate global promotion, validation, and atomic activation.
- Existing backend supports `defer`; central UI intentionally collapses Deferred into Pending. Backend contract must expose one canonical Pending state or map Deferred at boundary.
- Existing backend separates apply and promote flags. Integration must collapse them behind this UI contract or atomically map the single approved-synonym policy without exposing divergent states.

# Candidate Profile and Run Integration

Operation: list eligible Candidate Profiles and trigger reproducible runs
Contract owner: pending Candidate Profile resource, Run trigger operation, Pipeline Settings revision, and Synonym revision
Status: pending backend persistence, authorization, and immutable revision contract

## UI Behavior

- Trigger Run refreshes Candidate Profiles when the dialog opens and shows only authorized, Active, Succeeded profiles.
- Option text contains Profile Name and Profile ID for recognition. Profile ID remains the submitted identity.
- Empty, loading, retrieval-error, and stale-selection states must preserve safe form input and provide a path to Candidate Profiles.
- Run Details links to its Candidate Profile and shows profile identity, lifecycle state, and captured-configuration intent.
- Candidate Profile Details lists related Run IDs. Archived profiles remain available to historical runs but cannot start new runs.
- Pipeline Settings and Synonym changes apply to future runs. Completed runs continue using revisions captured at trigger time.

## Required Evidence

- Backend list authorization prevents profiles from another user or workspace appearing in the selector.
- Trigger accepts `profile_id`; backend validates authorization, Active state, and Succeeded status before creating the run.
- Run creation atomically resolves and stores `profile_revision_id`, `pipeline_config_revision_id`, and `synonym_revision_id`.
- Stale or newly unavailable profile selection returns a conflict or validation response; frontend refreshes options without duplicate submission.
- Archive prevents new selection without breaking historical resolution. Delete is rejected while any run references the profile.
- Frontend tests cover selector refresh, eligible filtering, empty and error states, stale selection, linked references, archived historical display, and duplicate-submit prevention.

## Known Gaps

- Prototype uses local state and descriptive snapshot labels. Backend revision identifiers and retrieval states remain pending.

# Bookmark Management Integration

Operation: central bookmark listing, removal, and selected filtered export
Contract owner: pending backend bookmark resource and export operation
Status: pending backend persistence and authorization contract

## UI Behavior

- Bookmark identity is Run ID plus Job ID. Pipeline stage is derived view state, not stored bookmark state.
- Bookmarks aggregates active and archived runs and reuses Run Details pipeline outcomes, job table, pagination, and Run Details navigation.
- Bookmark rows expose whether their source run is Active or Archived.
- Selection is pruned to current stage and search. Export requires selection and exports only selected rows in the current stage and filters.
- Run Details Export uses the same selection intersection contract: selected jobs ∩ current stage ∩ result filter ∩ search.
- Removing bookmarks never deletes jobs or runs. Deleting an archived run removes its orphaned bookmark records.
- The same job may appear once per run because outcomes and evidence are run-specific.

## Required Evidence

- Backend authorization scopes bookmark list, create, remove, and export to the current user.
- Backend validates selected Run ID and Job ID pairs and recomputes filtered export rows server-side.
- Frontend tests cover persistence, duplicate Run ID and Job ID identity, stage and search pruning, batch removal, export summaries, empty states, and archived-run bookmarks.
- Browser evidence confirms keyboard operation and supported light, dark, narrow, and zoomed layouts.
