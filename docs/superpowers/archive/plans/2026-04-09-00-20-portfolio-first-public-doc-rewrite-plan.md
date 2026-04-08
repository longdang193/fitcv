# Portfolio-First Public Doc Rewrite Plan

## Scope

Rewrite the public-facing:

- [README.md](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/README.md)
- [FitCV-pipeline.md](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/docs/FitCV-pipeline.md)

based on:

- [2026-04-09-00-10-portfolio-first-public-doc-rewrite-spec.md](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/docs/superpowers/archive/specs/2026-04-09-00-10-portfolio-first-public-doc-rewrite-spec.md)

Goal:

- make the public docs portfolio-first
- explain who uses the system, what problem it solves, and what engineering value it delivers
- remove obsolete and internal-note-style content

## Doc Alignment

- Feature YAML: none
- Feature history: none
- Feature docs: none
- Cross-cutting docs:
  - [README.md](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/README.md)
  - [FitCV-pipeline.md](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/docs/FitCV-pipeline.md)
  - [fitcv-control-plane-setup.md](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/docs/fitcv-control-plane-setup.md)
- Generated docs:
  - [feature_overview.md](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/docs/generated/feature_overview.md)
  - [stage_overview.md](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/docs/generated/stage_overview.md)

## Invariants

- Public docs must stay truthful to current behavior.
- The rewrite must improve clarity without introducing speculative claims.
- The final docs must stand on their own without relying on internal archived specs or plans.

## Tasks

1. Reframe the README opening.
- Add a clearer product identity.
- State who uses the system.
- State the workflow problem it solves.

2. Rewrite the README around problem and solution.
- Add a concise “Problem” and “Solution” framing.
- Make the value proposition easy to understand quickly.

3. Add a clearer stage summary to the README.
- Name the current major pipeline stages explicitly.
- Keep the stage list concise and externally readable.

4. Add major control-plane features to the README.
- Surface:
  - run triggering
  - inspection
  - settings management
  - lifecycle controls
  - artifact exports

5. Add a short engineering-highlights section to the README.
- Emphasize the strongest system work:
  - reranker short-circuit
  - artifact truth alignment
  - run diagnostics
  - stage-aware execution modes
  - reuse/performance improvements

6. Rewrite `docs/FitCV-pipeline.md` as current-state architecture.
- Remove obsolete frontmatter and notebook-style framing.
- Replace advisory/proposal language with current-state explanation.

7. Reorganize the pipeline doc by delivered stages and safeguards.
- Present:
  - stage order
  - stage responsibilities
  - control-plane interaction
  - validation/safeguards
  - execution modes

8. Add a “major engineering improvements delivered” section to the pipeline doc.
- Highlight:
  - rule-filter/ranking separation
  - reranker short-circuit before expensive CV analysis
  - artifact contract cleanup
  - stage diagnostics and bundle export
  - performance/reuse work

9. Remove obsolete or misleading content.
- Delete internal-note voice and second-person advice.
- Remove sections that read as future proposals rather than current design.

10. Run a public-facing readability pass.
- Check both docs as if read by:
  - a hiring manager reviewing your engineering work
  - an external engineer evaluating the repo
  - a product-minded reader asking what the system does

11. Re-run the public export dry validation.
- Confirm the rewrite still works with:
  - [publish_public_repo.ps1](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/scripts/publish_public_repo.ps1)

## Recommended Order

1. README rewrite
2. Pipeline doc rewrite
3. Public-facing readability pass
4. Export validation

## Risks

- Over-marketing the system and losing technical accuracy
- Keeping too much internal process language
- Leaving obsolete proposal language inside the pipeline doc

## Done When

- `README.md` clearly answers who uses FitCV, what problem it solves, and what the product does.
- `docs/FitCV-pipeline.md` reads like a polished architecture document, not an internal notebook.
- The docs visibly showcase the strongest control-plane, debugging, and optimization work.
- The public export remains clean and coherent after the rewrite.

