# CV System — History

## Changelog

### 1.11.0 — active

- Stage-transition artifacts now preserve bounded input, output, and changed-state context for `normalize`, `enrich`, `rule_filter`, `shortlist`, `ranking`, and `cv_generation`
- `cv_generation` remains the richest stage block, but this rollout keeps the separate `cv-debug.json` surface for compatibility
- The settings snapshot remains separate and is still not duplicated wholesale into every stage block

### 1.10.0 — active

- Effective run settings can now be exported once as a dedicated `settings-used.json` artifact instead of being duplicated into every stage block
- Stage-boundary artifact inspection can now be downloaded as per-stage JSON slices without changing the runtime stage contracts
- This rollout adds inspection surfaces only; it does not change ranking, CV generation, or validation authority

### 1.9.0 — active

- Run summaries now emit bounded stage-transition artifact blocks for `normalize`, `enrich`, `rule_filter`, `shortlist`, `ranking`, and `cv_generation`
- The new stage-transition artifact reuses existing runtime seams and keeps `cv_generation` summarized rather than duplicating the full CV debug payload
- This rollout adds stage-boundary inspection only; it does not change the authoritative CV generation or validation decisions

### 1.8.1 — active

- Adopted the stage-aware doc system by mapping `cv_system` to `primary_stage: cv_generation`
- Declared bounded stage participation across `enrich`, `ranking`, and `cv_generation`
- This was a documentation-structure adoption only; no runtime CV behavior changed by itself

### 1.8.0 — active

- Phase 1 ranking now uses only the runtime-computed `ai_score` and `vector_similarity` contract instead of implying inactive weighted features
- Reranker fit is now the sole post-filter authority for ranking-time fit and CV-generation eligibility; gap analysis remains explanatory support only
- Structured normalization and markdown validation now share one config-driven required-section contract, with bounded completeness checks for enabled required sections

### 1.7.0 — active

- Ranked jobs can now capture a bounded live CV-generation debug record containing initial structured output, initial validation state, repair metadata, and final accepted artifact when available
- Persistence failures during CV version storage can now be inspected through a run-scoped debug snapshot instead of relying only on logs

### 1.6.0 — active

- Experience composition now uses JD-sensitive role-level bullet selection instead of reusing the same narrow slice across jobs
- Prompt construction can attach bounded secondary supporting evidence to grouped role blocks, with achievements preferred and support kept explicitly secondary
- Experience prompt semantics now ask for grounded re-emphasis and synthesis instead of mere bullet restatement

### 1.5.0 — active

- Project evidence is now preserved as grouped `project_entry` blocks instead of only thin `name + skills` snippets
- Project prompt construction now carries richer grounded context such as duration, business value, selected stack lines, and selected highlights when present
- Sparse projects still degrade gracefully without invented impact language
- Thin project evidence remains fallback/supporting only rather than the primary Projects construction path

### 1.4.0 — active

- CV evidence retrieval is now section-aware rather than one flat mixed top-k pool
- Experience evidence is preserved as grouped role/company/date entries with bounded bullets
- Prompt construction now passes grouped work-history blocks into CV generation instead of flattening experience back into loose snippets

### 1.3.0 — active

- CV generation now creates a schema-versioned structured CV document before rendering markdown
- `cv_versions` now persists structured CV JSON plus generation metadata alongside markdown
- Run-scoped exports can include structured CV content and CV generation metadata for new rows

### 1.2.0 — active

- Admin-editable CV generation settings via settings UI
- Specs/plans: see `refs` in the feature contract

### 1.1.0 — active

- Preset-based CV composition configuration
- Specs/plans: see `refs` in the feature contract

### 1.0.0 — active

- Initial feature: preset registry and CV composition model
- Specs/plans: see `refs` in the feature contract

## Post-Execution Review

> Fill after status transitions to `active`.
