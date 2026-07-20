---
layer: change
artifact_type: spec
status: active
template_id: detailed-specification
name: fitcv-semantic-snapshot-ssot
parent_thread: workstream-pipeline-efficiency-and-reuse.efficiency-reuse-cross-stage-cache-safety
targets:
  - docs/intent/workstreams/threads/workstream-pipeline-efficiency-and-reuse/04-efficiency-reuse-cross-stage-cache-safety.md
  - src/fitcv/config.py
  - src/fitcv/semantic_snapshot.py
  - src/fitcv/enrich.py
  - src/fitcv/rule_filter.py
  - src/fitcv/embeddings.py
  - src/fitcv/ranking.py
  - src/fitcv/gap_analysis.py
  - src/fitcv/cv_generator.py
  - src/fitcv/validator.py
  - src/fitcv/pipeline.py
  - src/fitcv/evidence.py
  - src/fitcv/ai_score.py
  - src/fitcv/agentic_cv_analysis.py
  - src/fitcv/agentic_cv_generation.py
  - src/fitcv/reuse.py
  - tests/test_config.py
  - tests/test_semantic_snapshot.py
  - tests/test_enrich.py
  - tests/test_rule_filter.py
  - tests/test_embeddings.py
  - tests/test_ranking.py
  - tests/test_gap_analysis.py
  - tests/test_cv_generator.py
  - tests/test_validator.py
  - tests/test_ai_score.py
  - tests/test_evidence.py
  - tests/test_agentic_cv_analysis.py
  - tests/test_cv_generation_reason_mapping.py
  - tests/test_pipeline.py
  - tests/test_pipeline_stage_resume_parity.py
  - tests/test_pipeline_checkpoint_contract.py
  - tests/test_fitcv_cp/test_worker_job.py
  - tests/test_fitcv_cp/test_worker_job_auto_promote_skill_only.py
  - tests/test_fitcv_cp/test_worker_job_attempt_terminalization.py
  - docs/features/pipeline_performance/feature.source.yaml
  - docs/features/cv_system/feature.source.yaml
  - docs/features/trigger_run_management/feature.source.yaml
  - docs/stages/enrich.source.yaml
  - docs/stages/rule_filter.source.yaml
  - docs/stages/shortlist.source.yaml
  - docs/stages/ranking.source.yaml
  - docs/stages/cv_analysis.source.yaml
  - docs/stages/cv_generation.source.yaml
  - docs/architecture.md
  - docs/pipeline.md
  - docs/configuration.md
related_features:
  - pipeline_performance
  - cv_system
  - trigger_run_management
related_stages:
  - enrich
  - rule_filter
  - shortlist
  - ranking
  - cv_analysis
  - cv_generation
---

# FitCV Semantic Snapshot SSOT

## Goal

Define one canonical semantic snapshot contract for every job entry and every synonym-aware comparison input so taxonomy and synonym policy changes are resolved once, represented once, and consumed uniformly by every downstream stage.

The design must preserve enrich extraction reuse, eliminate duplicated canonicalization, and invalidate an expensive stage only when that stage's effective input changes. Updating an unrelated synonym mapping must not invalidate unaffected job results.

For a mapping pair `A:B`:

- `A` is the extracted raw alias or source value
- `B` is the resolved canonical value
- policy changes may require cheap reprojection from `A`
- downstream refresh is required only when the exact input consumed by that stage changes

## Triage

- layer: `change`
- owning workstream: `workstream-pipeline-efficiency-and-reuse`
- owning thread: `workstream-pipeline-efficiency-and-reuse.efficiency-reuse-cross-stage-cache-safety`
- primary feature: `pipeline_performance`
- supporting features: `cv_system`, `trigger_run_management`
- primary lens: semantic SSOT, exact-match reuse, and cross-stage cache safety
- plan needed after approval: yes
- roadmap or workstream reprioritization: no

## Problem Statement

Current semantic resolution and reuse identity are asymmetric:

