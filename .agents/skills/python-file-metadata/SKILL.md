---
name: python-file-metadata
description: Add structured metadata to files with behavioral weight (scripts, workflows, tests, utilities).
---
# Python File Metadata

Files with **behavioral weight** (scripts, orchestration logic, tests, utilities) must declare a structured metadata block at the top of the file. This metadata explains intent, scope, and constraints without requiring the reader to scan the entire file.

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

Always add this metadata incrementally as you touch relevant files in the codebase.
