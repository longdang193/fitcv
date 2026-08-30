---
layer: change
artifact_type: plan
template_id: implementation-plan
contract_version: "1"
status: active
name: fitcv-new-frontend-spec-plan-reconciliation
parent_spec: none
targets:
  - docs/superpowers/plans/2026-08-30-fitcv-new-frontend-spec-plan-reconciliation-plan.md
  - docs/superpowers/plans/2026-08-29-fitcv-new-frontend-vertical-slice-plan.md
  - docs/superpowers/specs/2026-08-30-fitcv-new-frontend-production-spec.md
  - docs/superpowers/specs/README.md
  - docs/fitcv-new-frontend.integration.md
---

# FitCV New Frontend Specification–Plan Reconciliation Plan

## Goal

Produce one executable, Git-tracked coordination plan that reconciles current FitCV specification and contract ownership, creates and approves one canonical greenfield frontend production specification, revises the existing proposed vertical-slice implementation plan in place, and stops before any production frontend or backend implementation.

## Implementation Outcomes

### Canonical production frontend specification

A new specification at `docs/superpowers/specs/2026-08-30-fitcv-new-frontend-production-spec.md` starts as a proposed `draft-specification`, then is promoted in place to an active `detailed-specification` only after independent review, explicit product-owner approval, and completion of applicable Design Export evidence. It owns the durable cross-cutting contract for the rebuilt FitCV frontend: greenfield authority, approved architecture boundaries, client/server ownership, API-client behavior, security, accessibility, responsive behavior, legacy coexistence, and verification intent.

### Reconciled focused specification state

All current files under `docs/superpowers/specs/` are classified against source, tests, and existing verification evidence. Focused specifications remain single owners of their feature contracts; status changes occur only when their complete contract lifecycle is proven. No completed or superseded specification is rewritten, and no duplicate frontend feature specification is created.

### Reconciled production implementation plan and integration evidence

`docs/superpowers/plans/2026-08-29-fitcv-new-frontend-vertical-slice-plan.md` is revised in place after parent-spec promotion. It has exactly one `parent_spec`, no active retired roadmap/workstream ownership, task-level Specification Coverage tied to the parent specification and focused specifications, concrete files/symbols/commands, safe dependencies and shared-write ownership, and a current execution-base candidate. The closed integration note is corrected so its ownership statement is current or explicitly historical and non-normative.

### Approval-gated execution readiness

Independent `xhigh` and `review` assessments cover this meta-plan before owner approval. Downstream specification and plan reviews have explicit verdicts and product-owner stop gates. Completion reports production-plan readiness only; it does not activate or execute the production vertical slices.

## Execution Approach

- Mode: `subagent-ready`
- Coordination: `git-tracked`
- Default task executor: `codex`
- Required skills: `skill-verification-before-completion`
- Isolation: `current workspace`; isolated worktree only if a later approved change requires concurrent write-capable lanes
- Commit policy: `verified per-task checkpoint commits preauthorized only after meta-plan owner approval`; no commit before that gate
- Preauthorized local actions: inspect declared repository files, create the parent draft specification, promote that same specification after approval, revise the declared vertical-slice plan and closed integration note after approval, run declared validators and tests, run read-only independent reviews, and create approved checkpoint commits after task proof
- User-approval actions: approve this meta-plan before activation, approve the parent specification before Task 4, approve the reconciled production plan before production execution, push, merge, publication, destructive cleanup, and any scope or base change
- Parallel ownership: read-only reviews may run independently; canonical writers are sequential and never share an active write target
- Sequential fallback: meta-plan owner approval → Task 1 → Task 2 → Task 3 → parent-spec owner approval → Task 4 → Task 5 → Task 6 → Task 7 → final owner approval
- CoS applicability: not selected; this meta-plan uses one sequential current-workspace lead, while the downstream production plan may independently select CoS only if its own execution topology satisfies current policy
- Coordination writes: only the lead controller edits this plan's Coordination State, task ledger, checklists, and evidence; task writers and reviewers never edit coordination state; accepted proof and each ledger transition share one checkpoint

## Coordination State

- Coordination owner: `single lead controller`
- Coordination schema: `2`
- Branch: `main`
- Base commit: `b861d13e`
- Expected workspace: clean at `b861d13e` before this plan is added; after drafting, only declared planning artifacts may be uncommitted and unrelated user changes remain preserved
- Next action: independently review reconciled production plan in Task 7
- Blockers: final production-plan owner approval is required before production implementation; future non-behavior deferrals need explicit owner, rationale, trigger, and approval reference

