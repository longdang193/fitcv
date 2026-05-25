---
layer: change
artifact_type: spec
status: proposed
template_id: detailed-specification
name: synonym-global-promotion-domain-role-family-symmetry
parent_thread: workstream-agentic-synonym-management.agentic-synonym-canonical-promotion-flow
targets:
  - config/taxonomy/skill_synonyms.yaml
  - config/taxonomy/domain_synonyms.yaml
  - config/taxonomy/role_family_synonyms.yaml
  - src/fitcv_cp/app.py
  - src/fitcv_cp/worker_job.py
  - src/fitcv_cp/templates/synonym_review.html
  - src/fitcv_cp/templates/synonym_promote_preview.html
  - docs/api.md
---

## Goal

Restore symmetry, SSOT correctness, and invariance for “Promote Synonyms to Global Policy” by implementing parallel global promotion per proposal `field` (`skill`, `domain`, `role_family`) so promotion always writes to the correct canonical global policy map(s).

## Key Deliverables

### Deliverable 1: Field-aware global promotion

Define and implement a promotion pipeline that routes each approved proposal to the correct SSOT map based on `proposal.field`, preventing cross-field writes (e.g., domain → skill map).

### Deliverable 2: Canonical global policy access for all fields

Define canonical load/persist and download/export surfaces for:
- global skill synonyms (`skill_synonyms`)
- global domain aliases (`domain_alias_map`)
- global role-family aliases (`role_family_alias_map`)

### Deliverable 3: Operator UX symmetry and clarity

Define promote preview + commit UX that:
- communicates which field(s) will be updated
- reports per-field counts (add/update/skip/conflict)
- makes non-skill promotion explicit and reviewable

### Deliverable 4: Validation and safety gates

Define deterministic formatting, conflict handling, and test coverage so promotion is SSOT-safe, idempotent, and auditable.

## Task/Wave Breakdown

### Wave 1: Source-first analysis

**Purpose:**
- baseline current behavior and isolate invariance violations before design choices

**Steps:**
- [ ] confirm proposal payload supports `field in {skill, domain, role_family}`
- [ ] confirm current promote-preview/commit path ignores `field`
- [ ] confirm current promote path persists only `config/taxonomy/skill_synonyms.yaml`
- [ ] confirm domain/role-family SSOT files exist and current schema keys (`domain_alias_map`, `role_family_alias_map`, neighbor maps)

**Verification:**
- [ ] evidence references recorded for proposal generation, promote-preview, promote-commit, and persistence

**Exit Criteria:**
- invariance break is precisely stated: “promotion must never write proposal of one field into SSOT of another field”

### Wave 2: Decision closure

**Purpose:**
- resolve correct symmetric contract for global promotion across fields

**Steps:**
- [ ] choose promotion routing rule (field → SSOT target map)
- [ ] choose whether mixed-field selection is allowed (single commit updates multiple SSOT maps)
- [ ] choose conflict strategy (block-all vs field-local partial apply) and operator messaging
- [ ] define export endpoints and filenames for domain/role-family symmetry
- [ ] define whether auto-promote extends beyond skills or remains skill-only

**Verification:**
- [ ] each decision has explicit choice + alternatives + impact on UI/routes/tests

**Exit Criteria:**
- spec defines one coherent end-to-end contract for preview, commit, persistence, and export

### Wave 3: Validation and approval readiness

**Purpose:**
- make proof obligations explicit so implementation can be planned safely

**Steps:**
- [ ] define required tests for each field promotion path
- [ ] define deterministic formatting expectations for each SSOT file
- [ ] define audit/event payload expectations for per-field promotions

**Verification:**
- [ ] validation plan proves “no cross-field writes” and “correct SSOT updated”

**Exit Criteria:**
- spec ready to hand off to implementation planning

## Design Decisions

### Decision: SSOT mapping per field

- context: promotion currently assumes single “global synonym map” but proposals already have multi-field semantics (`skill`, `domain`, `role_family`)
- choice:
  - `field == "skill"` promotes into `config/taxonomy/skill_synonyms.yaml` under `skill_synonyms`
  - `field == "domain"` promotes into `config/taxonomy/domain_synonyms.yaml` under `domain_alias_map`
  - `field == "role_family"` promotes into `config/taxonomy/role_family_synonyms.yaml` under `role_family_alias_map`
- alternatives considered:
  - single combined “global synonyms” file containing all sections (rejected: increases blast radius and complicates existing config contract)
  - disallow non-skill proposals entirely (rejected: proposals already exist; symmetry requires ability to curate them)
- impact:
  - promote-preview/commit must become field-aware
  - persistence functions must exist per SSOT surface
  - export/download endpoints must exist per SSOT surface

### Decision: Scope of promotion for non-skill fields

- context: domain/role-family SSOT includes both alias maps and neighbor maps; proposals represent alias→canonical mappings, not neighbor graph edits
- choice: promotion only updates alias maps:
  - `domain_alias_map` (not `domain_neighbors`)
  - `role_family_alias_map` (not `role_family_neighbors`)
