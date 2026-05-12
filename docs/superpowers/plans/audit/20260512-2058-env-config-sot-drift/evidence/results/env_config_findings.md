# Env Config Drift Findings

- Timestamp: 2026-05-12T20:58:55+02:00
- Scope: `.env`, `.env.yaml`, `.env.yaml.example`, `config/env.yaml`

## Observations

1. `config/env.yaml` exists and is marked canonical (`# canonical: true`).
2. `.env.yaml` exists with overlapping keys and divergent values:
   - `location`: `.env.yaml=us-central1` vs `config/env.yaml=US`
   - `enrichment_sleep_secs`: `.env.yaml=3` vs `config/env.yaml=1.0`
   - `.env.yaml` includes keys not present in `config/env.yaml` (`ai_score_model`, `enrichment_max_retries`, `apify_dataset_id`, `apify_token`).
3. `.env` is missing in this worktree, but runtime/docs reference `.env` usage in docker setup.
4. `.env.yaml.example` is missing in this worktree while setup doc currently instructs copying it.
5. Code/docs references show `.env.yaml` as default config path in control plane surfaces, while compose mounts both `.env.yaml` and `config/env.yaml`.

## Trigger Qualification

Qualifies under `audit-evidence-mandate-rule` trigger:
- **contract/invariant drift where failure boundary is unclear**.

Reason:
- Multiple config surfaces with overlap and inconsistent defaults break single source of truth contract and can produce runtime ambiguity.