| Task | State | Workspace | Executor | Depends On | Required Proof | Evidence |
| --- | --- | --- | --- | --- | --- | --- |
| Task 1 | `completed` | current | `codex` | meta-plan owner approval | inventory, source/test evidence, stale-owner and Design Export gate scan | six focused specs active; G-02/G-03/G-04 direct proof recorded; retired roadmap reference is historical; EX-01/EX-12 owner decisions recorded |
| Task 2 | `completed` | current | `codex` | Task 1 | draft-spec template and lifecycle validation | proposed parent spec created; template and lifecycle validators passed; prohibited-marker scan passed |
| Task 3 | `completed` | current | `codex` | Task 2 | independent draft-spec verdict | `SPEC READY FOR OWNER APPROVAL`; review agent found no P1/P2; template, lifecycle, repo-contract, and diff checks passed |
| Task 4 | `completed` | current | `codex` | Task 3 and explicit parent-spec owner approval | Design Export identity, owner decisions, independent PASS | metadata identity passed; source/output/task match; independent PASS bound to OpenDesign run and output blob; EX-01/EX-12 resolved |
| Task 5 | `completed` | current | `codex` | Task 4 | active detailed-spec template and lifecycle validation | same file promoted to active detailed specification; template/lifecycle/prohibited-marker checks passed |
| Task 6 | `completed` | current | `codex` | Task 5 | plan/integration reconciliation and validators | singular parent linkage; product/spec coverage matrix; historical integration ownership; proposed plan remains inactive |
| Task 7 | `active` | current | `codex` | Task 6 | independent plan verdict | required fixes addressed: baseline aligned to `9a83da1d`; synonym slice narrowed to feature-local scope; re-review pending |

## META-PLAN OWNER APPROVAL GATE

- Independent `xhigh` and `review` assessment must return no unresolved P1/P2 approval blockers.
- Product owner approved exact artifact `docs/superpowers/plans/2026-08-30-fitcv-new-frontend-spec-plan-reconciliation-plan.md` in Codex task on 2026-08-30; activation and Task 1 evidence are checkpointed in `0864016be8dedc0e6fb53f061d63a77f152166e6`.
- Before Task 1, lead controller records approval reference, changes this plan from `status: proposed` to `status: active`, leaves every task `pending`, and commits that active-plan state.
- After the active-plan checkpoint exists, lead controller marks Task 1 `active`, records the next action, and commits that ledger state before Task 1 work begins. Never copy a checkpoint SHA into the plan.
- Without explicit owner approval, do not run Task 1 as coordinated execution, create downstream specifications, revise the vertical-slice plan, or implement production code.

## Task Breakdown

### Task 1: Reconcile specification and contract state

**Purpose:**
- Establish authoritative current state before parent-spec writing or production-plan revision.

**Task Function:**
- Audit specification lifecycle, contract ownership, source/test evidence, stale planning references, and Design Export readiness.

**Template Profile:**
- Controller-selected: `normal`
- Selection basis: bounded repository audit with moderate evidence breadth and no canonical write.

**Validator Profile (optional):**
- Controller-selected: `review`
- Selection basis: independent check of inventory completeness and evidence classification.

**Specification Coverage:**
- Current Project OS spec-plan ownership and lifecycle rules.
- FitCV greenfield frontend authority and no-legacy-reuse boundary.
- Product intent, frozen UX, Design Export, closed integration note, canonical API/source/tests, and focused-spec lifecycle.

**Required Skills:**
- `skill-full-stack-integration`

**Files And Symbols:**
- Inspect: `docs/intent/project-charter.md`, `docs/intent/success-outcomes.md`, `docs/intent/constraints-and-non-goals.md`.
- Inspect: `docs/fitcv-settings-ui-prototype.html`, `design/fitcv-settings-ux-audit/fitcv-design-system-export.md`, `docs/fitcv-new-frontend.integration.md`, `docs/api.md`.
- Inspect: `docs/superpowers/specs/2026-08-01-19-49-fitcv-managed-scan-lifecycle-spec.md`, `docs/superpowers/specs/2026-08-01-23-49-canonical-candidate-uniform-evidence-projection-spec.md`, `docs/superpowers/specs/2026-08-29-fitcv-client-transient-notifications-spec.md`, `docs/superpowers/specs/2026-08-29-fitcv-core-personalization-json-spec.md`, `docs/superpowers/specs/2026-08-29-fitcv-cv-preview-transport-spec.md`, `docs/superpowers/specs/2026-08-29-fitcv-local-readiness-profile-authority-spec.md`, and `docs/superpowers/specs/README.md`.
- Inspect: `docs/superpowers/plans/2026-08-29-fitcv-new-frontend-vertical-slice-plan.md`.
- Inspect: `src/fitcv_cp/app.py::create_app`, `src/fitcv_cp/local_routes.py::local_readiness_status`, `src/fitcv_cp/sqlite_store.py`, `src/fitcv_cp/main.py::build_app`, `src/fitcv_cp/local_app.py::main`, `packaging/windows/fitcv-local.spec`, `scripts/build_fitcv_local.ps1`, `tests/test_fitcv_cp/test_app.py`, `tests/test_fitcv_cp/test_local_routes.py`, `tests/test_fitcv_cp/test_sqlite_store.py`, `tests/test_fitcv_cp/test_scan_contracts.py`, `tests/test_fitcv_cp/test_run_lifecycle.py`, `tests/test_fitcv_cp/test_run_detail_output_availability.py`, `tests/test_fitcv_cp/test_synonym_global_policy_io.py`, `tests/test_fitcv_cp/test_synonym_promote_preview_field_aware.py`, `tests/test_fitcv_cp/test_synonym_promote_commit_field_aware.py`, and current planning validators.
- Modify: none; return findings to lead controller, which owns coordination-state updates.
- Verify: repository status, source/test references, specification frontmatter, stale-owner references, and Design Export gate identity/review state.