- enrich parses raw and canonical skill fields using effective synonym policy
- cached enrich payloads preserve previously materialized canonical values
- ranking canonicalizes job and candidate skill values again from runtime config
- CV-analysis contract fingerprinting includes complete skill synonym map
- stage fingerprint builders independently choose which raw, canonical, policy, and contract fields participate

This creates two opposite failure modes:

1. stale semantic reuse: an enrich cache row may retain old canonical value `B` after effective mapping for `A` changes
2. excessive invalidation: an unrelated synonym-list edit changes a global policy fingerprint and forces fresh downstream work for jobs whose effective semantic inputs remain identical

The system needs one distinction that all stages honor:

- derivation changed: semantic policy or resolver changed, so reprojection may be required
- value changed: effective semantic data consumed by a stage changed, so that stage must recompute

No stage-specific synonym-refresh branch should remain.

## Current Source-Of-Truth Boundaries

| Concern | Current owner | Required disposition |
| --- | --- | --- |
| Effective taxonomy data and overlay precedence | `config.py` and effective run config | remain policy source; compile once into validated semantic policy |
| Raw job extraction facts | enrich extraction payload | remain immutable source facts and reusable independently from taxonomy changes |
| Skill canonicalization | enrich plus ranking | move to one semantic resolver |
| Domain and role-family canonicalization | enrich plus ranking helpers | move to same semantic resolver contract |
| Canonical job semantics | repeated flat enriched-row fields | replace as authority with one semantic snapshot; retain flat fields only as derived compatibility projections |
| Stage input identity | independent fingerprint builders | derive from exact stage input object plus stage contract |
| Reuse decision narration | `reuse.py` and stage-specific status fields | retain shared decision shape; feed it one uniform exact-match result |
| Operator synonym policy surfaces | control plane and run settings snapshots | remain policy administration and observability surfaces, never semantic runtime authority |

## Key Deliverables

### Canonical `SemanticSnapshot`

Define one versioned object containing subject identity, normalized raw-to-canonical entities for every supported semantic field, stable value identity, derivation provenance, and completeness state. Job snapshots are persisted with existing job payloads; candidate and criteria snapshots may remain run-scoped derived values.

### Single semantic resolver

Define one resolver that accepts immutable extraction facts plus compiled effective semantic policy and produces snapshot. Enrich, ranking, analysis, generation, resume, and cache-reuse paths must use this resolver instead of reading synonym maps independently.

### Exact stage-input reuse law

Define one rule for every reusable stage:

```text
reuse(stage, old, new) iff
old.stage_input_fingerprint == new.stage_input_fingerprint
and old.stage_contract_fingerprint == new.stage_contract_fingerprint
```

`stage_input_fingerprint` must hash same validated object passed into stage execution. It must not hash an unrelated global policy surface.

### Historical compatibility without stale trust

Define one compatibility projector for cached rows that predate native semantic snapshots. It reconstructs source facts from raw entity/list fields when possible and refuses affected reuse when sufficient raw facts are unavailable.

## Task/Wave Breakdown

### Wave 1: Source-first analysis

**Purpose:**
- identify current semantic owners, cache boundaries, and repeated canonicalization paths

**Steps:**
- [x] inspect enrich extraction, cache lookup, and merge behavior
- [x] inspect ranking and CV-analysis canonicalization and fingerprints
- [x] identify owning workstream, thread, features, and stages
- [x] classify raw facts, derived semantic values, policy data, and stage inputs

**Verification:**
- [x] current stale-reuse and excessive-invalidation paths are explicit

**Exit Criteria:**
- [x] design decisions do not depend on unstated semantic ownership assumptions

### Wave 2: Decision closure

**Purpose:**
- define one symmetric semantic and reuse contract

**Steps:**
- [x] define snapshot authority and compatibility projections
- [x] define policy compilation and resolver boundaries
- [x] define derivation, value, stage-input, and stage-contract fingerprints
- [x] define equality semantics for scalar, set, ordered-list, and multiset fields
- [x] define invalid-policy and incomplete-history behavior

**Verification:**
- [x] every admissible mapping and cache case resolves through same law

