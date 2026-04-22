# Doc System Lifecycle

This document defines the source-of-truth model for project docs.

## Core Principle

Documentation should let a human or agent answer:

- what exists
- what is current
- what changed
- why it changed
- where the real source of truth lives

Docs explain code. They do not replace it.

Canonical truth should flow downward from upstream owning layers. Lower layers
should derive or reference that truth rather than restating the same semantic
fact manually.

## Source-Of-Truth Layers

```text
code/                        -> real truth
docs/intent/*.md             -> project purpose and outcome sources
docs/operating_system/*.md   -> repo method and governance sources
repo_config/adoption-mode.yaml -> adoption mode and architecture metadata state source
docs/stages/*.source.yaml    -> human-owned stage source when stage-aware docs are in scope
docs/stages/*.yaml           -> generated stage contracts when stage-aware docs are in scope
docs/features/*/feature.source.yaml -> human-authored feature metadata source when adopted
docs/features/*/*.yaml       -> structured current-state truth
docs/features/<feature_id>/  -> feature explanation and history
docs/*.md                    -> cross-cutting product docs
README.md                    -> overview
docs/generated/*             -> generated discovery
```

## Placement Rules

### Code

Use code for:

- runtime behavior
- routes and APIs
- validation logic
- data and schema logic

### `docs/features/*/*.yaml`

Use feature YAML for:

- current feature contracts
- identity, status, dependencies, capabilities, refs

For generated architecture metadata, `feature.source.yaml` remains the human
source while generated contracts and lineage are rebuilt by
`tools/docs/generate_architecture_metadata.py`.

### `docs/features/<feature_id>/`

Use feature-specific docs for:

- architecture
- focused flows
- feature history

### `docs/*.md`

Use cross-cutting docs for:

- product architecture
- setup
- shared user/operator guidance

### `docs/operating_system/*.md`

Use operating-system docs for:

- repo governance
- publication workflow
- planning rules
- tooling policy
- instruction layering

### `docs/generated/*`

Use generated discovery for:

- indexes
- summaries
- lookup surfaces

Generated files must not be edited manually.

## Sync Principle

When behavior or structure changes:

- update code
- update the owning feature YAML when a feature contract changes
- update feature docs or cross-cutting docs as needed
- update operating-system docs when repo rules or workflows change
- refresh generated discovery from its source layers

Canonical generation/check workflow:

```powershell
python tools/docs/generate_architecture_metadata.py
python tools/docs/generate_architecture_metadata.py --check
```

Canonical architecture sync/check workflow:

```powershell
.\.venv\Scripts\python.exe scripts/sync_architecture_docs.py
.\.venv\Scripts\python.exe scripts/sync_architecture_docs.py --check
```

Canonical repo-contract validation workflow:

```powershell
.\.venv\Scripts\python.exe scripts/validate_repo_contracts.py --fast
.\.venv\Scripts\python.exe scripts/validate_repo_contracts.py
```

Use `sync_architecture_docs.py` to refresh generated architecture surfaces after
source changes through the wrapper. Use `validate_repo_contracts.py` as the
broader gate before commit, push, or CI completion.

Here `--fast` means the hook-facing subset, not a lightweight bypass. It still
runs the architecture sync check path and skips only the extra
validator-specific pytest pass.

## Practical Heuristic

Use the deepest layer that owns the fact:

- behavior -> code
- feature state -> feature YAML
- feature explanation -> feature docs
- repo workflow -> operating-system docs
- navigation -> README or generated discovery
