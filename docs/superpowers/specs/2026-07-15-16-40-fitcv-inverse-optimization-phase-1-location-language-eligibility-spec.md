---
layer: change
artifact_type: spec
status: active
template_id: detailed-specification
name: fitcv-inverse-optimization-phase-1-location-language-eligibility
parent_thread: workstream-fitcv-semantic-spine.semantic-spine-stage-authority-contract
parent_spec: docs/superpowers/specs/2026-07-14-22-25-fitcv-inverse-optimization-master-ssot-symmetry-spec.md
targets:
  - config/policy/eligibility.yaml
  - src/fitcv/config.py
  - src/fitcv/ingest.py
  - src/fitcv/normalize.py
  - src/fitcv/enrich.py
  - src/fitcv/fit_factors.py
  - src/fitcv/rule_filter.py
  - src/fitcv/pipeline.py
  - src/fitcv/pipeline_stage_runner.py
  - src/fitcv_cp/sqlite_store.py
  - docs/architecture.md
  - docs/configuration.md
  - docs/pipeline.md
  - docs/stages/normalize.source.yaml
  - docs/stages/enrich.source.yaml
  - docs/stages/rule_filter.source.yaml
  - docs/features/cv_system/feature.source.yaml
  - tests/test_config.py
  - tests/test_ingest.py
  - tests/test_normalize.py
  - tests/test_enrich.py
  - tests/test_fit_factors.py
  - tests/test_rule_filter.py
  - tests/test_pipeline.py
  - tests/test_pipeline_stage_resume_parity.py
  - tests/test_fitcv_cp/test_sqlite_store.py
related_features:
  - cv_system
  - inspection_debugging
related_stages:
  - normalize
  - enrich
  - rule_filter
---

# Detailed Spec: FitCV inverse optimization Phase 1 location, language, and eligibility

## Goal

Add actual job location and job-language requirements as first-class, durable fit
facts without confusing either with existing work mode, skill extraction, or
ranking composition.

Phase 1 establishes one uniform algebra for both factors:

`raw evidence -> canonical fact -> evaluator truth -> absolute normalizer -> policy projection`

The same evaluator and projection contracts handle every admissible case:
known match, known mismatch, partial evidence, missing evidence, disabled factor,
ranking-only factor, and hard-gated factor. Confirmed hard failures reject before
shortlist and ranking inputs are built. Unknown facts remain eligible with an
explicit diagnostic.

Phase 1 does not add location or language to final score composition. It emits
stable `ranking_value` and `ranking_enabled` outputs for Phase 3, which owns
ranking-v2 factor weights, baseline composition, and downstream label migration.

No new geography, language, schema, or policy framework is introduced. Existing
Pydantic extraction models remain the structured LLM boundary. Python standard
library normalization and current config loading remain the runtime foundation.

## Triage

- layer: `change`
- parent: inverse-optimization MASTER specification
- scope: one bounded Phase 1 child specification
- implementation code: out of scope for this document
- implementation plan: drafted separately after approval
- GitNexus: stale during drafting; advisory query returned no relevant process,
  so current source, tests, and stage docs are authoritative

## Current-State Diagnosis

Current source has useful inputs but no complete factor contract:

- `src/fitcv/ingest.py` adapts provider job shapes and preserves complete provider
  payload in `raw_json`; its Indeed adapter flattens nested location to one string.
- `src/fitcv/normalize.py` performs cleanup and deduplication. It does not own
  geography inference or score normalization.
- `src/fitcv/enrich.py` extracts `location_type`, meaning work mode
  (`remote | hybrid | onsite`), not actual city, region, or country.
- `src/fitcv/enrich.py` removes language names from skill entities but does not
  preserve those phrases as language requirements.
- candidate profile already exposes `preferences.locations`,
  `preferences.location_types`, and top-level `languages`; Phase 1 adapts these
  at factor boundary instead of creating a second candidate-profile owner.
- `src/fitcv/rule_filter.py` uses boolean checks and treats `location_type` as its
  only location check.
- both pipeline orchestration paths pass only `profile["preferences"]` to rule
  filter and copy only `marks` from passed records, so candidate languages and
  new factor results would otherwise be lost downstream.
- rule-filter SQLite rows persist reasons and marks but have no owned columns for
  factor results or eligibility-policy identity.
- `src/fitcv/ranking.py` owns current ranking calculations. Phase 1 does not
  modify its factor list or final-score formula.
- `config/policy/eligibility.yaml` and `src/fitcv/fit_factors.py` do not exist.

