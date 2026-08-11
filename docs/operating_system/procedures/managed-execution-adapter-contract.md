# Managed Execution Adapter Contract

## Boundary

Installed `harness-core` owns packet resolution, run records, authorization,
verification, outcomes, and controller decisions. Consumer scripts are bridge
entrypoints only. Host owns actual agent and workspace operations. Generic CLI
has no host adapter and exposes
`run-unavailable` only for explicit unavailable-adapter proof.

Host runtime dependencies must include compatible `harness-core` and
`harness-core-launcher` releases. Target virtual environments, dev groups, and
`requirements.txt` do not satisfy host `uv run` resolution. Launcher owns
absent/unloadable core result `harness_core_environment_unavailable`; no
consumer-script fallback exists.

Consumer installation, pinning, and preflight procedure:
[`harness-core-consumer-setup.md`](./harness-core-consumer-setup.md).

Managed work starts only when host calls `run_managed(root, request, adapter)`.
No packet or `.harness/runs/<run-id>/run.json` means source-first local work,
not harness-managed work.

## Generic CLI Retry Boundary

`harness-core run-unavailable --task <request.json>`
may create immutable packet and mutable `run.json` only to prove that no host
adapter is available. It cannot prepare a workspace, dispatch writer or
validator lanes, run packet checks, or retry managed work.

## Codex Provider Invocation

`runtime_provider_id: codex_app_server` selects provider identity; it does not
make generic core CLI a provider host. Use only the active pointer-selected
runtime through launcher:

```powershell
harness-core-launcher capabilities
harness-core-launcher preflight
harness-core-launcher run --harness-root <repo-root> --request <request.json>
harness-core-launcher run --harness-root <repo-root> --run-id <run-id>
harness-core-launcher terminalize-attempt --harness-root <repo-root> --run-id <run-id> --input <envelope.json>
```

Provider-host installation initializes absent user configuration with registered
launcher ID `installed_codex_app_server`.
The host reads no provider setting from repository policy, request, packet,
environment, or current directory. Configuration accepts a registered launcher
ID for host-spawned stdio or an explicit external WebSocket endpoint. It rejects
arbitrary command fields and secret-bearing fields.

### Committed Runtime Provenance

After a host-source fix, require this gate before product packet dispatch:

1. Commit changed host runtime module and its regression test. Preserve unrelated
   host work; clean repository state is not required.
2. Run `harness-core-launcher doctor` and record its active `host_root`, host
   commit, and host release.
3. Prove changed host source matches that committed file at `HEAD`.
4. Activate that committed host through launcher, then run fresh `doctor`,
   `capabilities`, and `preflight`.
5. Create fresh product successor request only after this proof passes. Never
   resume terminal-blocked run.

Passing `preflight` proves transport readiness, not committed runtime
provenance. A dirty imported changed module blocks product dispatch even when
preflight passes.

After a committed host-source update, refresh and prove the locked source host
before dispatch:

```powershell
harness-core-launcher upgrade --host-root <codex-harness-host-root>
harness-core-launcher doctor
harness-core-launcher capabilities
harness-core-launcher preflight
```

Never use bare `codex-harness-host` for preflight or dispatch. PATH can resolve
a stale user-level `uv tool` with incompatible host or core code. If it does,
inspect `Get-Command codex-harness-host -All` and `uv tool list`; preserve that
tool until an authorized operator chooses update or removal. Locked source-host
commands remain the only managed boundary. `run --help` must expose both
exclusive inputs: `--request` and `--run-id`.

`preflight` opens configured stdio or explicit external WebSocket transport and
completes `initialize`. `stdio` plus `host_spawn` is Windows-only: host resolves
one registered launcher, contains its suspended direct child in a Job Object,
verifies the child image, then resumes it. Unsupported hosts fail before child
creation with `containment_unavailable`; use trusted external WebSocket transport
instead. Preflight owns a temporary Job; managed lanes borrow their lease Job.

