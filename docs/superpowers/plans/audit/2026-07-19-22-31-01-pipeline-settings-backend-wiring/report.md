# Pipeline Settings Backend Wiring Audit

## 1. Current situation

- **Repository:** `JOB-PROJECT`
- **Branch / commit:** `main` at `a0f485de` (`Refine pipeline settings prototype`)
- **Approved UI source of truth:** `docs/fitcv-settings-ui-prototype.html`
- **Audited surface:** 42 prototype `SettingsRow` instances and every field inside managed `SettingsDialog` transactions.
- **Backend owners:** `src/fitcv_cp/settings_schema.py`, `src/fitcv_cp/settings_store.py`, `src/fitcv_cp/app.py`, baseline YAML under `config/`, and stage consumers under `src/fitcv/`.
- **Status:** unresolved integration gap. Prototype works as a local mock, but no prototype control connects to backend settings.
- **Constraint:** audit only. No production wiring or backend behavior changed.

## 2. Core problem

Expected: every prototype setting loads its canonical backend value, saves through the correct persistence boundary, restores correctly, and changes the owning processing stage.

Actual: prototype stores every editable value in browser `localStorage` under `fitcv-pipeline-settings-prototype-v4`. It performs no HTTP request and never reads `GET /settings`. Direct controls save local state on change; managed dialogs save local transaction objects. Cancel correctly discards dialog drafts, but only inside the mock.

Impact:

- All 42 rows are **UI-only** from production perspective.
- Active backend values do not load into prototype.
- Prototype defaults drift from canonical runtime defaults.
- Some prototype controls have no backend field.
- Some removed settings remain active in backend.
- Immediate single-key persistence is unsafe for cross-field invariants unless backend validates full effective state.

Severity: **High** for integration readiness.

## 3. Evidence and reproduction

### 3.1 Prototype persistence boundary

- `docs/fitcv-settings-ui-prototype.html:55` defines local storage key.
- `docs/fitcv-settings-ui-prototype.html:278` reads only `localStorage`.
- `docs/fitcv-settings-ui-prototype.html:318` writes only `localStorage`.
- `docs/fitcv-settings-ui-prototype.html:405` binds direct controls; line 412 persists locally on `change`.
- `docs/fitcv-settings-ui-prototype.html:521` saves managed dialogs into local transaction state.
- No `fetch`, `XMLHttpRequest`, or backend URL exists in prototype.

Browser verification:

- **Skip Incomplete Listings** changed local storage immediately and restored when toggled back.
- **Factor Weights** Cancel discarded changed draft; Save persisted only to local storage.
- Restore Defaults restored prototype defaults, not backend values.
- With **Semantic Alignment** off, four Match Method Manage buttons were native-disabled and showed dependency text.
- **Included Sections** disabled Save when Education and Experience were both off; Cancel discarded draft.

### 3.2 Backend persistence boundary

- `GET /settings`: `src/fitcv_cp/app.py:7261`.
- Single-key `POST /settings/{key}`: `src/fitcv_cp/app.py:7308`.
- Atomic HTML group save: `src/fitcv_cp/app.py:7384`.
- Section save: `src/fitcv_cp/app.py:7463`.
- Single SQLite row save: `src/fitcv_cp/settings_store.py:477`.
- Group SQLite save: `src/fitcv_cp/settings_store.py:495`.
- Latest valid active rows: `src/fitcv_cp/settings_store.py:526`.
- Canonical projection into runtime config: `src/fitcv_cp/settings_schema.py:1928`.

Active saved settings during audit:

| Backend field | Active saved value | Prototype value |
|---|---:|---:|
| `pipeline.vector_search_top_n` | 25 | 100 |
| `pipeline.final_top_n` | 10 | 10 |
| `cv_analysis.semantic_alignment.model` | `text-embedding-005` | `text-embedding-005` |
| `cv_generation_model` | `cx/gpt-5.5` | Removed from prototype |
| `cv_preset` | `europass` | Removed from prototype |

