# Prototype Integration Intent

Durable contracts:

- Candidate Profiles: `docs/superpowers/specs/2026-07-21-19-02-fitcv-central-workspace-frontend-backend-integration-spec.md`
- Local backup and restore: `docs/superpowers/specs/2026-07-16-22-29-fitcv-local-distribution-and-onboarding-spec.md`

Status: UI intent approved; prototype remains local-state only until backend wiring.

## Global Navigation

Operation: expose stable navigation and global application actions

Contract owner: frontend shell

### UI Behavior

- Health is absent from the sidebar.
- Header title icons keep one fixed size and do not shrink when header actions consume space.
- API Provider rows, Runs rows, and Bookmark rows use the same hover surface token without lift or border animation.
- Theme precedes Shutdown FitCV in global header actions. Both use the same borderless icon-button rest state; Shutdown keeps danger color and opens the existing confirmation dialog.
- Dedicated Run and Candidate Profile pages use one parent-owned section gap. Page headings do not repeat lifecycle status already shown by Overview.
- Bookmark Run cells show only the linked Run ID; lifecycle grouping remains owned by Runs.

## Candidate Profile Details Page

Operation: inspect one Candidate Profile

Contract owner: `GET /candidate-profiles/{profile_id}`

### UI Behavior

- Candidate Profile Details is a restorable dedicated page state, not a drawer.
- `Back to Candidate Profiles` returns to the collection page; browser Back and Forward preserve history.
- Candidate Profiles navigation remains active on details pages.
- Overview, lifecycle status, and safe input metadata use the canonical detail response.
- Profile details omit reverse Run listings; Runs remain discoverable from the Runs page. Archived profiles remain inspectable.

### Required Evidence

- Direct URL load, refresh, Back, and Forward resolve the same profile.
- Missing or unavailable profile IDs return a bounded not-found state without leaking raw uploads.
- Archived profiles remain directly resolvable without loading an unbounded Run list.
- Light, dark, narrow, zoomed, keyboard, and focus states pass.

## Theme Navigation

Operation: persist local light or dark preference

Contract owner: browser-local theme preference; no backend setting

### UI Behavior

- Appearance is absent from sidebar.
- One global header toggle owns theme selection.
- Light theme displays moon icon to switch to dark; dark theme displays sun icon to switch to light.
- Accessible name describes next action: `Switch to dark theme` or `Switch to light theme`.

## API Providers

Operation: manage provider catalog entries, one connection per provider, and provider-scoped models

Contract owner: future provider catalog, credential, connection verification, and model-management APIs. Current backend provider behavior remains authoritative until those contracts exist.

### UI Behavior

- `API Providers` is a dedicated collection page at `#api-providers`.
- `API Key Providers` replaces `Shared Providers` and contains OpenAI, Anthropic, DeepSeek, and Groq.
- Provider collections use setting-style rows with `Connected` or `No connection`; connection counts are not shown.
- Each provider collection has one outer section boundary; rows add separators without a second rounded container.
- Empty provider and model states remain unframed inside their owning section.
- Provider search and custom-provider actions use separate layout groups and reflow independently on narrow screens.
- Predefined and custom providers use one row and detail-page pattern.
- Custom provider actions create OpenAI-compatible or Anthropic-compatible entries, then open the dedicated provider page.
- Provider details are restorable at `#api-providers/{provider_id}` and include `Back to API Providers`.
- Each provider supports one connection. Connection actions are Test, Add or Update, and Remove.
- Predefined providers expose a disabled Base URL supplied by FitCV; custom providers require an editable Base URL and Display Name.
- API Key is stored as a credential. Existing credentials remain masked; entering a new key replaces the credential.
- Connection forms do not contain Model ID.
- OpenAI-compatible providers expose an `API Type` dropdown with `Chat Completions` and `Responses API`.
- Anthropic-compatible providers expose a disabled `API Type` dropdown fixed to `Messages API`.
- Test validates the exact current Base URL, API Key, API Type, and custom Display Name draft.
- Add Connection or Update Connection remains disabled until the current draft passes Test. Editing any tested field invalidates the result.
- No connection changes to Connected only when the successfully tested draft is added. An existing Connected configuration remains active until a successfully tested update replaces it.
- `credentialConfigured` records only whether a credential exists. `connectionStatus=verified` is the sole owner of Connected display, model actions, and LLM routing eligibility.
- Without a connection, Available Models is gray, marked disabled, and explains that a connection is required.
- Available Models has a top-right `Add Model` action. Its modal uses a text-only Test action and requires Model ID validation before Add Model is enabled.
- Add Model saves only the exact Model ID that passed the latest test; editing the value invalidates that test.
- Saved model rows expose only Test and Remove. A model is either validated and available, needs retest, or is removed.
- Connection, credential, Base URL, or API Type changes mark existing models `Needs retest` and remove them from LLM routing until tested again.
- Prototype connection and model actions remain local-state UI intent and make no network requests.

