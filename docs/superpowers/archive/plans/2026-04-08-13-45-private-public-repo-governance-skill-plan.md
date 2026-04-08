# Private / Public Repo Governance Skill Plan

## Scope

Create a reusable skill for future projects that teaches agents how to manage:

- a **private internal repo** as the development source of truth
- a **public curated repo** as the product-facing downstream mirror

The skill should help with repo-role decisions, publication boundaries, content classification, and public-release validation.

This plan is for the skill itself, not for implementing the publish workflow in this repository.

## Context

This plan is informed by:

- [2026-04-08-13-05-private-source-public-mirror-repo-governance-spec.md](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/docs/superpowers/archive/specs/2026-04-08-13-05-private-source-public-mirror-repo-governance-spec.md)
- [2026-04-08-13-20-private-source-public-mirror-repo-governance-plan.md](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/docs/superpowers/archive/plans/2026-04-08-13-20-private-source-public-mirror-repo-governance-plan.md)

## Goal

Produce a reusable agent skill that can be dropped into future projects and reliably answer:

- should this project use a private repo plus public mirror?
- what stays private vs public?
- how should publishing work?
- how do we validate that internal-only materials do not leak?

## Invariants

- The skill must be **generic**, not FitCV-specific.
- The skill must focus on **repo governance and publication boundaries**, not runtime/product validation.
- The skill should stay concise and emphasize decision rules over project-specific examples.
- Publication validation should be included only as a **boundary validator** for public release safety.

## Deliverables

1. A new skill folder, likely named:
- `private-public-repo-governance`

2. A concise `SKILL.md` that defines:
- when to use the skill
- repo-role model
- content classification model
- publish workflow guidance
- public-release boundary validation

3. Optional lightweight references:
- `references/publish-policy-template.md`
- `references/public-release-checklist.md`

4. Optional UI metadata:
- `agents/openai.yaml`

## Tasks

1. Define the skill trigger clearly.
- Write a tight description for when the skill should activate.
- Focus on triggers like:
  - private-vs-public repo split
  - curated open-source/public mirror
  - internal repo with downstream publication
  - portfolio/product-facing repo cleanup

2. Define the skill’s core operating model.
- Establish the central rule:
  - private repo = source of truth
  - public repo = curated downstream mirror
- Make clear that the skill recommends against using both repos as equal development sources.

3. Define the reusable content-classification model.
- Include the three buckets:
  - `always_private`
  - `usually_public`
  - `review_before_publish`
- Keep the model general enough for future projects, while still giving strong examples.

4. Add publication-boundary validation guidance.
- Include a validation pass for public publication safety.
- Focus on checks like:
  - internal agent/rule folders
  - planning/spec archives
  - logs/debug artifacts
  - internal process docs
  - private-path references in public docs

5. Keep the skill procedural, not bloated.
- Put only the workflow and decision rules in `SKILL.md`.
- Move templates/checklists into `references/` if they would make the main skill too long.

6. Draft supporting reference files.
- Add a small publish-policy template that future agents can adapt.
- Add a public-release checklist for final review before pushing public changes.

7. Add examples without overfitting.
- Include 2 or 3 compact examples of when to choose:
  - manual curated publish
  - scripted allowlist export
  - private-only development without public publishing yet

8. Add UI metadata if useful.
- If the skill will live in a discoverable skill list, generate `agents/openai.yaml`.
- Keep metadata human-readable and consistent with the trigger conditions.

9. Validate the skill against realistic prompts.
- Test it on prompts such as:
  - “I want a private repo and a clean public repo.”
  - “How should I publish only product-facing content?”
  - “What should stay private in an internal engineering repo?”
- Verify it does not drift into project-specific implementation details.

10. Refine for reuse.
- Tighten wording where the skill feels too tied to this repo.
- Make sure the reusable concepts are portable across future projects.

## Recommended Structure

```text
private-public-repo-governance/
  SKILL.md
  agents/
    openai.yaml
  references/
    publish-policy-template.md
    public-release-checklist.md
```

## Recommended `SKILL.md` Sections

1. `Overview`
2. `When to Use`
3. `Repo Role Model`
4. `Content Classification`
5. `Publication Workflow`
6. `Boundary Validation`
7. `Common Mistakes`

## Risks

- Making the skill too specific to this repository
- Mixing product/runtime validation into repo-governance validation
- Writing too much policy detail into `SKILL.md` instead of references
- Turning the skill into a one-off procedure rather than a reusable guide

## Done When

- A reusable skill exists with a clear trigger and compact workflow.
- The skill teaches the private-source/public-mirror model cleanly.
- The skill includes publication-boundary validation guidance.
- The skill can be used in future projects without FitCV-specific assumptions.

