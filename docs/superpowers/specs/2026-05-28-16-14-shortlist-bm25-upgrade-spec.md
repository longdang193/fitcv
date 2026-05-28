---
layer: change
artifact_type: spec
status: completed
template_id: detailed-specification
name: shortlist-bm25-upgrade-path
parent_thread: workstream-pipeline-efficiency-and-reuse.efficiency-reuse-late-stage-gating
targets:
  - src/fitcv/vector_search.py
  - src/fitcv/pipeline.py
  - src/fitcv/config.py
  - config/shortlist_lexical.yaml
  - tests/test_vector_search.py
  - tests/test_pipeline.py
related_features:
  - cv_system
  - pipeline_performance
related_stages:
  - shortlist
---

## Goal
Define MVP-v1 shortlist lexical retrieval that includes protected terms, weighted component-derived BM25 terms, and phrase boosts, while preserving SSOT, symmetry, and invariance.

## Key Deliverables

### Canonical query derivation contract
Single canonical source for shortlist intent components reused by vector and BM25 channels.

### Deterministic lexical term builder contract
Deterministic lexical term derivation from canonical components, including unigrams, key role/title n-grams, field weighting, and protected exact terms.

### Migration and verification guardrails
MVP rollout with deterministic observability hashes and invariance/symmetry/protected-term regression tests.

## Task/Wave Breakdown

### Wave 1: Source-first analysis
**Purpose:** lock current retrieval/query behavior and contracts before MVP-v1 changes.

**Steps:**
- [x] map current shortlist query component builder and vector query text rendering in `src/fitcv/vector_search.py`
- [x] map current shortlist stage orchestration and artifact/debug outputs in `src/fitcv/pipeline.py`
- [x] map current lexical/BM25 tokenization behavior and protected-term/phrase gaps
- [x] identify config keys and compatibility fallbacks touching shortlist query construction

**Verification:**
- [x] current-state behavior documented with symbol references and no unresolved ambiguity

**Exit Criteria:**
- deterministic current-state baseline captured, including known reuse behaviors

### Wave 2: Decision closure
**Purpose:** freeze MVP-v1 lexical design and contracts before implementation.

**Steps:**
- [x] define canonical component schema (SSOT) and deterministic ordering rules
- [x] define lexical term derivation rules from components: unigrams + key role/title bigrams/trigrams
- [x] define protected-term derivation rules from manual seed + taxonomy candidates
- [x] define field-weighting contract (`target_role/headline` high, `skills` high, `recent_roles` medium, `domains/location_types` low)
- [x] define phrase-boost contract for exact role/title phrases with deterministic cap
- [x] define normalization/tokenization policy with protected exact-term preservation (no drop/stem/mutate/split)
- [x] define fallback/compatibility behavior for missing fields and empty components

**Verification:**
- [x] each contract decision has explicit rationale and rejected alternatives

**Exit Criteria:**
- no open decision blocks implementation plan handoff

### Wave 3: Validation and approval readiness
**Purpose:** make proof obligations explicit for safe rollout.

**Steps:**
- [x] define invariance test matrix (same profile+config => identical component hash/text hash/term hash/protected hash)
- [x] define symmetry tests (vector and BM25 share same canonical component payload)
- [x] define protected-term tests (`ml`, `etl`, `dbt`, `gcp`, `sql`, `nlp`) and taxonomy-derived candidate stability tests
- [x] define phrase-boost tests (exact role phrase outranks split-token-only match, bounded contribution)
- [x] define observability evidence fields and rollout success thresholds

**Verification:**
- [x] validation plan demonstrates deterministic and relevance-safe behavior

**Exit Criteria:**
- specification ready for implementation execution

## Design Decisions

### Decision: SSOT shortlist intent payload
- context: vector and lexical channels diverged risk without strict shared source
- choice: centralize shortlist intent builder returning canonical components used by both channels
- alternatives considered:
  - separate vector text builder and BM25 builder from raw profile (rejected: drift risk)
  - BM25 tokenize full rendered blob without component contract (rejected: weak symmetry guarantees)
- impact:
  - shared contract surface in shortlist retrieval module
  - deterministic debug hashes available per run