## Key Deliverables

### Deliverable 1: distinct location and language fact contracts

Actual geography, work mode, and language requirements have separate fields,
versions, extraction statuses, and evidence. Raw provider text remains available
for audit and re-extraction.

### Deliverable 2: one symmetric evaluator and projection envelope

Location and language use same top-level result shapes and same policy projection
function. Factor-specific code owns only factor-specific truth and normalization.

### Deliverable 3: one eligibility-policy SSOT

`config/policy/eligibility.yaml` owns factor mode and mutable numeric values.
`src/fitcv/config.py` owns loading and validation. No environment file, ranking
module, rule filter, or UI surface carries copied eligibility defaults.

### Deliverable 4: hard-gate-safe downstream boundary

`rule_filter` evaluates each factor once, attaches complete diagnostics, rejects
confirmed failures only when mode is `gate_required`, and passes only retained
jobs to later score normalization, shortlist, and ranking stages.

## Canonical Contracts

### Provider-location evidence

Provider adaptation occurs once in `src/fitcv/ingest.py`.

```text
source_location:
  raw_text: string
  city_raw: string | null
  region_raw: string | null
  country_raw: string | null
  provider: string | null
```

Rules:

- keep existing `location` display string for compatibility
- keep `raw_json` unchanged as complete source evidence
- populate structured raw components only when provider supplies them
- do not geocode, infer distance, or convert city names in ingest
- do not put work mode in `source_location`
- `normalize` may trim and collapse whitespace but may not infer geography

### Canonical actual-location fact

`enrich` owns canonical job-side geography:

```text
actual_location:
  raw_text: string
  city: string | null
  region: string | null
  country: string | null
  remote_scope: unrestricted | city | region | country | unknown | not_applicable
  remote_scope_value: string | null
  extraction_status: complete | partial | unknown
  evidence:
    - source_field: location | description | provider_component
      text: string
  extraction_version: actual-location-extraction-v1
```

`location_type` remains unchanged and means work mode only.

Canonicalization uses Python standard library only: Unicode NFKC normalization,
trim, internal-whitespace collapse, and `casefold()` for comparison keys.
Original display text remains in evidence. Diacritics remain significant.

### Canonical language-requirement fact

`enrich` owns zero or more job-side language requirements:

```text
language_requirements[]:
  language: string
  expected_level: a1 | a2 | b1 | b2 | c1 | c2 | native | unspecified
  requirement_type: required | preferred | unspecified
  extraction_status: complete | partial | unknown
  evidence:
    - source_field: description | title | provider_component
      text: string
  extraction_version: language-requirement-extraction-v1
```

Rules:

- language phrases never re-enter canonical skill lists
- one language appears once after deterministic reduction
- duplicate mentions keep strongest requirement type and highest explicit level
- `required` outranks `preferred`, which outranks `unspecified`
- `native` is above `c2` for threshold comparison
- missing level becomes `unspecified`; it is not guessed after validation fails
- invalid data becomes partial or unknown evidence, not fabricated requirement
- LLM-facing Pydantic fields contain raw values and evidence only; the model does
  not supply `extraction_status`
- code derives canonical `extraction_status` after Pydantic validation and
  deterministic reduction
- `complete` means language and requirement type are validated; an explicit or
  legitimately unspecified level is allowed
- `partial` or `unknown` requirements never produce confirmed `unmet`; they use
  the factor `unknown_value` and keep a diagnostic
- canonical list order is language key, requirement priority, then level order
- existing Pydantic structured output is extended; no second parser is added

### Candidate fit-context adapter

`src/fitcv/fit_factors.py` derives transient candidate context from existing
profile SSOT:

```text
candidate_fit_context:
  preferred_locations: normalized values from preferences.locations
  preferred_work_modes: normalized values from preferences.location_types
  language_inventory_status: complete | unknown
  language_capabilities[]:
    language: string
    level: a1 | a2 | b1 | b2 | c1 | c2 | native | unknown
    source: native | level | read_write_speak | unknown
```

Rules:

- `preferred_work_modes` is not consumed by `location_fit`; current declared
  preference logic continues to own work-mode preference
- normalized tokens equal to configured valid work modes are removed from
  `preferred_locations`; current profiles may contain values such as `Remote` in
  both fields, but work-mode tokens are not geography
- absent `languages` key means inventory unknown
- a present valid list, including an empty list, means inventory complete
- a present malformed or non-list `languages` value means inventory unknown with
  a diagnostic; it never becomes an empty complete inventory
