# Pre-Fix Findings

- Symptom: saving the Agentic Processing reuse card returned `{"detail":"Unknown section: 'agentic-reuse'"}`.
- Source evidence:
  - `src/fitcv_cp/app.py` rejects section names not present in `all_settings_sections`.
  - `src/fitcv_cp/app.py` renders a settings card with `submit_slug="agentic-reuse"`.
  - `src/fitcv_cp/settings_schema.py` defined `AGENTIC_REUSE_SECTION_KEYS` but omitted `"agentic-reuse"` from `AGENTIC_SETTINGS_SECTIONS`.
- Conclusion: this was a static UI/backend registry drift, not a per-setting validation issue.
