---
layer: change
artifact_type: plan
status: proposed
template_id: implementation-plan
name: candidate-profile-template-split
parent_thread: workstream-fitcv-semantic-spine.semantic-spine-checkpoint-and-continue-truth
parent_spec: docs/superpowers/specs/2026-05-14-candidate-profile-private-surface-spec.md
targets:
  - data/candidate_profile.yaml
  - data/candidate_profile.template.yaml
  - data/candidate_profile.private.yaml
  - .gitignore
  - repo_config/publication-config.json
  - tests/
related_features: []
related_stages: []
---

## Goal

Create canonical `data/candidate_profile.template.yaml` from current candidate profile source, while preserving private data boundary and keeping validator/publication behavior green.

## Key Deliverables

### Deliverable 1: Canonical template + private split contract

Define and apply deterministic split between reusable template fields and private user data fields, with explicit ownership of each file:
- `candidate_profile.template.yaml` = safe scaffold, defaults, comments, no secrets
- `candidate_profile.private.yaml` = personal values, ignored from publication
- `candidate_profile.yaml` role clarified (alias/source/deprecated path decided in-task)

### Deliverable 2: Repo boundary alignment

Ensure ignore/publication/runtime config rules treat private candidate data as private-only and template as shareable starter surface.

### Deliverable 3: Validator-proof evidence

Add/adjust checks so template schema/shape remains stable and regressions fail fast.

## Task/Wave Breakdown

### Task 1: Inventory candidate-profile shape and classify fields

**Purpose:**
- Build explicit field taxonomy before file split.

**Files:**
- Inspect: `data/candidate_profile.yaml`
- Inspect: `data/sample_data_engineer_jobs.json`
- Verify: `repo_config/publication-config.json`

**Preconditions:**
- Existing candidate profile content is current baseline.

**Steps:**
- [x] Step 1: Parse current `candidate_profile.yaml` keys and nested structures.
- [x] Step 2: Classify keys into `template-safe` vs `private-required` vs `optional-private`.
- [x] Step 3: Record mapping table used by split logic (in plan execution notes or test fixture).

**Task 1 Classification Map (Top-Level Coverage):**

| Source key | Classification | Split target intent | Notes |
| --- | --- | --- | --- |
| `name` | private-required | `candidate_profile.private.yaml` | Direct identity PII. |
| `headline` | optional-private | `candidate_profile.private.yaml` | Personal branding text. |
| `summary` | optional-private | `candidate_profile.private.yaml` | Personal narrative content. |
| `contact` | private-required | `candidate_profile.private.yaml` | Email/phone/URLs/location are sensitive. |
| `experiences` | optional-private | `candidate_profile.private.yaml` | Personal employment history. |
| `education` | optional-private | `candidate_profile.private.yaml` | Personal academic records. |
| `skills` | template-safe | `candidate_profile.template.yaml` | Keep scaffold shape with placeholder entries only. |
| `projects` | optional-private | `candidate_profile.private.yaml` | Personal project ownership/claims. |
| `certifications` | optional-private | `candidate_profile.private.yaml` | Credential IDs/years are person-linked. |
| `languages` | optional-private | `candidate_profile.private.yaml` | Language levels and notes person-linked. |
| `achievements` | optional-private | `candidate_profile.private.yaml` | Achievement claims person-linked. |
| `interests` | optional-private | `candidate_profile.private.yaml` | Personal preference data. |
| `volunteering` | optional-private | `candidate_profile.private.yaml` | Person-linked activity history. |
| `preferences` | private-required | `candidate_profile.private.yaml` | Job target/location/salary preferences sensitive. |

**Coverage check:** 14/14 top-level keys from `data/candidate_profile.yaml` classified exactly once.

**Verification:**
- [x] Manual check: every source field appears exactly once in classification table.

**Exit Criteria:**
- Clear, complete field-classification map approved for split.

### Task 2: Create template file and private file contract

**Purpose:**
- Materialize template/private files with stable structure.