Other audited fields currently use baseline configuration because no active SQLite override exists.

### 3.3 Verification commands

```powershell
$env:PYTHONPATH='src'
python -m pytest tests/test_fitcv_cp/test_settings_schema.py tests/test_fitcv_cp/test_settings_store.py tests/test_fitcv_cp/test_settings_store_sqlite.py -q -k "not feature_source_names_operator_facing_agentic_settings_capability"
```

Result: `194 passed, 1 deselected`.

```powershell
$env:PYTHONPATH='src'
python -m pytest tests/test_rule_filter.py tests/test_ranking_contract.py -q
python -m pytest tests/test_evidence.py -q -k "semantic or alignment or weight"
python -m pytest tests/test_cv_generator.py -q -k "disabled_sections or required_sections or composition"
python -m pytest tests/test_fitcv_cp/test_worker_job.py tests/test_fitcv_cp/test_app.py -q -k "reuse and (ranking or cv_analysis or cv_generation or synonym)"
```

Results: `77 passed, 1 skipped`; `5 passed`; `6 passed`; `7 passed`.

Full schema selection still has one stale test referencing intentionally deleted `docs/features/settings_system/feature.source.yaml`: `tests/test_fitcv_cp/test_settings_schema.py:312`.

Cross-field reproduction:

```text
single_final_above_ai ACCEPTED
single_strong_below_stretch ACCEPTED
cv_no_education_or_experience ACCEPTED
```

Partial validation accepts a final count above a stored AI pool and a Strong threshold below a stored Stretch threshold because sibling keys are absent. Backend also accepts both Education and Experience disabled.

## 4. Root cause and boundary

Primary root cause: approved prototype is a self-contained visual contract, not a frontend client. Keys, defaults, persistence, and transactions were designed separately from canonical schema.

Prototype path:

```text
Prototype control → local JavaScript state → localStorage
```

Production path:

```text
Settings route → schema validation → SQLite pipeline_settings → active overlay → effective_settings_json → worker/stage
```

SSOT violations:

1. Prototype keys duplicate canonical facts under different names.
2. Prototype defaults duplicate backend defaults and drift.
3. Screening exposes booleans while backend owns one `rule_filter.selected_filters` list.
4. Synonym reuse exposes canonical and legacy control fields.
5. Runtime UI invents noncanonical batch-size fields.
6. Removed Gap Thresholds remain active in schema, config, tests, and stage code.

Symmetry violations:

1. Prototype gives all runtime stages delay, batch size, and concurrency; backend supports batch size only for Enrichment.
2. Location and Work Mode are separate UI toggles, but backend has one combined rule code.
3. Direct settings save immediately, while interdependent settings require transactions.
4. UI blocks invalid CV composition, but backend accepts it.
5. UI runtime warnings have no backend warning contract.

## 5. Resolution and verification

No implementation fix applied. Audit disposition: **unresolved**.

Status vocabulary:

- **Disconnected:** matching backend field exists; prototype neither loads nor saves it.
- **Local mirror:** row mirrors another prototype row but has no backend connection.
- **No backend owner:** UI concept has no schema/API/runtime field.
- **Ambiguous:** UI concept spans multiple backend fields or different semantics.

### 5.1 Per-`SettingsRow` audit

#### Overview

