# Harness Core Consumer Setup

Use this procedure when a consumer repository first adopts, upgrades, or
repairs package-backed harness execution.

## Ownership

`harness-core` owns request admission, packet lifecycle, run records, and
controller decisions. `harness-core-launcher` lets legacy consumer bridge
scripts delegate to that installed package. Provider hosts own lane dispatch;
consumer scripts never implement managed execution.

## Install

Install the organization-managed `harness-core-launcher` release channel. Do
not copy release tags, host paths, host APIs, packet APIs, or provider contract
values into consumer repositories. Host source owns its locked core dependency;
the active local runtime pointer proves their exact compatible release profile.

Consumer policy owns only route intent and `harness_core.request_api`. Do not
copy package internals or rewrite bridge scripts.

## Preflight

Run from consumer repository root:

```powershell
uv run --locked harness-core --identity
uv run --locked harness-core validate --repo-root .
```

For managed provider work, use the active local runtime only:

```powershell
harness-core-launcher doctor
harness-core-launcher capabilities
harness-core-launcher preflight
```

`harness-core-launcher` selects one verified pointer-owned host root. Never
invoke bare `codex-harness-host`; PATH can select stale runtime. Provider host
owns trusted user transport configuration. Repository policy never carries
endpoint, launch-command, or credential values.
For `stdio` plus `host_spawn`, provider host requires Windows Job containment
and rejects unsupported hosts before child creation with
`containment_unavailable`; configure trusted external WebSocket transport
instead. Host lifecycle and recovery evidence rules live in
[`managed-execution-adapter-contract.md`](managed-execution-adapter-contract.md).

Core derives provider compatibility from its runtime protocol profile. Legacy
provider `contract_version` is diagnostic-only; current policy must not add a
second compatibility table. Historical packets remain readable without profile
backfill and never become current dispatch evidence.

## Personal Controller

For personal local use, initialize one fixed controller authority once:

```powershell
harness-core-launcher controller-init
```

Then close an eligible ambiguous outcome without writing an envelope or choosing
a key:

```powershell
harness-core-launcher close --harness-root <repo-root> --run-id <run-id> --decision <accept|block|waive> --reason <reason>
```

Launcher verifies active profile, invokes active core module, and starts no
provider host or packet work. Core binds current outcome, signs existing
`controller_authorization/v1` in memory, atomically finalizes, and replays exact
same decision and UTF-8 reason before key or registry lookup. Private key stays
at `~/.codex/harness-controller/controller-ed25519.pem`; public trust stays at
`~/.codex/harness-authorities.toml`. Any process under same OS user that can
invoke launcher can exercise this authority. Use only for personal local
installations, never shared machines or production. Detached
`sign-controller-authorization` plus `terminalize-attempt --input` remains
advanced compatibility path.

`retry` and `escalate` remain
`harness-core-launcher decision --harness-root <repo-root> --run-id <run-id>
--decision <decision.json>`. They require host adapter admission and current
provider preflight; never route them through core-only control commands.

Migration preflight reports active unleased legacy attempts as isolated. They
cannot dispatch or resume, but do not block new leased-packet admission. Preserve
their packet bytes. External operator creates signed
`legacy_cleanup_attestation/v1` with `harness-core sign-legacy-cleanup`, using
an Ed25519 key outside repository and agent workspace. Current trusted public
records live only in `~/.codex/harness-authorities.toml`; migrate an existing
old file with `harness-core migrate-harness-authorities` before validation.
Controller submits canonical `harness-core-launcher terminalize-attempt
--harness-root <repo-root> --run-id <run-id> --input <envelope.json>`.
The temporary `--evidence <legacy-attestation.json>` wrapper accepts only a
policy-defined historical legacy attestation. `--auto-block` is retired. Core
validates signature, scope, identity, and freshness, records a block-only
`attempt_outcome/v2`, then policy auto-finalizes one `attempt_terminal_receipt/v3`.
Direct legacy abandonment is retired. Detached ambiguous-outcome closure uses
an external `sign-controller-authorization` signature and outcome envelope;
raw actor or approval flags are rejected. Personal local closure uses `close`
above. Core issues a finite execution lease only when
`planned` becomes `running`; host returns bounded terminal observations while
controller alone invokes `terminalize_attempt(envelope)`.

Upgrade host and core through one staged release profile. Preserve old runs and
create successors after migration; never mutate historical packet evidence.

For local `codex-harness-host` development, policy/schema changes require a
published core release plus matching host `pyproject.toml` and `uv.lock` pins.
Starter-kit synchronization does not update host virtual environments. From
`project-OS-starter`, run:

```powershell
pwsh -NoProfile -File .\scripts\deploy_harness_core_to_host.ps1
```

The bridge stages and verifies the host release profile, atomically activates
the local pointer, then runs doctor and preflight. It never resolves host from
PATH. A host run rejects a present `repo_config/harness.yaml` when its version
differs from loaded `policy_schema_version`, before packet creation.

## Failure Routing

| Result | Owner | Action |
| --- | --- | --- |
| `harness_core_environment_unavailable` | environment | Install or repair package environment. No packet exists. |
| `harness_core_request_api_incompatible` | consumer release pin | Upgrade or pin consumer package release. No packet exists. |
| `harness_core_host_api_incompatible` | provider host runtime or release pin | Align provider host runtime, locked core release line, and host API. No packet exists. |
| `harness_core_packet_dispatch_incompatible` | policy/host compatibility skew | Preserve historical packet evidence. Align request API, packet API, and host contract; then create successor. |
| `harness_runtime_profile_activation_busy` | another activation holds launcher lock | Wait for current activation to finish, then rerun `harness-core-launcher upgrade`. |
| `cleanup_pending: true` | obsolete profile cleanup could not finish | Active profile already switched. Close process holding obsolete profile; next upgrade retries cleanup. |
| `execution_mode_unavailable` | provider host capability | Block or finalize controller-authorized waiver with reason. Do not use generic CLI as fallback. |

Automation uses installed `harness-core` commands or provider-host entrypoints.
