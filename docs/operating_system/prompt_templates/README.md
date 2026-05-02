# Prompt Templates

Use these prompts when you want to guide an agent through the repo process in
a consistent way.

Lifecycle order:

1. `intent-prompt.md`
2. `master-workstream-roadmap-build-prompt.md`
3. `registered-workstream-set-build-prompt.md`
4. `bounded-change-thread-build-prompt.md`
5. `roadmap-to-workstream-prompt.md`
6. `workstream-to-spec-prompt.md`
7. `thread-set-to-spec-set-prompt.md`
8. `spec-set-to-spec-authoring-map-prompt.md`
9. `spec-prompt.md`
10. `spec-set-execution-map-prompt.md`
11. `plan-prompt.md`
12. `execute-prompt.md`
13. `validate-or-drift-prompt.md`
14. `managed-metadata-update-prompt.md`
15. `mode-migration-prompt.md`
16. `workstream-alignment-review-prompt.md`
17. `roadmap-gap-prompt.md`
18. `roadmap-vs-execution-divergence-prompt.md`
19. `provider-history-sync-prompt.md`
20. `gitnexus-refresh-prompt.md`
21. `parallel-bounded-change-planning-prompt.md`
22. `thread-checkpoint-result-pack-prompt.md`
22. `thread-checkpoint-result-pack-prompt.md`

Use the smallest prompt that matches the step you actually want.

Construction prompts:

- use a master-workstream-roadmap build prompt when intent exists and you need
  the major delivery threads
- use a registered-workstream-set build prompt when the roadmap exists and you
  need the concrete workstream set
- use a bounded-change-thread build prompt when a workstream exists and you
  need execution-capable slices or thread-file-ready outputs

Routing prompts:

- use an intent prompt when the project purpose or direction is still fuzzy
- use a roadmap-to-workstream prompt when you are translating intent or a
  roadmap thread into the right delivery branch
- use a workstream-to-spec prompt when a thread is already chosen and you want
  the next bounded design slice
- use a thread-set-to-spec-set prompt when you already have a thread set and
  want the complete spec inventory before detailed-spec authoring
- use a spec-set-to-spec-authoring-map prompt when the complete spec set exists
  and you need to sequence detailed-spec authoring
- use a spec-set-execution-map prompt when the approved detailed specs exist
  and you need a distinct implementation execution map for ordering, waves, and
  parallelism

Execution prompts:

- use a spec prompt when one chosen detailed spec needs to be written down
- use a plan prompt when the spec is approved and you want execution steps
- use an execution prompt when a plan already exists

Review and upkeep prompts:

- use a validation/drift prompt when you want to find gaps or missing surfaces
- use a managed-metadata update prompt when the repo is already in
  `managed_architecture_metadata` and you want to update or repair managed
  metadata surfaces in place
- use a mode-migration prompt when you want to assess or plan
  `starter_method_only -> managed_architecture_metadata`
- use a workstream-alignment review prompt when you want to sanity-check
  whether a proposed change actually belongs to the named workstream
- use a roadmap-gap prompt when you think the master roadmap may be missing a
  durable thread
- use a roadmap-vs-execution divergence prompt when you want to compare
  upstream roadmap/workstream intent against specs, plans, and execution so far
- use a provider-history sync prompt when Codex chats disappear after switching
  model providers and history metadata needs to be synced with
  `codex-provider-sync`
- use a GitNexus refresh prompt when GitNexus is stale, failing, or clearly out
  of sync with the current repo
- use a parallel bounded-change planning prompt when you already have bounded
  change candidates and want to know what can run in parallel safely
- use a thread-checkpoint result-pack prompt when a bounded change thread needs
  a visible execution-pass checkpoint artifact
- use a thread-checkpoint result-pack prompt when a bounded thread execution
  pass needs a visible, standardized checkpoint artifact

These are guidance files, not required repo artifacts.

The practical ladder is:

`intent -> master roadmap -> registered workstream set -> bounded change thread files -> complete spec set -> spec-authoring map -> detailed specs -> implementation execution map -> implementation plan -> execution passes with thread checkpoint result packs`

with `operating_system` remaining a parallel branch when the work is really
about repo method rather than product delivery.

When the work is product-direction work, name the roadmap thread it follows.
When it is true operating-system work, say why it should remain
`parent_workstream: none`.

When naming a real workstream, use a valid ID from `docs/intent/workstreams/`.
