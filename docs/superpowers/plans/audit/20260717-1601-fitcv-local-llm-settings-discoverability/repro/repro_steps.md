# Reproduction

1. Complete FitCV Local onboarding.
2. Open `/admin/runs` or `/admin/settings`.
3. Before the fix, inspect navigation; no provider, API, model, or LLM settings link exists.
4. Manually open `/local/onboarding`; the controller form still works but page remains labeled Setup and shows Finish setup.

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_fitcv_cp/test_local_routes.py -k completed_onboarding_remains_available_as_local_settings -q
```

The regression must fail before the fix and pass after the navigation and completed-state template changes.
