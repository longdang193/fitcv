# Config Loader Unification Design

## Goal

Unify FitCV runtime configuration so pipeline code, library modules, tests, and scripts all resolve config through a single loader while temporarily supporting both `.env.yaml` and `config/env.yaml`.

## Current Problem

The repo has two config entry points:

- `fitcv.config.load_config()` loads `.env.yaml` and merges `config/*.yaml`
- `fitcv.pipeline.load_config_bundle()` reads `config/env.yaml` directly

This split allows drift in critical values such as `vertex_location`, `gemini_model`, and policy overlays. The recent Vertex AI issue happened because different execution paths loaded different location values.

## Approved Approach

Use `fitcv.config.load_config()` as the single config loader and keep temporary backward compatibility for both config file locations.

## Design

### Canonical Loader

`fitcv.config.load_config()` remains the only public loader.

It will:

- accept an explicit path to either `.env.yaml` or `config/env.yaml`
- resolve a default config file when no path is given
- merge policy files from `config/`
- normalize legacy keys into the canonical runtime shape

### Backward Compatibility

During the transition, both `.env.yaml` and `config/env.yaml` remain valid.

Behavior:

- explicit `.env.yaml` works
- explicit `config/env.yaml` works
- default resolution prefers `.env.yaml`, then falls back to `config/env.yaml`
- a warning is emitted when the legacy `config/env.yaml` path is used directly

### Canonical Runtime Shape

The unified config should expose explicit keys needed by the app:

- `gcp_project`
- `bigquery_dataset`
- `service_account_key`
- `vertex_location`
- `gemini_model`
- `pipeline`
- `paths`

Legacy `location` remains accepted as input during the transition, but caller code should not rely on it for Vertex behavior.

### Pipeline Change

`fitcv.pipeline.run_pipeline()` should stop reading raw YAML directly.

`load_config_bundle()` should become a thin wrapper around `fitcv.config.load_config()` or be removed if test ergonomics remain simple.

### Test Strategy

Add focused regression coverage for:

- default config resolution
- explicit legacy path loading
- pipeline using the shared loader
- normalized `vertex_location` visibility through pipeline config

## Non-Goals

- removing legacy config files immediately
- renaming all config keys in one pass
- refactoring unrelated modules
