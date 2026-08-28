---
template_id: draft-specification
target_globs:
- docs/superpowers/specs/*.md
required_sections:
- Goal and Scope
- User Flow and Business Rules
- UI Intent and Known States
- Assumptions and Open Questions
- Prototype and Validation Findings
- Promotion Readiness
required_frontmatter:
  artifact_type: spec
  status: proposed
  layer: change
distribution_tier: starter_kit
---

# Draft Specification Template

Use while behavior or UI intent still needs prototype validation. Keep one file
and promote it in place to detailed specification after approval and all
applicable post-approval inputs are complete.

## Goal and Scope

- problem or opportunity:
- affected users or systems:
- desired outcome:
- included scope:
- excluded scope:

## User Flow and Business Rules

### User or System Flow

1. <trigger>
2. <expected transition>
3. <observable outcome>

### Business Rules

- <known rule>
- <important failure or constraint>

## UI Intent and Known States

- target platform:
- intended interaction:
- loading, empty, success, error, disabled, and retry states:
- accessibility or responsive intent:
- durable design-system owner:

Use `Not applicable: <reason>` when no UI exists.

## Assumptions and Open Questions

### Verified Facts

- <fact and source>

### Assumptions

- <assumption requiring validation>

### Open Questions

- <question that changes behavior or design>

## Prototype and Validation Findings

- prototype reference or `Not created: <reason>`:
- UX approval: `Not approved` | `<owner-approved revision/reference>`:
- design export reference or `Not required: <reason>`:
- scenario tested:
- observed result:
- accepted behavior:
- rejected behavior:
- remaining uncertainty:
- boundary implication when material: frontend, backend, shared contract, data/state, capability, feasibility, or failure behavior:

Before owner-approved UX freeze, prototypes are exploratory validation evidence.
After owner-approved UX freeze, the recorded prototype may be an immutable
approved UX reference and evidence. It remains neither canonical behavior nor
design-system truth.
Record only material boundary implications. Do not prescribe production
components, implementation mechanisms, or runtime providers here.

## Promotion Readiness

- [ ] important behavior and state transitions are settled
- [ ] material backend boundary, failure, state, dependency, contract, and trace claims are selected
- [ ] UI intent conflicts are resolved
- [ ] applicable post-approval Design Export or reconciliation inputs are complete or explicitly not applicable
- [ ] approved deferrals are explicit
- [ ] user approved promotion

After approval and completion of applicable post-approval inputs, replace this
template content in same file with `detailed-specification`, set `status: active`,
preserve prototype/validation evidence, and run planning and template validators.