### Decision: MVP-v1 includes weighted lexical terms from same components
- context: lexical relevance should improve now while keeping deterministic behavior
- choice: derive unigrams + key role/title n-grams from canonical components and apply deterministic field weighting
- alternatives considered:
  - raw blob tokenize only (rejected: weak signal control)
  - postpone weighting/phrase boost (rejected: misses original MVP intent)
- impact:
  - stronger lexical relevance with deterministic controls
  - explicit weighting/phrase behavior testability

### Decision: Taxonomy-assisted protected-term sourcing with deterministic filter
- context: manual protected-term maintenance should stay low-admin
- choice: derive protected-term candidates from taxonomy synonym files plus manual seed, then apply deterministic filter
- alternatives considered:
  - manual list only (rejected: operational drift)
  - unrestricted taxonomy import (rejected: noisy/non-fragile terms)
- impact:
  - admin effort reduced
  - deterministic and auditable protected-term set

### Decision: Phrase boost contract for role titles
- context: exact title phrase match must outperform fragmented token coincidence
- choice: deterministic phrase list from role/title fields with bounded boost contribution
- alternatives considered:
  - no phrase boost (rejected: weak role specificity)
  - unbounded phrase stacking (rejected: score inflation risk)
- impact:
  - better role precision while controlled score behavior

### Decision: Config path contract for lexical policy SSOT
- context: repo has both `config/` and `configs/`, risk of split policy source
- choice: store shortlist lexical policy at `config/shortlist_lexical.yaml` in MVP-v1 because taxonomy synonym SSOT already lives under `config/taxonomy/`
- alternatives considered:
  - `configs/shortlist_lexical.yaml` (rejected for MVP-v1: cross-root indirection and drift risk)
- impact:
  - one config root for taxonomy + lexical protected-term policy in this lane
  - deterministic path resolution in code and tests

## Normative Scoring and Tokenization Contract (MVP-v1)

### Canonical Component and Term Build Sequence
1. Build canonical components in fixed field order:
   - `headline`, `target_role`, `recent_roles`, `skills`, `role_families`, `domains`, `location_types`
2. Normalize values for matching:
   - trim
   - lowercase
   - stable dedupe preserving first-seen order
3. Build term families from normalized components:
   - unigrams from all non-empty fields
   - key bigrams/trigrams from `headline`, `target_role`, and `recent_roles`
4. Build protected-term set:
   - manual seed + taxonomy-derived candidates after deterministic filter
   - deterministic sorted final set
5. Apply protected-term tokenization overrides before stopword/min-length/stemming logic.

### Protected-Term Deterministic Filter
- Input sources:
  - manual seed from `config/shortlist_lexical.yaml`
  - taxonomy candidates from:
    - `config/taxonomy/domain_synonyms.yaml`
    - `config/taxonomy/role_family_synonyms.yaml`
    - `config/taxonomy/skill_synonyms.yaml`
- Algorithm (fixed order):
1. lowercase normalize candidate
2. reject empty candidate
3. reject candidate containing whitespace (single token required)
4. include if any:
   - in manual seed
   - length <= configured `max_len_auto_protect`
   - contains one of configured protected punctuation markers (`+`, `#`, `.`)
   - contains at least one digit
5. apply stopword/noise exclusion list to non-manual candidates only
6. union manual + filtered taxonomy candidates
7. sort lexicographically for final runtime set

### Field Weighting and Lexical Score Formula
- Field weights (defaults, config overridable):
  - `target_role`: 3.0
  - `headline`: 3.0
  - `skills`: 2.5
  - `recent_roles`: 1.5
  - `role_families`: 1.0
  - `domains`: 0.75
  - `location_types`: 0.5
- BM25 combination contract:
  - If BM25F implementation exists in current stack: use BM25F with above per-field weights.
  - If BM25F unavailable: fallback to weighted-sum of per-field BM25 scores:
    - `lexical_base_score(doc) = sum_f(weight_f * bm25_f(doc, query_terms_f))`
  - Implementation MUST choose one path by explicit config key and log chosen mode in shortlist debug artifact.

