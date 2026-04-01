# Experience Evidence Preservation Implementation Plan

> **For agentic workers:** Execute this plan task-by-task with verification after each task. Keep the current CV generation pipeline working throughout the rollout, and use the shallow-experience failure case as a regression target.

**Goal:** Preserve grouped work-history evidence for CV generation so rich candidate profiles do not collapse into shallow one-role Experience sections.

**Architecture:** Introduce grouped experience-entry evidence as primary section-construction input for the Experience section, separate section-construction evidence from supporting evidence, replace the flat global evidence budget with a section-aware shaped budget, and pass structured work-history blocks into structured CV generation.

**Tech Stack:** Python, FastAPI, BigQuery, Jinja2

**Source spec:** `docs/superpowers/specs/2026-03-30-experience-evidence-preservation-design.md`

**Affected feature contract:** `docs/features/cv_system/cv_system.yaml`

**Supporting docs to update during implementation:**

- `docs/features/cv_system/cv_system.yaml`
- `docs/features/cv_system/history.md`

## Status Snapshot

- Completed:
  - Task 1: grouped experience evidence model
  - Task 2: section-aware shaped evidence selection
  - Task 3: grouped experience prompt construction
  - Task 6: feature-doc updates
- Partially complete:
  - Task 4: runtime behavior now flows through the updated shared evidence and prompt seams, but no dedicated `pipeline.py`-level regression slice was added yet
- Pending:
  - Task 5: deeper regression coverage for the full shallow-experience failure chain

---

## Task 1: Model Grouped Experience Evidence

**Files:**

- Modify: `src/fitcv/evidence.py`
- Modify: `tests/test_evidence.py`

- [x] **Step 1.1: Add grouped experience-entry evidence normalization**
  - Introduce an `experience_entry` evidence representation that preserves:
    - role
    - company
    - location
    - start/end dates
    - selected bullets
    - aggregated skills
    - stable source reference
  - Keep the representation grounded in the candidate profile rather than reconstructing job structure later

- [x] **Step 1.2: Distinguish evidence roles**
  - Make the evidence layer explicit about:
    - section-construction evidence
    - supporting evidence
  - Experience entries should become section-construction evidence for the Experience section
  - Existing projects and achievements remain available as supporting evidence for this rollout

- [x] **Step 1.3: Add failing unit tests**
  - grouped experience entries preserve role/company/date context
  - aggregated skills are retained
  - grouped entries remain traceable to the source profile

- [x] **Step 1.4: Confirm tests pass**

---

## Task 2: Add Section-Aware Evidence Selection

**Files:**

- Modify: `src/fitcv/evidence.py`
- Modify: `tests/test_evidence.py`

- [x] **Step 2.1: Replace the one-pool global evidence budget**
  - Move from one mixed global top-k across projects, achievements, and experience bullets
  - Introduce a shaped budget with separate capacity for:
    - grouped experience entries
    - supporting projects
    - supporting achievements
  - Make the first-pass policy explicit:
    - reserve grouped-experience capacity so multiple grounded roles can survive when relevant evidence exists
    - reserve smaller supporting/project capacity instead of letting everything compete in one pool
    - use conservative defaults even if the final counts remain configurable

- [x] **Step 2.2: Preserve multi-role capacity**
  - Ensure that when multiple relevant grounded experience entries exist, the selection budget preserves enough grouped work-history context to represent more than one role
  - Keep the first implementation configurable, but do not rely on weight tuning alone

- [x] **Step 2.3: Add bounded bullet selection inside each grouped experience entry**
  - Select the most relevant bullets within each entry
  - Cap bullets per entry to keep prompts bounded
  - Preserve role-level structure even when only a subset of bullets is used

- [x] **Step 2.4: Add failing unit tests**
  - multiple relevant roles can survive selection
  - experience entries do not have to compete for every slot with projects
  - bullet capping works without losing role structure

- [x] **Step 2.5: Make config ownership explicit**
  - Decide where shaped-budget and per-entry bullet-cap controls live
  - For first rollout, either:
    - add explicit config keys with conservative defaults
    - or keep code-level defaults intentionally and document them clearly
  - Avoid leaving the new budgeting semantics implicit

- [x] **Step 2.6: Confirm tests pass**

---

## Task 3: Make CV Prompt Construction Section-Aware

**Files:**

- Modify: `src/fitcv/cv_generator.py`
- Modify: `tests/test_cv_generator.py`

- [x] **Step 3.1: Add grouped work-history blocks to prompt construction**
  - Pass structured experience-entry evidence to the generator as role/company/date blocks with bounded bullets
  - Do not reduce grouped experience back into flat snippets before prompting
  - The generator should consume pre-grouped work-history blocks as canonical experience inputs rather than inferring job grouping from loose bullet fragments

