---
feature_type: add
feature_name: none
status: planned
summary: "Implement a minimal CI-first hook workflow that enforces adapter verification, baseline tests, and publication-boundary dry checks on push and pull request events."
---

# CI Hook Layer Implementation Plan

**Feature:** `none`  
**Spec:** `docs/superpowers/archive/specs/2026-04-09-21-55-ci-hook-layer-spec.md`  
**Type:** `add`  
**Status:** `planned`  

> **For agentic workers:** Use `executing-plans` or `subagent-driven-development` to implement task-by-task.

**Goal:** Add the first real automatic hook layer to `JOB-PROJECT` by creating a GitHub Actions workflow that runs adapter integrity checks, baseline tests, and a publication-boundary dry check on every push and pull request.

**Architecture:** The implementation adds one centralized CI workflow under `.github/workflows/` and keeps all repo-specific verification logic inside the existing PowerShell scripts and test suite. The workflow is intentionally small and binary: each job runs one high-value check with clear remediation, and the docs are updated so the repo operating system explicitly treats CI as part of the normal enforcement loop.

**Key Invariants:**
- Existing scripts remain the source of truth for adapter and publication-boundary checks.
- The first hook layer stays CI-first and does not require local Git hook setup.
- The initial workflow remains small, readable, and deterministic.
- This work is cross-cutting operating-system automation, so `Feature: none` remains valid.

**Rollout / Revert:**  
- rollback_trigger: CI proves flaky or blocks normal work for non-deterministic reasons  
- rollback_method: revert the workflow file and the accompanying doc updates in one commit  

---

## Doc Update Matrix

- Feature contract: `none`
- Stage contracts: `none`
- Feature history: `none`
- Feature-specific docs: `none`
- Cross-cutting docs:
  - `docs/operating_system/repo-governance.md`
  - `docs/operating_system/publication-workflow.md`
- README: `README.md`
- Generated discovery: `none`

## File Map

### Create

- `.github/workflows/repo-hooks.yml`

### Modify

- `docs/operating_system/repo-governance.md`
- `docs/operating_system/publication-workflow.md`
- `README.md`

### Verify

- `scripts/sync_agent_adapters.ps1`
- `scripts/verify_agent_adapters.ps1`
- `scripts/publish_public_repo.ps1`
- `tests/*`

## Runner And Command Decisions

### CI runner

Use `windows-latest` for the first rollout.

Reason:

- the repo’s hook scripts are PowerShell-first
- the current local operating flow is already Windows-oriented
- this minimizes adaptation work for the initial hook layer

### Python version

Use Python `3.11`.

Reason:

- `pyproject.toml` declares `requires-python = ">=3.11"`
- the repo is already configured for Python 3.11 tooling

### Dependency installation

Use standard pip-based setup in the workflow:

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt pytest-httpx
python -m pip install -e .
```

Reason:

- `requirements.txt` provides most runtime and test dependencies
- `pytest-httpx` appears in dev dependencies but not in `requirements.txt`
- `pip install -e .` ensures the package itself is installed cleanly from `src/`

### Baseline test command

Use:

```powershell
python -m pytest
```

Reason:

- `pyproject.toml` already points pytest at `tests`
- `tests/conftest.py` skips live integration tests when credentials are absent
- this is the clearest baseline hook behavior for the first rollout

## Task 1: Create the GitHub Actions workflow skeleton

**Files:**
- Create: `.github/workflows/repo-hooks.yml`
- Docs: `docs/operating_system/repo-governance.md`, `docs/operating_system/publication-workflow.md`, `README.md`

- [ ] Step 1: Create `.github/workflows/repo-hooks.yml` with triggers for `push` and `pull_request`.
- [ ] Step 2: Set workflow-wide defaults so PowerShell steps use `pwsh`.
- [ ] Step 3: Add three named jobs:
  - `adapter-integrity`
  - `baseline-tests`
  - `publication-boundary`
- [ ] Step 4: Use `runs-on: windows-latest` for each job in the first version.
- [ ] Step 5: Keep the first workflow simple and avoid path filters or matrix expansion.
- [ ] Step 6: Commit the initial workflow scaffold.

## Task 2: Implement the adapter-integrity job

**Files:**
- Modify: `.github/workflows/repo-hooks.yml`
- Verify: `scripts/sync_agent_adapters.ps1`, `scripts/verify_agent_adapters.ps1`
- Docs: `docs/operating_system/repo-governance.md`

- [ ] Step 1: Add checkout using `actions/checkout`.
- [ ] Step 2: Add Python setup using `actions/setup-python` with Python `3.11`.
- [ ] Step 3: Install dependencies with:

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt pytest-httpx
python -m pip install -e .
```

- [ ] Step 4: Run:

```powershell
.\scripts\sync_agent_adapters.ps1
.\scripts\verify_agent_adapters.ps1
```

- [ ] Step 5: Add a post-sync Git diff check so CI fails if synchronization changes tracked files:

```powershell
git diff --exit-code
```

