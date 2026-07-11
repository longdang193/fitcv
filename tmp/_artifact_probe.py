import json, pathlib
rid='5656eb4d-34ec-4445-938d-f49ebadb8e14'
d=json.loads(pathlib.Path(f'tmp/{rid}.stage-artifacts.json').read_text(encoding='utf-8'))
stages=((d.get('artifacts') or {}).get('stages') or {})
for sid in ['ranking','pipeline_complete','cv_analysis']:
    s=stages.get(sid) or {}
    sr=s.get('stage_result') or {}
    ev=sr.get('evidence') or {}
    dec=ev.get('decision_summary') or {}
    print('\nSTAGE',sid)
    print(' decision_summary keys=',list(dec.keys())[:25])
    if sid=='pipeline_complete':
        qm=(dec.get('quality_metrics') or {})
        print(' quality_metrics keys=',list(qm.keys()))
        print(' ranking qm=',(qm.get('ranking') or {}))
