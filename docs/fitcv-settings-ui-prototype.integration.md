# Prototype Integration Intent

Durable contracts:

- Candidate Profiles: `docs/superpowers/specs/2026-07-21-19-02-fitcv-central-workspace-frontend-backend-integration-spec.md`
- Local backup and restore: `docs/superpowers/specs/2026-07-16-22-29-fitcv-local-distribution-and-onboarding-spec.md`

Status: UI intent approved; prototype remains local-state only until backend wiring.

## Candidate Profile Details Page

Operation: inspect one Candidate Profile and navigate to related Runs

Contract owner: `GET /candidate-profiles/{profile_id}` and `GET /candidate-profiles/{profile_id}/runs`

### UI Behavior

- Candidate Profile Details is a restorable dedicated page state, not a drawer.
- `Back to Candidate Profiles` returns to the collection page; browser Back and Forward preserve history.
- Candidate Profiles navigation remains active on details pages.
- Overview, lifecycle status, safe input metadata, and related Run links use the canonical detail response.
- Related Run links open dedicated Run Details pages. Archived profiles remain inspectable.

### Required Evidence

- Direct URL load, refresh, Back, and Forward resolve the same profile.
- Missing or unavailable profile IDs return a bounded not-found state without leaking raw uploads.
- Related Runs remain resolvable after profile archive.
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
- Predefined and custom providers use one row and detail-page pattern.
- Custom provider actions create OpenAI-compatible or Anthropic-compatible entries, then open the dedicated provider page.
- Provider details are restorable at `#api-providers/{provider_id}` and include `Back to API Providers`.
- Each provider supports one connection. Connection actions are Add or Update, Verify, and Remove.
- Predefined providers expose a disabled Base URL supplied by FitCV; custom providers require an editable Base URL and Display Name.
- API Key is stored as a credential. Existing credentials remain masked; entering a new key replaces the credential.
- Connection forms do not contain Model ID.
- OpenAI-compatible providers expose an `API Type` dropdown with `Chat Completions` and `Responses API`.
- Anthropic-compatible providers expose a disabled `API Type` dropdown fixed to `Messages API`.
- Without a connection, Available Models is gray, marked disabled, and explains that a connection is required.
- Available Models has a top-right `Add Model` action. Its modal requires Model ID validation before Add Model is enabled.
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
- One provider cannot create a second connection.
- Removing a connection disables model actions and makes its models unavailable to LLM routing without deleting model metadata.
- Duplicate Model IDs and untested Add Model attempts are rejected.
- Browser storage inspection confirms no API key value is persisted.

### Known Backend Gap

- Current backend supports OpenAI and OpenAI-compatible configuration with one active provider.
- Multiple provider records, Anthropic transport, provider-scoped model verification, and credential-manager integration require backend contracts before wiring.

## LLM Configuration

Operation: choose default model route and task-specific overrides

Contract owner: future LLM routing configuration API. Current single-provider runtime remains authoritative until routing persistence exists.

### UI Behavior

- `LLM Configuration` is a dedicated page at `#llm-configuration`.
- Default Route selects one validated model from configured providers.
- Task Overrides cover Screening, Ranking, CV Analysis, and CV Generation.
- Empty override means `Use default model`.
- Models needing retest and providers without a connection are unavailable for routing.
- Removing a selected model or invalidating its test repairs affected routes to a valid default or empty state.
- Prototype routing changes remain local-state UI intent and make no network requests.

### Required Evidence

- Default and override selections persist across refresh in prototype state.
- Provider connection and model validation changes reconcile routing selections deterministically.
- Empty-model state links users back to API Providers.
- Light, dark, narrow, keyboard, and focus states pass.

### Known Backend Gap

- Multiple provider routing and per-task overrides are not current backend capabilities.
- Backend implementation must resolve provider, credential handle, API style, and model ID from one canonical routing owner.

## Data and Backup Page

Operation: inspect local storage, download backup, and stage backup restore

Contract owner: `GET /local/data`, `POST /local/data/backup`, and `POST /local/data/import`; archive contract `fitcv-backup.v1`

### UI Behavior

- Page shows Local Mode state and backend-resolved database location.
- Download Backup streams one canonical `.fitcv.zip` archive.
- Import Backup selects a file, then shows validation intent before enabling Restore Backup.
- Restore requires explicit confirmation and communicates required idle state and restart.
- Theme controls are not duplicated on this page.

### Required Evidence

- Backup and restore reject queued or running work.
- Backup uses SQLite native backup API and excludes credentials, logs, prior backups, WAL/SHM files, and incomplete-run artifacts.
- Restore validates archive version, checksums, schema compatibility, SQLite integrity, and required files before atomic replacement.
- Failed restore keeps current storage pointer and retained source data unchanged.
- Frontend covers invalid extension, incompatible archive, integrity failure, active-work rejection, confirmation cancellation, success, restart, and duplicate-submit prevention.

### Known Gap

- Prototype buttons demonstrate approved states without network requests; backend routes already exist and need frontend wiring.