Startup uses the host-owned short cap inside existing operation budget. Failure
output is `preflight_failed` with sanitized `failure_code` and
`session_observation`. Reaped managed sessions produce only current
packet-declared terminal evidence. If cleanup cannot prove containment stopped,
host emits bounded `terminal_recording_failed` recovery evidence; it must not
emit incomplete lane evidence, write `run.json`, retry, or terminalize.

`run` admits core and host API, then repeats liveness proof before packet,
workspace, or `run.json` creation. Missing or invalid trusted configuration
returns `provider_runtime_unavailable`; configured transport or authentication
failure returns `preflight_failed`. `--request` starts one run; `--run-id`
resumes one existing planned attempt without request resubmission. Inputs are
exclusive. Current dispatchable packet API stores a non-secret runtime binding;
host re-reads configuration before every lane and returns
`provider_configuration_changed` before provider or product work if binding
drifts. Binding contains static transport configuration only; current host
instance identity belongs to mutable preflight evidence and the execution lease.
Historical bindings with a host instance ID compare by their static projection.
`harness_core.static_provider_runtime_binding` is that projection for core and
host consumers.
No automatic transport fallback exists.

`harness-core-launcher decision --harness-root <repo> --run-id <id> --decision
<file>` is the only CLI retry or escalation boundary. Host supplies current
admission and preflight facts; core creates the immutable successor packet and
writes decision state. Generic core `decision` rejects executable retry or
escalate without an adapter. Terminal decisions remain core-only.

Do not use `run-unavailable` for retry. It proves generic CLI lacks injected
adapter and is terminal evidence for that invocation only. Preserve that
blocked run; create successor request with new `run_id` for provider-host retry.

Packet owns role-derived claim schema only for agent-invocation lanes. Host
prompts and core claim validation consume that immutable schema. Deterministic
integration and check nodes record normalized observations, not agent roles or
claims.

Packet `agent_identity` is immutable copy of selected `agents/<template>.toml`:
`{template, model_provider, model, reasoning_effort}`. Template TOML remains
sole static source. Host starts every dispatched lane with exact provider and
model, disables provider fallback, starts turn with exact reasoning effort,
then requires app-server response to confirm `{model_provider, model,
reasoning_effort}`. App-server has no template field; confirmed runtime model
selection plus immutable template copy proves selected template contract.
Missing or mismatched confirmation blocks lane evidence and acceptance.

Host records a confirmed selection as `app_server_model_selection` on every
completed App Server turn whose result becomes core evidence: lane evidence,
packet checks, completed claim-repair finalization, and delegated-child
completion. Core compares every present record to immutable packet
`agent_identity`; no producer may substitute a caller-selected model. Field is
additive for historical evidence only: core permits its absence from older
records, while current host-produced evidence always includes it.

## Packet Context And Verification

Core resolves the selected authority, toolset, and verification profile into
one immutable packet. Host uses only resolved packet tools. Controller runs
only packet-declared checks through `run_checks`; worker authority never grants
check execution.

Core owns `work_context` normalization and validation. Host renders one context
object exactly once per turn: supplied `packet["work_context"]`, or legacy
`{"version": 0, "objective": packet["user_request"]}` when an already
admitted packet omits it. Host must not separately render `user_request`, parent
transcript, or a second instruction channel, and must not duplicate core context
schema validation. Core validates supplied context digest, fact/reference
identity, UTF-8/count limits, and readonly-artifact SHA-256/byte length before
dispatch. Host materializes only those packet artifacts.

Core evaluates packet postconditions against final change collection. A
`workspace_unchanged` postcondition fails on every change from packet base;
write verification records only configured controller checks. No profile,
artifact, or context fallback is permitted.

## Runtime Budget And Abnormal Turn Recovery

