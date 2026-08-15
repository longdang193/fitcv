# Planning Dispatch

Use this decision table only when artifact choice is unclear. Create the smallest artifact needed for safe execution.

| Condition | Action |
| --- | --- |
| Local, reversible, design-clear change | Edit directly |
| Broad problem framing, options, or trade-offs remain | Use `skill-brainstorming`; save a report only when requested |
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

## Artifact Ownership

- brainstorming reports own exploration
- specifications own approved behavior and design decisions
- draft specifications temporarily own exploratory behavior, UI intent, assumptions, prototype references, and validation findings; promotion replaces draft content in place
- implementation plans own exact tasks, files, commands, dependencies, execution approach, shared-write controls, and verification
- the optional roadmap owns only coordinated direction across several outcomes

No artifact is required merely to connect two other artifacts. Source, tests,
configuration, and validators remain executable truth.
