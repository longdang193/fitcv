# Bounded Change Thread Checkpoints

This folder stores visible checkpoint result packs for bounded change threads.

Use path shape:

```text
docs/intent/workstreams/checkpoints/<workstream-id>/<thread-slug>/
  <timestamp-or-checkpoint-id>.md
```

Rules:

- checkpoint unit is the bounded change thread
- each meaningful execution pass should publish one result pack
- use `docs/operating_system/templates/checkpoint-result-pack.md`
- active and completed thread statuses should always have at least one pack

Validation:

- run `.\.venv\Scripts\python.exe scripts/validate_checkpoint_packs.py`
- or run `.\.venv\Scripts\python.exe scripts/validate_repo_contracts.py --fast`