| Setting label | Frontend component | Backend owner | API or configuration field | Current wiring status | Expected behavior | Issue found + SSOT/symmetry violations | Recommended fix |
|---|---|---|---|---|---|---|---|
| Initial Candidate Pool Size | Number `SettingsRow` | Retrieval / shortlist | `pipeline.vector_search_top_n` | Disconnected; prototype key `pipeline.initialPool`; prototype 100, baseline 50, active 25 | Load effective value; save canonical integer; cap shortlist retrieval | Key/default drift; single-key save can violate `vector >= ai >= final` against stored siblings | Bind canonical key; validate merged retrieval trio server-side or save trio transactionally |
| AI Reranking Pool Size | Number `SettingsRow` | Ranking candidate selection | `pipeline.ai_score_top_n` | Disconnected; prototype key `pipeline.aiPool`; prototype 40, baseline 50 | Bound jobs sent to AI scoring | Key/default drift; relational invariant unsafe through partial validation | Bind canonical key and merged-state validation with pool-size ordering |
| Final Output Count | Number `SettingsRow` | Pipeline final selection | `pipeline.final_top_n` | Disconnected; prototype key `pipeline.finalCount`; prototype 10, baseline 15, active 10 | Bound final ranked output and late CV stages | Partial save accepts value above current AI pool | Bind canonical key; validate against effective AI pool before commit |
| Final Evidence Items Per Job | Number `SettingsRow` | CV analysis evidence retrieval | `pipeline.evidence_top_k` | Disconnected; prototype key `pipeline.evidenceItems`; prototype/backend 5 | Control selected evidence count per ranked job | Duplicate local default despite matching value | Bind canonical field; stage mirror reads same effective value |
| Maximum Applications | Number `SettingsRow` | Global pre-enrichment/rule filter | `global_job_filters.applications_count_max` | Disconnected; prototype key `overview.maxApplications`; defaults 200 | Filter listings over application-count limit | Canonical owner exists but prototype duplicates key/default | Bind canonical key; Enrichment mirror remains read-only navigation surface |
| Maximum Posting Age | Number `SettingsRow` | Global pre-enrichment/rule filter | `global_job_filters.max_age_days` | Disconnected; prototype key `overview.maxPostingAge`; defaults 30 | Filter listings older than configured days | Canonical owner exists but prototype duplicates key/default | Bind canonical key; Enrichment mirror reads same effective value |

#### Enrichment

| Setting label | Frontend component | Backend owner | API or configuration field | Current wiring status | Expected behavior | Issue found + SSOT/symmetry violations | Recommended fix |
|---|---|---|---|---|---|---|---|
| Maximum Applications | Read-only mirror + gear link | Overview owner / global filter | `global_job_filters.applications_count_max` | Local mirror only | Show canonical effective value; gear navigates to Overview | Value mirrors prototype state, not backend effective value | Keep mirror UI; source value from shared canonical frontend store |
| Maximum Posting Age | Read-only mirror + gear link | Overview owner / global filter | `global_job_filters.max_age_days` | Local mirror only | Same as above | Same disconnection | Same fix |
| Skip Incomplete Listings | Toggle `SettingsRow` | None confirmed | None | No backend owner; prototype default On | Skip listings lacking data needed for reliable fit decisions | UI-only; no schema field, persistence field, or confirmed stage gate | Define exact completeness predicate and owner first; add one canonical bool only if approved, otherwise remove row |

#### Screening

| Setting label | Frontend component | Backend owner | API or configuration field | Current wiring status | Expected behavior | Issue found + SSOT/symmetry violations | Recommended fix |
|---|---|---|---|---|---|---|---|
| Require Fit Context | Toggle `SettingsRow` | Rule filter | Membership of `missing_fit_context` in `rule_filter.selected_filters` | Disconnected; not direct bool field | Toggle filter-code membership; persist list; affect rule filtering | UI bool versus list SSOT needs adapter | Use one selected-filter adapter with atomic full-list save; add focused API/stage test |
| Location Preference | Toggle `SettingsRow` | Rule filter | Likely membership of `location_type_excluded` | Disconnected; semantic mismatch | Enable exclusion based on configured location preference | Label says “prefer”; backend code is exclusion and also overlaps work mode | Clarify rule semantics; rename description or split backend rules |
| Work Mode Preference | Toggle `SettingsRow` | None independently | No separate code; overlaps `location_type_excluded` | No backend owner | Independently enable work-mode exclusion | Symmetrical UI has no symmetrical backend field | Add distinct canonical rule code only if stage can distinguish it; otherwise merge UI with Location |
| Seniority Preference | Toggle `SettingsRow` | Rule filter | Membership of `seniority_mismatch` | Disconnected | Enable seniority mismatch exclusion | UI bool versus canonical list | Map through selected-filter adapter and save atomically |
| Contract Preference | Toggle `SettingsRow` | Rule filter | Membership of `contract_type_excluded` | Disconnected | Enable contract-type exclusion | UI bool versus canonical list | Same adapter |
| Experience Preference | Toggle `SettingsRow` | Rule filter | Membership of `experience_level_excluded` | Disconnected | Enable experience-level exclusion | UI bool versus canonical list | Same adapter |

