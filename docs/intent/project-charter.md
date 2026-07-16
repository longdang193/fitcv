# Project Charter

FitCV exists to turn job data into evidence-backed fit decisions and grounded CV
outputs while preserving deterministic stage semantics, operator control, and
inspectable artifacts.

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
