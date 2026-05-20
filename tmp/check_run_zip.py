import json, zipfile
run = "e8cde832-a950-4d02-ba93-65ac0bafc3cc"
z = zipfile.ZipFile(f"tmp/{run}-artifacts.zip")
names = z.namelist()
print("has_run_json", f"fitcv-run-{run}/run.json" in names)
p = f"fitcv-run-{run}/run.json"
if p in names:
    data = json.loads(z.read(p))
    eff = data.get("effective_settings_json")
    print("has_effective_settings_json", bool(eff))
    if eff:
        cfg = json.loads(eff)
        sm = cfg.get("synonym_management", {})
        print("synonym_management", {k: sm.get(k) for k in ["apply_to_run_enabled", "promote_global_enabled", "triage_recommendation_reuse_enabled"]})