### Credential Boundary

- API keys never enter localStorage or exported prototype state.
- Prototype persists only `credentialConfigured` and non-secret connection metadata.
- Later Windows backend integration stores provider credentials in Windows Credential Manager.
- UI never returns a stored credential value; replacement requires entering a new key.

### Required Evidence

- Direct provider URL load, refresh, Back, and Forward resolve the same provider.
- Shared and custom provider pages support light, dark, narrow, keyboard, and focus states.
- Missing Display Name, invalid Base URL, and missing first API Key produce bounded field errors.
- Failed or stale connection tests cannot enable Add Connection or Update Connection.
- One provider cannot create a second connection.
- Removing a connection disables model actions and makes its models unavailable to LLM routing without deleting model metadata.
- Duplicate Model IDs and untested Add Model attempts are rejected.
- Browser storage inspection confirms no API key value is persisted.

### Known Backend Gap

- Current backend supports OpenAI and OpenAI-compatible configuration with one active provider.
- Multiple provider records, Anthropic transport, provider-scoped model verification, and credential-manager integration require backend contracts before wiring.

## LLM Configuration

Operation: configure the default model route and task-specific LLM runtime behavior

Contract owner: future LLM routing and runtime configuration API backed by the canonical provider model registry. Current single-provider runtime remains authoritative until routing persistence exists.

### UI Behavior

- `LLM Configuration` is a dedicated page at `#llm-configuration`.
- Default Route lists added models across connected providers only when each model has passed validation.
- Model labels use `Provider · Model ID`; provider connection counts or copied model catalogs are not routing owners.
- Missing or unavailable Default Route remains empty and shows a required-state warning. It never silently selects an unrelated model.
- Task Configuration contains one setting row each for Enrich Extraction, Ranking AI Score, CV Generation, and Synonym Recommendation.
- CV Analysis is excluded because its current pipeline flow is deterministic rather than LLM-backed.
- Synonym Recommendation is the UI label for backend task ID `synonym_triage_recommendation`.
- Each task Manage action opens one dialog containing Model, Timeout, and Temperature.
- Model defaults to `Default`, which inherits Default Route. Models needing retest and models from disconnected providers are unavailable; invalid task selections repair to `Default`.
- Synonym Recommendation can use its external-LLM route when configured while preserving the current built-in recommendation fallback.
- Prototype routing changes remain local-state UI intent and make no network requests.

### Required Evidence

- Default Route and task settings persist across refresh in prototype state.
- Provider connection and model validation changes reconcile routing selections deterministically.
- Empty-model state links users back to API Providers.
- Task dialogs are keyboard operable and respect declared numeric bounds.
- Light, dark, narrow, keyboard, and focus states pass.

### Known Backend Gap

- Multiple-provider routing and persisted task-level model, timeout, or temperature settings are not current backend capabilities.
- Backend implementation must resolve provider, credential handle, API style, and model ID from the canonical provider model registry.
- Current runtime sends temperature `0.0`; the Temperature control remains UI intent until the runtime accepts task-specific values.
- Backend validation must reject unavailable models and numeric values outside supported bounds.

## Prompt Management