#### Shortlisting

| Setting label | Frontend component | Backend owner | API or configuration field | Current wiring status | Expected behavior | Issue found + SSOT/symmetry violations | Recommended fix |
|---|---|---|---|---|---|---|---|
| Initial Candidate Pool Size | Read-only mirror + gear link | Overview owner / shortlist | `pipeline.vector_search_top_n` | Local mirror only | Show canonical effective value and navigate to Overview | Correct UI owner pattern, but value is local-only | Keep mirror; read shared effective settings state |

#### Ranking

| Setting label | Frontend component | Backend owner | API or configuration field | Current wiring status | Expected behavior | Issue found + SSOT/symmetry violations | Recommended fix |
|---|---|---|---|---|---|---|---|
| AI Reranking Pool Size | Read-only mirror + gear link | Overview owner / ranking | `pipeline.ai_score_top_n` | Local mirror only | Show canonical effective value | Prototype 40; backend baseline 50 | Read canonical value from shared store |
| Final Output Count | Read-only mirror + gear link | Overview owner / pipeline | `pipeline.final_top_n` | Local mirror only | Show canonical effective value | Prototype 10 differs from baseline 15; active override happens to be 10 | Read effective value and preserve source/provenance |
| Factor Weights | Manage `SettingsRow` | Ranking policy | Six `ranking_policy.structured_factor_weights.*` fields | Disconnected local transaction | Load six fields; Save atomically only when total is 1; Cancel discards | Five prototype defaults drift; no grouped JSON endpoint; HTML group route exists | Bind registered ranking group through atomic JSON transaction; use backend defaults/validation |
| Strong Fit Threshold | Number `SettingsRow` | Ranking policy | `ranking_policy.fit_label_thresholds.strong` | Disconnected; default 0.70 matches | Label baseline scores at/above threshold Strong | Immediate single-key save can produce Strong <= stored Stretch | Save both thresholds transactionally or validate candidate against current sibling |
| Stretch Fit Threshold | Number `SettingsRow` | Ranking policy | `ranking_policy.fit_label_thresholds.stretch` | Disconnected; default 0.40 matches | Label scores below Strong but at/above Stretch | Same partial-validation risk | Same transaction/merged validation fix |

#### CV Analysis

| Setting label | Frontend component | Backend owner | API or configuration field | Current wiring status | Expected behavior | Issue found + SSOT/symmetry violations | Recommended fix |
|---|---|---|---|---|---|---|---|
| Final Evidence Items Per Job | Read-only mirror + gear link | Overview owner / CV analysis | `pipeline.evidence_top_k` | Local mirror only | Show canonical effective value | Local-only | Read shared effective state |
| Semantic Alignment | Toggle `SettingsRow` | Evidence retrieval | `cv_analysis.semantic_alignment.enabled` | Disconnected; prototype default Off, baseline On | Enable semantic channels in evidence scoring | Default drift; child disabled state is local-only | Bind canonical bool; revalidate/close child dialogs from authoritative state |
| Embedding Model | Read-only `SettingsRow` | CV analysis metadata | `cv_analysis.semantic_alignment.model` | Disconnected display; backend field metadata-only | Show effective model, never edit here | Value happens to match active saved value | Load effective value; keep non-editable |
| Skills Match | Manage `SettingsRow` | Evidence retrieval | `required_skill_lexical_weight`, `required_skill_semantic_weight` | Disconnected; local dependency works | Save pair atomically; total 1; disabled while parent off | Prototype 0.45/0.55; backend 0.70/0.30 | Bind canonical pair and backend defaults; grouped save |
| Role Match | Manage `SettingsRow` | Evidence retrieval | `role_lexical_weight`, `role_semantic_weight` | Disconnected | Same pair contract | Prototype 0.45/0.55; backend 0.60/0.40 | Same fix |
| Responsibilities Match | Manage `SettingsRow` | Evidence retrieval | `responsibility_lexical_weight`, `responsibility_semantic_weight` | Disconnected | Same pair contract | Prototype 0.45/0.55; backend 0.25/0.75 | Same fix |
| Domain Match | Manage `SettingsRow` | Evidence retrieval | `domain_lexical_weight`, `domain_semantic_weight` | Disconnected | Same pair contract | Prototype 0.45/0.55; backend 0.40/0.60 | Same fix |