**Exit Criteria:**
- [x] no design branch depends on a specific stage, synonym file, or lifecycle mode

### Wave 3: Validation and approval readiness

**Purpose:**
- make implementation proof and rollout constraints explicit

**Steps:**
- [x] define acceptance criteria and validation evidence
- [x] define migration and rollback boundaries
- [x] approve this specification
- [x] write implementation plan

**Verification:**
- [x] validation covers fresh, cached, resumed, staged, and historical paths

**Exit Criteria:**
- implementation begins only after spec approval and plan handoff

## Design Decisions

### Decision: Snapshot is runtime semantic SSOT

- context: synonym files are policy inputs, while flat enriched-row fields are duplicated materializations
- choice: `SemanticSnapshot` is sole runtime authority for resolved semantics of a subject (`job`, `candidate`, or `criteria`)
- alternatives considered:
  - treat effective synonym map as runtime SSOT
  - retain each stage's local canonicalization
  - treat flattened enriched-row canonical fields as authority
- impact:
  - stages consume snapshot projections
  - job snapshots persist inside existing payloads; candidate and criteria snapshots remain derived unless persistence is already required
  - flat `*_canonical` and entity fields become derived compatibility outputs
  - no stage reads taxonomy maps directly for migrated semantic resolution

### Decision: Keep immutable extraction facts separate from semantic projection

- context: enrich LLM extraction is expensive; canonical reprojection is deterministic and cheap
- choice: preserve raw extraction facts independently and rebuild semantic snapshot whenever derivation compatibility is unknown or changed
- alternatives considered:
  - invalidate full enrich cache on every taxonomy change
  - trust cached canonical values indefinitely
- impact:
  - policy changes never require an LLM call by themselves
  - cached rows can adopt new canonical values from stored raw facts
  - insufficient historical raw facts block affected reuse instead of silently accepting stale values

### Decision: Compile one effective semantic policy

- context: skill synonyms, domain aliases, role-family aliases, overlays, and runtime snapshots currently expose several map shapes
- choice: `config.py` compiles already-effective run config into one normalized, validated `SemanticPolicy`
- alternatives considered:
  - let each stage normalize maps independently
  - add another policy configuration file
- impact:
  - current config and overlay precedence remain unchanged
  - policy compilation preserves taxonomy-specific normalization, flattens acyclic chains to terminal canonical values, rejects cycles, and provides deterministic ordering
  - no new operator setting is required

### Decision: Use one field contract registry

- context: fields differ only by taxonomy family, cardinality, and equality semantics
- choice: define one bounded code-owned registry equivalent to:

```text
required_skills   taxonomy=skill        cardinality=list   equality=set
preferred_skills  taxonomy=skill        cardinality=list   equality=set
must_have_skills  taxonomy=skill        cardinality=list   equality=set
candidate_skills  taxonomy=skill        cardinality=list   equality=set
domain            taxonomy=domain       cardinality=scalar equality=scalar
job_family        taxonomy=role_family  cardinality=scalar equality=scalar
```

- alternatives considered:
  - custom resolver function per field
  - user-configurable field contracts
- impact:
  - all admissible fields use one resolver algorithm
  - adding a future semantic field requires one explicit contract row and tests
  - runtime configuration cannot silently change equality semantics

### Decision: Entity records own canonical lists

- context: entity arrays and flattened canonical lists can drift
- choice: normalized entity records are authoritative; canonical scalar/list compatibility fields derive from them
- alternatives considered:
  - store independently authored entity and flattened fields
- impact:
  - one entity cannot expose conflicting canonical values across surfaces
  - list dedupe and ordering happen once

### Decision: Separate derivation identity from value identity

- context: a policy edit can change how a value was derived without changing value observed by downstream stages
- choice: maintain distinct fingerprints:

| Fingerprint | Payload | Purpose |
| --- | --- | --- |
| `raw_semantic_source_fingerprint` | normalized immutable extraction facts | source identity |
| `semantic_derivation_fingerprint` | source fingerprint, compiled policy fingerprint, resolver contract | decide whether snapshot reprojection is required |
| `semantic_value_fingerprint` | normalized resolved snapshot values | semantic equality and observability |
| `stage_input_fingerprint` | exact validated execution input for one stage | expensive stage reuse |
| `stage_contract_fingerprint` | stage schema, model, prompt, algorithm, and behavior versions | implementation compatibility |

- alternatives considered:
  - one global synonym fingerprint
  - one fingerprint containing raw, policy, value, and every stage contract
- impact:
  - unrelated policy edits may cause cheap reprojection but not expensive downstream recomputation
  - changed canonical value invalidates only stages whose exact input changes

### Decision: Fingerprint exact execution inputs

- context: independently built fingerprint payloads can drift from runtime behavior
- choice: each stage builds one validated input object; execution and fingerprinting consume that same object
- alternatives considered:
  - maintain separate execution and fingerprint projections
  - add manual invalidation rules for synonym events
- impact:
  - reuse correctness becomes structural
  - stage dependencies are visible in input schemas
  - no event-driven cache purge system is needed

### Decision: Canonicalize both sides before comparison

- context: ranking and rule filtering currently canonicalize job, candidate, and must-have skills locally; job-only snapshots would leave comparison-side drift
- choice: every semantic list already participating in synonym-aware comparison uses same compiled policy and resolver contract before comparison
- alternatives considered:
  - snapshot only job values
  - preserve stage-local comparison canonicalization
  - expand synonym behavior into surfaces that do not currently use it
- impact:
  - existing synonym-aware comparisons become symmetric
  - candidate-side and must-have policy changes alter stage input only when resolved comparison inputs change
  - migration does not add synonym semantics to previously synonym-insensitive behavior

### Decision: Alias-sensitive behavior uses bounded equivalence projections

- context: some behavior, such as gap phrase matching, consumes aliases equivalent to a canonical skill rather than canonical value alone
- choice: shared semantic projection API derives bounded alias-equivalence sets from compiled policy for only canonical values consumed by alias-sensitive stage behavior
- alternatives considered:
  - treat unchanged canonical `B` as sufficient for every stage
  - let alias-sensitive stages read full synonym map directly
  - include full policy map in every stage fingerprint
- impact:
  - canonical-only stages remain stable when alias closure changes
  - alias-sensitive stages recompute only when relevant equivalence projection changes
  - stage input explicitly reveals whether behavior consumes canonical values, raw values, or alias closure

### Decision: Equality semantics are explicit

- context: case, whitespace, duplicates, and order can create false cache misses
- choice:
  - dispatch through resolver-owned taxonomy-specific normalization rules that preserve existing skill, domain, and role-family semantics
  - compare scalar fields as normalized scalars
  - compare set-semantic lists as sorted unique canonical values
  - preserve order only for fields explicitly declared ordered
  - preserve multiplicity only for fields explicitly declared multisets
- alternatives considered:
  - hash serialized input order blindly
- impact:
  - semantically equivalent inputs produce identical fingerprints
  - meaningful order changes remain detectable where required

### Decision: No new semantic database or invalidation service

- context: existing structured-job payloads, run state, and reuse snapshots already carry required artifacts
- choice: persist snapshot data inside existing payload/result contracts and derive cache validity through content fingerprints
- alternatives considered:
  - semantic snapshot table
  - dependency graph database
  - synonym-update cache purge worker
- impact:
  - migration remains bounded
  - rollback remains local
  - storage authority does not split

## Canonical Contracts

### `SemanticPolicy`

Required logical shape:

```text
schema_version
resolver_contract_version
taxonomies
  skill.alias_to_terminal_canonical
  domain.alias_to_terminal_canonical
  role_family.alias_to_terminal_canonical
policy_fingerprint
```

Policy compilation requirements:

- consume effective run config after existing base/overlay precedence
- trim and normalize keys and values deterministically
- reject empty alias or canonical values
- flatten alias chains to terminal canonical values
- reject cycles
- reject unresolved conflicts rather than selecting by iteration order
- produce stable sorted maps and one policy fingerprint
- preserve current allowed-value and taxonomy-family validation