- candidate language level precedence is `native`, explicit `level`, then minimum
  valid `read`, `write`, and `speak` when all three exist
- incomplete dimensional levels produce `unknown`, never optimistic level
- adapter does not mutate or persist second profile

### Shared evaluator result

Each factor evaluator returns same immutable logical record:

```text
factor_evaluation:
  factor_id: location_fit | language_fit
  status: pass | fail | unknown | not_applicable
  score: finite float in [0, 1] | null
  confidence: finite float in [0, 1]
  reason_code: string
  evidence: object
  evaluator_version: string
  normalizer_version: string
```

`score` is absolute and versioned. Current job-batch minimum, maximum,
percentile, rank, and candidate count never enter its calculation.

### Shared policy projection

One projection function maps either factor evaluation to:

```text
factor_policy_result:
  factor_id: location_fit | language_fit
  policy_version: string
  mode: disabled | ranking_only | gate_required
  eligibility_decision: retain | reject
  ranking_enabled: boolean
  ranking_value: finite float in [0, 1] | null
  diagnostic_code: string
  evaluation: factor_evaluation
```

Projection table:

| Mode | Evaluation | Eligibility | Ranking enabled | Ranking value |
| --- | --- | --- | --- | --- |
| `disabled` | any | retain | false | null |
| `ranking_only` | pass | retain | true | evaluator score |
| `ranking_only` | fail | retain | true | evaluator score |
| `ranking_only` | unknown | retain | true | factor `unknown_value` |
| `ranking_only` | not applicable | retain | true | factor `not_applicable_value` |
| `gate_required` | fail | reject | false | null |
| `gate_required` | pass | retain | false | null |
| `gate_required` | unknown | retain | false | null |
| `gate_required` | not applicable | retain | false | null |

No factor-specific branch may override this table. Factor-specific logic ends at
evaluator status, score, and reason.

### Eligibility config

Canonical shape:

```yaml
eligibility_policy:
  policy_version: eligibility-v1
  factors:
    location_fit:
      mode: ranking_only
      normalization:
        exact_city: 1.0
        exact_region: 0.8
        exact_country: 0.6
        remote_unrestricted: 1.0
        no_match: 0.0
        unknown_value: 0.5
        not_applicable_value: 0.5
    language_fit:
      mode: ranking_only
      normalization:
        met: 1.0
        unmet: 0.0
        unknown_value: 0.5
        not_applicable_value: 0.5
        requirement_weights:
          required: 1.0
          preferred: 0.5
          unspecified: 0.5
```

Validation rules:

- exactly two factor keys are accepted in Phase 1
- modes are closed enum values
- numeric values are finite and inside `[0, 1]`
- location scores satisfy
  `exact_city >= exact_region >= exact_country >= no_match`
- `required` requirement weight is positive and not below other weights
- unknown keys fail config loading
- missing canonical policy file fails in strict SSOT mode
- environment and ranking config may not shadow `eligibility_policy`
- validated policy fingerprint is SHA-256 over UTF-8 bytes from
  `json.dumps(validated_policy, sort_keys=True, separators=(",", ":"),
  ensure_ascii=False, allow_nan=False)`
- fingerprint payload is the validated `eligibility_policy` mapping only; runtime
  metadata, file paths, and the fingerprint field itself are excluded

Code owns schemas, enums, comparison logic, and projection semantics. Config owns
only mode and mutable numeric policy.

## Factor Semantics

### Location evaluator

Location comparison uses normalized exact tokens only. Candidate preference
values may contain comma- or semicolon-separated city, region, and country
tokens. Tokenization is deterministic and does not call geocoder.

Evaluation order:

1. no preferred locations -> `not_applicable`
2. unrestricted remote scope -> `pass` with `remote_unrestricted`
3. confirmed city match -> `pass` with `exact_city`
4. confirmed region match -> `pass` with `exact_region`
5. confirmed country match -> `pass` with `exact_country`
6. complete actual-location fact with no match -> `fail` with `no_match`
7. otherwise -> `unknown`

When multiple preferences match, highest configured absolute match score wins.
This is factor-internal aggregation, not top-level factor-weight normalization.

### Language evaluator

Language comparison uses exact normalized language keys and fixed CEFR order:

`a1 < a2 < b1 < b2 < c1 < c2 < native`

Per-requirement truth:

- job requirement status `partial` or `unknown` -> `unknown`
- complete requirement and declared candidate level meets or exceeds expected level -> `met`
- complete requirement and declared complete inventory lacks language -> `unmet`
- complete requirement and declared level is below expected level -> `unmet`
- candidate inventory or level is unknown -> `unknown`
- complete requirement with expected level `unspecified` and language present -> `met`

Aggregate status:

1. no requirements -> `not_applicable`
2. any confirmed unmet `required` requirement -> `fail`
3. no failure and any unknown `required` requirement -> `unknown`
4. otherwise -> `pass`

Preferred and unspecified requirements affect ranking score but never create
hard-gate failure. Absolute score is weighted mean of per-requirement normalized
values using config requirement weights. Unknown values use factor-specific
`unknown_value`. Denominator is requirement weight inside one factor; top-level
ranking weights are untouched.

## Artifact Contract

Each evaluated job carries one canonical map:

```text
fit_factor_results:
  location_fit: factor_policy_result
  language_fit: factor_policy_result
eligibility_policy_fingerprint: string
eligibility_decision: retain | reject
eligibility_reason_codes: string[]
```

Rules:

- rule-filter input grain is one enriched row per unique, non-empty canonical
  `job_url`, guaranteed by normalize and checked at the rule-filter boundary
- evaluator runs once per job and factor under one loaded policy context
- `rule_filter` consumes attached results; it does not recompute factor truth
- both passed and rejected diagnostics retain complete factor results
- rejected jobs do not enter shortlist or later score-normalization input
- retained unknown jobs remain observable through reason codes
- result serialization is deterministic and JSON-safe
- Phase 3 consumes `ranking_enabled` and `ranking_value`; Phase 1 does not change
  final score
- `pipeline.py` and `pipeline_stage_runner.py` build candidate fit context once,
  pass it to rule filter, and merge complete passed-record eligibility fields
- native SQLite persistence adds explicit JSON/text columns for factor results,
  policy fingerprint, decision, and reason codes; these facts do not hide inside
  generic `marks_json`
- `src/fitcv_cp/sqlite_store.py` solely owns rule-filter table migration, JSON
  encoding/decoding, delete/replace SQL, and transaction boundaries;
  `rule_filter.py` only builds domain rows and delegates persistence

## Admissible-Case Matrix

| Case | Evaluator result | Projection result |
| --- | --- | --- |
| factor disabled with complete match | preserved typed evaluation | retain, ranking disabled |
| factor disabled with malformed evidence | typed unknown diagnostic | retain, ranking disabled |
| ranking-only confirmed match | pass with absolute score | retain, ranking enabled |
| ranking-only confirmed mismatch | fail with absolute score | retain, ranking enabled |
| ranking-only unknown evidence | unknown | retain, configured unknown value |
| ranking-only no applicable preference/requirement | not applicable | retain, configured not-applicable value |
| hard-gated confirmed match | pass | retain, ranking disabled |
| hard-gated confirmed mismatch | fail | reject, ranking disabled |
| hard-gated unknown evidence | unknown | retain with diagnostic, ranking disabled |
| hard-gated not applicable | not applicable | retain, ranking disabled |
| one required language fails and another is unknown | fail | reject only in hard-gate mode |
| preferred language fails | pass with lower score | never rejected by language gate |
| unrestricted remote job with location preference | pass | policy mode decides projection |
| work mode mismatches but actual city matches | location evaluator passes | work-mode owner handles mismatch |

## Task/Wave Breakdown

### Wave 1: close fact, config, and ownership contracts

**Purpose:**
- establish names, owners, enums, versions, and policy boundary before behavior changes

**Primary targets:**
- `config/policy/eligibility.yaml`
- `src/fitcv/config.py`
- `src/fitcv/fit_factors.py`
- `tests/test_config.py`
- `tests/test_fit_factors.py`

**Steps:**
- [ ] add canonical eligibility-policy file and loader registry entry
- [ ] add strict schema, enum, range, ordering, and unknown-key validation
- [ ] define shared evaluator and policy-result records without class hierarchy
- [ ] define candidate fit-context adapter over existing profile fields
- [ ] define evaluator, normalizer, and policy version constants
- [ ] define exact SHA-256 canonical-JSON eligibility-policy fingerprint payload
  and one golden hash vector

**Verification:**
- [ ] invalid modes, values, ordering, keys, and shadows fail at config boundary
- [ ] same policy content yields same fingerprint independent of YAML key order
- [ ] both factors serialize through same result shapes

**Exit Criteria:**
- one SSOT owns policy values and one module owns executable factor semantics

### Wave 2: preserve source location and extract canonical facts

