# Project Adoption Migration

Adopt only layers needed by current repository:

1. Preserve product code and tests.
2. Copy root agent instructions and canonical skills.
3. Keep executable repository configuration in `repo_config/` only when an active script consumes it.
4. Add planning artifacts only when complexity requires them.
5. Run `python scripts/validate_repo_contracts.py --fast`.

Code discovery remains source-first. Describe required capability and evidence
before selecting a runtime tool. Resolve unmet capabilities through
`docs/operating_system/tooling/runtime-tool-resolution.md`; unavailable tools
never block safe work and never replace mandatory evidence.

Do not import generated architecture lineage, private tooling state, or
source-only adapter machinery into consume-only repositories.
