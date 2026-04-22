---
layer: operating_system
artifact_type: spec
status: completed
parent_workstream: none
targets:
  - docs/features/*/feature.source.yaml
  - docs/features/*/lineage.generated.yaml
  - docs/generated/feature_capabilities_index.yaml
  - scripts/sync_architecture_docs.py
  - scripts/validate_adoption_shape.py
  - scripts/**/*.py
  - tests/**/*.py
  - .github/workflows/*.yml
  - docs/**/*.md
  - repo_config/adoption-mode.yaml
related_features:
  - admin_control_plane_core
  - bounded_parallel_enrichment
  - cv_system
  - inspection_debugging
  - multi_file_job_input
  - pipeline_performance
  - run_lifecycle_controls
  - settings_system
  - trigger_run_management
  - ui_consistency_theming
related_stages:
  - normalize
  - enrich
  - rule_filter
  - shortlist
  - ranking
  - cv_analysis
  - cv_generation
---

# Required Metadata Correction Spec

## Triage

Layer: `operating_system`  
Feature type: `CHANGE`  
Summary: Correct the repo's Mode B metadata contract so capability IDs, lineage inputs, and file-level metadata are source-owned, evidence-backed, and aligned with the latest `project-OS-starter` guidance instead of being mechanically derived from prose.  
Reasoning: The repo already adopted Mode B structure, but some capability metadata was generated or normalized too mechanically. That produced precise-looking identifiers that are not anchored to stable implementation or proof surfaces. The latest starter guidance makes that distinction explicit and requires the repo to tighten the contract before adding more metadata.  
Invariants:

- The private repo remains the development source of truth.
- `docs/features/*/feature.source.yaml` remains the human-owned semantic source for feature and capability meaning.
- Generated contracts, lineage, and discovery remain script-owned outputs.
- File-level metadata should clarify real ownership and proof, not fabricate lineage precision.
- Capability IDs must remain stable identifiers, not sentence fragments copied from specs or changelog prose.
- Mode B shared-surface sync remains recorded in `repo_config/adoption-mode.yaml`.

Dependencies:

- `..\project-OS-starter` at commit `814e1a063541e79e6ca6e09268bfc5b81df057f2`
- `..\project-OS-starter\.agents\skills\python-file-metadata\SKILL.md`
- `..\project-OS-starter\docs\adoption_guide.md`
- `..\project-OS-starter\docs\operating_system\project-adoption-migration-guide.md`
- `..\project-OS-starter\docs\superpowers\specs\2026-04-21-starter-shared-surface-sync-contract-spec.md`
- `repo_config/adoption-mode.yaml`
- `scripts/sync_architecture_docs.py`
- `scripts/validate_adoption_shape.py`

Affected stages:

- `normalize`
- `enrich`
- `rule_filter`
- `shortlist`
- `ranking`
- `cv_analysis`
- `cv_generation`

Affected features:

- `admin_control_plane_core`
- `bounded_parallel_enrichment`
- `cv_system`
- `inspection_debugging`
- `multi_file_job_input`
- `pipeline_performance`
- `run_lifecycle_controls`
- `settings_system`
- `trigger_run_management`
- `ui_consistency_theming`

Primary lens: `cross-cutting`

Affected docs:

- feature_source: `docs/features/*/feature.source.yaml`
- feature_yaml: `docs/features/*/<feature_id>.yaml`
- feature_lineage: `docs/features/*/lineage.generated.yaml`
- feature_history: `docs/features/*/history.md`
- stage_source: `docs/stages/*.source.yaml`
- stage_contract: `docs/stages/*.yaml`
- feature_docs: `docs/features/*/*.md`
- cross_cutting_docs:
  - `docs/architecture.md`
  - `docs/configuration.md`
  - `docs/usage.md`
  - `docs/operating_system/project-adoption-migration-guide.md`
  - `docs/operating_system/feature-lifecycle.md`
  - `docs/operating_system/repo-governance.md`
