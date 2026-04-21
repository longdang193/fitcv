# Configuration

FitCV splits configuration ownership by purpose.

## Repo Method Configuration

`repo_config/` owns repo-level behavior:

- `repo_config/adoption-mode.yaml`
- `repo_config/publication-config.json`
- `repo_config/agent-adapter-mappings.json`

These files control Mode B adoption state, curated publication boundaries, and adapter sync surfaces.

## Runtime Product Configuration

`config/` owns product and pipeline runtime defaults such as:

- environment-specific YAML
- runtime policies
- taxonomy/config-room data used by the pipeline

Operators can override supported runtime settings through the admin UI, but the runtime configuration model still resolves from the config layer plus persisted settings snapshots.

## Lifecycle Configuration

Managed architecture metadata uses:

- `docs/features/<feature_id>/feature.source.yaml`
- `docs/stages/<stage_id>.source.yaml`

Generated contracts and discovery are refreshed with:

```powershell
python scripts/sync_architecture_docs.py
```

Validate repo-wide adoption shape with:

```powershell
python scripts/validate_adoption_shape.py
```
