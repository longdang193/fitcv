# Project Guidance

This project uses `general-os` as a semantic coordination layer above Git and
the selected native runtime.

Git owns repository state and recovery facts. The native runtime owns
execution, tools, approvals, and subordinate workers. Durable project intent,
task boundaries, dependencies, acceptance criteria, and material authority
exceptions belong in the project's own coordination state when the project
has established them.

Keep project-specific guidance, goals, and decisions in this repository. Do
not persist runtime IDs, heartbeats, temporary plans, worker registries, or
mirrored lifecycle state.