- [ ] Step 6: Confirm the job fails meaningfully when generated adapter outputs drift from source.
- [ ] Step 7: Commit the adapter-integrity job.

## Task 3: Implement the baseline-tests job

**Files:**
- Modify: `.github/workflows/repo-hooks.yml`
- Verify: `tests/*`
- Docs: `README.md`

- [ ] Step 1: Add checkout and Python setup to the `baseline-tests` job.
- [ ] Step 2: Reuse the same dependency installation commands as the adapter job.
- [ ] Step 3: Run:

```powershell
python -m pytest
```

- [ ] Step 4: Confirm the job does not require live GCP credentials for default execution because integration tests are skipped automatically when credentials are absent.
- [ ] Step 5: Make sure the README mentions that baseline tests now run automatically in CI.
- [ ] Step 6: Commit the baseline-tests job and README update.

## Task 4: Implement the publication-boundary job

**Files:**
- Modify: `.github/workflows/repo-hooks.yml`
- Verify: `scripts/publish_public_repo.ps1`
- Docs: `docs/operating_system/publication-workflow.md`

- [ ] Step 1: Add checkout and Python setup to the `publication-boundary` job.
- [ ] Step 2: Install dependencies only if the publication script needs repo state or Python-installed tooling present for dry-run validation.
- [ ] Step 3: Run the curated export dry check without `-Push`:

```powershell
.\scripts\publish_public_repo.ps1
```

- [ ] Step 4: Confirm the job succeeds without a configured `public` remote because the script only requires the remote when `-Push` is used.
- [ ] Step 5: Update `docs/operating_system/publication-workflow.md` so the CI dry check becomes part of the normal publication-boundary operating loop.
- [ ] Step 6: Commit the publication-boundary job and doc update.

## Task 5: Update operating-system docs to treat CI as a real hook layer

**Files:**
- Modify: `docs/operating_system/repo-governance.md`
- Modify: `docs/operating_system/publication-workflow.md`
- Modify: `README.md`

- [ ] Step 1: Update `docs/operating_system/repo-governance.md` to record that hook enforcement now includes CI-triggered adapter verification and baseline checks.
- [ ] Step 2: Update `docs/operating_system/publication-workflow.md` to record that curated export preparation is also exercised through CI dry checks.
- [ ] Step 3: Update `README.md` with a short note that pushes and pull requests are expected to pass the repo hook workflow.
- [ ] Step 4: Keep these updates short and operational rather than turning them into another long policy layer.
- [ ] Step 5: Commit the doc updates if not already committed alongside earlier tasks.

## Task 6: Validate the workflow locally as far as possible

**Files:**
- Verify: `.github/workflows/repo-hooks.yml`
- Verify: `scripts/sync_agent_adapters.ps1`
- Verify: `scripts/verify_agent_adapters.ps1`
- Verify: `scripts/publish_public_repo.ps1`

- [ ] Step 1: Run locally:

```powershell
.\scripts\sync_agent_adapters.ps1
.\scripts\verify_agent_adapters.ps1
python -m pytest
.\scripts\publish_public_repo.ps1
```

- [ ] Step 2: Confirm the working tree is clean after sync if no adapter drift exists.
- [ ] Step 3: Review the workflow YAML for job names, triggers, and command correctness.
- [ ] Step 4: If available, use a YAML or GitHub Actions linter; otherwise perform a manual review focused on indentation, runner choice, shell choice, and action versions.
- [ ] Step 5: Commit any final fixes required to make the workflow internally consistent.

## Task 7: Verify in GitHub after push

**Files:**
- Verify: `.github/workflows/repo-hooks.yml`
- Docs: exact entries from the Doc Update Matrix

- [ ] Step 1: Push the branch containing the hook workflow.
- [ ] Step 2: Confirm GitHub Actions starts automatically on the branch push.
- [ ] Step 3: Inspect each job result:
  - adapter integrity
  - baseline tests
  - publication boundary
- [ ] Step 4: If CI fails, fix the repo or workflow rather than weakening the hook semantics without cause.
- [ ] Step 5: Once green, confirm the workflow is suitable to run on pull requests.
- [ ] Step 6: Commit any final remediation required after the first live CI run.

## Validation Commands

Run locally before claiming completion:

```powershell
.\scripts\sync_agent_adapters.ps1
.\scripts\verify_agent_adapters.ps1
python -m pytest
.\scripts\publish_public_repo.ps1
git status --short
```

## Completion Criteria

The implementation is complete when:

- `.github/workflows/repo-hooks.yml` exists and runs on `push` and `pull_request`
- adapter integrity checks are automated in CI
- baseline tests are automated in CI
- publication-boundary dry checks are automated in CI
- `docs/operating_system/repo-governance.md` reflects the new hook behavior
- `docs/operating_system/publication-workflow.md` reflects the new hook behavior
- `README.md` mentions the CI hook expectation
- local verification commands pass
- the first GitHub Actions run is green or any failures are fixed before closeout
