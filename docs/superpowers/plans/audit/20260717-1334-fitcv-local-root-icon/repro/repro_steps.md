# Reproduction

1. Complete FitCV Local onboarding so `onboarding.json` has `complete: true`.
2. Launch `dist\fitcv-local\fitcv-local.exe`.
3. Before fix, browser opens loopback `/`; middleware allows completed setup through and FastAPI returns `404 {"detail":"Not Found"}` because no root route exists.
4. Inspect `packaging/windows/fitcv-local.spec` and `packaging/windows/FitCV.iss`; before fix neither config declares `fitcv.ico`.
5. Before the tray fix, open Windows notification overflow; FitCV remains absent while `/healthz` returns `200`.
6. Run a console-enabled frozen build; startup logs `Shell_NotifyIconW failed for FitCV tray` before the server starts.

```powershell
.\dist\fitcv-local\fitcv-local.exe
.\.venv\Scripts\python.exe -m pytest tests/test_fitcv_cp/test_local_routes.py -k local_root_redirects_to -q
.\.venv\Scripts\python.exe -m pytest tests/test_fitcv_cp/test_windows_tray.py -q
```