**Purpose:**
- retain provider evidence and produce durable location/language facts without skill leakage

**Primary targets:**
- `src/fitcv/ingest.py`
- `src/fitcv/normalize.py`
- `src/fitcv/enrich.py`
- `tests/test_ingest.py`
- `tests/test_normalize.py`
- `tests/test_enrich.py`

**Steps:**
- [ ] adapt provider-native location components into `source_location` once
- [ ] preserve current `location`, `location_type`, and `raw_json` contracts
- [ ] extend existing Pydantic output with bounded location/language models
- [ ] keep extraction status out of LLM-facing fields and compute it in code
- [ ] reduce duplicate language requirements deterministically
- [ ] retain language evidence outside required/preferred skill entities
- [ ] include new extraction contracts in enrich fingerprint and reuse compatibility

**Verification:**
- [ ] Indeed nested and LinkedIn string locations produce same fact shape
- [ ] raw input remains replayable after structured extraction
- [ ] invalid nested output degrades to partial or unknown without dropping job
- [ ] language phrases appear in requirements and not canonical skill lists
- [ ] unchanged job is not reused across changed extraction contract version

**Exit Criteria:**
- actual location and language requirements are durable, versioned job facts

### Wave 3: implement absolute evaluators and symmetric projection

**Purpose:**
- turn canonical facts into uniform truth and policy results

**Primary targets:**
- `src/fitcv/fit_factors.py`
- `tests/test_fit_factors.py`

**Steps:**
- [ ] adapt candidate location and language context at function boundary
- [ ] implement location evaluator with city, region, country, and remote cases
- [ ] implement language evaluator with CEFR threshold and requirement-type rules
- [ ] apply versioned absolute normalizers without cohort data
- [ ] apply one shared mode/status projection table
- [ ] emit deterministic evidence and reason codes for every result

**Verification:**
- [ ] exhaustive factor-mode-by-status matrix matches projection table
- [ ] same fact/context/policy tuple returns byte-equivalent JSON-safe result
- [ ] input ordering does not change language reduction, score, or diagnostics
- [ ] changing unrelated jobs in batch does not change evaluated job values

**Exit Criteria:**
- every admissible input returns typed result; no factor-specific projection branch remains

### Wave 4: integrate hard-gate boundary and downstream handoff

**Purpose:**
- reject confirmed failures once and expose ranking-ready outputs without composing rank

**Primary targets:**
- `src/fitcv/rule_filter.py`
- `src/fitcv/pipeline.py`
- `src/fitcv/pipeline_stage_runner.py`
- `src/fitcv_cp/sqlite_store.py`
- `tests/test_rule_filter.py`
- `tests/test_pipeline.py`
- `tests/test_pipeline_stage_resume_parity.py`
- `tests/test_fitcv_cp/test_sqlite_store.py`

**Steps:**
- [ ] evaluate location and language once for each enriched job
- [ ] build candidate fit context once from full profile in each orchestration path
- [ ] pass candidate context explicitly; missing context yields typed unknown
- [ ] attach canonical factor results to passed and rejected records
- [ ] convert hard-gated failures into stable reject reason codes
- [ ] retain hard-gated unknown and not-applicable cases with diagnostics
- [ ] ensure only retained jobs reach shortlist and later score-normalization inputs
- [ ] merge complete eligibility fields into passed jobs in both orchestration paths
- [ ] persist eligibility fields through one `sqlite_store.py` replace operation
  with explicit additive SQLite columns
- [ ] keep existing work-mode check separate during compatibility window
- [ ] leave ranking feature list and final-score formula unchanged

**Verification:**
- [ ] gate-required failure is absent from shortlist/ranking input fixtures
- [ ] unknown hard-gate result remains present and marked
- [ ] ranking-only failure remains present with `ranking_enabled: true`
- [ ] disabled factor never rejects and never emits ranking value
- [ ] `location_type_excluded` does not consume actual-location result
- [ ] full pipeline and stage-runner paths preserve identical result payloads
- [ ] stored filter rows round-trip factor results and policy identity exactly

**Exit Criteria:**
- eligibility boundary is deterministic, observable, and upstream of ranking inputs

### Wave 5: synchronize documentation and validate scope

**Purpose:**
- align human-owned stage and feature contracts, then regenerate managed outputs

**Primary targets:**
- `docs/architecture.md`
- `docs/configuration.md`
- `docs/pipeline.md`
- `docs/stages/normalize.source.yaml`
- `docs/stages/enrich.source.yaml`
- `docs/stages/rule_filter.source.yaml`
- `docs/features/cv_system/feature.source.yaml`

