# Settings System — History

## Changelog

### 2.6.0 — active

- Retrieval settings now expose `cv_analysis.semantic_alignment.*` controls, including enable/model settings and lexical-versus-semantic weights for responsibility and domain alignment
- Settings validation now rejects hybrid-weight pairs that do not sum to `1.0`
- Specs/plans: see `refs` in the feature contract

### 2.5.0 — active

- Ranking settings now include explicit `preference_fit_weights` for domain, role-family, and location-type calibration
- Ranking settings copy now reflects semantic role alignment for `title_relevance` and AI-reranker label calibration for fit thresholds
- Specs/plans: see `refs` in the feature contract

### 2.4.1 — active

- Ranking settings copy now matches runtime semantics for title-to-target-role similarity and domain/location preference alignment
- Specs/plans: see `refs` in the feature contract

### 2.4.0 — active

- Ranking settings now map to a real six-feature runtime contract instead of a hidden two-feature subset
- Supported ranking features can be made non-contributing explicitly with weight `0.0` while still remaining visible in runtime and artifacted config
- Specs/plans: see `refs` in the feature contract

### 2.3.0 — active

- Admin-editable CV generation and composition settings
- Specs/plans: see `refs` in the feature contract

### 2.0.0 — active

- Preset-based CV config migration
- Specs/plans: see `refs` in the feature contract

### 1.0.0 — active

- Initial feature: BigQuery-backed settings store and schema registry
- Specs/plans: see `refs` in the feature contract

## Post-Execution Review

> Fill after status transitions to `active`.