`repo_config/harness.yaml:execution_budgets` owns named profiles, maximum turn
timeout, `finalization_reserve_seconds`, and lease duration model. Reserve is
positive and less than every named profile timeout.
`defaults.execution_budget_profile` selects initial profile. Core copies one
resolved `execution_budget` into every immutable packet, including the bounded
whole-lane `lane_timeout_seconds` and `check_timeout_seconds`. Request and
controller decision cannot choose an arbitrary profile or timeout.

Host gives each normal App Server lane turn `turn_timeout_seconds -
finalization_reserve_seconds`. On interruption or empty final text, host runs one
separate read-only finalizer for exactly `finalization_reserve_seconds`. Finalizer
may inspect at most once, never writes or runs diagnostics, and returns only its
structured claim. It is a completion phase, not a lane, check, retry, or resume.
`lane_timeout_seconds` bounds the complete work turn and finalizer lifecycle;
packet-native tool probes and checks use `check_timeout_seconds`. The short
`preflight` bound is transport-only and never substitutes for packet budget. On
Windows, every provider or packet-native tool process for one lease uses that
lease's Job Object containment.

For a current leased packet, an unusable claim after a completed work turn may use exactly
one core-authorized repair. Core first collects completed-turn identity, then
requests repair against that same open provider session and original thread ID.
Host uses only packet finalization reserve, a read-only sandbox, and no dynamic
tools. It closes session before stopped-containment evidence; it never reopens a
session, starts a fresh repair thread, or turns claim repair into retry, resume,
validation, or product work.

`repo_config/harness.yaml:orchestration` owns concurrency. Core resolves
`max_parallel_lanes` into packet orchestration to cap every concurrent work
lane, while `max_parallel_writers` further caps only write-capable lanes. Older
consumer policy without `max_parallel_lanes` resolves it to
`max_parallel_writers`; current packets always carry both resolved values. Host
uses packet limit for executor capacity and never substitutes a host constant.
For current leased packets, host returns one bounded packet-declared terminal
observation for each terminal dispatched lane and each
host-run packet check (`check:<name>`). Core validates schema, lane, immutable
run/attempt/packet/lease/host binding, lease duration, and timestamp before
persisting normalized observations under
`attempt.host_terminal_observations` inside `terminalize_attempt(evidence)`.
Observation sources are `completed`, `provider_failure`, `timeout`, and
`cancellation`; host crash uses separate recovery absence proof. Observations
record only lane, opaque runtime IDs when available, terminal/interrupt state,
bounded item and command state, final-claim state, containment, stop proof, and
error field names plus SHA-256 hashes and byte lengths. They never store raw
command output, prompts, environment values, provider error text, or assistant
text. Provider failure observations may also carry core-normalized
`provider_session_observation/v1`: bounded lifecycle timing, launcher binding
digest, process identity and cleanup state, plus redacted and size-capped stderr
diagnostic metadata.

If completed host stop proof exists but core later rejects a claim, check result,
or verification semantics, core records `evidence.failure` and terminalizes the
attempt as `core_failure`. Host must not rewrite completed work as
`provider_failure`, and core must not leave the lease active.

Core derives timeout as `dispatch_timeout` unless terminal evidence shows a
write-capable work lane completed one or more commands but emitted no final
claim after finalization reserve expires. That condition is
`writer_completion_missing`; it permits only `block`, never retry, escalation,
or resume. Other timeouts may only `escalate` through packet
`escalation_profile` or `block`; timeout never permits `retry`. Provider failure
derives `dispatch_failed` with packet retry-policy decisions. Escalation creates
a fresh successor packet with core-selected profile. Preserve older packet and
evidence unchanged.
If an attempt is already `planned`, resume it with provider `--run-id`; do not
submit its request again.

Inspect `attempt.execution_lease`, `attempt.host_terminal_observations`, and
`attempt.terminal_record` before controller decision. They distinguish missing,
active, and completed command state without provider transcript recovery.
Evidence informs decision; it never selects one.

## Read-Only Evidence Artifacts