- readme: `README.md`
- generated:
  - `docs/generated/feature_capabilities_index.yaml`
  - `docs/generated/features_index.yaml`
  - `docs/generated/feature_dependency_graph.yaml`
  - `docs/generated/feature_overview.md`
  - `docs/generated/features_by_status.yaml`
  - `docs/generated/stages_index.yaml`
  - `docs/generated/stage_overview.md`

Generated refresh required: `yes`  
Capability IDs: `managed feature capability IDs`  
Invariant IDs: `none`  
Spec needed: `yes`  
Plan needed: `yes`

## Problem

The repo has the right Mode B folder structure, but the current metadata
contract is still semantically too loose in two important ways.

First, some feature capability IDs were normalized from long prose descriptions
instead of being curated as stable capability identifiers. That created IDs
such as:

- `inspection_debugging.run-detail-page-with-3-tab-inspection-interface`

even though there is no matching implementation identifier, test proof marker,
or other stable code anchor with that name. The identifier looks canonical, but
it is really a sentence-shaped summary.

Second, the current generator reinforces that behavior. `scripts/sync_architecture_docs.py`
can slugify capability names into IDs, which makes generated lineage appear
more precise than the human-owned sources actually are.

That creates several risks:

- capability IDs become changelog-like rather than durable
- file-level metadata may point at unstable or over-granular IDs
- lineage gives a false sense of traceability
- future metadata work gets harder because the semantic layer is already noisy

The latest starter guidance makes the intended model clearer:

- `feature.source.yaml` owns capability truth
- file-level metadata should only reference capabilities when the file
  materially participates in lineage
- tests may prove capabilities, but proof is not ownership
- capability IDs should be stable and feature-qualified, not prose fragments

## Goal

Define and execute a metadata correction contract for this repo so that:

1. capability IDs describe stable product/domain capabilities rather than
   sentence-level change notes
2. file-level metadata is required only on surfaces with real behavioral or
   lineage weight
3. lineage is derived from human-owned semantic sources plus real file metadata,
   not invented by slugifying prose
4. validation catches over-specified, weakly anchored, or malformed metadata
   before more drift accumulates

## Non-Goals

This spec does not:

- require a one-to-one mapping from every spec title or release note to a
  capability ID
- require capability IDs to match code symbol names exactly
- require every Python file to declare capability ownership
- require backfilling metadata onto low-value helpers or passive content files
- require a fully automated code-to-capability graph
- reopen the completed Mode B source/generated rollout

## Current Baseline

The repo already has:

- Mode B recorded in `repo_config/adoption-mode.yaml`
- starter shared-surface review recorded against starter commit
  `814e1a063541e79e6ca6e09268bfc5b81df057f2`
- top-of-file `@meta` docstrings on the main architecture sync and validation
  scripts
- top-of-file `@meta` docstrings on the current Python test modules
- generated feature contracts, generated lineage, and generated discovery

The remaining problem is not missing structure. It is that some metadata is
too eager, too granular, or not tied cleanly enough to stable ownership and
proof semantics.

## Observed Drift In This Repo

### 1. Capability IDs are sometimes changelog sentences in disguise

Several feature sources, especially `inspection_debugging`, contain many
capability IDs that look like summarized implementation notes rather than stable
capability contracts. These IDs are often long, change-specific, and likely to
shift as UX or diagnostic detail changes.

This is especially visible where one feature accumulates many spec-driven
changes over time and each change becomes its own capability ID.

### 2. The generator can fabricate canonical-looking IDs

`scripts/sync_architecture_docs.py` currently normalizes missing or string-only
capability entries by slugifying names into `<feature_id>.<kebab-suffix>` IDs.

That behavior is convenient for migration, but it is too permissive for
steady-state Mode B. It turns descriptive text into canonical identifiers
without requiring a human curation step.

### 3. File-level metadata scope is not yet explicit enough

Starter guidance says to add metadata to files with behavioral weight and to
add `capabilities` or `invariants` only when the file materially affects
generated lineage.

This repo currently has some top-of-file metadata on scripts and tests, but the
repo does not yet have a written local policy for:

- which Python files must carry `@meta`
- when a Python file may declare `capabilities`
- when a test should use `@proves`
- which non-Python files need lineage metadata
- which doc and asset surfaces should participate in refs or proof only