### `SemanticEntity`

Required logical shape:

```text
field
raw_value
canonical_value
```

Optional provenance may include extraction confidence or resolution source, but optional provenance must not affect downstream stage fingerprints unless that stage consumes it.

### `SemanticSnapshot`

Required logical shape:

```text
schema_version
subject_kind: job | candidate | criteria
subject_identity
field_completeness
  <registered scalar or list field>: complete | incomplete
fields
  <registered scalar or list field>
raw_semantic_source_fingerprint
semantic_derivation_fingerprint
semantic_value_fingerprint
resolver_contract_fingerprint
policy_fingerprint
incomplete_reasons_by_field
```

Every job must have a job snapshot. Candidate and criteria inputs use same contract with their registered field subsets. Snapshot must not duplicate independently authored canonical lists. Compatibility fields derive from `fields`. `subject_identity` is the existing `raw_job_fingerprint` for jobs, a stable fingerprint of the authoritative candidate-profile input for candidates, and a stable fingerprint of the authoritative criteria/preferences input for criteria. Subject identity does not participate in `semantic_value_fingerprint`; artifact lookup and stage inputs include it only when identity is consumed.

### Stage input contract

Each reusable stage input builder must:

1. accept canonical snapshots and non-semantic stage inputs
2. select only fields consumed by stage behavior
3. normalize stage-specific unordered structures
4. validate required values
5. return one serializable input object
6. derive `stage_input_fingerprint` from that object
7. pass that same object to stage execution

## Uniform Reuse Law

For stage `S`, old artifact `O`, and current candidate input `N`:

```text
reusable(S, O, N) =
    reuse_enabled(S)
    and O.stage == S
    and O.stage_input_fingerprint == fingerprint(N.stage_input)
    and O.stage_contract_fingerprint == N.stage_contract_fingerprint
    and N.stage_input.semantic_requirements_complete == true
```

No additional synonym-list-change condition is allowed.

If a stage consumes canonical values only, raw alias changes that resolve to same canonical values do not invalidate it. If a stage consumes raw aliases, relevant alias-equivalence closure, confidence, provenance, or display order, those values belong in its exact input and naturally participate in reuse identity. Unchanged canonical `B` is therefore sufficient only for canonical-only stages, never as a global shortcut.

## Admissible Case Matrix

| Change | Snapshot result | Expected downstream behavior |
| --- | --- | --- |
| add unused `C:D` mapping | job semantic values unchanged | reproject if needed; reuse all stages with unchanged exact inputs |
| remove unused mapping | job semantic values unchanged | reuse all unaffected stages |
| change used `A:B` to `A:B2` | canonical value changes | recompute stages consuming changed field |
| add `A2:B` while job contains `A` | canonical value unchanged; relevant alias closure may change | reuse canonical-only stages; recompute alias-sensitive stages only when their bounded equivalence projection changes |
| raw alias changes from `A` to `A2`, both resolve to `B` | canonical-only projection unchanged | reuse canonical-only stages; recompute raw-consuming stages |
| synonym map order changes | compiled policy and values equivalent | reuse |
| list order changes for set-semantic field | semantic value equivalent | reuse |
| duplicate list value added | semantic value equivalent after dedupe | reuse |
| case or surrounding whitespace changes | normalized value equivalent | reuse |
| candidate alias resolves differently | candidate semantic input changes | recompute comparison stages using candidate value |
| resolver contract changes but projected stage input is identical | derivation changes, stage input unchanged | downstream reuse remains valid unless stage contract also changes |
| stage algorithm, prompt, model, or schema changes | stage contract changes | recompute that stage |
| policy contains cycle or unresolved conflict | policy compilation fails | run cannot use invalid policy; no stale fallback |
| legacy cache lacks sufficient raw facts | snapshot incomplete | affected stage reuse denied; fresh authoritative path required |
| synonym promotion occurs during manual staged run | current run policy remains frozen | promotion affects the next run; continuing the current run uses its original compiled policy |