**Steps:**
- [ ] document actual location versus work mode
- [ ] document candidate language and location boundary inputs
- [ ] document modes, unknown behavior, and hard-gate ordering
- [ ] document Phase 3 ownership of ranking composition
- [ ] update human-owned source YAML before generated outputs
- [ ] regenerate architecture metadata and validate planning lifecycle

**Verification:**
- [ ] generated feature, stage, and lineage outputs match source docs
- [ ] no generated contract is hand-edited as authority
- [ ] source search finds no second eligibility-policy owner

**Exit Criteria:**
- docs and generated architecture surfaces describe implemented contract exactly

## Design Decisions

### Decision: preserve work mode and actual geography separately

- context: current `location_type` means remote, hybrid, or onsite
- choice: retain `location_type`; add `source_location` evidence and
  `actual_location` canonical geography
- alternatives considered:
  - rename or overload `location_type`
  - parse city from `location_type`
- impact:
  - current work-mode behavior remains compatible
  - location factor no longer conflates city with work mode

### Decision: adapt provider structures at ingest boundary

- context: Indeed supplies nested city/country data before normalization
- choice: adapt native provider fields once in `ingest.py`, then pass one source
  evidence shape downstream
- alternatives considered:
  - reparse `raw_json` in enrich
  - add provider branches to factor evaluator
- impact:
  - downstream extraction stays provider-neutral
  - provider-specific code does not spread

### Decision: use current Pydantic boundary and standard library normalization

- context: structured extraction uses Pydantic; runtime needs exact normalization
  and ordinal comparison only
- choice: extend installed Pydantic models and use `unicodedata`, `re`, and
  string methods
- alternatives considered:
  - add geocoder, language library, fuzzy matcher, or schema framework
- impact:
  - no new dependency or network behavior
  - uncertain aliases remain explicit rather than guessed truth

### Decision: separate truth, absolute normalization, and policy mode

- context: hard gates and ranking inputs need same facts but different actions
- choice: evaluator determines truth, normalizer assigns stable values, shared
  projector applies mode
- alternatives considered:
  - separate hard-filter and ranking implementations
  - factor-specific policy branches
- impact:
  - one admissible-case algebra covers both factors
  - hard-gate changes do not rewrite evaluator semantics

### Decision: unknown hard constraints pass with diagnostics

- context: extraction or candidate profile may be incomplete
- choice: `gate_required` rejects only confirmed `fail`; `unknown` and
  `not_applicable` remain eligible
- alternatives considered:
  - fail closed on missing data
  - silently treat unknown as pass
- impact:
  - uncertainty does not create false exclusion
  - operators can inspect why gate did not decide

### Decision: normalizers are absolute and versioned

- context: cohort min-max or percentile scaling changes same job when batch changes
- choice: categorical match and CEFR satisfaction values come from one versioned
  policy independent of cohort
- alternatives considered:
  - min-max normalization within run
  - percentile or rank normalization
- impact:
  - scores are reproducible across runs and admissible batch sizes

### Decision: Phase 1 emits rank inputs but does not compose rank

- context: ranking-v2 needs separate overlap ablation and label-migration gate
- choice: expose `ranking_enabled` and `ranking_value`; defer weights and final
  score to Phase 3
- alternatives considered:
  - insert location/language into current ranking immediately
- impact:
  - eligibility can ship without changing `strong|stretch|skip`

## Invariants

1. `location_type` means work mode only.
2. `actual_location` means geography only.
3. Raw provider payload and raw location text remain replayable.
4. Language requirements never become canonical skills.
5. Candidate profile remains sole owner of candidate locations and languages;
   boundary adaptation removes work-mode tokens from geographic preferences.
6. `fit_factors.py` adapts candidate data but persists no shadow profile.
7. Both factors return same evaluator and policy-result shapes.
8. Every input returns one typed admissible result; malformed data cannot escape
   as untyped exception or silent default.
9. `gate_required` rejects confirmed `fail` only.
10. Unknown hard-constraint facts remain eligible with diagnostic.
11. Disabled factors cannot reject or rank.
12. Hard-gated factors cannot rank.
13. Ranking-only factors cannot reject.
14. Factor scores, when present, are finite and inside `[0, 1]`.
15. Same input and versions produce same score across runs and cohorts.
16. Current batch extrema, ranks, and sizes never enter factor normalizers.
17. Factor-internal aggregation never changes top-level ranking weights.
18. Top-level factor weights are not normalized per job.
19. Rejected jobs leave candidate pool before downstream score-normalization inputs,
    shortlist, and ranking.
