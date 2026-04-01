# Project Evidence Preservation Implementation Plan

> **For agentic workers:** Execute this plan task-by-task with verification after each task. Keep the current grouped experience path working throughout the rollout, and use the divergent-project-output failure case as a regression target.

**Goal:** Preserve richer grouped project evidence for CV generation so project sections stay grounded, action-oriented, and more consistent across runs.

**Architecture:** Introduce `project_entry` as first-class section-construction evidence, apply section-aware grouped-project ranking plus bounded intra-project selection, pass richer project blocks into prompt construction, and keep structured CV `projects` generation grounded in those grouped project entries.

**Tech Stack:** Python, FastAPI, BigQuery, Jinja2

**Source spec:** `docs/superpowers/specs/2026-03-31-project-evidence-preservation-design.md`

**Affected feature contract:** `docs/features/cv_system/cv_system.yaml`

**Supporting docs to update during implementation:**

- `docs/features/cv_system/cv_system.yaml`
- `docs/features/cv_system/history.md`

---

## Status Snapshot

- Completed:
  - Task 1: first-class grouped project evidence
  - Task 2: grouped-project ranking, bounded intra-project selection, and code-level defaults
  - Task 3: richer section-aware project prompt construction
  - Task 6: feature-doc updates
- Partially complete:
  - Task 4: runtime behavior now flows through grouped `project_entry` evidence and richer project prompt blocks, but no dedicated `pipeline.py` implementation change was required for this slice
- Pending:
  - Task 5: deeper regression coverage for the previously under-specified project-evidence path

---

## Task 1: Add First-Class Grouped Project Evidence

**Files:**

- Modify: `src/fitcv/evidence.py`
- Modify: `tests/test_evidence.py`

- [ ] **Step 1.1: Introduce `project_entry` evidence normalization**
  - Add a first-class `project_entry` evidence type that preserves:
    - `name`
    - `source_ref`
    - `duration` when present
    - `url` when present
    - `skills`
    - `tech_stack`
    - `business_value`
    - `highlights`
  - Keep grouped project evidence grounded in the candidate profile rather than constructing it late in prompt assembly

- [ ] **Step 1.2: Separate project section-construction evidence from supporting evidence**
  - Make the evidence layer explicit that:
    - grouped `project_entry` is a distinct first-class evidence type consumed by section-construction logic for the Projects section
    - supporting project snippets or highlights remain secondary evidence for broader CV emphasis where allowed
  - Preserve existing `experience_entry` semantics without regression

- [ ] **Step 1.3: Define sparse-project fallback behavior**
  - Projects with only minimal fields such as:
    - `name`
    - `duration`
    - `skills`
    should still produce valid grouped project evidence
  - Avoid requiring `business_value` or `highlights` to exist

- [ ] **Step 1.4: Add failing unit tests**
  - grouped project entries preserve source fields when present
  - sparse projects still produce valid grouped entries
  - grouped project entries remain traceable to source profile refs

- [ ] **Step 1.5: Confirm tests pass**

---

## Task 2: Add Section-Aware Project Selection and Budgeting

**Files:**

- Modify: `src/fitcv/evidence.py`
- Modify: `tests/test_evidence.py`

- [ ] **Step 2.1: Add grouped-project ranking**
  - Rank projects at the `project_entry` level using a normalized grouped-project text assembled from available project fields
  - Keep relevance grounded in the target JD
  - Perform highlight/stack/detail trimming only after grouped-project ranking
  - Preserve enough detail in grouped-project ranking for it to reflect:
    - skills
    - implementation context
    - purpose/outcome context when present

- [ ] **Step 2.2: Reserve bounded grouped-project capacity**
  - Add section-aware grouped-project capacity when the Projects section is enabled
  - When the Projects section is enabled and relevant grouped project evidence exists, preserve at least one bounded grouped-project entry for section construction, subject to composition limits
  - Keep grouped-project capacity distinct from grouped-experience capacity
  - Avoid making project representation depend on whichever thin snippet survives a generic mixed pool

- [ ] **Step 2.3: Add bounded intra-project selection**
  - After grouped project entries are selected, choose bounded:
    - highlights
    - stack lines
    - contextual fields for prompt use
  - Preserve purpose, outcome, or impact context when present
  - Preserve implementation context when present

- [ ] **Step 2.4: Make config ownership explicit**
  - For the first rollout, keep grouped-project capacity and per-project detail caps as code-level defaults with clear documentation
  - Do not introduce new user-facing config keys unless required by existing composition settings

- [ ] **Step 2.5: Add failing unit tests**
  - grouped project entries are ranked as grouped units
  - multiple relevant projects can survive selection
  - supporting project evidence does not consume reserved grouped-project capacity
  - intra-project selection is bounded

- [ ] **Step 2.6: Confirm tests pass**

---

## Task 3: Make Project Prompt Construction Richer and Section-Aware

**Files:**

- Modify: `src/fitcv/cv_generator.py`
- Modify: `tests/test_cv_generator.py`

- [ ] **Step 3.1: Replace thin project construction prompt input**
  - Stop using thin `name + skills` formatting as the primary construction path for the Projects section
  - Add grouped project blocks that can include:
    - name
    - duration
    - purpose / outcome / impact when present
    - selected tech stack
    - selected highlights

