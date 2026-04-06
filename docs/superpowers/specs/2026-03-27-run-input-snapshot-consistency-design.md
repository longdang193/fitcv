# Run Input Snapshot Consistency — Design Spec

**Date:** 2026-03-27
**Author:** Admin Control Plane
**Status:** Draft

---

## Problem

The run-detail inspection tabs currently treat trigger modes inconsistently.

Today:

- `jobs_input_json` is captured for `paste` and `upload` jobs input
- `candidate_profile_json` is captured for `upload` and `paste` candidate profile input
- `path` jobs input does not capture a run-scoped snapshot
- `default_config` candidate profile does not capture a run-scoped snapshot

This creates an awkward inspection model:

- some runs show the exact immutable input used
- other runs show only a source label or file path
- two runs triggered through different modes but using equivalent JSON content do not produce equally auditable run detail

That inconsistency weakens both debugging and auditability.

---

## Goal

Make run-detail inspection behavior consistent by capturing immutable run-scoped input snapshots for all successful trigger modes when the resolved content is readable at trigger time.

Specifically:

1. `path` jobs input should capture the resolved JSON payload into `jobs_input_json`
2. `default_config` candidate profile should capture the resolved candidate profile JSON into `candidate_profile_json`
3. `upload` and `paste` modes keep their current snapshot behavior

The UI should still preserve the original source labels (`path`, `upload`, `paste`, `default_config`) so the admin knows how the run was triggered.

---

## Non-Goals

- Re-reading external files at run-detail time
- Turning run detail into a live view of current repo files
- Changing the selected trigger mode semantics
- Replacing `jobs_path` or source metadata with snapshots only

---

## Design

### Snapshot Principle

Run detail should show what the run actually used, not merely where the inputs originally came from.

Therefore:

- source fields describe how the run was triggered
- snapshot fields store the immutable content resolved at trigger time

This makes the run record both:

- operational metadata
- an audit snapshot of resolved inputs

Canonical snapshots are stored as validated, parsed input re-serialized into a stable JSON form.
They are intended to preserve run input semantics, not original formatting, key ordering, or whitespace from the source file.

---

### Jobs Input Behavior

`jobs_input_json` should become the canonical run-scoped snapshot for all successful jobs input modes when the resolved JSON is available at trigger time.

Required behavior by mode:

- `paste`
  - unchanged
  - canonical pasted JSON is stored in `jobs_input_json`
- `upload`
  - unchanged in principle
  - canonical uploaded JSON is stored in `jobs_input_json`
- `path`
  - new behavior
  - the server reads the resolved file at trigger time
  - if the file decodes and parses successfully as the expected JSON array, the canonical JSON is stored in `jobs_input_json`

`jobs_input_source` must still remain the original mode:

- `path`
- `upload`
- `paste`

The run should therefore be able to say:

- source: `path`
- original path: `data/sample_jobs.json`
- snapshot: present

This is not contradictory. It is the desired behavior.
The original `jobs_path` metadata must remain stored alongside the snapshot for operational traceability.

---

### Candidate Profile Behavior

`candidate_profile_json` should become the canonical run-scoped snapshot for all successful candidate profile modes when the resolved profile content is available at trigger time.

Required behavior by mode:

- `upload`
  - unchanged
  - canonical JSON is stored in `candidate_profile_json`
- `paste`
  - unchanged
  - canonical JSON is stored in `candidate_profile_json`
- `default_config`
  - new behavior
  - the server resolves the configured candidate profile file during trigger processing
  - the resolved profile is normalized into canonical JSON and stored in `candidate_profile_json`

The `default_config` snapshot must be generated from the same resolved profile object that will be used for pipeline execution.
The stored snapshot and the execution input must not come from two different resolution paths.

`candidate_profile_source` must still remain the original mode:

- `default_config`
- `upload`
- `paste`

This allows the run to show:

- source: `default_config`
- snapshot: present

That is the consistent and intended model.

---

### Trigger-Time Resolution Rule

Snapshots must be captured at trigger time, not lazily later.

This means:

- the app resolves the selected jobs input and candidate profile input during trigger handling
- the resolved content is stored on the run record before worker execution
- the worker and run detail both rely on the same immutable run-scoped record

This prevents later file edits from changing what a historical run appears to have used.

---

### Failure Semantics

Snapshot capture should not introduce hidden silent drift.

Required rules:

- if a selected input mode depends on reading a file at trigger time, and that file cannot be read or validated, the trigger request should fail clearly
- do not fall back to “store source only” for a newly triggered run when the selected mode was expected to produce a resolved snapshot
- old runs without snapshots remain valid historical records and should still render gracefully

This means:

- `path` mode should fail at trigger time if the jobs JSON file cannot be read/parsed
- `default_config` mode should fail at trigger time if the configured candidate profile cannot be loaded/validated

The first implementation should prefer correctness and auditability over permissive partial metadata.

---

### Run Detail Behavior

The run-detail tabs should prefer the immutable snapshot whenever it exists, regardless of source mode.

Rendering precedence should be explicit:

- for new supported runs, render the immutable snapshot as the primary inspection content
- render source badges and original path metadata as contextual information around that snapshot
- only render source-only fallback panels for older or legacy runs that do not have snapshot fields populated

Updated expectations:

- `Original Job Input`
  - shows the snapshot for `path`, `upload`, and `paste` runs when present
- `Candidate Profile`
  - shows the snapshot for `default_config`, `upload`, and `paste` runs when present

Fallback info panels should now be reserved mainly for:

- old pre-feature runs
- legacy runs created before this consistency change
- explicitly broken historical records that already lack snapshots

---

### Data Model Semantics

No new columns are required.

The semantic change is:

- `jobs_input_json` no longer means “paste/upload only”
- `candidate_profile_json` no longer means “upload/paste only”

New meaning:

- `jobs_input_json` = canonical resolved jobs-input snapshot for supported trigger modes in new runs; older records may still lack it
- `candidate_profile_json` = canonical resolved candidate-profile snapshot for supported trigger modes in new runs; older records may still lack it

Source fields remain independent metadata describing how the run was triggered.

Expanded snapshot capture is acceptable for current admin-tool scope and expected run sizes.
If snapshot volume grows materially later, storage tuning can be considered separately.

---

### Why This Is Better

This design improves:

- auditability
- debugging consistency
- run-detail usability
- conceptual symmetry across trigger modes

It also makes the inspection tabs easier to understand:

- the tab shows the immutable input used by the run
- the source badge explains where that input came from

That is a cleaner model than mixing “sometimes snapshot, sometimes only reference” based solely on trigger mode.

---

## Acceptance Criteria

- [ ] `path` jobs input captures a canonical immutable snapshot in `jobs_input_json`
- [ ] `default_config` candidate profile captures a canonical immutable snapshot in `candidate_profile_json`
- [ ] `upload` and `paste` modes keep their current snapshot behavior
- [ ] `jobs_input_source` and `candidate_profile_source` still preserve the original trigger mode
- [ ] Original source metadata such as `jobs_path` remains available alongside the snapshot
- [ ] Run detail prefers immutable snapshots regardless of whether the source mode was `path`, `upload`, `paste`, or `default_config`
- [ ] Run detail does not re-read current repo files for `path` or `default_config` inspection when a run-scoped snapshot exists
- [ ] `default_config` snapshots reflect the resolved profile object actually used for pipeline execution
- [ ] New trigger requests fail clearly if a selected file-backed mode cannot be resolved into a valid snapshot at trigger time
- [ ] Old runs without snapshots continue to render gracefully
