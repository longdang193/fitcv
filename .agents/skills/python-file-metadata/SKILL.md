---
name: python-file-metadata
description: Add structured metadata to files with behavioral weight (scripts, workflows,
  tests, utilities).
allowed-tools: []
hooks:
  pre: []
  post: []
required_reads: []
required_outputs: []
related_skills: []
tags:
- skill
- python-file-metadata
---

# Python File Metadata

Files with **behavioral weight** (scripts, orchestration logic, tests, utilities) must declare a structured metadata block at the top of the file. This metadata explains intent, scope, and constraints without requiring the reader to scan the entire file.

The hard invariants from this workflow are also enforced by the generated
`python-contracts` rule surface. Use this skill for the richer metadata
decision-making about when lineage is materially affected and how ownership
should be expressed.

## Required On

- **Entry-point scripts**: CLI, orchestration, jobs
- **Orchestration / workflow files**: HPO, benchmarking, training
- **Test modules**: Unit, integration, E2E
- **Migration / cleanup scripts**: One-time or destructive logic
- **Shared utilities**: Clarifies intent, ownership, and safe reuse

## Metadata Format

Use a **comment-only docstring** at the very top of the file. Do **not** include runtime logic.

### For Standard Files

```python
"""
@meta
name: <script_name>
type: script            # script | test | utility | migration
domain: <domain>        # e.g., hpo | benchmarking | training
responsibility:
  - <Bullet 1>
  - <Bullet 2>
inputs:
  - <Input file/state>
outputs:
  - <Output file/state>
capabilities:
  - <optional-capability-id>
invariants:
  - <optional-invariant-id>
tags:
  - <tag1>
lifecycle:
  status: active        # active | deprecated | legacy
"""
```

### For Test Files

```python
"""
@meta
type: test
scope: unit              # unit | integration | e2e
domain: <domain>
covers:
  - <Tested feature 1>
excludes:
  - <Excluded environment/feature>
tags:
  - fast
  - ci-safe
"""
```

Use optional `capabilities` and `invariants` only when the file materially
affects generated lineage. Do not add capability IDs just because a helper is
nearby.

Use `features` only as a fallback convenience field when capability linkage does
not yet provide enough stable feature ownership. When capability IDs already
determine feature linkage, prefer capability-first metadata and omit the
redundant `features` list.

Use function-level `@capability <capability_id>` only for canonical
capability-owning functions. Helpers, wrappers, tests, adapters, and incidental
callers should rely on file-level `@meta` or test proof metadata instead.

Capability-first rule:

- upstream feature sources own capability truth
- Python files should point to capabilities when they materially participate in
  lineage
- downstream feature linkage should be derived from those capabilities whenever
  possible rather than typed again by hand

Tests that prove a capability can add `@proves <capability_id>` in the relevant
test function docstring. This is proof evidence, not implementation ownership.

Always add this metadata incrementally as you touch relevant files in the codebase.

This metadata participates in the repo's steady-state architecture workflow:

- `feature.source.yaml` is the human-owned semantic source for opted-in features
- generated feature contracts and `lineage.generated.yaml` are standard outputs
- lineage completeness is enforced rather than treated as advisory
- temporary exception blocks in feature source are exceptional debt, not normal steady-state ownership

After changing source metadata that affects architecture lineage, prefer the
canonical repo workflow:

```powershell
.\.venv\Scripts\python.exe scripts/sync_architecture_docs.py
.\.venv\Scripts\python.exe scripts/sync_architecture_docs.py --check
```
