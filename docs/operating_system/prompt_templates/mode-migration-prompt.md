# Mode Migration Prompt

Use this when you want to assess or plan migration from
`starter_method_only` to `managed_architecture_metadata`.

If you are not sure whether this migration belongs to a product workstream or
to `operating_system`, use `roadmap-to-workstream-prompt.md` first.

If the repo is already in `managed_architecture_metadata` and the job is to
update or repair managed surfaces in place, use
`managed-metadata-update-prompt.md` instead.

```text
Assess or plan the migration from starter_method_only to managed_architecture_metadata.

Repo context:
- current repo:
- current adoption mode:
- known missing surfaces:
- known validator warnings:
- migration constraints:
- roadmap thread this migration supports (use a valid ID from `docs/intent/workstreams/`, or `none` if operating_system-only):
- if `none`, why:

Please:
1. assess whether the repo is still healthy in Mode A or has outgrown it
2. say how this migration follows the roadmap or why it is operating_system work
3. identify the missing managed surfaces and migration debt
4. draft a spec or implementation plan for the migration
5. call out risks, sequencing, and validation steps
```

Expected output:
- migration assessment, spec, or plan
