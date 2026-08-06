# Managed Execution Adapter Contract

## Boundary

`scripts/harness_task.py` owns packet resolution, run records, authorization,
verification, outcomes, and controller decisions. Host owns actual agent and
workspace operations. Generic CLI has no host adapter and exposes
`run-unavailable` only for explicit unavailable-adapter proof.

Managed work starts only when host calls `run_managed(root, request, adapter)`.
No packet or `.harness/runs/<run-id>/run.json` means source-first local work,
not harness-managed work.

## Generic CLI Retry Boundary

`uv run python scripts/harness_task.py run-unavailable --task <request.json>`
may create immutable packet and mutable `run.json` only to prove that no host
adapter is available. It cannot prepare a workspace, dispatch writer or
validator lanes, run packet checks, or retry managed work.

## Codex Provider Invocation

`runtime_provider_id: codex_app_server` selects provider identity; it does not
make generic core CLI a provider host. From installed `codex-harness-host`
source root, verify capability and dispatch same request through provider host:

```powershell
uv run codex-harness-host capabilities
uv run codex-harness-host run --harness-root <repo-root> --server-uri ws://127.0.0.1:4500 --request <request.json>
```

Do not use `run-unavailable` for retry. It proves generic CLI lacks injected
adapter and is terminal evidence for that invocation only. Preserve that
blocked run; create successor request with new `run_id` for provider-host retry.

Controller records the resulting `block`, `retry`, or other allowed decision
through a JSON file, not inline text:

```powershell
uv run python scripts/harness_task.py decision --run-id <run-id> --decision <decision.json>
```

`<decision.json>` contains `{"kind":"block","reason":"..."}` or another
policy-allowed decision. This records controller disposition only; it cannot
replace provider-host writer, check, or validator evidence.

Packet owns role-derived claim schema for every executable lane. Host prompts
and core claim validation consume that same immutable schema.

Packet `agent_identity` is immutable copy of selected `agents/<template>.toml`:
`{template, model_provider, model, reasoning_effort}`. Template TOML remains
sole static source. Host starts every dispatched lane with exact provider and
model, disables provider fallback, starts turn with exact reasoning effort,
then requires app-server response to confirm `{model_provider, model,
reasoning_effort}`. App-server has no template field; confirmed runtime model
selection plus immutable template copy proves selected template contract.
Missing or mismatched confirmation blocks lane evidence and acceptance.

## Plan-Linked Coordination

Optional `coordination` frontmatter on Git-tracked active implementation plan
is static coordination SSOT. It owns `target_branch`, `base_ref`, task IDs,
dependencies, canonical topology, and planned write paths. Every manifest task
maps exactly once to prose `Coordination ID`.

For a plan-linked request, core derives topology, base ref, and planned paths
from manifest task, rejects conflicting request values, and copies only
`plan_ref`, `plan_task_id`, and normalized `plan_digest` into immutable packet.
Existing `base_commit` remains sole resolved code-base identity.

`run.json` owns task-state derivation, handoff, evidence, and decisions.
`coordination-status` is read-only; `handoff` writes only current non-terminal
coordinated run. Controller activates one ready task at a time for one plan and
checks active same-branch path overlap. Same logic applies to every canonical
topology; parallelism remains packet-internal. No cross-controller lock, lease,
queue, scheduler, or host-turn resume is provided. Changed digest or base
commit blocks continuation; controller creates successor attempt.

## Provider Admission

`repo_config/harness.yaml` is sole registry for static managed-provider IDs,
contract versions, route allowlists, and route defaults. Request resolution
copies exactly one provider object into immutable packet state. A host reports
current mode enforcement only through `capabilities()`; static policy never
claims a mode is enforced. `provider_capabilities.yaml` supports generated
agent surfaces only and never participates in runtime selection or acceptance.

A candidate stays absent from route policy until it passes same packet,
workspace, tool-binding, check, read-only validator, and controller-acceptance
proof as every admitted provider. No automatic provider fallback exists.

## Required Adapter Methods

Host adapter provides these methods:

| Method | Input | Required result |
| --- | --- | --- |
| `capabilities()` | none | map of mode to `enforced`, `advisory`, or `unavailable` |
| `identity()` | none | exact packet `runtime_provider` object: `{provider_id, contract_version}` |
| `prepare_workspace(lane, packet)` | immutable lane and packet | workspace identity object |
| `dispatch_lane(lane, packet, workspace, cancellation_token)` | immutable lane, packet, workspace | opaque dispatch handle |
| `collect_claim(handle)` | dispatch handle | role-valid `claimed_result` |
| `collect_lane_evidence(handle, lane, packet, workspace)` | dispatch handle, immutable lane and packet, workspace | host execution evidence for exactly one dispatched lane |
| `cancel_lane(handle)` | dispatch handle | cancellation attempt |
| `materialize_final_state(lane, packet, workspaces)` | immutable integration lane, packet, workspaces | final workspace identity object |
| `verify_tool_bindings(lane, packet, workspace)` | immutable lane, packet, workspace | one verified root binding per selected packet tool |
| `run_checks(packet, workspace)` | immutable packet, final workspace | host check evidence from selected packet-scoped shell binding |