**Files:**
- Modify: `data/candidate_profile.template.yaml`
- Modify: `data/candidate_profile.private.yaml`
- Modify: `data/candidate_profile.yaml`

**Preconditions:**
- Task 1 classification complete.

**Steps:**
- [x] Step 1: Create `candidate_profile.template.yaml` with placeholders + comments and no personal values.
- [x] Step 2: Create/update `candidate_profile.private.yaml` with private value slots populated or ready.
- [x] Step 3: Decide `candidate_profile.yaml` behavior:
  - keep as compatibility loader target, or
  - reduce to pointer/merge instruction, or
  - deprecate with migration note.

**Verification:**
- [x] YAML parse check for all candidate-profile YAML files.
- [x] Diff review: template file contains no private literals.

**Exit Criteria:**
- Template/private split complete and syntactically valid.

### Task 3: Enforce privacy/publication boundary

**Purpose:**
- Prevent accidental publication or commit leak of private profile data.

**Files:**
- Modify: `.gitignore`
- Modify: `repo_config/publication-config.json`
- Verify: `scripts/validate_repo_config.py`

**Preconditions:**
- Task 2 complete.

**Steps:**
- [x] Step 1: Ensure `data/candidate_profile.private.yaml` ignored locally.
- [x] Step 2: Ensure publication config excludes private profile file and allows template file when needed.
- [x] Step 3: Confirm no boundary conflict with existing repo governance rules.

**Verification:**
- [ ] `python scripts/validate_repo_config.py` *(blocked by repo-level missing `repo_config/starter-kit-manifest.json` and `configs/`, unrelated to candidate-profile changes)*
- [x] Publication config static review for explicit private-file exclusion.

**Exit Criteria:**
- Private file protected from export/commit path; template remains shareable.

### Task 4: Add regression checks for template contract

**Purpose:**
- Make split durable under future edits.

**Files:**
- Modify: `tests/` (new focused test file, e.g. `tests/test_candidate_profile_template_contract.py`)
- Verify: related validator scripts as needed

**Preconditions:**
- Task 2 and Task 3 complete.

**Steps:**
- [x] Step 1: Add test asserting template file exists and parses as mapping.
- [x] Step 2: Add test asserting forbidden private keys/values do not appear in template.
- [x] Step 3: Add test asserting required scaffold keys exist in template.

**Verification:**
- [x] `pytest -q tests/test_candidate_profile_template_contract.py`

**Exit Criteria:**
- Regression test suite catches template/privacy drift.

### Task 5: Final integrated validation

**Purpose:**
- Confirm green baseline after split.

**Files:**
- Verify: `data/candidate_profile*.yaml`
- Verify: `repo_config/publication-config.json`
- Verify: validator/test outputs

**Preconditions:**
- Tasks 1–4 complete.

**Steps:**
- [x] Step 1: Run targeted tests + relevant validators.
- [x] Step 2: Resolve any drift from publication or metadata validators.
- [x] Step 3: Capture final evidence summary for handoff.

**Verification:**
- [x] `pytest -q tests/test_candidate_profile_template_contract.py` *(3 passed)*
- [x] `python scripts/validate_repo_config.py` *(passed)*
- [x] `python scripts/validate_repo_contracts.py --fast` *(passed; lifecycle linkage warnings only)*

**Exit Criteria:**
- Candidate-profile template split passes local contract gates.

## Verification

- `pytest -q tests/test_candidate_profile_template_contract.py`
- `python scripts/validate_repo_config.py`
- `python scripts/validate_repo_contracts.py --fast`

## Completion Criteria

1. `data/candidate_profile.template.yaml` exists with canonical scaffold and no private values.
2. Private candidate values are isolated to `data/candidate_profile.private.yaml` and boundary-protected.
3. Publication/config validation remains green.
4. Regression test coverage exists for template/privacy contract.
5. Handoff includes exact migration note for `data/candidate_profile.yaml` role.
