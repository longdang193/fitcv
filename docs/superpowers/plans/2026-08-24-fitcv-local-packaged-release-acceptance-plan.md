---
template_id: implementation-plan
artifact_type: plan
status: completed
layer: change
name: fitcv-local-packaged-release-acceptance
targets:
  - docs/intent/workstreams/threads/workstream-operator-control-plane/08-fitcv-local-distribution-and-onboarding.md
  - docs/superpowers/plans/2026-08-24-fitcv-local-packaged-release-acceptance-plan.md
---

# FitCV Local Packaged Release Acceptance

## Goal

Define host-local packaged acceptance as the normal personal-use release gate.
Keep clean-machine and code-signing evidence separate for public release without
changing FitCV runtime or product behavior.

## Implementation Outcomes

- `PERSONAL_PACKAGED_READY` requires packaging, install, onboarding, provider/model,
  readiness, one real Run, reconciliation, restart, singleton, uninstall,
  reinstall, and credential-redaction evidence.
- `OPTIONAL_CLEAN_MACHINE_VERIFIED` records clean-machine evidence without blocking
  personal use; `PUBLIC_RELEASE_READY` additionally requires clean-machine proof
  and code signing.
- Routine Sandbox relay, temporary firewall plumbing, and pristine-machine
  dependency-absence checks are removed from personal-use acceptance.

## Execution Approach

- Mode: `inline sequential`
- Coordination: `git-tracked`
- Executor: `codex`
- Required skills: `skill-executing-plans`, `skill-verification-before-completion`
- Isolation: `current workspace`
- Commit policy: `no commits during execution`
- Preauthorized local actions: documentation edits and declared governance checks
- User-approval actions: push, merge, publication, destructive cleanup
- Parallel ownership: none
- Sequential fallback: update canonical workstream, then validate plan and repository contracts

## Coordination State

- Coordination owner: `single lead controller`
- Branch: `main`
- Base commit: `2ba6d7c51984027e6e5eaaacd29f6250db749c7a`
- Policy implementation checkpoint: `9d39d802cd69e130ed46ce2dd1e074f21c728c6c`
- Current pre-closure HEAD: `49279b18906fd52c90dd01ca0350a3a8e52b7d23` (`origin/main`)
- Active task(s): `none`
- Expected workspace: `main` at closure commit; preserve unrelated `config/taxonomy/skill_synonyms.yaml` change and `stash@{0}`
- Next action: execute a separate host-local `PERSONAL_PACKAGED_READY` acceptance task
- Blockers: `none`

| Task | State | Workspace | Executor | Depends On | Required Proof | Evidence |
| --- | --- | --- | --- | --- | --- | --- |
| Task 1 | `completed` | current | `codex` | none | governance, template, repository validation | `9d39d802`; planning PASS; template PASS; repository contracts PASS (10 checks); packaging tests 5 passed; diff check PASS; no runtime/product changes |

## Acceptance Classes

### PERSONAL_PACKAGED_READY

- clean packaging build succeeds
- installer identity and SHA-256 hash are recorded
- packaged installer launches on host
- `/healthz` returns success
- fresh temporary FitCV data root is used
- canonical onboarding completes
- provider and model verification pass
- `/local/readiness` returns `ready:true`
- one real packaged pipeline Run reaches its intended terminal state
- browser/API/artifact state reconciles
- restart persistence passes
- singleton behavior passes
- uninstall preserves user data
- reinstall recovers prior state
- logs and diagnostics contain no credentials

### OPTIONAL_CLEAN_MACHINE_VERIFIED

Run only as separate evidence after the personal gate. Windows Sandbox, another
VM, or another clean machine is optional. Its failure or omission does not block
personal-use readiness.

### PUBLIC_RELEASE_READY

Requires `PERSONAL_PACKAGED_READY`, clean-machine acceptance, executable and
installer code signing, and signed-hash publication. Clean-machine proof and
signing are not personal-use requirements.

## Safety Invariants

Keep these lightweight runtime contracts unchanged:

