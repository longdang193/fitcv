---
name: skill-central-config-layer
description: Use when shared configuration spans multiple modules, services, agents, or pipelines.
required_reads: []
distribution_tier: starter_kit
---
# Central Config Layer

## Purpose

Create or improve a central configuration layer so shared rules do not drift across files.

Use this skill when:

- values are hardcoded in multiple modules
- the same enums or thresholds appear repeatedly
- environment settings are mixed with business rules
- agents or pipelines need one source of truth
- normalization rules should be reused
- configuration should be easier to tune without editing code

## Core principle

Separate configuration by responsibility.

Typical config categories:

1. **Environment / infrastructure config**
   - project IDs
   - dataset names
   - regions
   - API endpoints
   - credentials paths
   - model names

2. **Runtime / pipeline behavior config**
   - batch sizes
   - retry counts
   - timeout values
   - top-N limits
   - scheduling settings
   - enabled or disabled stages

3. **Business-rule / policy config**
   - thresholds
   - weights
   - classification rules
   - allowed values
   - fallback defaults
   - tie-break order

4. **Taxonomy / normalization config**
   - enum lists
   - canonical names
   - synonym maps
   - mapping tables
   - category hierarchies

## Recommended directory layout

Prefer a dedicated config directory:

```text
config/
├── env.yaml
├── runtime.yaml
├── policy.yaml
├── taxonomy.yaml
└── synonyms.yaml
```

For very small projects, a single file may be enough at first. Once multiple modules share assumptions, split by responsibility.

## What to centralize

Centralize values that are:

- reused across modules
- likely to change
- policy or environment related
- part of shared business logic
- needed by multiple agents or pipeline stages

Examples:

- model names
- retry counts
- top-N values
- threshold cutoffs
- ranking weights
- enum sets
- mapping rules
- canonical names
- feature flags

## What not to centralize

Do not centralize:

- unstable one-off experiments
- long procedural logic
- complex SQL bodies
- implementation details that are only used once
- values that are truly local to one function and unlikely to change

## Output expectations

When applying this skill, produce:

1. A diagnosis of config sprawl or missing config boundaries
2. A recommended config structure
3. A split of which values belong in which file
4. Example config schemas
5. Validation rules
6. Refactor guidance
7. A migration checklist

## Recommended workflow

1. Inventory hardcoded values across the codebase
2. Group them by environment, runtime, policy, taxonomy, or normalization
3. Create config files with stable keys
4. Add a config loader with validation
5. Refactor modules to consume config instead of literals
6. Update tests to use config fixtures
7. Document the config contract

## Validation guidance

The config loader should validate:

- required files exist
- required keys exist
- enum values are unique
- thresholds are within valid ranges
- weights are valid or normalized
- mappings do not collide badly
- defaults are explicitly defined
- environment keys are present

## Review checklist

Check for:

- duplicated constants
- duplicated enum lists
- duplicated thresholds
- repeated model names
- repeated API limits
- inconsistent naming across modules
- hidden assumptions in tests
- drift between code and documentation

## Config patterns

### env.yaml

Use for infrastructure and external dependency settings:

- project_id
- dataset
- region
- credentials_path
- api_base_url
- model_name

### runtime.yaml

Use for execution behavior:

- batch_size
- retry_count
- timeout_seconds
- max_concurrency
- top_n
- enabled_steps

### policy.yaml

Use for decision rules:

- thresholds
- weights
- tie_break_order
- defaults
- scoring rules

### taxonomy.yaml

Use for allowed values and category systems:

- levels
- categories
- states
- enums
- mappings

### synonyms.yaml

Use for canonicalization:

- canonical value → aliases
- normalization maps
- title or skill variants
- naming cleanup rules

## Migration checklist

- identify repeated literals
- move reusable settings into config
- keep file names stable
- validate config on load
- avoid leaking config parsing into business logic
- update tests to use sample config fixtures
- document defaults and fallback behavior

## Output format

When using this skill, provide:

- a short diagnosis
- proposed config files
- exact keys to create
- affected modules
- risky migrations
- suggested validation rules