## Invariants

- One effective run config owns taxonomy data and overlay precedence and remains frozen for the run lifetime.
- One compiled `SemanticPolicy` owns normalized taxonomy lookup.
- One resolver owns raw-to-canonical semantic projection.
- One `SemanticSnapshot` contract owns resolved semantics for job, candidate, and criteria subjects; each persisted job has one native job snapshot.
- Entity records own canonical compatibility fields; compatibility fields never become independent truth.
- Fresh enrich, reused enrich, resumed run, staged run, and run-all paths produce equivalent snapshots for equivalent source facts and policy.
- Enrich LLM reuse never depends on unrelated synonym-list updates.
- Canonical reprojection never requires an LLM call.
- No stage reads synonym or alias maps directly after migration; stages consume shared canonical or bounded equivalence projections.
- No stage maintains a synonym-specific cache invalidation branch.
- Stage execution and stage fingerprinting use same validated input object.
- Expensive reuse is accepted only on exact stage-input and stage-contract matches.
- Incomplete historical semantic fields never silently authorize reuse for stages consuming those fields; unrelated complete projections remain reusable.
- Policy normalization is deterministic and independent of dictionary insertion order.
- Invalid cycles and conflicts fail closed.
- Raw extraction facts remain available for audit and reprojection.
- Human display values remain derived and do not control semantic equality unless explicitly consumed by a stage.

## Acceptance Criteria

1. A native `SemanticPolicy`, `SemanticEntity`, and subject-aware `SemanticSnapshot` contract exists with versioned schemas and deterministic serialization.
2. One resolver handles skills, domains, and role families through explicit field contracts.
3. Fresh and cached enrich rows produce same semantic snapshot for same raw facts and effective policy.
4. Changing a used mapping updates canonical output without a new enrich LLM call.
5. Adding, removing, or reordering an unused mapping does not change downstream stage-input fingerprints.
6. Rule filtering and ranking canonicalize job, must-have, and candidate values through same resolver path.
7. Alias-sensitive gap analysis consumes a bounded equivalence projection rather than full synonym map.
8. Shortlist job-summary signatures derive semantic values from snapshot projection.
9. CV-analysis reuse no longer depends on entire global synonym map when exact inputs remain unchanged.
10. Every reusable stage hashes its exact validated execution input plus its stage contract.
11. Set-semantic fields are insensitive to order, duplicates, case, and surrounding whitespace after normalization.
12. Invalid alias cycles and unresolved conflicts fail policy compilation with actionable errors; acyclic chains flatten deterministically to terminal canonical values.
13. Legacy cached rows with sufficient raw facts reproject successfully; insufficient rows deny affected reuse truthfully.
14. Initial, retry, continue, run-all, and manual-staged execution paths produce symmetric reuse decisions.
15. Existing operator synonym review and promotion workflows remain available and continue producing effective run config snapshots.
16. Existing scores, filters, shortlist text, gaps, analysis outputs, and generation inputs remain behaviorally equivalent when semantic projections are equivalent.
17. No new database, background invalidation worker, or cache-purge API is introduced.
18. Managed feature/stage contracts and generated lineage remain synchronized.

## Non-Goals

- Redesign synonym proposal generation, review, approval, or global promotion UX.
- Change base-versus-overlay precedence.
- Add fuzzy, probabilistic, embedding-based, or LLM-driven canonical resolution.
- Reclassify taxonomy values or introduce new taxonomy families.
- Recompute historical runs or rewrite historical database rows in place.
- Guarantee reuse for incomplete legacy artifacts.
- Add a generic external cache platform.
- Change stage scoring, ranking, analysis, or generation semantics beyond eliminating duplicate canonicalization and invalidation drift.
- Make field equality semantics user-configurable.

## Risks and Mitigations

### Risk: Hidden stage dependency omitted from input

- impact: stale reuse despite changed behavior input
- mitigation: stage execution must accept same validated object used for fingerprinting; direct config reads are prohibited inside migrated stage logic

