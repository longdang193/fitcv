# Task 10a: Config Layer — Central Policy Config + Refactor

Introduce a [config/](file:///workspaces/fitcv/.worktrees/task-1-scaffold/tests/conftest.py#36-41) directory with 4 YAML files covering all shared policy values.
Extend [config.py](file:///workspaces/fitcv/.worktrees/task-1-scaffold/src/fitcv/config.py) to merge them into every call. Refactor Tasks 4–9 modules to read
all hardcoded values from config, keeping the public API and all existing tests unchanged.

## Audit of hardcoded values

| Module | Hardcoded values |
|--------|-----------------|
| [rule_filter.py](file:///workspaces/fitcv/.worktrees/task-1-scaffold/src/fitcv/rule_filter.py) | `_SENIORITY_LADDER` list, `_SENIORITY_ALIASES` dict, `_SKILL_SYNONYMS` dict |
| [enrich.py](file:///workspaces/fitcv/.worktrees/task-1-scaffold/src/fitcv/enrich.py) | `_VALID_LOCATION_TYPES`, `_VALID_SENIORITY` frozensets, `ai_score_model` default `"gemini-2.0-flash"`, `enrichment_version` default `"v1"` |
| [vector_search.py](file:///workspaces/fitcv/.worktrees/task-1-scaffold/src/fitcv/vector_search.py) | `top_n=50` default, `retrieval_strategy="job_summary_v1"` default, max skills in query text `[:15]` |
| [ai_score.py](file:///workspaces/fitcv/.worktrees/task-1-scaffold/src/fitcv/ai_score.py) | `top_n=50` default, `gemini_model` default `"gemini-2.0-flash"`, [fit_label](file:///workspaces/fitcv/.worktrees/task-1-scaffold/src/fitcv/ai_score.py#89-96) thresholds (0.7 / 0.4), Vertex AI sleep `0.5` |

All of the above will move to YAML files and be injected through [load_config()](file:///workspaces/fitcv/.worktrees/task-1-scaffold/src/fitcv/config.py#17-42).

---

## Proposed Changes

### Config YAML files

#### [NEW] [taxonomy.yaml](file:///workspaces/fitcv/.worktrees/task-1-scaffold/config/taxonomy.yaml)

```yaml
seniority:
  ladder: [intern, entry, associate, mid, senior, lead, manager, director]
  aliases:
    junior: entry
    jr: entry
    sr: senior
    staff: lead
    principal: lead
    vp: director
    vice president: director

valid_location_types: [remote, hybrid, onsite]

valid_seniority_enrich: [junior, mid, senior, lead]

valid_contract_types:
  - Full-time
  - Part-time
  - Contract
  - Internship
  - Temporary

valid_experience_levels:
  - Internship
  - Entry level
  - Associate
  - Mid-Senior level
  - Director
  - Executive
```

#### [NEW] [skill_synonyms.yaml](file:///workspaces/fitcv/.worktrees/task-1-scaffold/config/skill_synonyms.yaml)

Maps alias → canonical (both lowercased at load time):

```yaml
gcp: google cloud
google cloud platform: google cloud
bigquery: google bigquery
big query: google bigquery
k8s: kubernetes
aws: amazon web services
azure: microsoft azure
ml: machine learning
nlp: natural language processing
postgres: postgresql
pg: postgresql
airflow: apache airflow
```

#### [NEW] [pipeline.yaml](file:///workspaces/fitcv/.worktrees/task-1-scaffold/config/pipeline.yaml)

```yaml
gemini_model: gemini-2.0-flash
embedding_model: text-embedding-005
enrichment_version: v1
enrichment_batch_size: 1           # reqs/s (Gemini free tier)
embedding_batch_size: 100
vector_top_n: 50                   # top-N from VECTOR_SEARCH
vector_max_candidate_skills: 15    # max skills in candidate query text
retrieval_strategy: job_summary_v1
rerank_top_n: 50                   # max jobs sent to AI reranking
rerank_sleep_secs: 0.5             # sleep between Vertex AI calls
```

#### [NEW] [ranking.yaml](file:///workspaces/fitcv/.worktrees/task-1-scaffold/config/ranking.yaml)

```yaml
ranking_weights:
  ai_score: 0.40
  must_have_match: 0.20
  vector_similarity: 0.15
  title_relevance: 0.10
  seniority_fit: 0.10
  preference_fit: 0.05

fit_label_thresholds:
  strong: 0.70
  stretch: 0.40
  # below stretch → skip

missing_value_defaults:
  ai_score: 0.0
  must_have_match: 0.0
  vector_similarity: 0.0
  title_relevance: 0.5
  seniority_fit: 0.5
  preference_fit: 0.5
```

---

### Config loader

#### [MODIFY] [config.py](file:///workspaces/fitcv/.worktrees/task-1-scaffold/src/fitcv/config.py)

- Add `_CONFIG_DIR` constant pointing to [config/](file:///workspaces/fitcv/.worktrees/task-1-scaffold/tests/conftest.py#36-41) relative to repo root
- Add `_load_yaml_file(path) -> dict` helper
- Extend [load_config(path)](file:///workspaces/fitcv/.worktrees/task-1-scaffold/src/fitcv/config.py#17-42) to deep-merge `taxonomy.yaml`, `skill_synonyms.yaml`, `pipeline.yaml`, `ranking.yaml` into the base config dict
- Missing `config/*.yaml` files → warn + empty dict (do not crash)
- Resulting merged keys available directly: `config["seniority"]`, `config["skill_synonyms"]`, `config["ranking_weights"]`, etc.

---

### Module refactors

> All changes are backwards-compatible: existing unit tests must still pass without modification.

#### [MODIFY] [rule_filter.py](file:///workspaces/fitcv/.worktrees/task-1-scaffold/src/fitcv/rule_filter.py)

- Remove module-level `_SENIORITY_LADDER`, `_SENIORITY_ALIASES`, `_SKILL_SYNONYMS` constants
- Add `_get_seniority_ladder(config)`, `_get_skill_synonyms(config)` helpers that read from config with hardcoded dicts as fallback (safe degradation)
- [_normalise_seniority(raw, config=None)](file:///workspaces/fitcv/.worktrees/task-1-scaffold/src/fitcv/rule_filter.py#58-66) — accepts optional config
- [_canonicalise_skill(skill, config=None)](file:///workspaces/fitcv/.worktrees/task-1-scaffold/src/fitcv/rule_filter.py#116-120) — accepts optional config
- [check_seniority](file:///workspaces/fitcv/.worktrees/task-1-scaffold/src/fitcv/rule_filter.py#68-96), [check_must_have_skills](file:///workspaces/fitcv/.worktrees/task-1-scaffold/src/fitcv/rule_filter.py#156-172) — pass config through; existing unit tests still pass because fallback = hardcoded dicts

#### [MODIFY] [enrich.py](file:///workspaces/fitcv/.worktrees/task-1-scaffold/src/fitcv/enrich.py)

- `_VALID_LOCATION_TYPES`, `_VALID_SENIORITY` → read from `config["valid_location_types"]` / `config["valid_seniority_enrich"]` with current frozensets as fallback
- [_coerce_field](file:///workspaces/fitcv/.worktrees/task-1-scaffold/src/fitcv/enrich.py#64-89) → accept optional [config](file:///workspaces/fitcv/.worktrees/task-1-scaffold/tests/conftest.py#36-41) param
- [enrich_job](file:///workspaces/fitcv/.worktrees/task-1-scaffold/src/fitcv/enrich.py#258-290) → read model name from `config["gemini_model"]` (already does, but `"gemini-2.0-flash"` literal becomes `config.get("gemini_model", "gemini-2.0-flash")`)
- [merge_scraped_and_enriched](file:///workspaces/fitcv/.worktrees/task-1-scaffold/src/fitcv/enrich.py#201-254) → read `enrichment_version` from `config["enrichment_version"]`

#### [MODIFY] [vector_search.py](file:///workspaces/fitcv/.worktrees/task-1-scaffold/src/fitcv/vector_search.py)

- [build_candidate_query_text](file:///workspaces/fitcv/.worktrees/task-1-scaffold/src/fitcv/vector_search.py#26-55) → read `max_skills` from `config.get("vector_max_candidate_skills", 15)`
- [run_vector_search](file:///workspaces/fitcv/.worktrees/task-1-scaffold/src/fitcv/vector_search.py#115-182) → read [top_n](file:///workspaces/fitcv/.worktrees/task-1-scaffold/tests/test_vector_search.py#71-75) default from `config.get("vector_top_n", 50)`
- [store_shortlist](file:///workspaces/fitcv/.worktrees/task-1-scaffold/src/fitcv/vector_search.py#186-225) → read `retrieval_strategy` from `config.get("retrieval_strategy", "job_summary_v1")`

#### [MODIFY] [ai_score.py](file:///workspaces/fitcv/.worktrees/task-1-scaffold/src/fitcv/ai_score.py)

- [parse_score_response](file:///workspaces/fitcv/.worktrees/task-1-scaffold/src/fitcv/ai_score.py#98-152) → read `fit_label_thresholds` from [config](file:///workspaces/fitcv/.worktrees/task-1-scaffold/tests/conftest.py#36-41) (with `{strong: 0.7, stretch: 0.4}` fallback)
- [score_job](file:///workspaces/fitcv/.worktrees/task-1-scaffold/src/fitcv/ai_score.py#156-196) → read model from `config["gemini_model"]`
- [run_ai_scoring](file:///workspaces/fitcv/.worktrees/task-1-scaffold/src/fitcv/ai_score.py#200-243) → read [top_n](file:///workspaces/fitcv/.worktrees/task-1-scaffold/tests/test_vector_search.py#71-75) from `config.get("rerank_top_n", 50)`, sleep from `config.get("rerank_sleep_secs", 0.5)`

---

### Tests

#### [MODIFY] [test_config.py](file:///workspaces/fitcv/.worktrees/task-1-scaffold/tests/test_config.py) — extend existing tests

- `test_load_config_merges_taxonomy` — config contains `seniority.ladder` key after load
- `test_load_config_merges_skill_synonyms` — config contains `skill_synonyms` dict
- `test_load_config_merges_pipeline` — config contains `gemini_model`, `vector_top_n`
- `test_load_config_merges_ranking` — config contains `ranking_weights.ai_score`
- `test_load_config_missing_optional_yaml_does_not_crash` — delete one file → load_config still succeeds

#### Existing tests remain unchanged

[test_rule_filter.py](file:///workspaces/fitcv/.worktrees/task-1-scaffold/tests/test_rule_filter.py), [test_enrich.py](file:///workspaces/fitcv/.worktrees/task-1-scaffold/tests/test_enrich.py), [test_vector_search.py](file:///workspaces/fitcv/.worktrees/task-1-scaffold/tests/test_vector_search.py), [test_ai_score.py](file:///workspaces/fitcv/.worktrees/task-1-scaffold/tests/test_ai_score.py) — all pass without modification because refactored functions fall back to hardcoded dicts when config is not provided.

---

## Verification Plan

### Automated Tests

```bash
# From worktree root
cd /workspaces/fitcv/.worktrees/task-1-scaffold
python -m pytest tests/ -v --tb=short
```

Expected: all previously passing tests still pass (no regressions). New config tests added.

### Manual spot-check

```bash
python -c "
from fitcv.config import load_config
cfg = load_config('.env.yaml')
print('seniority ladder:', cfg['seniority']['ladder'])
print('gcp→', cfg['skill_synonyms']['gcp'])
print('gemini_model:', cfg['gemini_model'])
print('ranking weights:', cfg['ranking_weights'])
"
```