20. Evaluator output is computed once per job and reused downstream.
21. Both pipeline orchestration paths preserve identical eligibility payloads.
22. Config owns mutable numeric policy; code owns semantics and schemas.
23. Eligibility policy has one canonical file and one exact canonical-JSON fingerprint.
24. SQLite stores eligibility facts in owned columns, not generic marks, and
    `sqlite_store.py` is the sole SQL/codec owner.
25. Phase 1 does not modify final ranking formula or fit-label thresholds.
26. No new runtime dependency, geocoder, fuzzy matcher, or policy framework is added.

## Acceptance Criteria

- provider-native location components are preserved without losing `raw_json`
- `actual_location`, `location_type`, and source-location evidence are distinct
- enrichment emits deterministic actual-location and language-requirement facts
- candidate adapter consumes existing locations and languages without changing ownership
- config loader validates canonical policy and rejects malformed or shadowed policy
- location and language return same result envelopes for every case
- exhaustive projection tests cover three modes by four evaluator statuses
- confirmed language or location failure rejects only under `gate_required`
- unknown and not-applicable hard-gate results remain eligible with reason code
- ranking-only failures remain eligible with absolute score
- disabled and hard-gated factors emit `ranking_enabled: false`
- same job value is unchanged when unrelated batch jobs are added or removed
- language requirements do not appear in canonical skill lists
- rejected jobs are absent from downstream shortlist and ranking inputs
- normal and resumed/staged pipeline paths preserve same eligibility payload
- SQLite filter rows round-trip factor results and policy fingerprint
- current ranking feature list, score formula, and fit-label thresholds are unchanged
- human-owned stage and feature docs change before generated sync
- focused tests and repo validators pass

## Non-Goals

- add location or language weights to final ranking score in Phase 1
- change `strong`, `stretch`, or `skip`
- remove BM25/BM25F; Phase 2 owns that independent cleanup
- change vector shortlist behavior
- add distance, commute time, coordinates, radius search, timezone, visa, work
  authorization, relocation, or tax-residency logic
- add fuzzy city matching or global geographic ontology
- translate arbitrary location or language names through new dependency
- infer candidate legal eligibility from preferred locations
- infer language ability from nationality, residence, name, or job history
- make preferred language failure a hard rejection
- fail closed when extraction evidence is unknown
- add admin UI for policy editing in first implementation; canonical YAML setting
  is sufficient
- create generic factor plugins, evaluator registries, factories, or DSLs
- modify candidate-profile storage unless implementation evidence proves current
  boundary adapter cannot represent required facts

## Risks and Mitigations

| Risk | Mitigation |
| --- | --- |
| city and work mode remain conflated | separate fields, schemas, tests, and stage ownership |
| provider adapter loses structured location detail | retain raw provider JSON and source components at ingest boundary |
| extraction invents city, country, or level | validate bounded values; preserve evidence; degrade to partial or unknown |
| language leaks back into skill matching | dedicated requirement field plus negative skill-list tests |
| localized names do not exact-match | retain evidence and explicit mismatch/unknown; add aliases only after measured cases |
| incomplete language data causes false rejection | absent inventory is unknown; incomplete level is unknown; unknown gate passes |
| empty language list is interpreted inconsistently | key-present inventory is complete; key-absent inventory is unknown; test both |
| remote job is rejected by office city | unrestricted remote is explicit pass; restricted/unknown scope stays typed |
| score changes with batch composition | absolute normalizers plus cohort-invariance tests |
| config becomes executable DSL | closed schema; code owns projection and comparison semantics |
| rule filter and ranking recompute different values | attach one canonical result and require downstream reuse |
| main and staged pipeline paths diverge | change and parity-test both orchestration paths in same wave |
| eligibility evidence is hidden in generic marks | add explicit additive SQLite columns and round-trip tests |
| hard gate distorts later normalization | reject before shortlist and score-normalization inputs |
| factors overlap holistic AI score | Phase 1 does not compose rank; Phase 3 requires ablation and migration gate |
| new fields invalidate enrich reuse silently | include extraction schema and versions in enrich fingerprint |

## Validation Plan

- proof target: policy ownership is singular and validated
  - method: config tests for canonical load, missing file, invalid mode, numeric
    range, ordering, unknown key, env shadow, and key-order fingerprint invariance
  - evidence: only `config/policy/eligibility.yaml` supplies mutable values
