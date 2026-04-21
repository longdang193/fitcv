# Architecture

FitCV combines an operator-facing control plane with a staged job-processing pipeline and a managed architecture-doc layer.

## Runtime Architecture

- `src/fitcv_cp/` owns the FastAPI admin UI, run lifecycle actions, inspection surfaces, and settings UI.
- `src/fitcv/` owns the pipeline stages, CV analysis/generation behavior, and supporting runtime logic.
- Redis and RQ provide background execution for pipeline runs.
- BigQuery persists run state, events, structured jobs, and generated artifacts.

## Documentation Architecture

- `docs/features/<feature_id>/feature.source.yaml` is the human-owned feature source.
- `docs/features/<feature_id>/<feature_id>.yaml` is the generated feature contract.
- `docs/features/<feature_id>/lineage.generated.yaml` is generated feature evidence.
- `docs/stages/<stage_id>.source.yaml` is the human-owned stage source.
- `docs/stages/<stage_id>.yaml` is the generated stage contract.
- `docs/generated/*` is generated discovery, not a source-of-truth layer.

## Sync And Validation

Refresh generated architecture docs with:

```powershell
python scripts/sync_architecture_docs.py
```

Validate Mode B repo shape with:

```powershell
python scripts/validate_adoption_shape.py
```