#### CV Generation

| Setting label | Frontend component | Backend owner | API or configuration field | Current wiring status | Expected behavior | Issue found + SSOT/symmetry violations | Recommended fix |
|---|---|---|---|---|---|---|---|
| Included Sections | Manage `SettingsRow` | CV composition / generator / validator | Eight `cv_*_enabled` fields | Disconnected local transaction | Load all flags; Save atomically; require Education or Experience; Cancel discards | Backend consumes flags but accepts both required sections off; removed model/preset/pages remain active elsewhere | Add relational invariant to canonical validator; grouped JSON save; decide removed-field ownership |

#### Runtime & Limits

| Setting label | Frontend component | Backend owner | API or configuration field | Current wiring status | Expected behavior | Issue found + SSOT/symmetry violations | Recommended fix |
|---|---|---|---|---|---|---|---|
| Enrichment | Manage `SettingsRow` | Enrichment runtime | `stage_runtime.enrich.sleep_secs`, `.batch_size`, `.concurrency` | Disconnected; prototype 0.5/10/6, baseline 0/10/8 | Save all three atomically; stage uses them | Default drift; warnings UI-only; implementation consumes projected flat compatibility keys | Bind canonical fields; keep one projection boundary; return structured warnings from backend |
| Ranking | Manage `SettingsRow` | Ranking runtime | `stage_runtime.ranking.sleep_secs`, `.concurrency` | Partial concept; prototype invents Batch Size | Save supported fields; scoring consumes delay/concurrency | No ranking batch-size field; prototype 0/20/8 versus backend 0/—/4 | Remove Batch Size unless backend behavior is designed; bind two canonical fields |
| CV Analysis | Manage `SettingsRow` | CV analysis runtime | `stage_runtime.cv_analysis.sleep_secs`, `.concurrency` | Partial concept; prototype invents Batch Size | Save supported fields; analysis consumes delay/concurrency | No batch-size field; prototype 0.2/10/6 versus backend 0/—/4 | Remove Batch Size; bind two canonical fields |
| CV Generation | Manage `SettingsRow` | CV generation runtime | `stage_runtime.cv_generation.sleep_secs`, `.concurrency` | Partial concept; prototype invents Batch Size | Save supported fields; generation consumes delay/concurrency | No batch-size field; prototype 1/5/4 versus backend 0/—/4 | Remove Batch Size; bind two canonical fields |

#### Automation & Reuse