Core owns catalog kinds, route profile admission, immutable content hashes, and
packet records. API 5 direct handoff requests name an exact terminal source run
and attempt plus an allowed profile; they never name artifact IDs, paths, or
content. Core resolves bounded descriptors and records packet proof plus target
attempt audit. Recurring friction supplies its bounded source set only to that
same resolver.

Host materializes only API 6 packet descriptors as separate read-only sidecar
files outside writable workspace access, validates packet proof, descriptor
size, and SHA-256, and exposes only descriptor metadata plus exact read path in
prompt context. A read-only packet tool probes and rejects writes to evidence
paths. Host never clones or mounts ambient `.harness`. A route with missing
required evidence rejects before dispatch. Current
`sanitized_command_trace` uses `context_limits.artifact_max_bytes` as one cap
for whole canonical UTF-8 JSON artifact after host redaction. Host drops older
records and truncates retained fields until trace fits. Invalid optional trace
retention never blocks terminal observation recording; core stores bounded
artifact rejection evidence instead. Terminal observation never contains raw
transcript material.

## Stranded Run Recovery

`recover-stranded` is controller-only non-replay recovery for a `running`
attempt stranded before host terminal evidence was written. It requires exact
run and attempt IDs, a bounded reason, and JSON external host evidence with
source `host` and code `terminal_recording_failed`. Core rejects product
evidence, mismatch, prior claims or evidence, and ordinary running work. It
records immutable packet identity plus external failure evidence, creates a
block-only outcome, and policy auto-finalizes a v3 terminal receipt. It never
dispatches, resumes, retries, or runs checks.

## Plan-Linked Coordination

Optional `coordination` frontmatter on Git-tracked active implementation plan
is static coordination SSOT. It owns `target_branch`, `base_ref`, task IDs,
dependencies, canonical topology, allowed paths, and planned write paths. Every manifest task
maps exactly once to prose `Coordination ID`.

For a plan-linked request, core derives topology, base ref, allowed paths, and planned paths
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

Admission order: launcher load, consumer `harness_core.request_api`, adapter
`host_api`, provider preflight, packet resolution, workspace, then dispatch.
Unsupported request or host API blocks before packet creation. New packet
`core_identity` records package release, request API, packet API, and host API.
Unversioned or unreadable planned packet cannot resume; preserve it and create
controller successor.

`repo_config/harness.yaml` is sole registry for static managed-provider IDs,
contract versions, route allowlists, and route defaults. Request resolution
copies exactly one provider object into immutable packet state. A host reports
current mode enforcement only through `capabilities()`; static policy never
claims a mode is enforced. `provider_capabilities.yaml` supports generated
agent surfaces only and never participates in runtime selection or acceptance.

A candidate stays absent from route policy until it passes same packet,
workspace, tool-binding, check, read-only validator, and controller-acceptance
proof as every admitted provider. No automatic provider fallback exists.
Core runtime protocol profile owns current provider contract and host
compatibility. Historical packet readers retain their declared compatibility;
current profile mismatch fails before workspace preparation or lane dispatch.

## Required Adapter Methods

Host adapter provides these methods:

| Method | Input | Required result |
| --- | --- | --- |
| `capabilities()` | none | map of mode to `enforced`, `advisory`, or `unavailable` |
| `identity()` | none | exact packet `runtime_provider` object: `{provider_id, contract_version}` |
| `prepare_workspace(lane, packet)` | immutable lane and packet | workspace identity plus normalized baseline evidence |
| `dispatch_lane(lane, packet, workspace, delegation_bridge)` | immutable lane, packet, workspace, optional core-owned delegation bridge | opaque dispatch handle |
| `collect_lane_completion(handle, lane, packet, workspace)` | dispatch handle and immutable lane context | completed turn identity, or bounded terminal observation for provider failure |
| `collect_claim(handle)` | dispatch handle | role-valid `claimed_result` |
| `repair_claim(handle, lane, packet, workspace, failure)` | one completed leased work handle plus core-normalized unusable-claim failure | one read-only, no-tool repair from same open provider session and original thread |
| `collect_lane_evidence(handle, lane, packet, workspace)` | dispatch handle, immutable lane and packet, workspace | host execution evidence for exactly one dispatched lane |
| `cancel_lane(handle)` | dispatch handle | cancellation attempt |
| `materialize_final_state(lane, packet, workspaces)` | immutable integration lane, packet, workspaces | final workspace identity object |
| `verify_tool_bindings(lane, packet, workspace)` | immutable lane, packet, workspace | one verified root binding per selected packet tool |
| `run_checks(packet, workspace)` | immutable packet, final workspace | host check evidence from selected packet-scoped shell binding |