### Phrase Boost Contract
- Phrase source fields: `headline`, `target_role`, `recent_roles`
- Phrase list: deterministic unique bigrams/trigrams from source fields.
- Phrase match condition: exact phrase substring match in normalized job text.
- Boost accumulation rule:
  - compute `phrase_hits` set (deduped)
  - `phrase_boost_raw = sum(boost_per_phrase[p] for p in phrase_hits)`
  - `phrase_boost = min(phrase_boost_raw, phrase_boost_cap)`
- Final lexical score:
  - `lexical_score(doc) = lexical_base_score(doc) + phrase_boost`
- Required default caps:
  - `phrase_boost_cap` <= 20% of max observed `lexical_base_score` in shortlist candidate set for same query execution.

### Deterministic Tie-break Contract
For equal `lexical_score` values, ordering MUST be:
1. higher `lexical_base_score`
2. higher phrase-hit count
3. lexicographic ascending `job_url`

## Invariants
- Same input profile + same config + same component-builder version MUST produce identical canonical components.
- Same canonical components MUST drive both vector query text and BM25 lexical term derivation.
- Canonical field order and dedupe order MUST be stable across runs.
- Protected terms MUST remain exact and unstemmed in lexical derivation.
- Protected-term final set MUST be deterministic (same config and taxonomy inputs => same sorted set).
- Phrase boosts MUST be deterministic and bounded.
- BM25 shortlist search universe MUST remain constrained to `passed_job_urls`.

## Acceptance Criteria
- Canonical component builder exists and is only source for shortlist query intent.
- Vector query text and BM25 lexical term builder both consume same component object in shortlist flow.
- `config/shortlist_lexical.yaml` defines lexical/protected-term policy SSOT.
- BM25 lexical term builder outputs unigrams + key role/title n-grams with configured field weights.
- Protected exact term set enforced for acronyms/skills, including taxonomy-derived fragile terms.
- Phrase boosts applied for exact role/title phrases with bounded contribution.
- Deterministic tie-break ordering is implemented and tested.
- Invariance and symmetry tests pass in CI.

## Non-Goals
- No reranker model prompt/schema changes.
- No non-shortlist stage contract changes.
- No advanced semantic expansion beyond deterministic component-derived terms.

## Risks and Mitigations
- Risk: weighted/phrase settings overfit lexical ranking.
  - Mitigation: bounded weights/boosts + sensitivity tests.
- Risk: hidden drift between canonical builder and downstream consumers.
  - Mitigation: single public builder interface + hash assertions in tests.
- Risk: taxonomy noise pollutes protected set.
  - Mitigation: single-token + fragility filter + stopword/noise exclusions.

## Validation Plan
- proof target: SSOT shared source is enforced
  - method: unit tests inspect both vector and lexical call paths consume same component payload object/serialization
  - evidence: passing tests in `tests/test_vector_search.py` and shortlist pipeline tests
- proof target: invariance guarantee
  - method: deterministic snapshot/hash tests over repeated runs
  - evidence: stable `components_hash`, `canonical_text_hash`, `bm25_terms_hash`, `protected_terms_hash`
- proof target: symmetry between channels
  - method: integration test asserts vector query render and BM25 lexical builder input equality
  - evidence: test assertion logs and artifact payloads
- proof target: protected term exactness
  - method: tokenizer tests for protected terms
  - evidence: tests showing `dbt/sql/gcp/ml/etl/nlp` preserved exact
- proof target: phrase boost behavior
  - method: scoring tests with exact phrase vs split-token cases and tie-break checks
  - evidence: expected lexical ordering with bounded deltas and stable equal-score ordering

## Completion Criteria
1. all Key Deliverables are satisfied
2. implementation plan aligned to MVP-v1 scope is approved
3. verification evidence for invariance/symmetry/protected terms/phrase boosts exists and passes








## Scope Clarification (Post-Implementation)

- MVP-v1 completed in this lane delivers deterministic canonical BM25 term payload construction and shortlist observability/debug hashes.
- MVP-v1 does not add runtime BM25 retrieval-channel execution or RRF fusion-based shortlist ordering.
- Hybrid retrieval (`vector` + `bm25` + `hybrid_rrf`) remains tracked by:
  - `docs/superpowers/specs/2026-05-28-14-09-shortlist-hybrid-retrieval-spec.md`
  - `docs/superpowers/plans/2026-05-28-14-14-shortlist-hybrid-retrieval-plan.md`

