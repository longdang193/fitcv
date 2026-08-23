---
template_id: implementation-plan
artifact_type: plan
status: active
layer: change
name: fitcv-local-final-p0-integration-acceptance
targets:
  - docs/superpowers/plans/2026-08-23-fitcv-local-final-p0-integration-acceptance-plan.md
  - scripts/run_fitcv_local_p0_acceptance.py
  - tests/test_fitcv_cp/acceptance_harness.py
---

# FitCV Local Final P0 Integration Acceptance

## Goal

Run read-only final FitCV Local acceptance from a clean checkpoint after real
Local provider/model readiness and one real ready-state anchor Run are proven,
without changing product code, tests, harness, prior plans, Docker, Redis, or
RQ requirements.

## Implementation Outcomes

- The acceptance plan conforms to the implementation-plan template and preserves
  its 25-probe contract.
- Real Local readiness, controlled harness evidence, and the real ready-state
  anchor Run remain separate evidence classes.
- The acceptance run remains read-only, readiness-gated, independently
  validated, and deferred until the separate 25-probe task starts.

## Execution Approach

- Mode: `read-only acceptance`
- Coordination: `git-tracked`
- Required skills: `skill-executing-plans`, `skill-backend-verification`, `skill-verification-before-completion`
- Isolation: `current workspace`
- Commit policy: `no commits during execution`
- Preauthorized local actions: `read-only acceptance checks and declared validation commands`
- User-approval actions: `provider writes, push, merge, publication, destructive recovery, cleanup`
- Parallel ownership: `none`
- Sequential fallback: `readiness gate, then acceptance probes`
- Workspace: `C:\Users\HOANG PHI LONG DANG\repos\JOB-PROJECT`
- Runtime: `FITCV_LOCAL_MODE=1`, `FITCV_CP_INLINE_EXECUTION=1`, no `REDIS_URL`
- Base: `69b3d89e76b8eee02ce93d6406ba55ef4e23fea4`
- Worker: one bounded execution lead
- Validator: independent read-only validator
- Full 25-probe run: deferred to separate task; no product edits authorized

## Coordination State

- Coordination owner: `single lead controller`
- Branch: `main`
- Base commit: `69b3d89e76b8eee02ce93d6406ba55ef4e23fea4`
- Checkpoint identity: derive from the Git commit containing this plan; do not self-reference a future SHA.
- Active task(s): `none`
- Expected workspace: `main` at new checkpoint with readiness and final plans tracked; P20 worktree untouched
- Next action: run separate final 25-probe acceptance task from fresh disposable storage and real ready-state anchor
- Blockers: `none`

| Task | State | Workspace | Executor | Depends On | Required Proof | Evidence |
| --- | --- | --- | --- | --- | --- | --- |
| Task 1 | `pending` | main | bounded acceptance worker | readiness gate | readiness, exactly 25 probe rows, independent validation, Git drift | readiness gate PASS; 25-probe run intentionally deferred |

## Canonical Probe Matrix

| Probe | Contract | Result | Evidence |
| --- | --- | --- | --- |
| P1 | Runtime truth | PASS | supplemental facts |
| P2 | Profile snapshot immutability | PASS | worker facts |
| P3 | Settings snapshot immutability | PASS | worker facts |
| P4 | Upload source equality | PASS | supplemental facts |
| P5 | Scan source equality | PASS | supplemental facts |
| P6 | Multi-Scan ordering | PASS | worker facts |
| P7 | Combined upload + Scan ordering | PASS | worker facts |
| P8 | Scan/upload equivalence | PASS | supplemental facts |
| P9 | Worker source isolation | PASS | worker facts |
| P10 | Per-job identity conservation | PASS | supplemental facts |
| P11 | Profile semantic matching | PASS | worker facts |
| P12 | Screening evidence | PASS | worker facts |
| P13 | Stage conservation | PASS | supplemental facts |
| P14 | Ranking integrity | PASS | worker facts |
| P15 | Artifact reconciliation | PASS | supplemental facts |
| P16 | Summary reconciliation | PASS | supplemental facts |
| P17 | SQLite/API/browser equality | PASS | supplemental facts |
| P18 | Event ordering | PASS | supplemental facts |
| P19 | Failure matrix | PASS | worker facts |
| P20 | Retry/resume immutability | PASS | worker facts |
| P21 | Idempotency | PASS | supplemental facts |
| P22 | Eligibility race | PASS | worker facts |
| P23 | Historical persistence | PASS | worker facts |
| P24 | Action target identity | PASS | supplemental facts |
| P25 | Five-job semantic trace | PASS | worker facts |

## Acceptance Rules

- Readiness failure returns `BLOCKED`; no partial probe run.
- Any product defect returns `FAIL` / `NOT INTEGRATED`; do not patch during acceptance.
- `PASS` / `INTEGRATED` requires P1–P25 PASS, direct or derived critical evidence,
  independent validator agreement, and unchanged implementation/harness baseline.
- Preserved P20 worktree remains out of scope and untouched.

## Readiness Evidence Boundary

### Real Local readiness

Final acceptance must use canonical Local onboarding/provider/model APIs and a
fresh disposable storage root. It must prove:

1. provider connection is persisted as `verified` with credential configured;
2. selected model is `validated`;
3. `validated_connection_revision == connection_revision`;
4. default and required task routes resolve to eligible model records; and
5. `/local/readiness` returns HTTP `200`, `ready:true`, `reasons:[]` without
   monkeypatching.

### Controlled acceptance harness

