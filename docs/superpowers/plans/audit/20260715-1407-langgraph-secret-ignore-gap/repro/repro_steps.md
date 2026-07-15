# Reproduction

1. In `C:\Users\HOANG PHI LONG DANG\repos\fitcv-langgraph`, run:

```powershell
git status --short -- "fitcv-491123-51c030d71e07.json"
git check-ignore -v -- "fitcv-491123-51c030d71e07.json"
```

2. Before fix, first command reports `??` and second command returns no matching ignore rule.
3. After fix, first command does not report credential-shaped file and second command points to exact `.gitignore` rule.

Determinism: commands inspect filename tracking state only; file content is never read.