| Setting label | Frontend component | Backend owner | API or configuration field | Current wiring status | Expected behavior | Issue found + SSOT/symmetry violations | Recommended fix |
|---|---|---|---|---|---|---|---|
| Reuse Enrichment Results | Toggle `SettingsRow` | Reuse policy / enrich | `reuse.enrich.enabled` | Disconnected; defaults On | Enable exact compatible enrichment reuse | Key drift only | Bind canonical bool; preserve reuse diagnostics |
| Reuse Ranking Results | Toggle `SettingsRow` | Reuse policy / ranking | `reuse.ranking.enabled` | Disconnected; defaults On | Enable exact compatible ranking-score reuse | Key drift only | Bind canonical bool |
| Reuse CV Analysis Results | Toggle `SettingsRow` | Reuse policy / CV analysis | `reuse.cv_analysis.enabled` | Disconnected; defaults On | Enable compatible analysis reuse | Key drift only | Bind canonical bool |
| Reuse Generated CVs | Toggle `SettingsRow` | Reuse policy / CV generation | `reuse.cv_generation.enabled` | Disconnected; defaults On | Enable fingerprint-matched CV reuse | Key drift only | Bind canonical bool |
| Reuse Synonym Review Results | Toggle `SettingsRow` | Synonym reuse policy | Canonical `reuse.synonym_triage.enabled`; legacy fallback `synonym_management.triage_recommendation_reuse_enabled` | Ambiguous and disconnected | Reuse compatible prior recommendation results | Label implies proposals/review decisions; backend reuses recommendation computation; duplicate legacy field remains | Bind canonical reuse field only; rename description to actual behavior; hide/deprecate legacy field |
| Generate Synonym Proposals | Toggle `SettingsRow` | Synonym management | `synonym_management.propose_enabled` | Disconnected; defaults On | Permit proposal generation/regeneration | No wiring | Bind canonical bool |
| Require Manual Review | Toggle `SettingsRow` | None | None | No backend owner | Prevent unreviewed proposals affecting matching | Backend uses capability and automation gates; no direct manual-review invariant | Replace with explicit automation controls or add enforced policy field |
| Apply Approved Synonyms | Toggle `SettingsRow` | Synonym capability gate | `synonym_management.apply_to_run_enabled` | Disconnected; semantic mismatch | UI says approved decisions are used in current run | Backend field only permits apply; automatic apply also needs `auto_apply_recommendation_enabled` | Rename to permission language or expose separate auto-apply toggle and dependency |
| Promote Approved Synonyms | Toggle `SettingsRow` | Synonym capability gate | `synonym_management.promote_global_enabled` | Disconnected; prototype Off, backend baseline On | UI says decisions are shared for future runs | Backend field only permits promotion; automatic promote needs another field; default drift | Rename as permission gate or add separate automation control; load canonical baseline |

### 5.2 `SettingsDialog` field audit

