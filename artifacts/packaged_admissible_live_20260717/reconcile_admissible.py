import json
import os
import pathlib
import sqlite3

path = pathlib.Path(os.environ["FITCV_AUDIT_DB"])
run_id = os.environ["FITCV_AUDIT_RUN_ID"]
connection = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
tables = [
    row[0]
    for row in connection.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
    )
]
counts = {}
for table in tables:
    columns = [row[1] for row in connection.execute(f'PRAGMA table_info("{table}")')]
    if "run_id" in columns:
        counts[table] = connection.execute(
            f'SELECT COUNT(*) FROM "{table}" WHERE run_id = ?', (run_id,)
        ).fetchone()[0]
row = connection.execute(
    "SELECT run_json FROM local_pipeline_runs WHERE run_id = ?", (run_id,)
).fetchone()
run = json.loads(row[0]) if row else {}
selected = {
    key: run.get(key)
    for key in (
        "run_id",
        "status",
        "total_jobs",
        "passed_filter",
        "ranked",
        "cvs_generated",
        "error_message",
        "queue_job_id",
        "orchestration_backend",
    )
}
selected["has_cv_generation_debug"] = bool(run.get("cv_generation_debug_json"))
selected["has_results_export"] = bool(run.get("results_export_json"))
payload = {
    "database": str(path),
    "run_id": run_id,
    "integrity_check": connection.execute("PRAGMA integrity_check").fetchone()[0],
    "foreign_key_violations": len(connection.execute("PRAGMA foreign_key_check").fetchall()),
    "pipeline_run": selected,
    "run_scoped_counts": counts,
}
pathlib.Path(os.environ["FITCV_AUDIT_OUT"]).write_text(
    json.dumps(payload, indent=2, default=str) + "\n", encoding="utf-8"
)
