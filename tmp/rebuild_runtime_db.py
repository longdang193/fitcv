import sqlite3, pathlib
src = pathlib.Path('data/fitcv_cp.sqlite3')
dst = pathlib.Path('data/fitcv_cp_runtime.sqlite3')
if dst.exists():
    dst.unlink()
with sqlite3.connect(src) as s, sqlite3.connect(dst) as d:
    d.execute('PRAGMA journal_mode=DELETE;')
    d.execute('''CREATE TABLE IF NOT EXISTS local_pipeline_runs (
        run_id TEXT PRIMARY KEY,
        run_json TEXT NOT NULL,
        created_at TEXT NOT NULL
    )''')
    d.execute('''CREATE TABLE IF NOT EXISTS local_pipeline_run_events (
        run_id TEXT NOT NULL,
        event_id TEXT NOT NULL,
        stage TEXT NOT NULL,
        level TEXT NOT NULL,
        message TEXT NOT NULL,
        payload_json TEXT,
        created_at TEXT NOT NULL
    )''')
    d.execute('''CREATE TABLE IF NOT EXISTS cv_versions (
        version_id TEXT PRIMARY KEY,
        run_id TEXT,
        job_url TEXT,
        fit_classification TEXT,
        generated_at TEXT,
        cv_generation_model TEXT,
        cv_prompt_version TEXT,
        cv_schema_version TEXT,
        cv_structured_json TEXT,
        cv_markdown TEXT
    )''')
    for t in ('local_pipeline_runs','local_pipeline_run_events','cv_versions'):
        try:
            rows = s.execute(f'SELECT * FROM {t}').fetchall()
            if not rows:
                continue
            cols = [r[1] for r in s.execute(f'PRAGMA table_info({t})').fetchall()]
            ph = ','.join(['?']*len(cols))
            d.executemany(f"INSERT INTO {t}({','.join(cols)}) VALUES ({ph})", rows)
            print(t, len(rows))
        except Exception as e:
            print(t, 'skip', e)
    d.commit()
print('created', dst, 'size', dst.stat().st_size)