- alternatives considered:
  - extend proposals to support neighbor edits (defer: requires new proposal families and UI, higher risk)
- impact:
  - non-skill promotion is symmetry-restoring but bounded to alias canonicalization only

### Decision: Promote selection model across fields

- context: operator selection UI spans multiple field groups; promote flow must define how selections are interpreted
- choice: allow mixed-field selection; commit applies updates to each SSOT map independently within one operator action, returning per-field counts
- alternatives considered:
  - require one field per promotion commit (simpler but breaks queue symmetry and forces manual repetition)
- impact:
  - preview page must group selected rows by `field`
  - commit must compute and persist per-field overlays deterministically

### Decision: Conflict handling and atomicity

- context: within a selected set, duplicate alias values with multiple proposed canonicals are conflicts today; current behavior can block commit when conflicts exist
- choice:
  - conflicts are evaluated per field (since SSOT maps are separate)
  - commit applies only when there are zero conflicts in the selected set for a given field
  - when mixed-field selection, commit may apply some fields and skip others if skipped fields have conflicts; response must report per-field outcomes
- alternatives considered:
  - “all-or-nothing” across all fields (simpler but amplifies small conflicts into total failure)
  - “partial apply within a field” (rejected: makes operator intent ambiguous and increases accidental policy drift)
- impact:
  - preview must surface conflict rows per field with explicit reasons
  - commit must persist only conflict-free field maps

### Decision: Export/download symmetry

- context: operators can download global skill synonyms today; symmetric SSOT requires equivalent exports for domain and role-family policy
- choice:
  - add:
    - `GET /admin/synonyms/global-skill.yaml` (back-compat alias kept for existing `/admin/synonyms/global.yaml`)
    - `GET /admin/synonyms/global-domain.yaml`
    - `GET /admin/synonyms/global-role-family.yaml`
  - each endpoint returns deterministic YAML matching SSOT file schema keys
- alternatives considered:
  - single “global.yaml” containing all sections (rejected: breaks existing consumers and increases ambiguity)
- impact:
  - docs/api.md updated to list new endpoints and clarify per-field SSOT

### Decision: Auto-promote scope

- context: auto-promote exists in worker run-execution path; extending it to non-skill fields increases policy mutation surface without operator confirmation
- choice: keep `auto_promote_global_enabled` skill-only for now; spec adds manual promotion symmetry first
- alternatives considered:
  - extend auto-promote to domain/role-family immediately (defer: require additional guardrails and opt-in)
- impact:
  - implementation should enforce: auto-promote only processes proposals with `field == "skill"` unless explicitly extended in a follow-up spec

## Invariants

- Promotion must never write a proposal into the wrong SSOT surface:
  - `field == "domain"` must not modify `skill_synonyms.yaml`
  - `field == "role_family"` must not modify `skill_synonyms.yaml`
- SSOT files remain canonical:
  - `config/taxonomy/skill_synonyms.yaml` owns `skill_synonyms`
  - `config/taxonomy/domain_synonyms.yaml` owns `domain_alias_map` and `domain_neighbors`
  - `config/taxonomy/role_family_synonyms.yaml` owns `role_family_alias_map` and `role_family_neighbors`
- Promotion is deterministic and idempotent:
  - applying same selected set twice yields zero net changes second time
  - persisted YAML output uses stable key ordering and stable formatting conventions
- Non-goal invariants (explicitly not changed in this spec):
  - neighbor maps (`domain_neighbors`, `role_family_neighbors`) are not mutated by promotion

## Validation Plan

- proof target: promote-preview groups and routes selected proposals by `field`
  - method: unit test of preview builder with mixed-field payload
  - evidence: test asserts per-field rows and per-field counts, and asserts no cross-field map writes are computed

- proof target: promote-commit updates correct SSOT file for each field and never touches other fields
  - method: unit/integration test with temp config dir and sample payload selecting skill+domain+role-family
  - evidence:
    - `skill_synonyms.yaml` updated only for `field=skill`
    - `domain_synonyms.yaml` updated only under `domain_alias_map`
    - `role_family_synonyms.yaml` updated only under `role_family_alias_map`

- proof target: worker auto-promote remains skill-only
  - method: unit test for worker promotion function using non-skill proposals in payload
  - evidence: no writes to domain/role-family SSOT; non-skill proposals reported as skipped with explicit reason

- proof target: exports exist for all global policy maps
  - method: route test / HTTP client test
  - evidence: 200 response with YAML containing expected top-level keys (`skill_synonyms`, `domain_alias_map`, `role_family_alias_map`)

- proof target: deterministic formatting and sorting
  - method: snapshot test of persisted YAML strings for each map type
  - evidence: stable sorted keys + trailing newline; no empty/invalid entries persisted

## Completion Criteria

1. promote-preview and promote-commit are field-aware and SSOT-correct for `skill`, `domain`, `role_family`
2. domain and role-family global policy export endpoints exist and are documented
3. tests prove invariants (“no cross-field writes”, “deterministic persistence”, “idempotent promotion”)
4. no behavior outside bounded scope is changed (neighbor maps and unrelated settings remain untouched)
