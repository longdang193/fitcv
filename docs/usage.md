# Usage

FitCV supports two main usage modes: operator workflows and engineering workflows.

## Operator Workflow

1. Open the admin UI at `http://localhost:8000/admin/runs`.
2. Trigger a run from file upload, pasted JSON, or path input.
3. Choose `Run All` or `Stage by Stage`.
4. Inspect run health, stage progress, and downloadable artifacts.
5. Review stage-owned diagnostics before acting on generated CV outputs.

## Engineering Workflow

1. Update code, settings, or lifecycle sources in the private repo.
2. Refresh generated architecture docs with `python scripts/sync_architecture_docs.py` when feature or stage source files change.
3. Run `python scripts/validate_adoption_shape.py` when working on Mode B lifecycle surfaces.
4. Use the curated publication workflow only when public-safe code and docs are ready.

## Related Surfaces

- [pipeline.md](C:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/docs/pipeline.md)
- [FitCV-pipeline.md](C:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/docs/FitCV-pipeline.md)
- [docs/generated/stage_overview.md](C:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/docs/generated/stage_overview.md)
