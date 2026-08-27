# Project Charter

FitCV exists to turn job data into evidence-backed fit decisions and grounded CV
outputs while preserving deterministic stage semantics, operator control, and
inspectable artifacts.

## Current Product Scope

The current completion target is Personal FitCV for personal use:

- one trusted user on a user-owned Windows computer
- primarily FitCV Local and its local browser UI
- the user's own candidate profile and job-search data
- the repo-owned internal LLM runtime with user-configured provider settings
- explicit human review before external action based on a recommendation or generated CV

This is the current completion target, not a permanent limit on future product
direction. FitCV is not currently targeting a multi-user SaaS, Internet-facing
service, hostile shared-compute environment, or high-availability production
platform.

Product promise:

- make FitCV usable by non-technical Windows users through FitCV Local
- keep one repo-owned internal LLM runtime and one browser control plane
- preserve stage order, checkpoint meaning, and operator-facing run truth
- introduce AI only in bounded seams where it improves quality or efficiency
- keep deterministic validation and acceptance as final gate
- keep data, configuration, credentials, backups, and shutdown under clear user control
- retain Docker and Redis/RQ as developer/server options, not end-user prerequisites

FitCV Local should feel like installed FitCV, not a second product. External
runtime repositories, sibling mounts, dynamic imports, and alternate transports
are outside charter.
