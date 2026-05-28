---
layer: change
artifact_type: plan
status: completed
template_id: implementation-plan
name: shortlist-bm25-upgrade-implementation
parent_thread: workstream-pipeline-efficiency-and-reuse.efficiency-reuse-late-stage-gating
parent_spec: docs/superpowers/specs/2026-05-28-16-14-shortlist-bm25-upgrade-spec.md
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
Implement MVP-v1 shortlist lexical behavior: canonical SSOT component builder shared by vector + lexical channels, weighted component-derived BM25 terms, protected exact terms, phrase boosts, and invariance/symmetry verification.

## Key Deliverables

### Shared shortlist intent contract in production code
`src/fitcv/vector_search.py` exposes canonical component payload and deterministic rendering APIs used by both vector and lexical paths.

### Lexical SSOT policy with low admin overhead
Single lexical config source defines manual seed + taxonomy derivation + deterministic filter, weighted-field settings, phrase-boost caps, and scoring-mode selection.

### Evidence-backed regression safety
Unit/integration coverage for invariance, symmetry, protected terms, phrase boosts, deterministic tie-breaks, and shortlist-lane behavior under reuse/fallback conditions.

## Task/Wave Breakdown

### Task 1: Canonicalize shortlist intent payload APIs
**Purpose:** establish single source-of-truth component model reused by both retrieval channels.

**Files:**
- Inspect: `src/fitcv/vector_search.py`
- Modify: `src/fitcv/vector_search.py`
- Verify: `tests/test_vector_search.py`

**Preconditions:**
- existing shortlist query component extraction and rendered text behavior understood
- schema-compatible output for existing vector query code path

**Steps:**
- [x] Introduce/normalize one canonical component builder function with fixed field order:
  - `headline`, `target_role`, `recent_roles`, `skills`, `role_families`, `domains`, `location_types`
- [x] Ensure deterministic list normalization (trim, dedupe, stable order, empty-field behavior)
- [x] Keep existing rendered query text generation consuming canonical components only
- [x] Add deterministic hash helper(s) for component payload and rendered canonical text

**Verification:**
- [x] `python -m pytest -q tests/test_vector_search.py -k "component or query"`

**Exit Criteria:**
- vector path obtains its query text only from canonical component payload

### Task 2: Add lexical policy config and deterministic protected-term builder
**Purpose:** implement low-admin deterministic lexical policy foundation.

**Files:**
- Modify: `config/shortlist_lexical.yaml`
- Modify: `src/fitcv/config.py`
- Modify: `src/fitcv/vector_search.py`
- Verify: `tests/test_vector_search.py`

**Preconditions:**
- Task 1 complete
- taxonomy files readable:
  - `config/taxonomy/domain_synonyms.yaml`
  - `config/taxonomy/role_family_synonyms.yaml`
  - `config/taxonomy/skill_synonyms.yaml`

**Steps:**
- [x] Add lexical SSOT config with:
  - manual seed list (`ml`, `etl`, `dbt`, `gcp`, `sql`, `nlp`)
  - taxonomy derive toggle and source file list
  - deterministic protected-term filter knobs (`max_len_auto_protect`, punctuation markers, stopword/noise list)
  - field weights and phrase-boost cap settings
  - scoring mode key (`bm25f` or `weighted_sum_fallback`)
- [x] Implement deterministic protected-term builder using fixed algorithm order:
  1. lowercase normalize candidate
  2. reject empty
  3. reject whitespace-containing tokens
  4. include if manual seed OR (length/punctuation/digit criteria)
  5. apply stopword/noise exclusion to non-manual candidates only
  6. union manual + filtered taxonomy candidates
  7. deterministic lexicographic sort output
- [x] Expose debug output fields: `protected_terms_hash`, `protected_terms_count`

**Verification:**
- [x] `python -m pytest -q tests/test_vector_search.py -k "protected or taxonomy or hash"`

**Exit Criteria:**
- protected-term set deterministic from config + taxonomy inputs

### Task 3: Implement weighted BM25 term builder from canonical components
**Purpose:** satisfy MVP-v1 lexical behavior with symmetry/invariance.

**Files:**
- Modify: `src/fitcv/vector_search.py`
- Verify: `tests/test_vector_search.py`

**Preconditions:**
- Task 2 complete

**Steps:**
- [x] Build deterministic unigram terms from canonical components
- [x] Build key bigram/trigram phrases from role/title fields
- [x] Apply field-weighting contract:
  - high: `target_role`, `headline`, `skills`
  - medium: `recent_roles`
  - low: `domains`, `location_types`
