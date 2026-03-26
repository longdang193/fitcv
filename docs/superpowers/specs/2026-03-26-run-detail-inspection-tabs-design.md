# Run Detail Inspection Tabs — Design Spec

**Date:** 2026-03-26
**Author:** Admin Control Plane
**Status:** Draft

---

## Problem

The current run detail page renders all inspection data in a single flat column: enriched jobs table, candidate profile JSON, and jobs input snapshot are stacked vertically. As more data is surfaced per run, this layout becomes difficult to scan and forces the admin to scroll through unrelated sections to reach the information they need.

## Goal

Reorganize the run detail page into a **tabbed inspection interface** so an admin can quickly navigate between:
1. What the system derived from job inputs (enriched + filtered view)
2. What raw job data was submitted for the run
3. What candidate profile context influenced filtering and ranking

---

## Context

### Data already stored per run (in `pipeline_runs`)

| Field | Type | Present when |
|---|---|---|
| `jobs_input_source` | `STRING` | always (path / upload / paste) |
| `jobs_path` | `STRING` | always |
| `jobs_input_json` | `STRING` | paste mode only |
| `candidate_profile_source` | `STRING` | always when explicitly set |
| `candidate_profile_json` | `STRING` | upload / paste mode only |

### Data already in template context (from `app.py`)

- `enriched_jobs` — list of run-scoped enriched job records
- `filter_results_by_job_url` — dict mapping job_url → `{passed, reasons}`
- `candidate_profile_pretty` — pretty-printed JSON string (or `None`)
- `run.jobs_input_json` — raw job JSON snapshot (or `None`)

No backend changes are required.

---

## Design

### Tab Bar

Three tabs sit above the inspection pane, below the run metadata card and CV results banner:

```
[ 📊 Enriched Jobs ]  [ 📄 Original Job Input ]  [ 👤 Candidate Profile ]
```

Active tab is highlighted. Tab switching is pure client-side JS (no page reload).

---

### Tab 1: Enriched Jobs (default active)

Renders the existing enriched jobs table with columns:

- Job Title (linked)
- Location Type
- Seniority
- Job Family
- Domain
- Required Skills (top 5)
- Filter outcome (✓ pass / ✗ reject with inline reason codes)

No change to this content — it moves from inline to inside the tab pane.

---

### Tab 2: Original Job Input

**When `run.jobs_input_json` is present:**

Render a scrollable `<pre>` block with the raw JSON snapshot.
Label with source badge (`paste`).
Add heading: `"Raw job payload captured at trigger time (immutable snapshot)"`.

**When `run.jobs_input_json` is absent:**

Render a fallback info panel:

```
Source: {jobs_input_source} · Path: {jobs_path}
No immutable raw snapshot was stored for this run.
Only paste-mode runs capture a raw JSON snapshot at trigger time.
```

---

### Tab 3: Candidate Profile

**When `candidate_profile_pretty` is present:**

Render two sub-sections:

1. **Formatted view** — A readable summary of key profile fields (name, seniority, skills, location preferences) extracted from `candidate_profile_parsed`. Lets non-technical admins scan the profile without reading JSON.
2. **Raw JSON view** — A scrollable `<pre>` block with the full pretty-printed profile JSON.

Label with source badge (`upload` or `paste`).
Add heading: `"Candidate profile JSON captured at trigger time (immutable snapshot)"`.

**When `candidate_profile_pretty` is absent:**

Render a fallback info panel:

```
Source: {candidate_profile_source if set, otherwise "—"}
No candidate profile snapshot was stored for this run.
Default-config and pre-feature runs do not capture a profile snapshot.
```

> **Fallback label rule:** If `candidate_profile_source` is `NULL` (pre-feature run), display `—` or `"not recorded"`. **Never** infer or substitute `default_config`. Only display `default_config` when that value is literally stored in `candidate_profile_source`.

---

### Event Timeline

The event timeline remains **below** the tab panes, always visible. It is not part of any tab.

---

## Fallback Rules Summary

| Scenario | Tab 2 | Tab 3 |
|---|---|---|
| paste jobs + paste profile | raw JSON ✓ | formatted + raw JSON ✓ |
| upload jobs + upload profile | fallback (source + path) | formatted + raw JSON ✓ |
| path jobs + default profile | fallback (source + path) | fallback (source=`default_config`) |
| old run (pre-feature, all NULLs) | fallback (source=`—`, path shown) | fallback (source=`—`, not `default_config`) |

> **Null source rule:** `candidate_profile_source=NULL` means the source was not recorded (pre-feature run). Display `—`. Do not substitute `default_config` as that implies a known source choice that was not actually recorded.

Old runs must not crash — all fields are nullable.

---

## Non-Goals

- No server-side rendering split (single page, single template response)
- No deep-link to specific tabs via URL hash (out of scope)
- No JSON syntax highlighting (plain `<pre>` is sufficient)
- No tab for the Event Timeline

---

## Acceptance Criteria

- [ ] Default active tab is Enriched Jobs on page load
- [ ] Tab switching is instant (no reload)
- [ ] Tab 2 renders raw JSON snapshot when present
- [ ] Tab 2 shows fallback metadata (source + path) when no snapshot, without crashing for NULL source
- [ ] Tab 3 renders **both** formatted summary view **and** raw JSON snapshot when profile snapshot is present
- [ ] Tab 3 shows fallback metadata when no snapshot; source is `—` when `candidate_profile_source` is NULL (never infers `default_config`)
- [ ] Old runs without any snapshot fields render without errors
- [ ] Event Timeline is always visible below the tabs (not inside any pane)
- [ ] All existing automated tests pass
- [ ] New tests cover: default active tab, Tab 2 fallback, Tab 3 fallback, Event Timeline outside panes
