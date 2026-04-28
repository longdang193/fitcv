# Bounded Change Thread Registry

This folder holds the explicit bounded change thread files that sit between the
registered workstream layer and downstream specs/plans.

Use this subtree when a workstream already exists and you want the next
execution-capable slices to be visible in the worktree.

The planning ladder is:

`master roadmap -> registered workstreams -> bounded change thread files -> specs -> implementation plans -> execution`

Rules:

- create one folder per registered workstream
- keep thread files lightweight and execution-oriented
- use thread files for slices that may later produce specs or plans
- do not turn the master roadmap into a thread tracker
- do not turn thread files into full design docs

Recommended shape:

```text
docs/intent/workstreams/threads/
  README.md
  <workstream-id>/
    01-<thread-slug>.md
    02-<thread-slug>.md
```

Suggested thread frontmatter:

```yaml
---
thread_id: <workstream-id>.<thread-slug>
status: proposed | active | blocked | completed
---
```

Suggested thread body:

- goal
- why now
- dependencies
- shared surfaces
- linked spec
- linked plan
- notes

Thread files should answer:

- what specific slice this is
- why it should move now
- what it depends on
- what it touches
- what downstream artifacts it produced

The parent workstream is derived from the folder path:

- `docs/intent/workstreams/threads/<workstream-id>/`

In this first pass, the thread registry is product-workstream-focused. A
parallel `operating_system` thread branch may be added later if the repo needs
it.