- proof target: provider adaptation preserves source truth
  - method: ingest and normalize tests for LinkedIn string, Indeed nested, absent,
    malformed, and raw-JSON replay cases
  - evidence: one source-location shape reaches enrich while raw payload remains
- proof target: extraction creates durable distinct facts
  - method: Pydantic tests for complete, partial, duplicate, malformed, missing,
    remote, and multilingual descriptions
  - evidence: location, work mode, and language requirements serialize separately
- proof target: language requirements do not contaminate skills
  - method: enrich fixtures containing Python, English, German B2, and soft skills
  - evidence: Python remains skill; English and German become requirements only
- proof target: evaluator algebra is total and symmetric
  - method: table-driven tests over both factors, all statuses, all modes,
    reordered inputs, duplicate inputs, and malformed inputs
  - evidence: every case returns typed result and shared projection has no exception
- proof target: hard-gate unknown policy is safe
  - method: rule-filter tests for pass, fail, unknown, and not-applicable under
    `gate_required`
  - evidence: only confirmed fail rejects; retained uncertain cases have diagnostics
- proof target: normalization is globally stable
  - method: evaluate same job/context under different cohorts and input orders
  - evidence: status, score, ranking value, reason, and fingerprint are identical
- proof target: downstream boundary excludes rejected jobs
  - method: pipeline fixture with retained, rejected, and unknown jobs through rule
    filter into shortlist/ranking input construction
  - evidence: rejected ID never appears downstream; retained unknown ID remains
- proof target: orchestration paths remain symmetric
  - method: run same enriched jobs and profile through main pipeline and stage runner
  - evidence: passed jobs, rejected jobs, factor results, fingerprint, and reasons match
- proof target: eligibility evidence is durably owned
  - method: SQLite schema-upgrade and round-trip tests for old table, new table,
    passed rows, rejected rows, unknown results, and null-safe compatibility
  - evidence: factor-result JSON and policy identity round-trip without using marks
- proof target: ranking behavior is unchanged in Phase 1
  - method: existing ranking and fit-label regressions before and after artifact attachment
  - evidence: same current inputs yield same score, order, and labels
- proof target: docs remain source-first
  - method: update stage/feature source YAML, generate metadata, then run check mode
  - evidence: generated stage, feature, lineage, and discovery files match source
- proof target: repo planning and contracts remain valid
  - method: fast hook validator, planning lifecycle, repo-contract validator,
    architecture check, and `git diff --check`
  - evidence: all commands exit zero

Focused implementation validation should include:

```text
python -m pytest tests/test_config.py tests/test_ingest.py tests/test_normalize.py
python -m pytest tests/test_enrich.py tests/test_fit_factors.py tests/test_rule_filter.py
python -m pytest tests/test_pipeline.py tests/test_pipeline_stage_resume_parity.py
python -m pytest tests/test_fitcv_cp/test_sqlite_store.py tests/test_ranking.py
python scripts/hooks/run_validator.py --fast
python scripts/validate_planning_lifecycle.py
python tools/docs/generate_architecture_metadata.py --check
python scripts/validate_repo_contracts.py --fast
git diff --check
```

## Completion Criteria

This specification is complete when:

1. MASTER Phase 1 scope and child spec agree on owners, modes, boundaries, and deferrals
2. every fact, evaluator status, normalizer, projection, and admissible case has one contract
3. acceptance, non-goals, risks, and proof evidence are implementation-ready
4. plan-document review returns `ready` after blocking findings are fixed
5. planning lifecycle, architecture check, repo-contract validator, and
   `git diff --check` pass
6. spec is approved for separate implementation-plan drafting

Phase 1 implementation is complete only when:

1. approved implementation plan is terminal
2. focused tests prove all evaluator and projection cases
3. rejected jobs are proven absent from downstream ranking inputs
4. ranking regressions prove no Phase 1 score or label change
5. human-owned docs and generated architecture outputs are synchronized
6. no competing eligibility-policy owner or copied numeric default remains

Canonical source-of-truth:

<LINK>
- `docs/superpowers/specs/2026-07-14-22-25-fitcv-inverse-optimization-master-ssot-symmetry-spec.md`
- `docs/operating_system/governance/repo-governance.md`
- `docs/operating_system/lifecycle/doc-system-lifecycle.md`
- `docs/operating_system/templates/detailed-specification-template.md`
- `scripts/validate_planning_lifecycle.py`
</LINK>