| Dialog / field | Backend owner | API or configuration field | Current wiring status | Validation / dependency status | Issue found | Recommended fix |
|---|---|---|---|---|---|---|
| Factor Weights / Must-have Match | Ranking policy | `ranking_policy.structured_factor_weights.must_have_match` | Local only | Prototype and backend full-family sum=1 | Default matches 0.30 | Atomic canonical group save |
| Factor Weights / Title Relevance | Ranking policy | `.title_relevance` | Local only | Same | Prototype 0.18, backend 0.20 | Use backend default |
| Factor Weights / Seniority Fit | Ranking policy | `.seniority_fit` | Local only | Same | Prototype 0.14, backend 0.15 | Use backend default |
| Factor Weights / Preference Fit | Ranking policy | `.declared_preference_fit` | Local only; nested link works | Same | Prototype 0.16, backend 0.15 | Use backend default; keep nested child transaction |
| Factor Weights / Location Fit | Ranking policy | `.location_fit` | Local only | Same | Prototype 0.12, backend 0.10 | Use backend default |
| Factor Weights / Language Fit | Ranking policy | `.language_fit` | Local only | Same | Prototype/backend 0.10 | Atomic canonical group save |
| Preference Fit / Domain Preference | Ranking policy | `ranking_policy.declared_preference_component_weights.domain` | Local only | Prototype/backend sum=1 | Prototype 0.40, backend 0.50 | Use backend default and group save |
| Preference Fit / Role Family Preference | Ranking policy | `.role_family` | Local only | Same | Prototype 0.35, backend 0.30 | Same |
| Preference Fit / Work Mode Preference | Ranking policy | `.work_mode` | Local only | Same | Prototype 0.25, backend 0.20 | Same |
| Skills Match / Exact Wording | Evidence retrieval | `cv_analysis.semantic_alignment.required_skill_lexical_weight` | Local only | Disabled while parent off; pair sum=1 | Default drift | Bind canonical pair transaction |
| Skills Match / Semantic Similarity | Evidence retrieval | `.required_skill_semantic_weight` | Local only | Same | Default drift | Same |
| Role Match / Exact Wording | Evidence retrieval | `.role_lexical_weight` | Local only | Same | Default drift | Same |
| Role Match / Semantic Similarity | Evidence retrieval | `.role_semantic_weight` | Local only | Same | Default drift | Same |
| Responsibilities Match / Exact Wording | Evidence retrieval | `.responsibility_lexical_weight` | Local only | Same | Large default drift | Same |
| Responsibilities Match / Semantic Similarity | Evidence retrieval | `.responsibility_semantic_weight` | Local only | Same | Large default drift | Same |
| Domain Match / Exact Wording | Evidence retrieval | `.domain_lexical_weight` | Local only | Same | Default drift | Same |
| Domain Match / Semantic Similarity | Evidence retrieval | `.domain_semantic_weight` | Local only | Same | Default drift | Same |
| Included Sections / Summary | CV composition | `cv_summary_enabled` | Local only | Group Save/Cancel works locally | No backend group client | Bind grouped save |
| Included Sections / Education | CV composition | `cv_education_enabled` | Local only | UI requires Education or Experience | Backend invariant missing | Add canonical relational validation |
| Included Sections / Experience | CV composition | `cv_experience_enabled` | Local only | Same | Backend invariant missing | Same |
| Included Sections / Skills | CV composition | `cv_skills_enabled` | Local only | Bool | No issue beyond disconnection | Bind grouped save |
| Included Sections / Certifications | CV composition | `cv_certifications_enabled` | Local only | Bool | No issue beyond disconnection | Bind grouped save |
| Included Sections / Projects | CV composition | `cv_projects_enabled` | Local only | Bool | No issue beyond disconnection | Bind grouped save |
| Included Sections / Publications | CV composition | `cv_publications_enabled` | Local only | Bool; default Off matches backend | No issue beyond disconnection | Bind grouped save |
| Included Sections / Languages | CV composition | `cv_languages_enabled` | Local only | Bool | No issue beyond disconnection | Bind grouped save |
| Enrichment Runtime / Request Delay | Enrichment runtime | `stage_runtime.enrich.sleep_secs` | Local only | Nonnegative; warnings local only | Prototype 0.5, backend 0 | Bind canonical field; server warning response |
| Enrichment Runtime / Batch Size | Enrichment runtime | `stage_runtime.enrich.batch_size` | Local only | Integer >=1 | Defaults match 10 | Bind canonical field |
| Enrichment Runtime / Concurrency | Enrichment runtime | `stage_runtime.enrich.concurrency` | Local only | Integer >=1; warning local only | Prototype 6, backend 8 | Use backend default |
| Ranking Runtime / Request Delay | Ranking runtime | `stage_runtime.ranking.sleep_secs` | Local only | Nonnegative | Defaults match 0 | Bind canonical field |
| Ranking Runtime / Batch Size | None | None | UI-only | Local integer validation | Invented setting | Remove field |
| Ranking Runtime / Concurrency | Ranking runtime | `stage_runtime.ranking.concurrency` | Local only | Integer >=1 | Prototype 8, backend 4 | Use backend default |
| CV Analysis Runtime / Request Delay | CV analysis runtime | `stage_runtime.cv_analysis.sleep_secs` | Local only | Nonnegative | Prototype 0.2, backend 0 | Use backend default |
| CV Analysis Runtime / Batch Size | None | None | UI-only | Local integer validation | Invented setting | Remove field |
| CV Analysis Runtime / Concurrency | CV analysis runtime | `stage_runtime.cv_analysis.concurrency` | Local only | Integer >=1 | Prototype 6, backend 4 | Use backend default |
| CV Generation Runtime / Request Delay | CV generation runtime | `stage_runtime.cv_generation.sleep_secs` | Local only | Nonnegative | Prototype 1, backend 0 | Use backend default |
| CV Generation Runtime / Batch Size | None | None | UI-only | Local integer validation | Invented setting | Remove field |
| CV Generation Runtime / Concurrency | CV generation runtime | `stage_runtime.cv_generation.concurrency` | Local only | Integer >=1 | Defaults match 4 | Bind canonical field |