### 4. Shared-surface sync is recorded, but metadata semantics need a local correction pass

The repo already complies with the starter's shared-surface review contract,
but that review does not by itself correct the semantic quality of local
feature and file metadata. This repo needs a repo-local cleanup spec before it
adds more metadata under the wrong model.

## Required Metadata Contract

### A. Capability metadata in `feature.source.yaml`

Managed feature sources remain the canonical semantic owner of capability IDs.

Required rules:

- every managed capability must use a stable, feature-qualified ID
- capability IDs should name durable product or domain behavior
- capability IDs must not be generated from prose by default
- capability names may be human-readable, but names and summaries are not IDs
- when a long implementation note exists, it belongs in `summary`, history, or
  linked specs/plans rather than inside the ID itself

Preferred shape:

```yaml
capabilities:
  - capability_id: inspection_debugging.run-detail-inspection-tabs
    name: Run detail inspection tabs
    summary: Show a three-tab run detail inspection surface for operators.
```

Not preferred in steady state:

```yaml
capabilities:
  - capability_id: inspection_debugging.run-detail-page-with-3-tab-inspection-interface
    name: Run detail page with 3-tab inspection interface
```

The second shape may be understandable, but it is too close to prose and too
easy to proliferate.

### B. Python file metadata

Python files with behavioral weight must keep the starter-style top-of-file
`@meta` docstring.

Required-on surfaces in this repo:

- entry-point scripts under `scripts/`
- migration or cleanup scripts under `scripts/migrations/`
- validation, sync, or orchestration scripts
- test modules under `tests/`
- shared Python utilities whose behavior is reused across multiple flows

Rules:

- `capabilities` is optional and should appear only when the file materially
  participates in feature lineage
- `invariants` is optional and should appear only when the file enforces a real
  repo or product invariant
- helper files should not list capabilities just because they are nearby
- tests should prefer `@proves <capability_id>` at test-function level when the
  test is evidence for a capability rather than the owner of it

### C. Workflow and config metadata

Non-Python lineage surfaces should also be explicit where they materially
contribute to behavior.

Required review targets:

- `.github/workflows/*.yml`
- repo-config files under `repo_config/`
- pipeline or runtime manifests when they own behavior
- docs frontmatter for specs/plans already covered by the doc lifecycle rules

Rules:

- these files should use the metadata shape already natural to their format
- they should reference canonical feature IDs or capability IDs only when they
  materially participate in the behavior
- do not add metadata to passive files that only mention a feature incidentally

### D. Docs and assets

Docs and assets should participate in architecture metadata through refs and
ownership, not by pretending to be implementation.

Rules:

- specs and plans remain execution artifacts with frontmatter metadata
- feature-local docs should be linked through refs and history, not promoted to
  canonical capability ownership
- operator-facing artifacts or templates may need metadata only when they have
  direct behavioral weight in the runtime or validation contract
- static assets should only gain metadata if the repo actually relies on that
  metadata for ownership, publishing, or validation

## Proposed Design

### 1. Tighten the semantic capability model

Create a stricter local rule for capability IDs:

- one stable ID per durable capability
- long-tail change notes move to `summary`, linked specs/plans, or history
- capability IDs should be reviewed and curated by humans when source files are
  touched

This repo should prefer a smaller set of durable capabilities over a one-change
equals one-capability pattern.

### 2. Distinguish ownership from proof

Adopt the starter distinction explicitly:

- `feature.source.yaml` owns capability semantics
- implementation files may reference capabilities when they materially
  participate in the capability
- tests use `@proves` for evidence when appropriate
- generated lineage assembles those surfaces without implying that proof files
  are semantic owners

### 3. Reduce generator inventiveness

Update `scripts/sync_architecture_docs.py` so it no longer silently converts
descriptive strings into canonical capability IDs in steady-state Mode B.

Preferred behavior:

- migration compatibility may still detect legacy string entries
- validation should flag them
- generated outputs may preserve them as legacy warnings or transitional facts
- the generator should not pretend they are fully curated canonical capability
  IDs