- Credential Manager owns provider secrets.
- Loopback plus Host/Origin/CSRF protections remain enforced.
- Logs and diagnostics redact secrets.
- Cleanup is PID-scoped.
- Application files and user data remain separate.

Do not add Sandbox relay, firewall rules, environment-isolation layers, or
pristine-machine dependency audits to the personal-use gate.

## Task Breakdown

### Task 1: Reconcile packaged acceptance policy

**Purpose:**
- Make host-local packaged evidence authoritative for personal use and preserve
  clean-machine/signing checks for public release only.

**Task Function:**
- Update canonical distribution and acceptance documentation.

**Template Profile:**
- Controller-selected: `normal`
- Selection basis: bounded documentation and governance change with no runtime behavior change.

**Validator Profile:**
- Controller-selected: `normal`
- Selection basis: independent template, planning, and repository contract validation.

**Specification Coverage:**
- Requirements 1–10 from approved personal-use release acceptance adjustment.

**Required Skills:**
- `skill-executing-plans`, `skill-verification-before-completion`

**Files And Symbols:**
- Modify: `docs/intent/workstreams/threads/workstream-operator-control-plane/08-fitcv-local-distribution-and-onboarding.md`
- Modify: `docs/superpowers/plans/2026-08-24-fitcv-local-packaged-release-acceptance-plan.md`
- Verify: `scripts/validate_planning_lifecycle.py`, `scripts/validate_template_required_sections.py`, `scripts/validate_repo_contracts.py`

**Dependencies:**
- Existing packaged runtime behavior and lightweight safety contracts remain unchanged.

**Authority:**
- Preauthorized local actions: documentation edits and declared validation commands.
- Stop for: runtime-file drift, plan/Git mismatch, or failed governance contract.

**Steps:**
- [x] Step 1: Update distribution workstream release classes and deferred public checks.
- [x] Step 2: Record the host-local packaged acceptance plan and safety invariants.
- [x] Step 3: Run governance/template/repository validation and inspect Git diff.

**Verification:**
- [x] `py scripts/validate_planning_lifecycle.py` — PASS
- [x] `py scripts/validate_template_required_sections.py` — PASS
- [x] `py scripts/validate_repo_contracts.py --fast` — PASS (10 checks)
- [x] `py -m pytest tests/test_fitcv_local_packaging.py -q` — 5 passed
- [x] `git diff --check` — PASS
- Expected: all checks pass; no runtime or product files change. Observed: all checks pass; only policy/documentation files changed.

**Exit Criteria:**
- Personal-use gate is host-local and complete.
- Clean-machine evidence is optional for personal use and required only for public release.
- Code signing is required only for public release.
- No source-mode 25-probe P0 suite runs for this policy change.

## Verification

- `py scripts/validate_planning_lifecycle.py`
- `py scripts/validate_template_required_sections.py`
- `py scripts/validate_repo_contracts.py --fast`
- `py -m pytest tests/test_fitcv_local_packaging.py -q`
- `git diff --check`

## Completion Criteria

1. Canonical distribution workstream names all three release classifications.
2. `PERSONAL_PACKAGED_READY` contains every required host-local acceptance item.
3. Clean-machine and code-signing requirements are limited to public release.
4. Sandbox relay, temporary firewall plumbing, and pristine-machine dependency
   absence are absent from the personal-use gate.
5. Lightweight safety contracts remain explicit and unchanged.
6. Governance, template, repository, packaging-contract, and diff checks pass.

## Closure Review

- Policy plan: `COMPLETED`
- Runtime/product behavior: unchanged
- Clean-machine/Sandbox acceptance: not run and not required for this policy task
- `PERSONAL_PACKAGED_READY`: not yet executed
- `OPTIONAL_CLEAN_MACHINE_VERIFIED`: optional and not required
- `PUBLIC_RELEASE_READY`: not targeted
- Closure checkpoint: `9d39d802cd69e130ed46ce2dd1e074f21c728c6c`
