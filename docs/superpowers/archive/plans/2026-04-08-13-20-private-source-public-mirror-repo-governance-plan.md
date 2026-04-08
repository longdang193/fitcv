# Private-Source / Public-Mirror Repo Governance Plan

## Scope

Implement the repository split described in:

- [2026-04-08-13-05-private-source-public-mirror-repo-governance-spec.md](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/docs/superpowers/archive/specs/2026-04-08-13-05-private-source-public-mirror-repo-governance-spec.md)

Primary goal:

- keep the private repo as the full development source of truth
- establish a clean, repeatable publication path into the public repo

## Doc Alignment

- Feature YAML: none
- Feature history: none
- Feature docs: none
- Cross-cutting docs:
  - [README.md](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/README.md)
  - [FitCV-pipeline.md](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/docs/FitCV-pipeline.md)
  - [fitcv-control-plane-setup.md](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/docs/fitcv-control-plane-setup.md)
- Generated docs:
  - [features_index.yaml](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/docs/generated/features_index.yaml)
  - [feature_overview.md](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/docs/generated/feature_overview.md)

## Invariants

- Private repo remains the only place with full internal history and workflow assets.
- Public repo receives only curated product-facing content.
- Publication must be reproducible and reviewable.
- Internal-only assets must never be published by default.

## Tasks

1. Define the public publication contract.
- Create a small source-of-truth policy doc listing:
  - always include
  - always exclude
  - review-before-publish
- Make the exclude list explicit for:
  - `.agents/`
  - `.cursor/`
  - `docs/superpowers/`
  - `logs/`
  - other debug/scratch outputs

2. Add public-repo remote governance docs.
- Document the two remotes and their roles:
  - private origin/internal source
  - public downstream mirror
- Clarify that day-to-day work stays in the private repo only.

3. Create a first publish workflow.
- Add a simple publish script or documented command workflow that:
  - exports only approved content
  - stages it in a temp export directory or publish worktree
  - verifies required public docs exist
  - pushes to the public repo

4. Make the publish workflow allowlist-first.
- Prefer “copy approved paths” over “copy everything then delete bad paths.”
- Keep the script easy to audit and safe against accidental leakage.

5. Reframe the public README for product-facing use.
- Tighten the main narrative around:
  - what the product does
  - architecture at a clean high level
  - setup/usage
  - key capabilities
- Remove internal-process framing from the public version.

6. Review cross-cutting docs for public suitability.
- Keep only docs that help an external reader understand the product.
- Move or exclude docs that are purely internal engineering memory.

7. Decide which generated docs belong in public.
- Keep only generated discovery docs that improve navigation and readability.
- Exclude generated outputs that mostly expose internal operating-system structure.

8. Add a verification checklist for publication.
- Before publishing, verify:
  - no `.agents` or `.cursor` content in export
  - no `docs/superpowers` content in export
  - no logs/debug artifact folders in export
  - public README and docs render coherently on their own

9. Run the first curated publication.
- Create one clean publication run from the private repo into `fitcv-public`.
- Inspect the result manually before treating the workflow as the default path.

10. Document ongoing operating rules.
- Add a short maintenance note covering:
  - where to develop
  - how to publish
  - what must stay private
  - when public docs should be refreshed

## Recommended Order

1. Publication contract
2. Publish workflow
3. Public README/doc cleanup
4. Verification checklist
5. First curated publication

## Risks

- Over-including files in the first public publish
- Keeping too much internal-process language in the public docs
- Letting the public repo become a second development repo by accident

## Done When

- The private repo is explicitly documented as the development source of truth.
- A repeatable publish workflow exists.
- The public repo can be refreshed without manual guesswork.
- Internal-only materials are excluded by default.
- The public repo reads like a clean product-facing repository.