`prepare_workspace` returns baseline evidence that core validates before lane
dispatch. A root lane, including every parallel lane, returns
`{"kind":"packet_base","base_commit":<packet base>,"clean":true}` after
materializing exact packet `base_commit` with no tracked or untracked changes.
A dependent sequential lane returns
`{"kind":"predecessor","lane_id":<direct dependency>}` only after host
materializes that direct predecessor state. Core still collects actual final
changes after lane execution. Invalid or missing evidence is
`workspace_baseline_invalid`; no lane runs. Hosts choose a platform-safe
workspace root and fail with this condition when tracked paths cannot fit there.

Only `enforced` capability permits dispatch. `advisory`, `unavailable`, absent,
or malformed capability produces `execution_mode_unavailable` before workspace
preparation or dispatch. For an enforced mode, core compares `identity()` with
immutable packet `runtime_provider` before workspace preparation or dispatch.
Core never substitutes a different provider after identity or capability failure.
An unavailable adapter may expose a non-empty `unavailable_detail` string. Core
persists it in the outcome so generic CLI fallback cannot be misreported as a
provider capability failure. Every host failure stores exact `{reason, phase,
detail}` at `attempt.evidence.failure` and mirrors `detail` in outcome. Friction
records retain only normalized fingerprint and metadata.

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
`ambient_mcp: false`, and workspace status before and after turn. If host used
finalization, evidence also records bounded prior terminal observation and
read-only finalizer thread, turn, and sandbox. Claim-only finalizers do not need
another packet-tool call; host keeps prior execution evidence separate from the
finalizer claim.

For an interrupted work turn with positive
`finalization_reserve_seconds`, host must use the read-only finalizer for every
admitted packet API version. If that finalizer times out, terminal observation
submitted to core must report full packet
`execution_budget.turn_timeout_seconds`, never the work-slice or finalizer
timeout. Preserve bounded per-slice observations in lane finalization evidence.

Core resolves one immutable `tool_use_requirement` on each agent lane from
packet tool bindings: eligible tools, required access, and minimum uses. Host
renders that requirement verbatim but records every actual packet-selected tool
use, including an empty list, plus exact packet workspace command results. Core
alone validates evidence against this requirement. Validator evidence still
requires a separate `read-only` turn and identical workspace status before and
after. Core stores terminal observations and lane records in `run.json`, then
fails or terminalizes when required tool proof is absent.

## Attempt Terminalization

For current leased packets, core owns `terminalize_attempt(evidence)`, terminal record
creation, outcome derivation, lease release, state history, and atomic
`run.json` replacement. Host never writes `run.json`. Host returns only
packet-declared terminal observation bound to run, attempt, immutable packet digest,
lease ID, lease epoch, and host instance ID.

Core issues one non-renewable execution lease immediately before `planned`
becomes `running`. Host rejects expired or mismatched lease bindings. On
Windows, host creates one unnamed Job Object per lease, assigns each provider
root before resume, and proves zero active processes before timeout or
cancellation terminalization. No PID-tree, process-group, `taskkill`, named-job
reopen, or host-side run-state fallback is allowed.

A delegated child is not an independent attempt. Core projects its parent's
active lease only into the host dispatch view; the stored child packet remains
immutable and lease-free. Host borrows that same lease containment. Missing or
inactive parent lease rejects child dispatch.