**Dependencies:**
- Meta-plan owner approval and current repository truth.
- No product-design choice may be introduced during audit.

**Authority:**
- Preauthorized local actions: read declared files, search source/tests, inspect Git history and status, run read-only validators, and report evidence.
- Stop for: missing canonical input, contradictory approved UX/design evidence, unresolved behavior, unresolved Design Export gate that affects durable frontend decisions, or any requested production-code change.

**Steps:**
- [x] Inventory every current specification, record status, accepted outcome, verification evidence, frontend relevance, and consuming vertical-slice task.
- [x] Confirm backend corrections directly verified for `G-02`, `G-03`, and `G-04`; distinguish backend proof from missing frontend proof.
- [x] Identify stale roadmap/workstream references, including absent `docs/intent/master-workstream-roadmap.md`; mark them historical or replacement-required without treating them as current authority.
- [x] Classify Design Export `EX-01`, `EX-05`, `EX-06`, `EX-07`, `EX-08`, `EX-09`, and `EX-12` gate state, durable identity, independent-review binding, and owner decision needs.
- [x] Define the smallest cross-cutting contract missing from current specifications and pass exact scope to Task 2.
- [x] Recommend no focused-spec status transition unless complete contract implementation and verification prove it; any needed transition requires a bounded plan revision before writing.

**Verification:**
- [x] `git status --short --branch`; Expected: approved-plan execution starts only from declared branch/base with unrelated changes preserved.
- [x] `Test-Path docs/intent/master-workstream-roadmap.md`; Expected: `False`; missing retired artifact is not required for execution.
- [x] `python scripts/validate_planning_lifecycle.py --repo-root .`; Expected: existing artifacts validate or any pre-existing finding is recorded without unrelated edits.

**Exit Criteria:**
- Evidence-backed inventory, status recommendations, Design Export gate assessment, and parent-spec scope are returned; no audit artifact is created.

### Task 2: Draft the FitCV New Frontend Production draft specification

**Purpose:**
- Create one implementation-independent proposed draft for the greenfield production frontend.

**Task Function:**
- Draft the canonical proposed specification from approved intent, frozen UX, Design Export evidence, focused specifications, and canonical backend contracts.

**Template Profile:**
- Controller-selected: `xhigh`
- Selection basis: cross-cutting architecture, ownership, security, accessibility, and unresolved-scope risk.

**Validator Profile (optional):**
- Controller-selected: `review`
- Selection basis: independent draft-template and boundary check before formal review.

**Specification Coverage:**
- Product intent and completion-critical Personal FitCV journeys.
- Frozen UX structure and interaction reference; project-owned design-system token authority.
- Canonical backend lifecycle, evidence, revision, capability, error, CSRF, ETag/CAS, idempotency, preview/download, and retry truth.
- Client-owned view, route/hash, unsaved-edit, selection, polling, and session-transient state only.
- Security, accessibility, responsive, legacy coexistence, packaging boundary, and verification intent.

**Required Skills:**
- `skill-spec-drafting`
- `skill-full-stack-integration`

**Files And Symbols:**
- Inspect: Task 1 evidence set and `docs/operating_system/templates/draft-specification-template.md`.
- Modify: `docs/superpowers/specs/2026-08-30-fitcv-new-frontend-production-spec.md`.
- Verify: same file, `scripts/validate_template_required_sections.py`, and `scripts/validate_planning_lifecycle.py`.

**Dependencies:**
- Task 1 complete.
- Parent specification remains `status: proposed` and `template_id: draft-specification`.

**Authority:**
- Preauthorized local actions: create one proposed draft specification and run document validators.
- Stop for: unresolved behavior/design that prevents a bounded draft, contradictory focused specification, or implementation sequencing in the specification. Record incomplete Design Export evidence as an explicit promotion blocker for Task 4 rather than silently treating it as approved.

**Steps:**
- [x] Create the declared file with `artifact_type: spec`, `template_id: draft-specification`, `status: proposed`, and `layer: change`.
- [x] Record goal/scope, user flow/business rules, UI intent/known states, verified facts, assumptions/open questions, prototype findings, Design Export gate state, and promotion readiness.
- [x] Define greenfield authority, runtime/build/hosting boundary, `/app` entry and deep-link behavior, same-origin delivery, FitCV Local packaging boundary, and legacy `/admin/*` compatibility without file-by-file implementation order.
- [x] Define backend-versus-client truth ownership, API error/CSRF/ETag-CAS/idempotency/download-preview/retry behavior, secret handling, safe rendering, accessibility, responsive behavior, reduced motion, and focus lifecycle.
- [x] Reference focused specifications without copying contracts; unresolved decisions remain explicit open questions and block promotion when they change behavior or durable design.

