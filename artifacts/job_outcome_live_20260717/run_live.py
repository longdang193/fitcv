import json
from pathlib import Path
from fitcv.config import load_config
from fitcv.pipeline import run_pipeline

root = Path(r"C:\Users\HOANG PHI LONG DANG\repos\JOB-PROJECT")
evidence_dir = root / "artifacts" / "job_outcome_live_20260717"
config = load_config(root / ".env.yaml")
config.setdefault("pipeline", {})["vector_search_top_n"] = 1
config["pipeline"]["ai_score_top_n"] = 1
config["pipeline"]["final_top_n"] = 1
config.setdefault("synonym_management", {})["auto_promote_global_enabled"] = False
config["synonym_management"]["promote_global_enabled"] = False
result = run_pipeline(
    evidence_dir / "jobs.json",
    config=config,
    run_id="job-outcome-live-20260717",
)
(evidence_dir / "result.json").write_text(
    json.dumps(result, ensure_ascii=False, indent=2, default=str),
    encoding="utf-8",
)
print(json.dumps({
    "run_id": result.get("run_id"),
    "total_jobs": result.get("total_jobs"),
    "ranked": result.get("ranked"),
    "cvs_generated": result.get("cvs_generated"),
    "outcomes": [row.get("job_outcome") for row in result.get("export_results", [])],
}, ensure_ascii=False, indent=2))