Operation: inspect and override prompt text for LLM-backed pipeline tasks

Contract owner: future prompt configuration API using server-owned default prompts and task IDs from the canonical prompt task registry

### UI Behavior

- `Prompt Management` is a dedicated Pipeline page at `#prompt-management`.
- Pipeline Prompts contains Enrich Extraction, Ranking AI Score, and CV Generation.
- Synonym Prompts contains Synonym Recommendation.
- Synonym Prompt copy describes reviewing synonym proposals and recommending an action without exposing provider-routing implementation details.
- Every row opens one task-scoped dialog with Prompt Type `Default` or `Custom`.
- Default prompts remain canonical system text, display read-only, and are not copied into stored overrides.
- Selecting Custom initializes the editor from the default prompt. Save requires non-empty text that differs from the default.
- Prompt input uses a native 4000-character limit, continuous count, approaching-limit warning, and `Character limit reached.` state.
- Closing a dirty prompt dialog requires discard confirmation. Save changes only the selected task.

### Required Evidence

- Prompt group membership matches the canonical LLM task list.
- Default and Custom states are keyboard operable, preserve read-only visibility, enforce validation, and warn before dirty discard.
- Prompt configuration persists across refresh in prototype state.
- Light, dark, narrow, keyboard, and focus states pass.

### Known Backend Gap

- Persisted prompt overrides are not a current backend capability.
- Backend must keep default prompt text as server-owned SSOT and persist only task custom prompt overrides.
- Backend validation must reject empty or unchanged custom prompts and prompt text above 4000 characters.

## System

Operation: manage local data, request retry, worker recovery, and process shutdown behavior

Contract owner: `GET /local/data`, `POST /local/data/backup`, `POST /local/data/import`, and `POST /local/system/shutdown`; archive contract `fitcv-backup.v1`. Retry and recovery persistence require future canonical configuration contracts.

### UI Behavior

- `System` is a dedicated Application page at `#system`.
- Data and Backup shows Local Mode state and backend-resolved database location.
- Download Backup streams one canonical `.fitcv.zip` archive.
- Import Backup selects a file, then shows validation intent before enabling Restore Backup.
- Restore requires explicit confirmation and communicates required idle state and restart.
- Request Retry owns Maximum Attempts, Initial Backoff, and Error Detail Limit globally.
- Maximum Attempts includes the initial attempt. Initial Backoff is the delay before retrying a transient provider failure.
- Worker Recovery owns Lease and Reconciler Interval globally. Lease controls worker ownership expiry; Reconciler Interval controls stalled-run scans.
- Prototype bounds are Attempts `1–10`, Initial Backoff `0–3600`, Lease `30–86400`, Reconciler Interval `5–3600`, and Error Detail Limit `1000–100000`.
- System does not duplicate Shutdown FitCV as a settings section.
- The global header Shutdown FitCV action requires confirmation.
- Shutdown is unavailable while queued or running work exists. It does not force-cancel workers or active runs.
- Successful shutdown stops the local service, prevents new executions until relaunch, and transitions the application to its stopped page.
- Theme controls are not duplicated on this page.
- Prototype actions remain local-state UI intent and make no network requests.

### Required Evidence

- Retry and recovery controls persist across refresh in prototype state and respect declared numeric bounds.
- Backup and restore reject queued or running work.
- Backup uses SQLite native backup API and excludes credentials, logs, prior backups, WAL/SHM files, and incomplete-run artifacts.
- Restore validates archive version, checksums, schema compatibility, SQLite integrity, and required files before atomic replacement.
- Failed restore keeps current storage pointer and retained source data unchanged.
- Frontend covers invalid extension, incompatible archive, integrity failure, active-work rejection, confirmation cancellation, success, restart, and duplicate-submit prevention.
- Header shutdown action and confirmation are keyboard operable, reject active work, prevent duplicate submission, and show the stopped state after success.
- Light, dark, narrow, keyboard, and focus states pass.

### Known Gap

- Backup, restore, and shutdown routes exist and need frontend wiring.
- Persisted retry and recovery settings require backend configuration contracts.
