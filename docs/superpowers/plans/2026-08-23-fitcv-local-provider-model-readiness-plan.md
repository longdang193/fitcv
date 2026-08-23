---
template_id: implementation-plan
artifact_type: plan
status: completed
layer: change
name: fitcv-local-provider-model-readiness
targets:
  - config/runtime/control_plane.yaml
  - src/fitcv_cp/local_routes.py
  - src/fitcv_cp/provider_registry.py
  - src/fitcv_cp/local_setup.py
  - src/fitcv_cp/settings_store.py
  - src/fitcv_cp/sqlite_store.py
  - docs/superpowers/plans/2026-08-23-fitcv-local-provider-model-readiness-plan.md
---

# FitCV Local Provider/Model Readiness

## Goal

Provision real FitCV Local provider and model state through canonical APIs so
the final P0 acceptance starts from an application-proven ready state.

## Implementation Outcomes

### Canonical provider state

The configured OpenAI-compatible provider connection is persisted through Local
onboarding APIs with verification status `verified`; credential presence is
confirmed without exposing secret material.

### Canonical model and routing state

Model `cx/gpt-5.4-mini` is persisted as `validated`, its validated connection
revision equals the current provider connection revision, and required routes
resolve to an eligible model.

### Readiness persistence

Fresh Local startup returns `/local/readiness` `ready:true` with empty reasons,
and the same result survives restart against the same disposable data root.

## Execution Approach

- Mode: `inline sequential`
- Coordination: `git-tracked`
- Executor: `codex`
- Required skills: `skill-executing-plans`, `skill-backend-verification`, `skill-verification-before-completion`
- Isolation: `current workspace`
- Commit policy: `no product/provider commit; record verified outcome in final checkpoint`
- Preauthorized local actions: disposable Local runtime, canonical provider/model APIs, read-only readiness inspection
- User-approval actions: provider writes, push, merge, destructive cleanup
- Parallel ownership: `none`
- Sequential fallback: provider connection, model validation, route verification, readiness, restart

## Coordination State

- Coordination owner: `single lead controller`
- Branch: `main`
- Base commit: `69b3d89e76b8eee02ce93d6406ba55ef4e23fea4`
- Active task(s): `none`
- Expected workspace: `main` with no product/runtime/provider diff; final P0 plan preserved
- Next action: run separate final 25-probe acceptance from fresh disposable storage
- Blockers: `none`

| Task | State | Workspace | Executor | Depends On | Required Proof | Evidence |
| --- | --- | --- | --- | --- | --- | --- |
| Task 1 | `completed` | main | codex | governance preflight | canonical provisioning, readiness, restart, independent read-only validation | PASS: `PROVISIONING_ONLY`; real readiness and restart proof recorded below |

## Task Breakdown

### Task 1: Provision and verify Local readiness

**Purpose:**
- Establish persisted provider, model, routing, and readiness state without changing product behavior.

**Task Function:**
- Canonical Local provider/model provisioning and runtime readiness verification.

**Template Profile:**
- Controller-selected: `none (lead controller)`
- Selection basis: bounded provisioning and direct runtime proof; no code implementation.

**Validator Profile:**
- Controller-selected: `normal`
- Selection basis: independent read-only persistence, routing, readiness, and restart reconciliation.

**Specification Coverage:**
- Provider connection verification, model validation, revision matching, eligible routing, `/local/readiness`, and restart persistence.

**Required Skills:**
- `skill-backend-verification`, `skill-verification-before-completion`

**Files And Symbols:**
- Inspect: `config/runtime/control_plane.yaml`
- Inspect: `src/fitcv_cp/local_routes.py`, `src/fitcv_cp/provider_registry.py`, `src/fitcv_cp/local_setup.py`, `src/fitcv_cp/settings_store.py`, `src/fitcv_cp/sqlite_store.py`
- Verify: canonical Local APIs and `/local/readiness`

**Dependencies:**
- Governance preflight identified and isolated the active-plan validator defect; no 25-probe run.

**Authority:**
- Preauthorized local actions: canonical provider/model API calls and disposable runtime checks.
- Stop for: provider credential failure, product defect, schema mutation outside owner, or workspace drift.

**Steps:**
- [x] Provision configured provider through canonical Local onboarding APIs.
- [x] Discover and validate `cx/gpt-5.4-mini` through canonical model APIs.
- [x] Verify eligible default/task routing and `/local/readiness`.
- [x] Restart against the same disposable state and reverify readiness.

**Verification:**
- [x] Provider discovery returned HTTP `200`; `cx/gpt-5.4-mini` was visible.
- [x] Canonical provider connection returned `verified`; credential was configured.
- [x] Model returned `validated`; `validated_connection_revision` matched `connection_revision`.
- [x] Default/task routes were eligible.
- [x] `/local/readiness` returned HTTP `200`, `ready:true`, `reasons:[]` before and after restart.

**Exit Criteria:**
- Real Local readiness is persisted and restart-stable without product/runtime/provider source changes.

## Verification

- Read-only independent inspection of provider connection, credential-configured boolean, revisions, model validation, routing, `/local/readiness`, and restart state.
- No provider secret material or disposable runtime artifacts are stored in this plan.

## Completion Criteria

1. Canonical provider connection is verified.
2. Canonical model validation matches current connection revision.
3. Required routes resolve to eligible model state.
4. `/local/readiness` is `ready:true` with `reasons:[]`.
5. Readiness survives restart.
6. Classification is `PROVISIONING_ONLY`; no product changes are required.

## Final Ledger

- Final decision: `PASS`.
- Classification: `PROVISIONING_ONLY`.
- Readiness before provisioning: HTTP `200`, `ready:false`, with missing verified provider/model readiness and stale default-route retest requirement.
- Readiness after provisioning: HTTP `200`, `{"ready":true,"reasons":[]}`.
- Restart proof: same disposable Local state returned `ready:true` with empty reasons after runtime restart.
- Provider proof: configured provider discovery HTTP `200`; connection `verified`; credential configured.
- Model proof: `cx/gpt-5.4-mini` visible and `validated`; validated connection revision matched current connection revision.
- Routing proof: default and required task routes resolved to eligible model state.
- Product changes: `NONE`.
- Next action: run separate final 25-probe FitCV Local P0 acceptance from fresh disposable storage using this canonical readiness flow.