### 5.3 Removed and deprecated setting audit

| Setting | Prototype status | Backend status | Issue | Recommended fix |
|---|---|---|---|---|
| Gap Thresholds | Removed | Still editable, persisted, configured, tested, and consumed | Approved removal incomplete. Fields remain in `SETTINGS_SCHEMA`, `config/policy/eligibility.yaml`, `src/fitcv/gap_analysis.py`, and tests | Decide migration; remove schema fields, config, consumers, stored rows, API exposure, and obsolete tests together |
| CV Preset | Removed | Metadata-only, still stored/read | UI/backend surface divergence | Confirm system-owned metadata; document and exclude from user settings payload |
| Maximum Pages | Removed | Active editable/consumed `cv_max_pages` | UI/backend surface divergence | Decide hidden system policy versus full deprecation |
| Generation Model | Removed | Active editable `cv_generation_model`; active override `cx/gpt-5.5` | UI/backend surface divergence | Move to Application/LLM settings owner or keep documented stage owner outside Pipeline |

## 6. Risk and next steps

### Highest-priority remediation

1. **Create one canonical frontend settings adapter.** Use backend keys directly, load saved plus baseline/effective values, and avoid copied defaults in page definitions.
2. **Add atomic JSON save support for managed dialogs and relational sets.** Reuse schema group registries; Save validates and commits one coherent payload. Cancel stays client-local.
3. **Resolve missing contracts before wiring UI-only rows.** Decide Skip Incomplete Listings, Work Mode Preference, Require Manual Review, and unsupported stage Batch Size fields.
4. **Enforce invariants in backend SSOT.** Pool ordering, fit-label ordering against effective siblings, Education-or-Experience, parent/child dependencies, and warning generation cannot rely only on UI.
5. **Remove or relocate deprecated settings.** Gap Thresholds need complete retirement. Removed CV fields need explicit ownership.
6. **Resolve synonym semantics.** Separate permission gates, automation toggles, and reuse behavior; expose only canonical `reuse.synonym_triage.enabled` for recommendation reuse.

### Suggested implementation order

1. Backend contract decisions and schema cleanup.
2. Atomic settings API for groups/sections.
3. Shared frontend settings store using canonical keys.
4. Wire Overview and mirrors.
5. Wire Screening toggles through selected-filter adapter.
6. Wire managed dialogs and backend validation messages.
7. Add focused load/save/restore/stage-consumption integration tests per page.

Residual risk: wiring controls before contract cleanup encodes prototype drift into adapters and creates a second translation layer, worsening SSOT violations.

## 7. Assumptions and unresolved questions

1. Is **Skip Incomplete Listings** a new enrichment predicate or an alias for existing fit-context filtering?
2. Should Location and Work Mode remain independent? If yes, what distinct backend rule codes own them?
3. Does **Require Manual Review** disable all automatic apply/promote actions, or block any proposal effect until explicit human status transition?
4. Should removed `cv_generation_model`, `cv_preset`, and `cv_max_pages` move to Application settings, become hidden policy, or be deprecated completely?
5. Should runtime warnings be advisory API data or one shared policy consumed by API and UI?
6. Should Overview controls remain immediate-save? If yes, backend must merge candidate value with current effective siblings before relational validation.
7. Should UI show resolved effective value only, or distinguish saved override from baseline default?