**Verification:**
- [x] `python scripts/validate_template_required_sections.py --repo-root . --require-template-selection`; Expected: proposed draft satisfies current draft template.
- [x] `python scripts/validate_planning_lifecycle.py --repo-root .`; Expected: proposed specification lifecycle and references validate.
- [x] `rg -n "TODO|TBD|placeholder|parent_specs|workstream-|master-workstream-roadmap" docs/superpowers/specs/2026-08-30-fitcv-new-frontend-production-spec.md`; Expected: no unresolved placeholder or retired planning authority; known keyword matches are absent from spec body.

**Exit Criteria:**
- One proposed draft exists, is validator-clean, references focused owners, records any incomplete Design Export gate explicitly, and contains no hidden implementation plan or unresolved behavior treated as approved.

### Task 3: Independently review the parent draft specification

**Purpose:**
- Prove the proposed draft is internally consistent and safe for product-owner approval.

**Task Function:**
- Perform read-only specification review against current repository evidence and Project OS boundaries.

**Template Profile:**
- Controller-selected: `review`
- Selection basis: independent contract, SSOT, security, accessibility, Design Export, and lifecycle review.

**Validator Profile (optional):**
- Controller-selected: `none`
- Selection basis: reviewer is the independent validator for this task.

**Specification Coverage:**
- Draft scope, known states, ownership boundaries, assumptions/open questions, prototype/Design Export evidence, focused-spec references, and promotion readiness.

**Required Skills:**
- `skill-plan-document-reviewer`

**Files And Symbols:**
- Inspect: `docs/superpowers/specs/2026-08-30-fitcv-new-frontend-production-spec.md`, all Task 1 canonical inputs, and `docs/operating_system/templates/draft-specification-template.md`.
- Modify: none; reviewer is read-only.
- Verify: exact path/line evidence, validator output, Design Export gate state, and contract-owner consistency.

**Dependencies:**
- Task 2 complete.

**Authority:**
- Preauthorized local actions: read-only inspection and bounded validation commands that create no tracked artifacts.
- Stop for: missing input, inability to verify a material claim, or request to silently edit the draft.

**Steps:**
- [x] Review SSOT/double ownership, contradiction with focused specifications, unresolved behavior, architecture ambiguity, accidental implementation detail, missing security/accessibility/compatibility boundaries, stale references, Design Export evidence, and parent-spec scope.
- [x] Return exactly one verdict: `SPEC READY FOR OWNER APPROVAL`, `SPEC REQUIRES FIXES`, or `BLOCKED`, with P1/P2/P3 findings and exact path/line evidence.
- [x] If fixes are required, return bounded findings to Task 2; writer revises same file and this review repeats.

**Verification:**
- [x] Reviewer report contains one allowed verdict and no repository modifications.
- [x] `git diff --check`; Expected: no whitespace errors in reviewed planning/specification changes.

**Exit Criteria:**
- Independent reviewer returns `SPEC READY FOR OWNER APPROVAL`, or the plan stops at exact blocker/fix loop.

### OWNER APPROVAL GATE — parent specification

- Stop after Task 3 passes.
- Product owner explicitly approved `docs/superpowers/specs/2026-08-30-fitcv-new-frontend-production-spec.md` on 2026-08-30, resolved `EX-01` and `EX-12`, and authorized continuation to Task 4; same-file promotion and approval evidence are checkpointed in `9a83da1d32a2c49d90e46a39ec5de99fa0e8b229`. Final production-plan approval remains separate.
- Reviewer readiness is not approval.
- Approval evidence is recorded before Task 4 in `9a83da1d32a2c49d90e46a39ec5de99fa0e8b229`; no production plan edit occurs before promotion.


### Task 4: Verify Design Export gate and owner decisions

**Purpose:**
- Establish complete, identity-bound Design Export evidence before promoting the parent draft to an active detailed specification.

**Task Function:**
- Reconcile Design Export source, output identity, independent review, and owner decisions without inventing visual behavior.

**Template Profile:**
- Controller-selected: `xhigh`
- Selection basis: high-risk visual authority, unresolved design decisions, evidence identity, and lifecycle-gate validation.

**Validator Profile (optional):**
- Controller-selected: `review`
- Selection basis: independent check that export evidence and owner decisions bind to the same source/output identity.

**Specification Coverage:**
- Frozen UX reference, project-owned design-system authority, Design Export lifecycle, and all behavior-changing visual decisions needed by the parent specification.

**Required Skills:**
- `skill-plan-document-reviewer`

**Files And Symbols:**
- Inspect: `design/fitcv-settings-ux-audit/fitcv-design-system-export.md`, `design/fitcv-settings-ux-audit/fitcv-design-system-export.md.artifact.json`, `design/fitcv-settings-ux-audit/fitcv-design-system-audit.md`, `docs/fitcv-settings-ui-prototype.html`, and Task 1 evidence.
- Modify: none; any owner decision or evidence update outside these declared plan targets stops for bounded plan revision and explicit approval.
- Verify: selected export method, exact source/output identity, independent PASS bound to that identity, and resolved `EX-01`/`EX-12` state.

**Dependencies:**
- Task 3 returned `SPEC READY FOR OWNER APPROVAL`.
- Product owner approved the draft and resolved behavior-changing Design Export decisions.