### Risk: Migration briefly creates two semantic authorities

- impact: snapshot and flat fields can disagree
- mitigation: derive compatibility fields from snapshot in one projector and add disagreement assertions during migration

### Risk: Legacy rows lack raw entity facts

- impact: canonical reprojection cannot be proven
- mitigation: mark snapshot incomplete and deny affected reuse; do not trust cached canonical values as fresh truth

### Risk: Policy compiler changes current overlay meaning

- impact: unexpected canonical outputs
- mitigation: compile only already-effective config; preserve existing precedence and test current fixtures before deleting old normalization paths

### Risk: Fingerprints remain overly broad

- impact: avoidable fresh work
- mitigation: stage input builders select consumed fields only; policy and derivation provenance stay outside stage inputs unless consumed

### Risk: Fingerprints become too narrow

- impact: stale stage outputs
- mitigation: contract tests mutate each consumed field and require fingerprint change; mutate each non-consumed field and require stability

### Risk: Set normalization removes meaningful order

- impact: stage behavior changes silently
- mitigation: equality semantics are code-owned per field; ordered fields remain ordered and tested

## Validation Plan

- proof target: policy compilation is deterministic
  - method: compile equivalent maps with different insertion order, case, whitespace, and overlay source order after effective merge
  - evidence: identical compiled policy and policy fingerprint

- proof target: invalid policy fails closed
  - method: empty, cyclic, chained, conflicting, and punctuation-sensitive mapping fixtures
  - evidence: acyclic chains flatten to terminal canonical values; empty values are ignored; cyclic, colliding, and unresolved conflict cases raise stable validation errors without collapsing distinct skills such as `C`, `C++`, `C#`, `.NET`, and `Node.js`

- proof target: snapshot resolution is uniform
  - method: parameterized scalar/list fixtures across skill, domain, and role-family contracts
  - evidence: same resolver emits expected canonical entities and stable value fingerprints

- proof target: fresh and reused enrich are symmetric
  - method: run fresh parse and cached raw-fact reprojection with same source/policy
  - evidence: identical native snapshots and compatibility fields; no runtime observation on cached path

- proof target: used mapping change avoids enrich LLM refresh
  - method: cache raw `A`, change effective mapping from `A:B` to `A:B2`, and execute enrich reuse path
  - evidence: enrich extraction remains reused; snapshot value changes to `B2`; affected downstream fingerprints change

- proof target: unrelated synonym edits preserve expensive reuse
  - method: add, remove, and reorder mappings absent from job and candidate semantic sources
  - evidence: semantic value and downstream stage-input fingerprints remain identical

- proof target: comparison symmetry holds
  - method: equivalent job-side, must-have, and candidate-side alias changes resolving to same canonical value
  - evidence: rule-filter and ranking inputs and outputs remain identical

- proof target: alias-sensitive projection is exact
  - method: add an alias for a canonical skill used by gap phrase matching, then add an unrelated alias mapping
  - evidence: relevant equivalence projection and gap-analysis fingerprint change only for first edit; canonical-only stage fingerprints remain stable

- proof target: shortlist semantic signature is snapshot-derived
  - method: compare fresh and reprojected snapshot inputs across order, duplicate, and unrelated-policy mutations
  - evidence: job-summary text and signature remain identical for equivalent semantic projection

- proof target: migration preserves behavior
  - method: golden fixtures before and after migration for rule-filter results, shortlist text/signature, ranking factors/scores, gap results, CV-analysis input, and generation input
  - evidence: outputs remain equivalent whenever canonical and alias-sensitive projections are equivalent

- proof target: stage dependencies are exact
  - method: mutation tests per stage input schema
  - evidence: every consumed field changes fingerprint; every excluded field leaves fingerprint stable

- proof target: execution and fingerprint payload cannot drift
  - method: spy or contract test around each migrated stage entrypoint
  - evidence: object serialized for fingerprint is object supplied to execution