### 4. Add validator rules for metadata quality

Expand `scripts/validate_adoption_shape.py` so it can catch:

- excessively prose-like capability IDs
- string-only capability entries where structured entries are required
- malformed or missing Python `@meta` blocks on required files
- file-level `capabilities` usage on files that do not materially need it
- missing canonical references when tests use `@proves`

The validator does not need semantic perfection, but it should block the most
common ways metadata drifts into noise.

### 5. Define the minimum required metadata surface

Document a bounded required set for this repo:

- required: behavioral Python scripts and test modules
- selective: workflows, manifests, config files, and assets with real runtime
  or publication weight
- not required by default: passive helpers, passive prose docs, and incidental
  asset files

That keeps the metadata contract meaningful instead of turning it into blanket
annotation work.

## Execution Batches

### Batch 1: Policy and inventory

- define the stable capability-ID policy
- inventory current over-long or change-note-style capability IDs
- inventory required Python files missing or misusing `@meta`
- decide which workflow/config/doc/asset surfaces need lineage metadata versus
  plain refs only

### Batch 2: Generator and validator tightening

- change the architecture generator so legacy strings are transitional data, not
  canonical capability truth
- add validation for required metadata surfaces
- add validation for capability-ID shape and legacy-capability detection
- add or update tests first

### Batch 3: Metadata normalization

- collapse overly specific capability IDs into stable capability contracts
- move long change details into summaries, history, and linked specs/plans
- update file-level metadata to canonical capability IDs
- add `@proves` markers where tests are evidence-bearing
- regenerate architecture outputs

### Batch 4: Governance refresh

- update local governance docs if needed
- update `repo_config/adoption-mode.yaml` notes/divergences if policy changes
- document the steady-state required metadata set so future work does not
  repeat this mistake

## Risks

### Risk 1: Capability collapse loses useful history

If several sentence-level capability IDs are merged too aggressively, the repo
could lose discoverability for past changes.

Mitigation:

- keep change detail in summaries, refs, specs, plans, and feature history
- collapse only the identifier layer, not the historical record

### Risk 2: Validator strictness lands before cleanup

If new validator rules arrive before metadata is normalized, the repo will fail
noisily and block normal work.

Mitigation:

- add tests and transitional warnings first
- tighten to hard failures only after normalization lands

### Risk 3: File metadata becomes over-applied again

If the repo responds by adding capability links to every nearby file, it will
recreate the same problem at a lower layer.

Mitigation:

- keep the "materially participates in lineage" threshold explicit
- prefer no capability metadata over speculative capability metadata

## Acceptance Criteria

This metadata correction is complete when all of the following are true:

1. `feature.source.yaml` capability IDs are stable, curated, and no longer read
   like sentence-level implementation notes.
2. `scripts/sync_architecture_docs.py` no longer upgrades descriptive strings
   into fully canonical capability IDs without an explicit curated source.
3. Required Python scripts and tests have valid top-of-file `@meta` blocks.
4. Tests that serve as capability evidence can use `@proves` without being
   confused for implementation ownership.
5. Generated lineage and discovery reflect curated capability truth rather than
   generator-invented IDs.
6. Validation catches malformed or drifted required metadata before merge.

## Validation Strategy

Minimum implementation verification:

- `.\.venv\Scripts\python.exe -m pytest tests/test_sync_architecture_docs.py tests/test_validate_adoption_shape.py`
- `.\.venv\Scripts\python.exe scripts/sync_architecture_docs.py`
- `.\.venv\Scripts\python.exe scripts/sync_architecture_docs.py --check`
- `.\.venv\Scripts\python.exe scripts/validate_adoption_shape.py`
- `git diff --check`

## Open Questions

1. Which current long-form capability IDs should collapse into the same stable
   capability contract versus remain distinct?
2. Should the validator merely warn on prose-like capability IDs first, or fail
   immediately once the cleanup starts?
3. Which workflow/config/doc/asset surfaces in this repo materially affect
   lineage enough to require explicit metadata instead of refs only?