**Authority:**
- Preauthorized local actions: inspect export metadata and evidence, return exact identity and review references to the lead, and run read-only validators; the lead alone records accepted proof in this plan's task ledger.
- Stop for: missing independent PASS, unresolved `EX-01` or `EX-12`, incomplete export identity, request to invent palette/inspectability behavior, or request to modify design evidence without a bounded approved change.

**Steps:**
- [x] Confirm current export identity: source `fitcv-settings-ui-prototype.html`, output `fitcv-design-system-export.md`, metadata task `final-design-export-curation`, and matching artifact metadata.
- [x] Require an independent PASS bound to the same source/output identity; an unrelated review or export `status: complete` field is insufficient.
- [x] Require current owner resolution for `EX-01` palette alignment and `EX-12` inspectability; future non-behavior deferrals may remain only with explicit owner, rationale, trigger, and approval reference.
- [x] If existing evidence cannot satisfy these checks, stop with exact blocker; do not promote the parent specification or create a substitute design-system SSOT.
- [x] Return accepted evidence and gate result to the lead; only the lead records proof in this plan's Coordination State and commits the ledger transition.

**Verification:**
- [x] `Get-Content -Raw design/fitcv-settings-ux-audit/fitcv-design-system-export.md.artifact.json`; Expected: output identity, source identity, task identity, and status are present.
- [x] `rg -n "EX-01|EX-12|REQUIRES_REVIEW|independent review|PASS" design/fitcv-settings-ux-audit/fitcv-design-system-export.md`; Expected: owner decisions are recorded in parent spec; export evidence remains unchanged and historical `REQUIRES_REVIEW` labels are not treated as unresolved current authority.
- [x] Independent review evidence names same source and output identities; Expected: identity match, not merely generic approval.

**Exit Criteria:**
- Design Export gate is complete and identity-bound, or execution is blocked with exact unresolved evidence/owner decision.

### Task 5: Promote the approved parent specification in place

**Purpose:**
- Convert approved draft into active canonical parent specification without creating a parallel specification.

**Task Function:**
- Perform same-file lifecycle promotion and preserve accepted evidence, approved deferrals, and ownership boundaries.

**Template Profile:**
- Controller-selected: `xhigh`
- Selection basis: lifecycle-sensitive semantic rewrite with Design Export and cross-boundary contract risk.

**Validator Profile (optional):**
- Controller-selected: `review`
- Selection basis: independent promotion and detailed-template validation.

**Specification Coverage:**
- Approved draft outcome, explicit owner decisions, complete Design Export gate, focused-spec ownership, and detailed-spec lifecycle rules.

**Required Skills:**
- `skill-spec-drafting`

**Files And Symbols:**
- Inspect: `docs/superpowers/specs/2026-08-30-fitcv-new-frontend-production-spec.md`, `docs/operating_system/templates/draft-specification-template.md`, and `docs/operating_system/templates/detailed-specification-template.md`.
- Modify: `docs/superpowers/specs/2026-08-30-fitcv-new-frontend-production-spec.md` only; lead separately updates this plan's coordination ledger.
- Verify: same file, planning validators, owner approval evidence, and preserved prototype/Design Export evidence.

**Dependencies:**
- Task 4 completed with identity-bound Design Export evidence.
- Product owner approved the draft.

**Authority:**
- Preauthorized local actions: replace draft content in same file with detailed specification content, set `template_id: detailed-specification`, set `status: active`, preserve evidence, and run validators.
- Stop for: missing approval, incomplete Design Export gate, unresolved behavior-changing question, completed/superseded focused-spec edit request, or request to create a second parent specification.

**Steps:**
- [x] Replace draft headings with detailed-specification headings while preserving verified facts, accepted behavior, rejected alternatives, prototype approval, Design Export evidence, and approved deferrals.
- [x] Ensure active specification owns behavior, interfaces, design decisions, invariants, acceptance criteria, and validation intent; keep file order, execution waves, commands, and CoS topology out.
- [x] Set `status: active` and verify exactly one canonical parent specification exists for this frontend outcome.

**Verification:**
- [x] `python scripts/validate_template_required_sections.py --repo-root . --require-template-selection`; Expected: active detailed specification satisfies required sections.
- [x] `python scripts/validate_planning_lifecycle.py --repo-root .`; Expected: active specification lifecycle validates.
- [x] `rg -n "TODO|TBD|placeholder|parent_specs|workstream-|master-workstream-roadmap" docs/superpowers/specs/2026-08-30-fitcv-new-frontend-production-spec.md`; Expected: no unresolved placeholder, plural parent linkage, or retired planning authority.

**Exit Criteria:**
- Same parent-spec file is active, detailed-template compliant, owner-approved, evidence-preserving, and ready to own downstream plan decisions.

### Task 6: Reconcile the existing vertical-slice plan and closed integration note

**Purpose:**
- Align existing production planning and reconciliation evidence with active parent specification and current Project OS plan contract.

**Task Function:**
- Revise existing plan in place and correct stale status, stop-point, and ownership statements in closed integration note.

