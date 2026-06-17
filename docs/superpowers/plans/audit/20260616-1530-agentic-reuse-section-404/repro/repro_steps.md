# Reproduction Steps

## Preconditions

- Current workspace checkout
- Python environment with test dependencies installed

## Source Reproduction

```powershell
rg -n "agentic-reuse|AGENTIC_REUSE_SECTION_KEYS|AGENTIC_SETTINGS_SECTIONS|Unknown section" src/fitcv_cp/app.py src/fitcv_cp/settings_schema.py
```

Expected pre-fix observation:

- UI card posts to `/admin/settings/section/agentic-reuse`
- section-save route raises `Unknown section` for unregistered slugs
- settings schema defines reuse keys but does not register the slug

## Verification

```powershell
python -m pytest tests/test_fitcv_cp/test_settings_schema.py -k "agentic_settings_sections or agentic_settings_section_ownership"
python -m pytest tests/test_fitcv_cp/test_app.py -k "agentic_reuse_valid_redirects or late_stage_stage_runtime_controls_in_agentic_section"
```