The committed harness may supply deterministic mutation and failure evidence for
probes such as P2, P3, P9, P19, and P20. Its readiness substitutions in
`scripts/run_fitcv_local_p0_acceptance.py` around lines 200–201, including
`onboarding_is_complete = lambda: True` and
`local_readiness_status = lambda: {"ready": True, "reasons": []}`, are harness controls only. They
do not count as P1 readiness evidence or provider/model readiness.

### Real ready-state anchor Run

Before relying on controlled harness evidence, final acceptance must execute one
real Run from the same canonically provisioned ready Local storage:

`canonical onboarding → verified provider → validated model → eligible routing → /local/readiness ready:true → real Run → pipeline execution → SQLite/API/artifact/browser reconciliation`

This anchor proves real user-ready state reaches the actual pipeline. Controlled
harness runs may then add deterministic race/failure evidence.

The final-acceptance controller owns this gate; the committed harness runner is
not itself a P1 readiness gate and its readiness monkeypatches must not be
counted as anchor evidence. The separate 25-probe task must record the anchor
Run proof before invoking `scripts/run_fitcv_local_p0_acceptance.py`; missing
anchor proof is `BLOCKED`.

## Cleanup Safety

- Final acceptance may terminate only PIDs started by that execution and remove
  only disposable resources created by that execution.
- No process-name-wide Python termination is allowed.
- `scripts/smoke_fitcv_local.ps1` uses PID-scoped `Stop-Process -Id
  $process.Id -Force`; it is not global Python cleanup.
- Earlier broad Python termination belonged only to disposable probe cleanup and
  is not accepted as final-acceptance behavior.

## Validator Boundary

- DeepAgents validator may inspect this plan, repository source, tests, and Git only.
- Codex controller owns disposable DB/API/browser evidence and passes only sanitized
  report facts or content through `codex.mcp.handoff.v1` when DeepAgents reconciliation
  is needed.
- Never pass `C:\tmp` report paths, SQLite paths, credentials, or runtime artifact paths
  to DeepAgents. Never copy disposable runtime artifacts into this repository.
- A validator that lacks required runtime evidence returns `BLOCKED`; it must not infer
  product failure from an inaccessible artifact.

## Task Breakdown

### Task 1: Readiness-gated final acceptance

**Purpose:**
- Run the final 25-probe acceptance only after Local provider/model readiness passes.

**Task Function:**
- Execute and reconcile read-only FitCV Local acceptance evidence.

**Template Profile:**
- Controller-selected: `normal`
- Selection basis: bounded acceptance execution with established contracts and high evidence requirements.

**Validator Profile:**
- Controller-selected: `normal`
- Selection basis: independent reconciliation of runtime, persistence, and probe evidence.

**Specification Coverage:**
- Canonical 25-probe matrix, readiness gate, independent validation, and no product edits.

**Required Skills:**
- `skill-executing-plans`, `skill-backend-verification`, `skill-verification-before-completion`

**Files And Symbols:**
- Inspect: `scripts/run_fitcv_local_p0_acceptance.py`
- Inspect: `tests/test_fitcv_cp/acceptance_harness.py`
- Verify: `/local/readiness`, probe report, Git status

**Dependencies:**
- Local provider/model readiness must return `ready:true` with empty reasons.

**Authority:**
- Preauthorized local actions: read-only runtime checks and declared acceptance commands.
- Stop for: readiness failure, product defect, provider failure, plan/Git mismatch, or workspace drift.

**Steps:**
- [ ] Step 1: Reprove real readiness on fresh disposable Local storage through canonical APIs.
- [ ] Step 2: Execute one real ready-state anchor Run from that same storage and reconcile SQLite/API/artifacts/browser state.
- [ ] Step 3: Run exactly the 25 canonical probes only after Steps 1–2 pass.
- [ ] Step 4: Reconcile independent validation and Git drift.

**Verification:**
- [ ] Real readiness, real anchor Run, 25 probe rows, independent validator, and `git diff --check`.
- Expected: all required evidence passes or acceptance is explicitly blocked.

**Exit Criteria:**
- Acceptance is `PASS` only when readiness, all probes, independent validation, and workspace invariants pass.

## Verification

- `py scripts/validate_planning_lifecycle.py`
- `py scripts/validate_template_required_sections.py`
- `py -m pytest tests/test_validate_repo_contracts.py -q`
- `git diff --check`
- Expected: all governance checks pass before runtime acceptance begins.

## Completion Criteria

- Active plan metadata matches canonical template and checkpoint ancestry recorded by Git.
- Real readiness and the ready-state anchor Run pass before any 25-probe execution.
- All 25 probes, independent validation, and Git-drift checks satisfy acceptance rules.
- Provider readiness failure remains `BLOCKED`; no partial acceptance is claimed.

## Final Ledger

- Final decision: `READY FOR FINAL 25-PROBE ACCEPTANCE`.
- Sanitized worker facts: P2, P3, P6, P7, P9, P11, P12, P14, P19, P20, P22, P23, and P25 were `PASS`.
- Sanitized supplemental facts: P1, P4, P5, P8, P10, P13, P15, P16, P17, P18, P21, and P24 were `PASS`.
- Independent validator reconciliation: prior 25-row evidence remains historical; no new 25-probe run was performed here.
- Readiness evidence: fresh real Local runtime returned `200` with `{"ready":true,"reasons":[]}` after canonical provider creation, connection verification, model validation, route persistence, and restart.
- Provider proof: connection `verified`, credential configured, model `cx/gpt-5.4-mini` `validated`, validated connection revision matched current connection revision, and eligible model count remained `1` after restart.
- No product, test, harness, or preserved-worktree changes authorized or made by readiness provisioning.
