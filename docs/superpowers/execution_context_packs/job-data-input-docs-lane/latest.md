# Execution Context Pack

## 1) Objective

- **Workstream / Plan:** `docs/superpowers/plans/2026-05-24-18-40-job-data-input-docs-plan.md`
- **Goal:** Document job-data input pipeline (LinkedIn via Apify) with one SSOT doc and clear navigation pointers.
- **Bounded Scope (in-scope only):**
  - `README.md`
  - `docs/job-data-input.md`
  - `docs/pipeline.md`
  - lane evidence artifacts under `docs/superpowers/` for closure only
- **Out of Scope (explicit):**
  - pipeline runtime behavior changes
  - schema changes, migrations, or ingestion code changes
  - publication workflow / public mirror changes

## 2) Canonical Inputs (Source of Truth)

- **Primary plan:** `docs/superpowers/plans/2026-05-24-18-40-job-data-input-docs-plan.md`
- **Specs / maps / thread docs:** none (doc-only lane)
- **Governance / workflow rules used:**
  - `docs/operating_system/prompt_templates/single-lane-merge-and-reconcile-prompt.md`
  - `docs/operating_system/templates/execution-context-pack-template.md`
  - `docs/operating_system/governance/execution-context-pack-governance.md`

## 3) Current Task State

- **Completed:**
  - Doc updates landed on lane branch:
    - `docs/job-data-input.md` added as SSOT
    - `README.md` points to SSOT
    - `docs/pipeline.md` points to SSOT
- **In Progress:**
  - Closure reconciliation + verification evidence + merge/push to `main`
- **Deferred / Dropped:**
  - none
- **Known divergence from plan (if any):**
  - none (pending verification commands)

## 4) Files Changed This Lane

- `README.md` — add Job Data Input section + SSOT link.
- `docs/job-data-input.md` — SSOT doc for Apify/LinkedIn job ingestion contract and transforms.
- `docs/pipeline.md` — add pointer to SSOT doc.

## 5) Verification State

- **Last commands run:**
  - `.\.venv\Scripts\python.exe scripts/validate_planning_lifecycle.py --strict` (PASS)
  - `.\.venv\Scripts\python.exe scripts/validate_checkpoint_packs.py` (PASS)
  - `.\.venv\Scripts\python.exe scripts/validate_repo_contracts.py --fast` (PASS)
  - `npx gitnexus detect_changes --scope staged --repo "C:\Users\HOANG PHI LONG DANG\repos\JOB-PROJECT"` (PASS: `No changes detected.`)
- **Failing checks (if any):**
  - none observed
- **Gaps still unverified:**
  - merge + post-merge repo-contract check on `main`

## 6) Open Blockers / Risks

- None known. Main risk: repo-wide planning/checkpoint validators might fail due to preexisting unrelated artifacts.

## 7) Next Exact Action

- **Action type:** verify → reconcile → merge
- **Target:** merge `codex/job-data-docs` into `main` via fast-forward only after validators pass.
- **Exact command or edit intent:**
  - run closure validators (Section 5)
  - stage + commit plan/context artifacts once verified
  - `git checkout main && git pull --ff-only && git merge --ff-only codex/job-data-docs`
  - rerun `.\.venv\Scripts\python.exe scripts/validate_repo_contracts.py --fast`
  - `git push origin main`

## 8) Resume Prompt (Copy/Paste)

```text
Read this execution context pack first. Verify current lane branch contains the files listed in Section 4. Run the exact verification commands in Section 5 and record their outputs. Only then proceed with ff-only merge and push.
```

## Source-Truth Rule

If context pack, source files, and command output disagree:
1. command output (exit code + log) wins
2. then source files
3. then context pack