**Template Profile:**
- Controller-selected: `xhigh`
- Selection basis: multi-slice dependency, shared-write, execution-base, generated-surface, and verification reconciliation.

**Validator Profile (optional):**
- Controller-selected: `review`
- Selection basis: independent plan-contract and integration-note ownership check.

**Specification Coverage:**
- Active parent specification at `docs/superpowers/specs/2026-08-30-fitcv-new-frontend-production-spec.md`.
- Focused specifications for Managed Scan, Candidate Profile evidence, transient notifications, personalization JSON, CV preview transport, and local readiness/profile authority.
- Product intent, closed frontend/backend reconciliation evidence, canonical API/source/tests, and current package/host boundaries.

**Required Skills:**
- `skill-writing-plans`
- `skill-full-stack-integration`
- `skill-verification-before-completion`

**Files And Symbols:**
- Inspect: `docs/superpowers/specs/2026-08-30-fitcv-new-frontend-production-spec.md`, `docs/superpowers/specs/README.md`, `docs/superpowers/specs/2026-08-01-19-49-fitcv-managed-scan-lifecycle-spec.md`, `docs/superpowers/specs/2026-08-01-23-49-canonical-candidate-uniform-evidence-projection-spec.md`, `docs/superpowers/specs/2026-08-29-fitcv-client-transient-notifications-spec.md`, `docs/superpowers/specs/2026-08-29-fitcv-core-personalization-json-spec.md`, `docs/superpowers/specs/2026-08-29-fitcv-cv-preview-transport-spec.md`, `docs/superpowers/specs/2026-08-29-fitcv-local-readiness-profile-authority-spec.md`, `docs/superpowers/plans/2026-08-29-fitcv-new-frontend-vertical-slice-plan.md`, `docs/fitcv-new-frontend.integration.md`, `docs/api.md`, `src/fitcv_cp/app.py`, `src/fitcv_cp/local_routes.py`, `src/fitcv_cp/main.py`, `src/fitcv_cp/local_app.py`, `packaging/windows/fitcv-local.spec`, `scripts/build_fitcv_local.ps1`, `tests/test_fitcv_cp/test_app.py`, `tests/test_fitcv_cp/test_local_routes.py`, `tests/test_fitcv_cp/test_sqlite_store.py`, `tests/test_fitcv_cp/test_scan_contracts.py`, `tests/test_fitcv_cp/test_run_lifecycle.py`, `tests/test_fitcv_cp/test_run_detail_output_availability.py`, `tests/test_fitcv_cp/test_synonym_global_policy_io.py`, `tests/test_fitcv_cp/test_synonym_promote_preview_field_aware.py`, and `tests/test_fitcv_cp/test_synonym_promote_commit_field_aware.py`.
- Modify: `docs/superpowers/plans/2026-08-29-fitcv-new-frontend-vertical-slice-plan.md`, `docs/fitcv-new-frontend.integration.md`, and `docs/superpowers/specs/README.md` only.
- Verify: modified documents, parent linkage, task ledger, coverage matrix, exact paths/symbols, dependencies, commands, and final proof sections.

**Dependencies:**
- Task 5 complete with active parent specification.
- No concurrent writer may edit either target.

**Authority:**
- Preauthorized local actions: revise existing plan in place, update stale status, stop-point, and ownership wording in closed integration note, remove retired normative ownership, update parent linkage and coordination metadata, and run planning validators.
- Stop for: material implementation-outcome change, new product behavior, unresolved parent-spec contradiction, base mismatch, shared-write ambiguity, or request to create a `v2` plan.

**Steps:**
- [x] Set exactly `parent_spec: docs/superpowers/specs/2026-08-30-fitcv-new-frontend-production-spec.md`; never add `parent_specs`.
- [x] Replace current Product/workstream coverage matrix with product/specification coverage mapping success outcomes, parent-spec requirements, focused specs, canonical contracts, vertical slices, and representative proof.
- [x] Remove active dependence on retired roadmap/workstream artifacts from production plan; retain identifiers only when clearly historical and non-normative.
- [x] Correct `docs/fitcv-new-frontend.integration.md` status, stop-point, and ownership wording; mark the August 29, 2026 reconciliation note historical where needed, make current intent plus active parent specification authoritative, preserve closed reconciliation evidence, and define deletion only after its mapping is absorbed and no active consumer remains.
- [x] Move durable architecture, hosting, routing, state ownership, security, accessibility, and legacy-coexistence decisions into parent specification; retain exact implementation mechanisms in plan.
- [x] Preserve valid vertical slicing: frontend work, required backend delta only, integration, focused verification, and slice acceptance; change topology only when approved spec or repository truth proves dependency or boundary wrong.
- [x] Reconcile every production-plan task's Specification Coverage, exact files/symbols, dependencies, disjoint ownership, executor/profile, required skills, local verification, slice acceptance, generated-surface order, and escalation boundaries.
- [x] Record production-plan execution-base candidate ancestry only; after Task 6 changes are checkpointed, Task 7 reviews ancestry, and later production activation captures exact clean pre-activation HEAD after final owner approval rather than using a self-referential SHA.
- [x] Keep production plan `status: proposed` until Task 7 passes and final owner approval is received; do not activate it or execute production tasks.

