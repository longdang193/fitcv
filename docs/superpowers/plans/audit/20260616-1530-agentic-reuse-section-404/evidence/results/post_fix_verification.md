# Post-Fix Verification

- Registered `"agentic-reuse"` in `AGENTIC_SETTINGS_SECTIONS`.
- Added focused tests for:
  - expected agentic section slugs
  - explicit ownership of reuse-section keys
  - successful POST to `/admin/settings/section/agentic-reuse`
  - rendered settings page form action for the reuse section
- Verification results:
  - `python -m pytest tests/test_fitcv_cp/test_settings_schema.py -k "agentic_settings_sections or agentic_settings_section_ownership"` -> passed
  - `python -m pytest tests/test_fitcv_cp/test_app.py -k "agentic_reuse_valid_redirects or late_stage_stage_runtime_controls_in_agentic_section"` -> passed