- [x] **Step 3.2: Make Experience construction explicit**
  - Ensure the prompt semantics clearly treat grouped experience-entry evidence as the primary source for the Experience section
  - Keep project evidence available in its dual role:
    - section-construction evidence for the Projects section when enabled
    - supporting evidence for overall CV emphasis where appropriate
  - Keep achievements as supporting evidence unless a dedicated achievement section path exists

- [x] **Step 3.3: Preserve composition compatibility**
  - Existing section toggles must still work
  - Prompt filtering and final render behavior must stay aligned

- [x] **Step 3.4: Add failing prompt/generator tests**
  - grouped experience blocks appear in the prompt
  - supporting evidence remains available
  - disabled sections still remain excluded from final markdown

- [x] **Step 3.5: Confirm tests pass**

---

## Task 4: Wire Section-Aware Evidence Through the Pipeline

**Files:**

- Modify: `src/fitcv/pipeline.py`
- Modify: `tests/test_pipeline.py`

- [ ] **Step 4.1: Replace flat Experience evidence usage in Layer 4**
  - Feed grouped experience-entry evidence into CV generation
  - Keep the current fit/gap/validation flow intact
  - Ensure the structured CV `experience` section is built primarily from grouped experience-entry evidence
  - Status: completed indirectly through shared `retrieve_evidence()` and prompt-construction updates; no dedicated `pipeline.py` patch was required for this slice

- [ ] **Step 4.2: Keep supporting evidence available**
  - Continue passing project evidence where useful:
    - as section-construction evidence for Projects when enabled
    - as supporting evidence for overall CV emphasis where appropriate
  - Continue passing achievement evidence as supporting evidence where useful
  - Avoid regressing project section quality while fixing experience richness
  - Status: partially covered by current shared evidence and prompt changes; deeper project-focused follow-up is still open

- [ ] **Step 4.3: Add failing pipeline tests**
  - structured CV generation receives grouped experience evidence
  - multiple relevant roles can appear in the Experience section path
  - the shallow one-role collapse is prevented for the known regression shape

- [ ] **Step 4.4: Confirm tests pass**

---

## Task 5: Add Regression Coverage for the Real Failure Mode

**Files:**

- Modify: `tests/test_pipeline.py`
- Modify: `tests/test_cv_generator.py`
- Modify: fixture/test data only if needed

- [ ] **Step 5.1: Encode the shallow-experience failure shape**
  - Add a regression test based on the real debugging scenario:
    - rich source profile
    - old flat selection collapses experience
    - new grouped selection preserves richer work-history context

- [ ] **Step 5.2: Assert section-faithful behavior**
  - Verify the Experience section can represent more than one grounded role when relevant evidence exists
  - Verify role/company/date grouping is preserved
  - Verify the fix does not depend on arbitrary prompt bloat
  - Avoid brittle assertions tied to one exact final role count unless the budget contract explicitly requires it

- [ ] **Step 5.3: Confirm tests pass**

---

## Task 6: Update Feature Docs

**Files:**

- Modify: `docs/features/cv_system/cv_system.yaml`
- Modify: `docs/features/cv_system/history.md`

- [x] **Step 6.1: Update feature contract**
  - Add section-aware evidence selection and grouped experience preservation to feature capabilities
  - Link the new spec and implementation plan

- [x] **Step 6.2: Record implementation history**
  - Note the change from flat snippet-ranked evidence toward section-aware experience construction
  - Record the regression motivation and the shaped-budget design

---

## Execution Order

1. Complete Task 1 first so the grouped evidence model is explicit and testable.
2. Complete Task 2 before touching the generator so selection semantics are stable.
3. Complete Task 3 once prompt inputs are well-defined.
4. Complete Task 4 after the evidence and prompt paths are stable.
5. Complete Task 5 before closing the work so the real shallow-experience failure mode stays covered.
6. Complete Task 6 last so the feature docs reflect the implemented behavior.

---

## Verification Checklist

- [x] Experience evidence preserves grouped role/company/date structure
- [x] CV evidence retrieval is section-aware rather than purely snippet-ranked
- [x] The Experience section is built primarily from grouped experience-entry evidence
- [x] Projects and achievements remain available as supporting evidence
- [ ] When multiple relevant grounded roles exist, the selection budget preserves enough context to represent more than one role
- [x] Existing structured CV generation and markdown rendering flows remain compatible

---

## Risks and Notes

### Prompt Bloat Risk

Grouped experience entries can become large. Keep bounded bullet selection and shaped budgets so prompts remain controlled.

### Section Imbalance Risk

Fixing experience richness must not accidentally starve project evidence when the Projects section is enabled. Preserve explicit supporting/project capacity.

### Regression Risk

The main regression target is the shallow-experience failure mode where rich profile history collapses to one role because evidence is flattened too early. Keep a dedicated test for that.

### Scope Guard

Do not turn this into a full redesign of ranking, exports, or the entire structured CV schema. The first goal is to preserve work-history structure through evidence selection and prompt construction.