**Verification:**
- [x] `python scripts/validate_template_required_sections.py --repo-root . --require-template-selection`; Expected: parent specification and production plan satisfy current templates.
- [x] `python scripts/validate_planning_lifecycle.py --repo-root .`; Expected: singular parent linkage, Git-tracked coordination schema, task ledger, and lifecycle state validate.
- [x] `rg -n "parent_specs|Product/workstream|master-workstream-roadmap|workstream-" docs/superpowers/plans/2026-08-29-fitcv-new-frontend-vertical-slice-plan.md docs/fitcv-new-frontend.integration.md`; Expected: no active retired ownership or plural parent linkage; historical references are explicitly non-normative.
- [x] `git diff --check`; Expected: no whitespace errors.

**Exit Criteria:**
- Existing vertical-slice plan is reconciled in place, integration evidence has no dead normative owner, parent linkage is singular and active, and production plan remains inactive pending independent review and owner approval.

### Task 7: Independently review the reconciled production plan

**Purpose:**
- Prove reconciled production plan is implementation-ready without starting production execution.

**Task Function:**
- Perform independent plan-readiness review against active parent specification, focused specifications, current source, tests, and Project OS coordination rules.

**Template Profile:**
- Controller-selected: `review`
- Selection basis: independent plan-contract, ownership, dependency, concurrency, and proof review.

**Validator Profile (optional):**
- Controller-selected: `none`
- Selection basis: reviewer is independent validator for this task.

**Specification Coverage:**
- Exact parent-spec coverage, complete vertical-slice coverage, current contract ownership, execution topology, shared-write controls, task-local verification, final frontend/API/E2E proof, and legacy retirement gate.

**Required Skills:**
- `skill-plan-document-reviewer`

**Files And Symbols:**
- Inspect: `docs/superpowers/plans/2026-08-29-fitcv-new-frontend-vertical-slice-plan.md`, `docs/superpowers/specs/2026-08-30-fitcv-new-frontend-production-spec.md`, `docs/superpowers/specs/2026-08-01-19-49-fitcv-managed-scan-lifecycle-spec.md`, `docs/superpowers/specs/2026-08-01-23-49-canonical-candidate-uniform-evidence-projection-spec.md`, `docs/superpowers/specs/2026-08-29-fitcv-client-transient-notifications-spec.md`, `docs/superpowers/specs/2026-08-29-fitcv-core-personalization-json-spec.md`, `docs/superpowers/specs/2026-08-29-fitcv-cv-preview-transport-spec.md`, `docs/superpowers/specs/2026-08-29-fitcv-local-readiness-profile-authority-spec.md`, `docs/fitcv-new-frontend.integration.md`, `docs/api.md`, `src/fitcv_cp/app.py`, `src/fitcv_cp/local_routes.py`, `src/fitcv_cp/main.py`, `src/fitcv_cp/local_app.py`, `packaging/windows/fitcv-local.spec`, `scripts/build_fitcv_local.ps1`, `tests/test_fitcv_cp/test_app.py`, `tests/test_fitcv_cp/test_local_routes.py`, `tests/test_fitcv_cp/test_sqlite_store.py`, `tests/test_fitcv_cp/test_scan_contracts.py`, `tests/test_fitcv_cp/test_run_lifecycle.py`, `tests/test_fitcv_cp/test_run_detail_output_availability.py`, `tests/test_fitcv_cp/test_synonym_global_policy_io.py`, `tests/test_fitcv_cp/test_synonym_promote_preview_field_aware.py`, and `tests/test_fitcv_cp/test_synonym_promote_commit_field_aware.py`.
- Modify: none; reviewer is read-only.
- Verify: exact path/line evidence, validator output, execution-base/workspace binding, and no-production-code boundary.

**Dependencies:**
- Task 6 complete with reconciled plan and integration note.

**Authority:**
- Preauthorized local actions: read-only review and bounded validators.
- Stop for: any task requiring invented product behavior, unresolved plan/spec conflict, unsafe shared write, stale base, missing proof command, or unverified generated-surface ownership.

**Steps:**
- [ ] Review exact parent-spec coverage, complete vertical-slice coverage, stale ownership removal, exact files/symbols, dependencies, shared writes, waves, downstream CoS suitability, backend-delta assumptions, task-local proof, slice acceptance, final proof, legacy retirement gate, Git binding, generated surfaces, authority boundaries, and activation-time production-base ancestry.
- [ ] Return exactly one verdict: `IMPLEMENTATION-READY`, `REQUIRED FIXES`, or `BLOCKED`, with P1/P2/P3 findings and exact evidence.
- [ ] If fixes are required, return to Task 6 for bounded reconciliation and repeat review; do not implement production code.

**Verification:**
- [ ] Reviewer report contains one allowed verdict and no repository modifications.
- [ ] `python scripts/validate_template_required_sections.py --repo-root . --require-template-selection`; Expected: validation passes after reconciliation.
- [ ] `python scripts/validate_planning_lifecycle.py --repo-root .`; Expected: validation passes after reconciliation.