- proof target: legacy compatibility is safe
  - method: fixtures with native snapshot, raw entities only, raw lists only, canonical-only fields, and malformed payloads
  - evidence: first three produce complete field projections where sufficient; canonical-only and malformed fields become incomplete and deny reuse only for stages consuming those fields

- proof target: lifecycle modes are symmetric
  - method: equivalent initial, retry, continue, run-all, and manual-staged tests
  - evidence: identical semantic value and stage-input fingerprints for equivalent inputs

- proof target: no duplicate canonicalization remains
  - method: source scan and targeted behavior tests
  - evidence: migrated stages do not read `skill_synonyms`, `domain_alias_map`, or `role_family_alias_map` directly

- proof target: managed docs remain synchronized
  - method: architecture sync/check, planning lifecycle validation, and repo contract validation
  - evidence: feature/stage sources and generated lineage pass validators

## Implementation Constraints

- Reuse existing config loading, stable JSON hashing, enriched payload storage, and `reuse.py` decision projection.
- Prefer one small semantic contract/resolver module; do not create resolver classes, factories, plugins, or per-stage adapters without a demonstrated requirement.
- Keep taxonomy data in existing config surfaces.
- Do not add runtime settings for fixed semantic laws.
- Do not add a database table when existing payload JSON can carry snapshot.
- Delete duplicate canonicalization after consumers migrate.
- Preserve raw extraction values for audit and compatibility.
- Keep compatibility projection one-way: snapshot to flat fields.
- Fail closed when exact semantic input cannot be reconstructed.

## Rollout And Rollback

### Rollout

1. add compiled semantic policy and resolver contract behind current effective config
2. build native snapshot from fresh enrich facts and derive existing compatibility fields
3. reproject cached enrich facts through same resolver
4. migrate rule-filter, shortlist embedding, ranking, and gap-analysis semantic inputs to shared projections
5. migrate CV-analysis and other reusable stages to exact execution-input fingerprints
6. add historical compatibility projector and incomplete-state reuse denial
7. delete direct stage synonym-map reads and duplicate normalization helpers
8. update feature/stage source contracts and regenerate managed docs

No dual-write of independently constructed canonical values is allowed. During migration, legacy flat fields may remain only when derived from snapshot.

### Rollback

- preserve raw extraction facts and existing flat compatibility fields
- snapshot readers may be disabled without deleting historical data
- rollback does not rewrite stored runs
- stage reuse falls back to fresh computation when native exact input cannot be proven
- operator synonym administration remains unchanged

## Completion Criteria

This specification is complete when:

1. snapshot, policy, entity, and fingerprint contracts are approved
2. one uniform reuse law covers every admissible mapping and lifecycle case
3. raw extraction and semantic projection ownership are distinct and approved
4. stage input equality semantics are explicit
5. historical incomplete-state behavior is approved
6. acceptance criteria and validation evidence are implementation-plan ready
7. affected feature and stage source updates are identified
8. downstream implementation plan is completed or explicitly dropped
9. every child item is `completed` or `dropped`

Canonical source-of-truth:

<LINK>
- `docs/intent/workstreams/threads/workstream-pipeline-efficiency-and-reuse/04-efficiency-reuse-cross-stage-cache-safety.md`
- `docs/intent/workstreams/threads/workstream-pipeline-efficiency-and-reuse/01-efficiency-reuse-exact-match-contract.md`
- `src/fitcv/config.py`
- `src/fitcv/enrich.py`
- `src/fitcv/rule_filter.py`
- `src/fitcv/embeddings.py`
- `src/fitcv/ranking.py`
- `src/fitcv/gap_analysis.py`
- `src/fitcv/evidence.py`
- `src/fitcv/reuse.py`
- `docs/features/pipeline_performance/feature.source.yaml`
- `docs/features/cv_system/feature.source.yaml`
- `docs/stages/enrich.source.yaml`
- `docs/stages/ranking.source.yaml`
- `docs/stages/cv_analysis.source.yaml`
- `docs/operating_system/lifecycle/doc-system-lifecycle.md`
- `scripts/validate_planning_lifecycle.py`
</LINK>