An expired lease with absent host and provider identities terminalizes block-only
as host crash. Live or unverified processes move attempt to nonterminal
`orphaned` with recovery-blocked evidence. Fresh cleanup proof may terminalize
that same attempt; retry, resume, acceptance, waiver, and successor creation
remain forbidden while orphaned.

## Personal Local Controller

Personal local installations may run `harness-core-launcher controller-init`
once. It creates one fixed Ed25519 private key at
`~/.codex/harness-controller/controller-ed25519.pem` and one matching active
public record in `~/.codex/harness-authorities.toml`. No issuer argument,
environment value, custom signer config, broker, daemon, or remote service
exists.

For an eligible ambiguous outcome, controller runs:

```powershell
harness-core-launcher close --harness-root <repo-root> --run-id <run-id> --decision <accept|block|waive> --reason <reason>
```

Launcher verifies active profile then invokes active core module. It does not
invoke provider host, create a packet, start a provider session, or alter old
attempt packets. Core takes run lock, validates UTF-8 reason bounds, replays an
exact matching personal receipt before key or registry lookup, or resolves
current personal authority, signs existing `controller_authorization/v1` in
memory, normalizes it, and calls shared outcome finalizer. A conflict, missing
or revoked signer, expired or ineligible outcome, or finalizer failure leaves
`run.json` unchanged.

This trust model deliberately grants closure authority to any process under
same OS user that can invoke launcher. It is personal-use only, excluded from
production and shared machines. Detached
`sign-controller-authorization` plus `terminalize-attempt --input` remains
compatible for advanced external approval. `retry` and `escalate` never use
this path: they stay `harness-core-launcher decision` operations and require
host adapter admission plus current provider preflight.

## Historical Legacy Cleanup

An active historical attempt without an execution lease is isolated from dispatch
and resume but never blocks admission of new leased packets. Core accepts its
only cleanup path through `terminalize_attempt(evidence)`. Host has no legacy
cleanup, reaper, `taskkill`, PID-tree, or named Job Object responsibility.

External operator signs exact `legacy_cleanup_attestation/v1` unsigned fields:
`attestation_id`, run and attempt IDs, packet SHA-256, issuer key ID, absence,
issue, and expiry timestamps, cleanup scope, discovery method, root identity,
identity list, complete-scope flag, reason SHA-256, and reason length. Transport
adds base64url `attestation_signature`. Core verifies Ed25519 over UTF-8 sorted
compact JSON bytes. Public attester records live only in
`~/.codex/harness-authorities.toml`; private key material stays outside
repository and agent workspace. `harness-core migrate-harness-authorities`
performs explicit old-registry conversion; current validation never falls back
to `harness-attesters.toml`.

Operator runs `harness-core sign-legacy-cleanup` with unsigned JSON and an
external private-key file. Controller passes signed JSON to
`harness-core-launcher terminalize-attempt --harness-root <repo-root> --run-id
<run-id> --input <envelope.json>` through active runtime profile.
For the policy-defined historical legacy packet API only, temporary
`--evidence <attestation.json>` translates to that envelope. `--auto-block` is
rejected. Core writes one tagged null-lease terminal record, records a
block-only outcome, then policy auto-finalizes one v3 receipt. Exact re-entry
replays safely after interruption; agents may transport evidence but cannot
mint, broaden, or apply it directly.

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
runs inside configured window. A policy-owned `follow_up` for recurring
`writer_completion_missing` selects fresh read-only `harness_diagnosis`.
Controller dispatches that diagnostic without an owner decision, preserves the
blocked product run, and creates a separate write-capable `harness_improvement`
only after diagnosis proves an owning code or contract change. `friction-resolve` requires accepted
`harness_improvement` run, names candidate event IDs, and appends controller
decision: `keep`, `revise`, `remove`, or `pending`. Neither command mutates
routes, policy, skills, tools, or providers. Fresh representative rerun proof
is required before `keep`.