- [x] Implement explicit scoring mode branch from config:
  - `bm25f` mode: BM25F using configured field weights
  - `weighted_sum_fallback` mode: `lexical_base_score(doc) = sum_f(weight_f * bm25_f(doc, query_terms_f))`
- [x] Enforce protected-term tokenizer policy:
  - no min-length drop for protected terms
  - no stemming/mutation/splitting for protected terms
- [x] Implement phrase boost exactly per spec contract:
  - deterministic phrase set
  - deduped phrase-hit accumulation
  - bounded cap rule
- [x] Implement deterministic tie-break order for equal lexical scores:
  1. higher `lexical_base_score`
  2. higher phrase-hit count
  3. lexicographic ascending `job_url`

**Verification:**
- [x] `python -m pytest -q tests/test_vector_search.py -k "bm25 or token or protected or phrase or weight"`

**Exit Criteria:**
- lexical term payload derives exclusively from canonical components with configured weighting, phrase boost, and tie-break behavior

### Task 4: Integrate shortlist-stage orchestration and observability
**Purpose:** wire lexical artifacts into shortlist execution with deterministic evidence surfaces.

**Files:**
- Modify: `src/fitcv/pipeline.py`
- Verify: `tests/test_pipeline.py`

**Preconditions:**
- Task 3 complete

**Steps:**
- [x] Thread canonical component payload + lexical term debug payload through shortlist stage context
- [x] Emit shortlist debug/trace fields:
  - `components_hash`
  - `canonical_text_hash`
  - `bm25_terms_hash`
  - `protected_terms_hash`
  - lexical policy version/mode
  - scoring mode actually used
- [x] Preserve shortlist universe constraint (`passed_job_urls`)

**Verification:**
- [x] `python -m pytest -q tests/test_pipeline.py -k "shortlist or vector"`

**Exit Criteria:**
- shortlist artifacts provide deterministic evidence for symmetry/invariance checks

### Task 5: Add invariance/symmetry/protected-term/phrase regression tests
**Purpose:** lock contracts with executable proof.

**Files:**
- Modify: `tests/test_vector_search.py`
- Modify: `tests/test_pipeline.py`

**Preconditions:**
- Tasks 1-4 complete

**Steps:**
- [x] Add invariance tests: same profile/config => identical components/text/term/protected hashes
- [x] Add symmetry tests: vector render and BM25 lexical builder consume same canonical payload
- [x] Add protected-term tests for exact retention (`ml`, `etl`, `dbt`, `gcp`, `sql`, `nlp`)
- [x] Add phrase-boost tests for exact role/title phrase lift with bounded effect
- [x] Add tie-break tests for equal lexical scores to enforce stable order contract
- [x] Add taxonomy-derived stability test for deterministic sorted protected-term output

**Verification:**
- [x] `python -m pytest -q tests/test_vector_search.py`
- [x] `python -m pytest -q tests/test_pipeline.py -k "shortlist or vector"`

**Exit Criteria:**
- new contracts enforced by CI-facing tests

### Task 6: Rollout hardening and closeout checks
**Purpose:** validate repo-level integrity and prepare handoff.

**Files:**
- Inspect: `docs/superpowers/specs/2026-05-28-16-14-shortlist-bm25-upgrade-spec.md`
- Modify: spec/plan status + evidence notes if needed

**Preconditions:**
- Tasks 1-5 complete

**Steps:**
- [x] Run full shortlist-lane verification set
- [x] Run repo fast contract validation
- [x] Confirm spec/plan evidence alignment and unresolved risk list
- [x] Prepare execution handoff packet for lane execution

**Verification:**
- [x] `python -m pytest -q tests/test_vector_search.py`
- [x] `python -m pytest -q tests/test_pipeline.py`
- [x] `python scripts/validate_repo_contracts.py --fast`

**Exit Criteria:**
- plan execution can proceed lane-by-lane with deterministic next-action gating

## Verification
- `python -m pytest -q tests/test_vector_search.py`
- `python -m pytest -q tests/test_pipeline.py`
- `python scripts/validate_repo_contracts.py --fast`

## Completion Criteria
1. all Key Deliverables are satisfied
2. lexical policy is SSOT-config-driven with deterministic derivation and weighting/phrase controls
3. invariance/symmetry/protected-term/phrase/tie-break proofs pass via tests and repo validators










