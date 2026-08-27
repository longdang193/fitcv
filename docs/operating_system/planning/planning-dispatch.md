# Planning Dispatch

Use `Artifact Selection` when artifact choice is unclear. Use `Executor
Selection` when task runtime choice is unclear. Create the smallest policy or
artifact needed for safe execution.

## Artifact Selection

| Condition | Action |
| --- | --- |
| Local, reversible, design-clear change | Edit directly |
| Broad problem framing, options, or trade-offs remain | Use `skill-brainstorming`; save a report only when requested |
| User explicitly invokes wayfinding for a known destination with materially unresolved dependent decisions expected to span multiple sessions | Use `skill-wayfinding` with one template-validated map and one writer |
| Behavior, UI intent, interfaces, or invariants need prototype validation | Use `skill-spec-drafting` with `draft-specification`; keep one file |
| Draft behavior is approved | Promote same file to `detailed-specification` and `status: active` |
| Behavior, interfaces, or invariants need durable definition without prototype work | Use `skill-spec-drafting` |
| Approved design or direct approved scope needs multiple implementation steps | Use `skill-writing-plans` |
| Multi-task execution needs durable resume or delegated checkpoints | Select `git-tracked` coordination |
| Parallel writers are required | Select `git-tracked` coordination with isolated worktrees and disjoint ownership |
| Several outcomes need coordinated direction | Use the optional roadmap; create specs or plans only where needed |
| Isolation materially reduces execution risk | Use `skill-using-git-worktrees`, then execute plan |
| Approved plan exists | Use `skill-executing-plans` |
| Final completion proof is needed | Use `skill-verification-before-completion` |
| Verified work needs an authorized Git disposition | Use `skill-finishing-a-development-branch` |

## Delivery Lifecycle

Use these gates only when their trigger applies:

1. Discovery or research when uncertainty exists.
2. Prototype and iterate when UX or behavior needs validation.
3. Design review when material design judgment is required.
4. UX or behavior approval when approval is required.
5. Detailed specification when durable behavior or contracts need definition.
6. Repository reconciliation when current source, tests, contracts, or configuration must be checked against approved scope.
7. Implementation plan when work needs multiple steps, dependencies, or handoffs.
8. Implementation.
9. Integration when a boundary is crossed.
10. Applicable frontend, backend, browser, or end-to-end verification.
11. Independent review when risk or policy requires it.

Downstream project-owned handoff: Release/Deploy → Observe, when applicable.

Design-clear reversible work may go directly to execution. Material backend
behavior requires direct backend proof. End-to-end verification applies only to
cross-boundary journeys. Release/deploy and observe remain project-owned and
optional; they are not generic lifecycle gates.

## Artifact Ownership

- brainstorming reports own exploration
- specifications own approved behavior and design decisions
- draft specifications temporarily own exploratory behavior, UI intent, assumptions, prototype references, and validation findings; promotion replaces draft content in place
- implementation plans own exact tasks, files, commands, dependencies, execution approach, shared-write controls, and verification
- the optional roadmap owns only coordinated direction across several outcomes

No artifact is required merely to connect two other artifacts. Source, tests,
configuration, and validators remain executable truth.

## Executor Selection

Executor and profile selection are independent. Select executor from task
authority, containment, topology, and expected runtime benefit. Then select the
lowest profile that can reliably complete that executor's bounded contract.

| Condition | Eligible executor |
| --- | --- |
| Codex-owned MCP, connected tools, project coordination, cross-task judgment, or final acceptance is required | `codex` |
| Task is bounded and runtime-managed batching, dependency execution, or compact execution state is likely to provide material benefit | `tura` |
| Task is bounded but long-horizon, context-heavy, exploratory, or materially helped by isolated internal contexts | `deepagents` |
| No delegated executor has clear task-specific benefit or executor fitness is unclear | `codex` |

These are advisory eligibility rules, not a classifier. Do not map profile rank
or task function permanently to an executor. Do not add automatic executor
fallback or runtime-internal plan coordination. Use task-specific evidence when
using `prefer`; otherwise keep Codex as the safe default.
