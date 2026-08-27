# Intent Layer

This directory holds the project's stable what-and-why sources.

Use it for:

- the original problem FitCV is solving
- who the upgraded pipeline is for
- what outcomes matter
- what promises should remain true
- what the project deliberately does not try to do

This layer governs by purpose.

It is different from `docs/operating_system/`, which governs by method.

It is also different from `docs/superpowers/specs/` and
`docs/superpowers/plans/`, which are execution-facing artifacts rather than
stable source docs.

## Files

- [project-charter.md](./project-charter.md)
  - core problem, project shape, and enduring promises
- [stakeholders.md](./stakeholders.md)
  - who depends on FitCV and what they need
- [success-outcomes.md](./success-outcomes.md)
  - what good looks like if the project succeeds
- [constraints-and-non-goals.md](./constraints-and-non-goals.md)
  - limits, boundaries, and deliberate exclusions
- [master-workstream-roadmap.md](./master-workstream-roadmap.md)
  - top-down bridge from intent into durable product workstreams and the parallel `operating_system` branch
- [workstream-coverage-and-progress-guide.md](./workstream-coverage-and-progress-guide.md)
  - precise ladder from roadmap to execution, plus coverage/progress/divergence rules
- [workstreams/threads/README.md](./workstreams/threads/README.md)
  - explicit bounded change thread file surface between registered workstreams and downstream specs/plans

## Rules

- keep these docs stable and source-like
- do not turn them into execution logs or release notes
- treat them as source material for later README synthesis
- use `master-workstream-roadmap.md` to translate intent into durable planning threads without replacing upstream intent docs
- use `workstream-coverage-and-progress-guide.md` when you need the precise execution ladder from roadmap coverage into bounded change thread files, specs, plans, and safe parallel work
- treat the charter, constraints, and success outcomes as the authority for the current product completion target
- allow downstream roadmaps, workstreams, specs, and plans to decompose intent, but not enlarge it without an explicit intent update
- do not treat supporting, maintenance, or deferred work as a product-completion blocker unless intent explicitly promotes it
- treat named technologies as implementation choices unless an intent document states their behavior as a durable contract
- if a document is really about how the repo should build, govern, or route work, it belongs in `docs/operating_system/` instead