**Exit Criteria:**
- Independent reviewer returns `IMPLEMENTATION-READY`, or execution stops at exact required fix or blocker.

### FINAL OWNER APPROVAL GATE — production execution

- Stop after Task 7 returns `IMPLEMENTATION-READY`.
- Return exact approved-candidate artifacts and summarize parent specification identity/status, focused-spec statuses, reconciled production-plan identity/status, execution-base candidate, remaining owner decisions, review verdicts, and whether production CoS execution is authorized.
- Do not activate production vertical-slice plan.
- Do not execute frontend or backend production code.
- Product owner approval remains required before production implementation.

## Verification

- [ ] `python scripts/validate_template_required_sections.py --repo-root . --require-template-selection`; Expected: template validation passes.
- [ ] `python scripts/validate_planning_lifecycle.py --repo-root .`; Expected: lifecycle and coordination validation pass.
- [ ] `python -m pytest tests/test_validate_template_required_sections.py tests/test_validate_planning_lifecycle.py`; Expected: planning validator tests pass.
- [ ] `git diff --check`; Expected: no whitespace errors in tracked changes.
- [ ] `Test-Path docs/intent/master-workstream-roadmap.md`; Expected: `False`; no retired roadmap is required.
- [ ] `$allowed = @('docs/superpowers/plans/2026-08-30-fitcv-new-frontend-spec-plan-reconciliation-plan.md','docs/superpowers/plans/2026-08-29-fitcv-new-frontend-vertical-slice-plan.md','docs/superpowers/specs/2026-08-30-fitcv-new-frontend-production-spec.md','docs/superpowers/specs/README.md','docs/fitcv-new-frontend.integration.md'); $changed = @((git diff --name-only --cached) + (git diff --name-only) + (git ls-files --others --exclude-standard) | Where-Object { $_ } | Sort-Object -Unique); $unexpected = @($changed | Where-Object { $_ -notin $allowed }); if ($unexpected.Count -gt 0) { throw 'Unexpected current-workspace paths' }; $untracked = @(git ls-files --others --exclude-standard); $badWhitespace = @($untracked | ForEach-Object { if (Test-Path -LiteralPath $_ -PathType Leaf) { $line = 0; Get-Content -LiteralPath $_ | ForEach-Object { $line++; if ($_ -match '[ \t]+$') { "$($_):$line" } } } }); if ($badWhitespace.Count -gt 0) { throw 'Whitespace in untracked files' }`; Expected: current workspace delta contains only declared planning/integration documents; unrelated pre-existing changes remain preserved; no production path changes; untracked files contain no trailing whitespace.
- [ ] `Test-Path docs/superpowers/specs/2026-08-30-fitcv-new-frontend-production-spec.md`; Expected `False` before Task 2, `True` after Task 2; same file remains through Task 5 promotion.
- [ ] `Test-Path docs/superpowers/plans/2026-08-29-fitcv-new-frontend-vertical-slice-plan.md` and `Test-Path docs/fitcv-new-frontend.integration.md`; Expected: both `True` before and after reconciliation, unless separately authorized sidecar cleanup occurs after evidence migration.
- [ ] `rg -n "parent_specs|Product/workstream|master-workstream-roadmap|workstream-" docs/superpowers/plans/2026-08-29-fitcv-new-frontend-vertical-slice-plan.md docs/fitcv-new-frontend.integration.md`; Expected: no active retired ownership or plural parent linkage; historical references are explicitly non-normative.
- [ ] Independent meta-plan review by one `xhigh` profile and one `review` profile; Expected: both return `IMPLEMENTATION-READY` with no unresolved P1/P2 approval blockers before meta-plan owner approval. Review reports may use task-specific verdicts; they do not satisfy owner approval.

No frontend build, backend mutation, browser implementation, package build, migration, or production E2E execution belongs to this meta-plan.

## Completion Criteria

This meta-plan is ready for completion verification only when:

1. relevant specification state is reconciled
2. one approved FitCV New Frontend Production specification exists
3. focused specifications have correct lifecycle status and remain non-duplicated
4. independent spec review passed
5. product owner approved the new parent specification
6. existing proposed vertical-slice plan was reconciled in place
7. the production plan has exactly one correct `parent_spec`
8. retired roadmap/workstream planning ownership has been removed from normative planning and reconciliation ownership
9. task-level Specification Coverage maps to parent/focused specifications and current contracts
10. durable design decisions live in parent specification rather than implementation plan
11. coordination state and execution-base assumptions match current repository truth
12. independent plan readiness review returned `IMPLEMENTATION-READY`
13. no production implementation was executed
14. final owner approval for production execution remains pending

Execution completion report returns exactly:

`SPEC–PLAN RECONCILIATION COMPLETE — PRODUCTION PLAN READY FOR OWNER APPROVAL`

If any required contract, approval, evidence, or repository state remains unresolved, execution completion report returns exactly:

`SPEC–PLAN RECONCILIATION INCOMPLETE`

with exact blocker. Independent reviewer reports use only their task-specific verdicts and do not use these completion strings. Do not continue into production implementation.
