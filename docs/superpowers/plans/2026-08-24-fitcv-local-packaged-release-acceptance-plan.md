---
template_id: implementation-plan
artifact_type: plan
status: proposed
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
- Base commit: `f4c8715d`
- Active task(s): `none`
- Expected workspace: `preserve unrelated config/taxonomy/skill_synonyms.yaml change`
- Next action: run governance and repository contract validation
- Blockers: `none`

| Task | State | Workspace | Executor | Depends On | Required Proof | Evidence |
| --- | --- | --- | --- | --- | --- | --- |
| Task 1 | `pending` | current | `codex` | none | governance, template, repository validation | pending |

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
- [ ] Step 1: Update distribution workstream release classes and deferred public checks.
- [ ] Step 2: Record the host-local packaged acceptance plan and safety invariants.
- [ ] Step 3: Run governance/template/repository validation and inspect Git diff.

**Verification:**
- [ ] `py scripts/validate_planning_lifecycle.py`
- [ ] `py scripts/validate_template_required_sections.py`
- [ ] `py scripts/validate_repo_contracts.py --fast`
- [ ] `py -m pytest tests/test_fitcv_local_packaging.py -q`
- Expected: all checks pass; no runtime or product files change.

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
