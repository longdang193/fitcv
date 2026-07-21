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
- Pending allows Approve, Decline, and Clear. Approved allows Clear only. Declined allows Approve and Clear.
- Approve adds a candidate mapping and refreshes configuration validation; Decline changes review status; Clear removes queue rows without reversing active mappings.
- Review filters and selection controls reuse shared panel spacing and table behavior. Conflict validation stays in the editor and suggestion details, not the review table.
- Suggestion Overview owns source-run metadata. Evidence contains only signals supporting the proposed canonical.
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