Only `enforced` capability permits dispatch. `advisory`, `unavailable`, absent,
or malformed capability produces `execution_mode_unavailable` before workspace
preparation or dispatch. For an enforced mode, core compares `identity()` with
immutable packet `runtime_provider` before workspace preparation or dispatch.
Core never substitutes a different provider after identity or capability failure.
An unavailable adapter may expose a non-empty `unavailable_detail` string. Core
persists it in the outcome so generic CLI fallback cannot be misreported as a
provider capability failure.

## Adapter-Owned Workspace Boundary

Every managed writable lane uses an adapter-owned isolated workspace. Host
dispatches the writer only with that workspace as its root and an enforced
write-capable sandbox that cannot write outside it. Host materializes one final
isolated state before validator dispatches; validator uses that state with an
enforced read-only sandbox.

Ambient desktop or CLI threads outside the adapter are source-first,
unvalidated work. They are not managed lanes and no host capability may claim
to intercept or accept their writes.

## Topology Materialization

Host keeps one effect boundary: `prepare_workspace` creates a writer workspace
and `materialize_final_state` produces one validator workspace. Core owns lane
DAG scheduling and does not branch on host topology implementation.

- `single_work_lane`: sole writer workspace is final state.
- `sequential_work_lanes`: permit one linear work-lane dependency chain only.
  Each successor uses a fresh base clone with its direct predecessor changes
  materialized before dispatch. Branches, joins, multiple roots, and missing
  predecessor state fail closed. Terminal workspace is final state.
- `parallel_work_lanes`: writers receive isolated base clones. Host creates one
  fresh final base clone and materializes writer changes in lane-ID order.
  Duplicate actual changed paths fail before any validator dispatch.

Initial materialization supports regular-file adds, modifications, deletions,
and untracked files. Reject renames, copies, unmerged entries, type changes,
submodules, and symlinks. Any materialization failure stops checks and validator
dispatch. Host advertises a topology `enforced` only after direct success and
failure tests plus live managed proof.

## Packet Tool Bindings

`repo_config/harness.yaml` owns logical tool metadata. Packet resolution copies
an immutable `tool_bindings` manifest with one declaration for every selected
route tool. Host must resolve every declaration to exactly one native binding
whose workspace root equals the dispatched lane workspace.

Each host binding evidence record must include tool, host kind, effective
access, root probe, workspace root, exact packet `runtime_provider`, and
`verified: true`. Writer lanes use
`writer_access`; validator lanes use `validator_access`, which must be
read-only. Missing, duplicate, ambient, mismatched, or unverified bindings
block dispatch. Ambient desktop MCP roots never satisfy a packet binding.

Host runs checks only through a verified selected `shell` binding in the final
packet workspace. Check evidence must identify that workspace, binding, and
exact packet `runtime_provider`.

## Lane Execution Evidence

After each lane claim, host returns immutable execution evidence from its own
dispatch handle. Agent JSON claims cannot provide this evidence. Each record
must include exact lane ID, workspace root, host thread ID, host turn ID,
enforced sandbox, selected packet tools used, raw tool-call names, command
results, exact packet `runtime_provider`, exact packet `agent_identity`,
`ambient_mcp: false`, and workspace status before and after turn.

Writer evidence must show use of at least one packet-selected tool with
`workspace_write` access. Each command result must use exact packet workspace.
Validator evidence must show a separate `read-only` turn, use of at least one
packet-selected read-only tool, and identical workspace status before and
after. Core stores both lane records in `run.json` and fails verification if a
work or validator lane lacks valid host evidence.

## Completion States

| Result | Meaning |
| --- | --- |
| `accepted` | Controller accepted fresh harness evidence with proven criteria. |
| `blocked` | Managed lifecycle could not continue. |
| `unvalidated` | Controller explicitly waived unavailable managed execution with reason. Local proof may exist but is not managed acceptance. |

Host must never convert `unvalidated` to `accepted`. Start a new managed run
after capability exists.

## Validator Lanes

Independent validator evidence exists only when host capability supports a
separate read-only lane. Host must dispatch validator with a fresh immutable
packet after implementer claim, record its own claim, and keep validator paths
read-only. Implementer claim, local tests, and controller prose never count as
validator evidence.

Every mode remains unavailable until selected host adapter proves its lane
semantics. Do not silently downgrade a requested mode.

## Controller Rule

Controller records only allowed decisions in `run.json`: accept, retry,
escalate, request approval, waive, or block. `waive` requires non-empty
`reason` and is allowed only when outcome permits it. Controller cannot accept
an unavailable or waived run.

## Friction Learning

`.harness/friction-events.jsonl` is append-only cross-run friction truth.
`repo_config/harness.yaml:friction_policy` owns only its schema version,
distinct-run threshold, and rolling window. Attempts retain event IDs, never
copied friction payloads.

One observed event schema records route, provider, topology, lane kind, phase,
source, code, evidence reference, timestamp, and deterministic fingerprint.
It excludes prompts, secrets, and raw command output. Core normalizes claim,
adapter, integration, check, validator, cancellation, and decision friction
into this schema.

`friction-report` is read-only and derives unresolved candidates from distinct
runs inside configured window. `friction-resolve` requires accepted
`harness_improvement` run, names candidate event IDs, and appends controller
decision: `keep`, `revise`, `remove`, or `pending`. Neither command mutates
routes, policy, skills, tools, or providers. Fresh representative rerun proof
is required before `keep`.