- [ ] **Step 3.2: Make the old thin path explicit**
  - Keep thin `name + skills` formatting only as fallback/supporting evidence
  - Do not use it as the primary construction path for the Projects section

- [ ] **Step 3.3: Preserve composition compatibility**
  - Respect existing section toggles
  - If the Projects section is disabled, grouped project evidence must not force project output
  - If composition limits the number of projects, prompt construction must still respect that cap

- [ ] **Step 3.4: Add failing prompt/generator tests**
  - grouped project blocks appear in the prompt
  - contextual project fields beyond skills are included when present
  - sparse project blocks degrade gracefully without invented impact
  - disabled Projects section still stays excluded from final markdown

- [ ] **Step 3.5: Confirm tests pass**

---

## Task 4: Wire Grouped Project Evidence Through the Pipeline

**Files:**

- Modify: `src/fitcv/pipeline.py`
- Modify: `tests/test_pipeline.py`

- [ ] **Step 4.1: Feed grouped project evidence into CV generation**
  - Ensure the runtime path uses grouped `project_entry` evidence for Projects composition
  - Keep the current fit/gap/validation flow intact
  - Preserve current grouped experience behavior without regression

- [ ] **Step 4.2: Keep the structured CV `projects` section grounded in grouped evidence**
  - Ensure the structured CV `projects` section derives project identities and core project context from grouped `project_entry` evidence
  - Supporting evidence may refine emphasis, but must not replace grouped-project sourcing
  - Avoid reconstructing project sections from tool-only snippets

- [ ] **Step 4.3: Add failing pipeline tests**
  - structured CV generation receives grouped project evidence
  - multiple relevant projects can appear in the Projects section path
  - grouped project evidence remains bounded and grounded

- [ ] **Step 4.4: Confirm tests pass**

---

## Task 5: Add Regression Coverage for the Divergent Project Failure Mode

**Files:**

- Modify: `tests/test_pipeline.py`
- Modify: `tests/test_cv_generator.py`
- Modify: fixture/test data only if needed

- [ ] **Step 5.1: Encode the real project inconsistency scenario**
  - Add a regression fixture representing the previously under-specified project evidence path that allowed tool-list-only project summaries despite richer source project context

- [ ] **Step 5.2: Assert section-faithful project behavior**
  - Verify grouped project evidence survives shaping intact
  - Verify project prompt assembly includes contextual fields beyond skills when present
  - Verify project sections remain grounded and more stable across equivalent runs
  - Avoid brittle assertions tied to one exact sentence

- [ ] **Step 5.3: Add non-regression checks**
  - Projects section disabled → no forced project output
  - Experience section path still behaves as before
  - Sparse projects still render without invented impact

- [ ] **Step 5.4: Confirm tests pass**

---

## Task 6: Update Feature Docs

**Files:**

- Modify: `docs/features/cv_system/cv_system.yaml`
- Modify: `docs/features/cv_system/history.md`

- [ ] **Step 6.1: Update feature contract**
  - Add grouped project evidence preservation and section-aware Projects construction to feature capabilities
  - Record `project_entry` as a first-class evidence type
  - Record that thin project evidence is fallback/supporting only
  - Record where grouped-project capacity and per-project detail caps live
  - Record non-regression expectations relative to grouped experience preservation
  - Link the new spec and implementation plan

- [ ] **Step 6.2: Record implementation history**
  - Note the change from thin project prompt evidence toward grouped project construction
  - Record the regression motivation and the grouped-project budget design

---

## Execution Order

1. Complete Task 1 first so `project_entry` is explicit and testable.
2. Complete Task 2 before changing prompt construction so grouped-project selection semantics are stable.
3. Complete Task 3 once the grouped project shape and budget rules are well-defined.
4. Complete Task 4 after the evidence and prompt seams are stable.
5. Complete Task 5 before closing the work so the divergent project-output failure mode stays covered.
6. Complete Task 6 last so the feature docs reflect the implemented behavior.

---

## Verification Checklist

- [ ] Grouped `project_entry` exists as first-class evidence in the evidence layer
- [ ] Project evidence is ranked at the grouped-project level rather than only via thin snippets
- [ ] The Projects section is built primarily from grouped project evidence
- [ ] Sparse projects degrade gracefully without invented impact
- [ ] Existing grouped experience behavior remains intact
- [ ] Structured CV generation and markdown rendering remain compatible with composition controls

---

## Risks and Notes

### Prompt Bloat Risk

Grouped project entries are larger than thin `name + skills` lines. Keep grouped-project budgets and intra-project selection bounded.

### Experience Regression Risk

Project improvements must not disturb the recent grouped-experience path. Keep project changes scoped to project construction and shared evidence semantics only where necessary.

### Composition Drift Risk

Richer project evidence must not override preset or section-detail controls. Keep explicit tests for disabled/composition-limited Projects behavior.

### Scope Guard

Do not turn this into a full redesign of ranking, exports, or the entire structured CV schema. The first goal is to preserve richer project structure through evidence shaping and prompt construction.
