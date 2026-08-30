---
name: skill-chief-of-staff
description: "Codex lead only: use when canonical work needs sustained top-level coordination across independent Codex main-agent lanes."
required_reads: []
distribution_tier: starter_kit
---

# Chief Of Staff

## Role

Coordinate canonical work without becoming its owner. CoS owns work binding,
situational synthesis, attention selection, top-level Codex main-agent choice,
lane briefing, evidence reconciliation, blocker routing, retirement, and
escalation. `skill-executing-plans` owns
approved-plan execution.
CoS coordinates work; it does not own work execution or canonical work truth.

## Activation

Use CoS only when canonical work is deterministically bindable, two or more
materially independent lanes need synthesis, or a substantial isolated detour
needs coordination. Use ordinary execution for single-lane work or simple
parallel aggregation. CoS activates only under a native Codex lead controller.
Use coordination mode `advisory` or `plan-bound-execution`.

Advisory CoS may inspect, synthesize, challenge, and recommend. Advisory CoS has
no mutation authority. V2 advisory scope supports only an exact-commit repository
audit; PR, release, incident, specification, research, and cross-repository
work remain out of scope. Plan-bound execution requires an approved plan that
lists `skill-chief-of-staff` in `Required skills` and needs sustained handoffs,
independent write-capable lanes, or cross-task coordination.
CoS must not activate for PR, release, incident, specification, research, or
cross-repository work in V2.

CoS activates only under a native Codex lead controller. A delegated Herdr main
agent receives a bounded lane task; it must not activate
CoS, create peer agents, or reactivate coordination. CoS applies only to
`Executor: codex`;
`deepagents` uses `dcode-project`, and `tura` uses `project-delegate`. Other
generated adapters may carry this skill, but their non-Codex lead must return
`BLOCKED` rather than activate it.

## Conditional References

- For `plan-bound-execution`, read `skill-executing-plans` for approved-plan execution and executor precedence.
- For plan-bound write lanes, read `skill-using-git-worktrees` for lane identity and isolated workspace ownership.
- For applicable plan-bound review, read `skill-requesting-code-review`, `skill-reviewing-pull-requests`, and `skill-receiving-code-review`.
- For applicable plan-bound acceptance, read `skill-verification-before-completion` and `skill-finishing-a-development-branch`.
- Read `docs/operating_system/tooling/runtime-tool-resolution.md` when runtime capability is material.

## Work Binding

Resolve canonical work before selecting lanes. Record in the current turn:

- Work identity
- evidence authority
- reference anchors
- source-relative freshness boundary
- acceptance authority
- Coordination mode: `advisory` or `plan-bound-execution`

Resolve acceptance authority in this order: explicit current-work owner,
canonical work owner, existing repository or workflow authority. Return
`BLOCKED` for acceptance-sensitive claims when no authority resolves. CoS
reports recommendations; the resolved external owner accepts them.

### Repository Snapshot Advisory Binding

For V2 advisory work, bind repository identity, exact commit SHA, scoped target,
and evidence authority before inspection. Commit-bound Git evidence remains
valid while its anchor is unchanged. Runtime evidence uses
`fresh-this-turn` or `reused-this-session`; external mutable evidence follows
its own freshness boundary. Do not create freshness state.

Remote or immutable inspection needs no worktree. If local tools can mutate the
repository, use clean isolation or equivalent pre/post Git-state
proof. Read-only behavior remains instruction-level when the runtime cannot
enforce it.

## Attention

CoS attention is pull-based on explicit CoS turns. No polling or subscription
mechanism is implied by this skill. Herdr lifecycle state is runtime observation
only. It does not prove task acceptance, update the ledger, or replace
canonical work truth.

### Attention Audit

Attention Audit applies to both coordination modes. On each explicit CoS turn
with outstanding CoS-coordinated work and bound canonical work, after Work
Binding and before selecting the mode-specific next action, perform a bounded
read-only Attention Audit.

Inspect only evidence relevant to the bound work and current mode. Advisory
repository audits inspect the bound repository target at its exact commit;
plan-bound execution inspects the current plan/task, Git/worktree, applicable
PR/review, and expected Herdr lane evidence. Do not scan unrelated work,
worktrees, sessions, or pull requests. Do not invent Herdr event semantics.

Audit result: `NO_ACTION | INSPECT | BLOCKED`.

