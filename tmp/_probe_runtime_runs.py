import sqlite3, json
from pathlib import Path

db = Path(r"runtime/fitcv_cp.sqlite3")
ids = [
  '4d83ef03-4acc-4acd-8ea6-240127a21098',
  '5656eb4d-34ec-4445-938d-f49ebadb8e14',
  '84c1c6a2-4b5f-49d6-991c-b3197e94f1bb',
]

con = sqlite3.connect(str(db))
con.row_factory = sqlite3.Row
cur = con.cursor()

print('DB', db)
tables = [r[0] for r in cur.execute("select name from sqlite_master where type='table' order by name")]
print('tables', len(tables))
print('run tables', [t for t in tables if 'run' in t or 'event' in t])

run_table = 'local_pipeline_runs' if 'local_pipeline_runs' in tables else ('pipeline_runs' if 'pipeline_runs' in tables else None)
event_table = 'local_pipeline_run_events' if 'local_pipeline_run_events' in tables else None
print('using run_table=', run_table, 'event_table=', event_table)

for rid in ids:
    print('\n=== RUN', rid, '===')
    if run_table is None:
        print('no run table')
        continue
    row = cur.execute(f"select * from {run_table} where run_id=?", (rid,)).fetchone()
    print('found', bool(row))
    if not row:
        continue
    print('status', row['status'], 'created', row['created_at'], 'started', row['started_at'], 'completed', row['completed_at'])
    print('counts total/passed/ranked/cv', row['total_jobs'], row['passed_filter'], row['ranked'], row['cvs_generated'])

    summary = json.loads(row['summary_json']) if row['summary_json'] else {}
    ts = summary.get('trace_summary') or {}
    # keep compact subset
    wanted = [k for k in sorted(ts.keys()) if any(x in k.lower() for x in [
        'rank', 'skip', 'strong', 'stretch', 'reuse', 'fresh', 'top_n', 'threshold'
    ])]
    if wanted:
        print('trace_summary keys:')
        for k in wanted:
            print(' ', k, '=', ts[k])

    if event_table:
        evs = list(cur.execute(
            f"select created_at, stage, level, message, payload_json from {event_table} where run_id=? order by created_at",
            (rid,),
        ))
        print('event_count', len(evs))
        for e in evs:
            stage = str(e['stage'] or '')
            if stage not in {'layer3_shortlist', 'layer3_ai_score', 'layer3_ranking', 'layer4_cv_analysis', 'pipeline_complete'}:
                continue
            msg = str(e['message'] or '')
            print(' ', e['created_at'], stage, e['level'], msg)
            payload_raw = e['payload_json']
            if not payload_raw:
                continue
            try:
                p = json.loads(payload_raw)
            except Exception:
                continue
            out = p.get('output_snapshot') or {}
            dec = p.get('decision_summary') or {}
            if stage == 'layer3_ranking':
                ld = dec.get('label_distribution') or {}
                rm = dec.get('reuse_metrics') or {}
                if not rm:
                    # fallback common location
                    rm = (out.get('ranking_decision_summary') or {}).get('reuse_metrics') or {}
                print('    label_distribution=', ld)
                print('    reuse_metrics=', rm)
            elif stage == 'layer3_ai_score':
                print('    output_snapshot=', out)
            elif stage == 'layer3_shortlist':
                print('    output_snapshot=', out)
            elif stage == 'layer4_cv_analysis':
                print('    output_snapshot=', out)
            elif stage == 'pipeline_complete':
                print('    output_snapshot=', out)