- `NO_ACTION` - evidence is consistent with the current lifecycle phase.
- `INSPECT` - CoS judgment or an approved in-scope correction is needed.
- `BLOCKED` - an existing canonical blocking condition prevents safe progress.

Consume blocking and verification semantics from their canonical owners; do not
recreate their failure taxonomy. Herdr absence alone is not a blocker. Treat it
as actionable only when current plan or current-turn evidence establishes that
a live bound agent is expected.

Audit outcomes are advisory attention results, not workflow-state transitions.
The audit does not mutate plan, Git, PR state, Herdr, authority, or durable
coordination state. Advisory CoS also does not mutate canonical work.
`attention_target` identifies what CoS should inspect; CoS remains the
next-action selector.

V1 has no autonomous wake mechanism, timer, scheduler, helper-agent dispatch,
new profile, hook integration, or persistent heartbeat state. No polling or
subscription mechanism is implied by this skill.

## Plan Binding

Plan Binding applies only to `plan-bound-execution`. Resolve the active plan in
this order:

1. explicit supplied plan path
2. plan already bound by the current execution context
3. exactly one active plan matching the current repository and worktree
4. otherwise return `BLOCKED` and show candidate evidence

Never choose newest filename, first match, or conversation-only inference.
Validate plan status, repository root, worktree, branch, base, current HEAD,
task ledger, dependencies, and ownership before dispatch. Resolve behavior from
`parent_spec` first when present, otherwise from the plan specification or
approved direct scope. Missing, stale, mismatched, or ambiguous binding blocks.

Plan-bound execution mode uses the existing runtime, lane, review, integration,
retirement, and durable-truth rules below. Select one dependency-ready task only
in `plan-bound-execution`. `skill-executing-plans` remains the sole approved-plan
execution owner.

## Runtime Gates (plan-bound execution)

Use runtime resolution rules for capability facts. On relevant Herdr, Codex,
configuration, provider, or tooling change, verify parity before material
dispatch:

- discovered `herdr` executable and version, plus required-operation smoke check
- discovered `codex` executable and version, plus required-operation smoke check
- `CODEX_HOME`
- provider and model configuration
- required MCP and tool surface
- sandbox behavior
- approval policy
- startup and trust prompts

`Executor Selection` owns executor choice. `Template Profile` selects the
profile contract; `agents/*.toml` owns its profile identity and model
capability. Before write-capable dispatch, prove the chain from selected
`Template Profile` through its canonical `agents/<profile>.toml` entry to the
resolved Codex model and instruction surface used by Herdr. A missing or
mismatched link returns `BLOCKED`; CoS must not fall back to native subagents
or a different profile.

Reuse parity evidence only inside the current lead-controller session until
one of those inputs changes. Every main-agent launch or reuse performs a cheap
identity and binding check:

- repository root and Git common directory
- exact worktree and branch
- HEAD and expected base
- lane ownership and allowed paths
- launched process cwd
- selected profile, resolved model, and Herdr launch binding

Any mismatch returns `BLOCKED` before write-capable launch.

For Herdr main-agent launch, use the repository-owned
`scripts/herdr_main_launcher.py`. CoS verifies the full lane contract, including
branch, `HEAD`, expected base, ownership, and allowed paths. Pass only selected
profile and verified runtime identity (`session`, `pane`, and `cwd`). The
launcher verifies runtime projection plus exact pane/cwd identity and reports
Git facts; it does not enforce the full CoS lane contract. Do not construct
provider, model, or developer-instruction overrides in CoS; the launcher
resolves them from `agents/*.toml` and projects them ephemerally into Codex.
Launcher evidence separates registry/runtime projection, Git identity, Herdr
observation, and launch-request evidence. Redact developer instructions and
record their digest instead. Record discovered versions and smoke-check required
operations; compare against a pinned version only when an applicable plan or
configuration explicitly pins one.

CoS uses only provider-resolved Herdr operations: discover/list, start, prompt,
wait, read, and retire/stop. Operation names and outputs come from the active
runtime; CoS must not invent commands, event semantics, subscriptions, or
durable Herdr state. Record returned facts in the current turn or plan-owned
evidence only.
For plan-bound execution, select one dependency-ready task. Prefer reuse of a healthy main-agent session
when plan, repository, lane, and context match. Select a fresh top-level Codex
main agent when context isolation materially helps. When resolving a blocker
becomes a substantial independent detour, park the current lane, dispatch a
fresh bounded Herdr main agent for that blocker, and merge back only compact
evidence or result. Do not supervise executor-local workers inside `deepagents`
or `tura`.

## Lane Contract (plan-bound execution)

Activate task and record ownership before launch. One write-capable main agent
gets one exact branch and isolated worktree. Use existing worktree, parallel-
write, review, verification, and finishing owners.

CoS has no direct Git or PR authority. An approved plan may grant the assigned
main agent bounded authority to create or reuse its lane, commit lane-owned
changes, push only its lane branch, create or update its PR, respond to review
comments, submit an assigned review, merge the exact approved PR into its
declared base after gates pass, and clean its verified-clean merged lane.

Never grant force push, direct or exceptional base mutation outside the exact
PR merge path, PR retargeting, branch-protection bypass, semantic conflict
resolution, unrelated branch or worktree mutation, unknown-file discard,
publication, or scope expansion.

Lane commits remain implementation artifacts. The lead controller records
coordination checkpoints in its own workspace after accepting proof; a lane
agent must not update the ledger as part of its implementation commit.

## Review And Integration (plan-bound execution)

Request review through `skill-requesting-code-review`. CoS dispatches only an
independent Herdr top-level Codex main-agent session. CoS never calls
`multi_agent_v1`, native Codex subagents, DeepAgents internal `task` workers,
Tura internal workers, or executor-local reviewers or helpers. The reviewer
receives the bounded contract, not the producer session history. Native
subagent review remains available only on non-CoS execution paths.

`skill-reviewing-pull-requests` owns independent PR inspection. Project OS
review is separate from GitHub review state. A review result binds to
repository, PR number, base ref and SHA when material, head ref and SHA,
verdict, checks inspected, and known limits. GitHub `APPROVE` occurs only when
review identity is eligible and repository rules allow it; otherwise use
`COMMENT` or no GitHub action. Required distinct-identity approval returns
`BLOCKED`.

Reviewer read-only behavior is instruction-level, not host-enforced by the
launcher. Capture pre-review and post-review Git state; any unexpected
modification is a review-boundary violation and an escalation.

For each base branch, grant one dependency-ready integration action at a time
to one designated main agent. Reuse implementation-main or select a fresh
integration main agent; do not create a permanent integration role. Merge only
the expected reviewed head with required proof, clean state, and no post-review
commit. An open or merged PR never completes a task automatically.

Branch and PR publication may occur after accepted lane proof when the active
plan grants it. Final merge and lane cleanup require whole-plan verification,
the exact reviewed head, remote expected-head confirmation, and post-merge
proof. Missing remote PR capability returns `BLOCKED`; do not substitute local
base mutation.

## Returns And Retirement (plan-bound execution)

Normalize main-agent execution returns to `DONE | DONE_WITH_CONCERNS | NEEDS_CONTEXT | BLOCKED`. Keep review decisions separate: CoS acceptance uses
`PASS | FAIL | BLOCKED` after checking evidence and never converts execution
status into a review verdict.
Route blockers to missing context, failed proof, runtime mismatch, review
failure, identity limitation, or user-authorized exception.

After accepted or merged lane work, prevent new writes, retire or stop the
Herdr main-agent session, confirm no live process owns the worktree, then invoke
`skill-finishing-a-development-branch`. Never let an agent remove the worktree
from which it is running.

## Durable Truth And Escalation

The active plan owns workflow state. Git owns branch, worktree, commit, and
change truth. GitHub owns PR, review, and merge truth. Herdr owns transient
process observation only. Do not require, create, or treat `identity.md`,
`cos.yaml`, fleet, heartbeat, supervisor, workflow database, model registry,
parity state file, or Herdr-state files as coordination state.

Escalate scope expansion, semantic conflicts, force updates, protected-branch
exceptions, missing eligible review identity, destructive recovery, unknown
files, failed required proof, and unresolved plan or lane identity mismatch.

## Output

Return selected task, plan binding, lane identity, `attention_result`, optional
`attention_target`, runtime evidence freshness (`fresh-this-turn` or
`reused-this-session`, with invalidation reason when reused), agent status, proof
decision, blockers, retirement result, and next action. Do not claim completion
from Herdr status, a lane commit, an open PR, or a merged PR.
